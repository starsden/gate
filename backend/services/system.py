"""
System service for Linux VPN Gateway.
Provides hardware metrics, OS info, resource utilization, and systemd service management.
Operates natively with Linux /proc, /sys, and systemctl, with safe fallbacks for local dev/testing.
"""

import os
import platform
import re
import shutil
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional

# Whitelist of manageable services
MANAGED_SERVICES = [
    {
        "name": "xray",
        "unit": "xray.service",
        "title": "Xray Core",
        "description": "VLESS / REALITY proxy daemon",
    },
    {
        "name": "hostapd",
        "unit": "hostapd.service",
        "title": "hostapd",
        "description": "Wi-Fi Access Point daemon",
    },
    {
        "name": "dnsmasq",
        "unit": "dnsmasq.service",
        "title": "dnsmasq",
        "description": "DHCP & DNS server",
    },
    {
        "name": "vpn-gateway",
        "unit": "vpn-gateway.service",
        "title": "VPN Gateway",
        "description": "FastAPI Web Controller",
    },
    {
        "name": "nftables",
        "unit": "nftables.service",
        "title": "nftables",
        "description": "Linux packet filtering & NAT",
    },
]

ALLOWED_SERVICE_NAMES = {s["name"] for s in MANAGED_SERVICES}

# Module-level state for CPU delta calculation
_prev_cpu_stat: Optional[tuple[int, int, float]] = None  # (idle_ticks, total_ticks, timestamp)
_cached_cpu_percent: float = 0.0


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _format_uptime(seconds: float) -> str:
    """Format uptime seconds into human-readable string (e.g., '3d 12h 15m')."""
    total_seconds = int(seconds)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def get_uptime_seconds() -> float:
    """Get system uptime in seconds."""
    if _is_linux():
        try:
            with open("/proc/uptime", "r") as f:
                return float(f.readline().split()[0])
        except Exception:
            pass

    # Fallback for macOS / other POSIX
    try:
        output = subprocess.check_output(["sysctl", "-n", "kern.boottime"], text=True)
        # Output format: { sec = 1716300000, usec = 0 } ...
        match = re.search(r"sec\s*=\s*(\d+)", output)
        if match:
            boot_time = int(match.group(1))
            return max(0.0, time.time() - boot_time)
    except Exception:
        pass

    # Generic fallback
    return 0.0


def get_os_info() -> Dict[str, str]:
    """Retrieve OS distribution, kernel, architecture, and hostname."""
    hostname = socket.gethostname()
    kernel = platform.release()
    arch = platform.machine()
    os_name = "Linux"

    if _is_linux() and os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r") as f:
                lines = f.readlines()
            info = {}
            for line in lines:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    info[k] = v.strip('"\'')
            os_name = info.get("PRETTY_NAME") or info.get("NAME") or "Linux"
        except Exception:
            os_name = "Linux"
    elif platform.system() == "Darwin":
        mac_ver = platform.mac_ver()[0]
        os_name = f"macOS {mac_ver}" if mac_ver else "macOS"

    return {
        "hostname": hostname,
        "os": os_name,
        "kernel": kernel,
        "arch": arch,
    }


def get_cpu_percent() -> float:
    """
    Calculate instantaneous CPU utilization using /proc/stat deltas.
    Non-blocking and zero external dependencies.
    """
    global _prev_cpu_stat, _cached_cpu_percent

    if not _is_linux():
        # macOS dev environment fallback
        try:
            load1, _, _ = os.getloadavg()
            cpu_count = os.cpu_count() or 1
            # Approximate percentage from 1-min load average capped at 100%
            return round(min(100.0, (load1 / cpu_count) * 100.0), 1)
        except Exception:
            return 12.0

    try:
        with open("/proc/stat", "r") as f:
            first_line = f.readline()
        # Format: cpu  user nice system idle iowait irq softirq steal guest guest_nice
        fields = [int(x) for x in first_line.split()[1:]]
        idle_ticks = fields[3] + (fields[4] if len(fields) > 4 else 0)
        total_ticks = sum(fields)
        now = time.time()

        if _prev_cpu_stat is not None:
            prev_idle, prev_total, prev_time = _prev_cpu_stat
            total_delta = total_ticks - prev_total
            idle_delta = idle_ticks - prev_idle

            if total_delta > 0:
                usage = 100.0 * (1.0 - (idle_delta / total_delta))
                _cached_cpu_percent = round(max(0.0, min(100.0, usage)), 1)
                _prev_cpu_stat = (idle_ticks, total_ticks, now)
                return _cached_cpu_percent

        _prev_cpu_stat = (idle_ticks, total_ticks, now)
        return _cached_cpu_percent
    except Exception:
        return _cached_cpu_percent


def get_memory_info() -> Dict[str, Any]:
    """Parse /proc/meminfo to retrieve RAM metrics."""
    if _is_linux() and os.path.exists("/proc/meminfo"):
        try:
            mem_data = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        # Extract integer value (in kB)
                        val_match = re.search(r"\d+", parts[1])
                        if val_match:
                            mem_data[key] = int(val_match.group(0)) * 1024  # to bytes

            total = mem_data.get("MemTotal", 0)
            available = mem_data.get("MemAvailable", 0)
            if available == 0 and "MemFree" in mem_data:
                # Fallback if MemAvailable not present
                available = mem_data.get("MemFree", 0) + mem_data.get("Buffers", 0) + mem_data.get("Cached", 0)

            used = max(0, total - available)
            percent = round((used / total * 100.0), 1) if total > 0 else 0.0

            return {
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "percent": percent,
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
            }
        except Exception:
            pass

    # Real macOS memory calculation via sysctl & vm_stat
    try:
        mem_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        vm_stat_out = subprocess.check_output(["vm_stat"], text=True)
        page_size_match = re.search(r"page size of (\d+) bytes", vm_stat_out)
        page_size = int(page_size_match.group(1)) if page_size_match else 4096
        free_m = re.search(r"Pages free:\s+(\d+)", vm_stat_out)
        inact_m = re.search(r"Pages inactive:\s+(\d+)", vm_stat_out)
        free_pages = int(free_m.group(1)) if free_m else 0
        inactive_pages = int(inact_m.group(1)) if inact_m else 0
        avail_bytes = (free_pages + inactive_pages) * page_size
        used_bytes = max(0, mem_bytes - avail_bytes)
        percent = round((used_bytes / mem_bytes * 100.0), 1) if mem_bytes > 0 else 0.0
        return {
            "total_bytes": mem_bytes,
            "used_bytes": used_bytes,
            "available_bytes": avail_bytes,
            "percent": percent,
            "total_gb": round(mem_bytes / (1024**3), 2),
            "used_gb": round(used_bytes / (1024**3), 2),
        }
    except Exception:
        return {
            "total_bytes": 0,
            "used_bytes": 0,
            "available_bytes": 0,
            "percent": 0.0,
            "total_gb": 0.0,
            "used_gb": 0.0,
        }


def get_disk_info() -> Dict[str, Any]:
    """Retrieve root filesystem disk usage."""
    try:
        total, used, free = shutil.disk_usage("/")
        percent = round((used / total * 100.0), 1) if total > 0 else 0.0
        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "percent": percent,
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
        }
    except Exception:
        return {
            "total_bytes": 32 * (1024**3),
            "used_bytes": 10 * (1024**3),
            "free_bytes": 22 * (1024**3),
            "percent": 31.0,
            "total_gb": 32.0,
            "used_gb": 10.0,
            "free_gb": 22.0,
        }


def get_temperature_c() -> Optional[float]:
    """Read CPU temperature from sysfs thermal zones or hwmon."""
    if not _is_linux():
        return 46.0 if os.environ.get("ENABLE_MOCKS") == "1" else None

    # Check thermal zones
    for zone in range(5):
        temp_path = f"/sys/class/thermal/thermal_zone{zone}/temp"
        if os.path.exists(temp_path):
            try:
                with open(temp_path, "r") as f:
                    val = f.read().strip()
                temp_c = float(val) / 1000.0
                if 10.0 < temp_c < 115.0:
                    return round(temp_c, 1)
            except Exception:
                continue

    # Check hwmon
    hwmon_base = "/sys/class/hwmon"
    if os.path.exists(hwmon_base):
        try:
            for hwmon in os.listdir(hwmon_base):
                for item in os.listdir(os.path.join(hwmon_base, hwmon)):
                    if item.startswith("temp") and item.endswith("_input"):
                        input_path = os.path.join(hwmon_base, hwmon, item)
                        try:
                            with open(input_path, "r") as f:
                                temp_c = float(f.read().strip()) / 1000.0
                            if 10.0 < temp_c < 115.0:
                                return round(temp_c, 1)
                        except Exception:
                            continue
        except Exception:
            pass

    return None


def get_service_status(service_name: str) -> Dict[str, str]:
    """Query systemctl for the status of a specific systemd unit."""
    has_systemctl = shutil.which("systemctl") is not None

    if not has_systemctl:
        if os.environ.get("ENABLE_MOCKS") == "1":
            return {
                "name": service_name,
                "status": "active",
                "substate": "running (dev)",
                "enabled": True,
            }
        return {
            "name": service_name,
            "status": "inactive",
            "substate": "systemctl unavailable",
            "enabled": False,
        }

    unit = f"{service_name}.service"
    try:
        # Query active state
        proc = subprocess.run(
            ["systemctl", "show", unit, "--property=ActiveState,SubState,UnitFileState"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = proc.stdout.strip()
        state = {}
        for line in output.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                state[k] = v

        active_state = state.get("ActiveState", "inactive")
        sub_state = state.get("SubState", "unknown")
        unit_file_state = state.get("UnitFileState", "unknown")

        return {
            "name": service_name,
            "status": active_state,  # active, inactive, failed, activating
            "substate": sub_state,    # running, exited, dead, etc.
            "enabled": unit_file_state in ("enabled", "static"),
        }
    except Exception as e:
        return {
            "name": service_name,
            "status": "error",
            "substate": str(e),
            "enabled": False,
        }


def get_all_services() -> List[Dict[str, Any]]:
    """Retrieve statuses of all managed gateway services."""
    results = []
    for svc in MANAGED_SERVICES:
        status_info = get_service_status(svc["name"])
        results.append({
            "name": svc["name"],
            "title": svc["title"],
            "description": svc["description"],
            "status": status_info["status"],
            "substate": status_info["substate"],
            "enabled": status_info["enabled"],
        })
    return results


def restart_service(service_name: str) -> Dict[str, Any]:
    """Safely restart a service if in whitelist. NEVER uses shell=True."""
    if service_name not in ALLOWED_SERVICE_NAMES:
        return {
            "success": False,
            "service": service_name,
            "error": f"Service '{service_name}' is not in allowed management list.",
        }

    has_systemctl = shutil.which("systemctl") is not None
    if not has_systemctl:
        return {
            "success": True,
            "service": service_name,
            "status": "active",
            "message": "Restart simulated on non-systemd environment.",
        }

    unit = f"{service_name}.service"
    try:
        proc = subprocess.run(
            ["systemctl", "restart", unit],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            status = get_service_status(service_name)
            return {
                "success": True,
                "service": service_name,
                "status": status["status"],
                "substate": status["substate"],
            }
        else:
            err = proc.stderr.strip() or proc.stdout.strip() or "systemctl restart failed"
            return {
                "success": False,
                "service": service_name,
                "error": err,
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "service": service_name,
            "error": "Restart timed out after 15 seconds.",
        }
    except Exception as e:
        return {
            "success": False,
            "service": service_name,
            "error": str(e),
        }


def get_full_system_payload() -> Dict[str, Any]:
    """Comprehensive system payload for the System page."""
    uptime_sec = get_uptime_seconds()
    os_info = get_os_info()
    os_info["uptime"] = _format_uptime(uptime_sec)
    os_info["uptime_seconds"] = int(uptime_sec)

    cpu_pct = get_cpu_percent()
    mem = get_memory_info()
    disk = get_disk_info()
    temp = get_temperature_c()

    services = get_all_services()

    return {
        "hardware": os_info,
        "resources": {
            "cpu_percent": cpu_pct,
            "cpu_cores": os.cpu_count() or 1,
            "ram": mem,
            "disk": disk,
            "temperature_c": temp,
        },
        "services": services,
    }


def get_dashboard_summary() -> Dict[str, Any]:
    """Lightweight aggregated metrics for Dashboard."""
    uptime_sec = get_uptime_seconds()
    mem = get_memory_info()

    return {
        "cpu_percent": get_cpu_percent(),
        "ram_percent": mem["percent"],
        "ram_used_gb": mem["used_gb"],
        "ram_total_gb": mem["total_gb"],
        "temperature_c": get_temperature_c(),
        "uptime": _format_uptime(uptime_sec),
    }
