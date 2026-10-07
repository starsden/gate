"""
VPN service for Linux VPN Gateway.
Manages Xray Core (VLESS / REALITY proxy daemon).
Supports standard vless:// URI parsing, configuration generation for transparent TUN routing,
atomic updates with backup/rollback, connection latency testing, and daemon control.
"""

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import routing

XRAY_CONF_PATH = Path("/etc/xray/config.json")
CONFIG_DIR = Path("/etc/vpn-gateway")
BACKUP_DIR = CONFIG_DIR / "backups"
LOCAL_STATE_FILE = Path(__file__).resolve().parent.parent.parent / "configs" / "vpn_state.json"

_vpn_start_time: Optional[float] = None


def _is_linux() -> bool:
    return platform.system() == "Linux"


def mask_uuid(uuid_str: str) -> str:
    """Mask UUID for secure display (e.g. ••••••••-••••-••••-••••-••••••••1234)."""
    if not uuid_str:
        return "N/A"
    clean_uuid = uuid_str.strip()
    if len(clean_uuid) >= 8:
        last4 = clean_uuid[-4:]
        return f"••••••••-••••-••••-••••-••••••••{last4}"
    return "••••••••"


def parse_vless_uri(uri: str) -> Dict[str, Any]:
    """
    Parse a standard vless:// link into structured parameters.
    Format: vless://<uuid>@<host>:<port>?type=<net>&security=<sec>&pbk=<key>&fp=<fp>&sni=<sni>&sid=<sid>&flow=<flow>#<name>
    """
    clean_uri = uri.strip()
    if not clean_uri.startswith("vless://"):
        raise ValueError("Invalid URI scheme: must start with 'vless://'")

    parsed = urllib.parse.urlparse(clean_uri)
    if not parsed.username or not parsed.hostname:
        raise ValueError("Malformed vless URI: missing UUID or server hostname.")

    uuid = parsed.username
    address = parsed.hostname
    port = parsed.port or 443

    # Query params
    params = urllib.parse.parse_qs(parsed.query)

    def get_param(*keys, default=""):
        for k in keys:
            if k in params and params[k]:
                return params[k][0]
        return default

    transport = get_param("type", "net", default="tcp").lower()
    raw_security = get_param("security", default="").lower()
    pbk = get_param("pbk", "publicKey", "public_key", "pk", default="")
    sid = get_param("sid", "shortId", "short_id", default="")
    flow = get_param("flow", default="")
    sni = get_param("sni", "serverName", "servername", "peer", default=address)
    fp = get_param("fp", "fingerprint", "client-fingerprint", default="chrome")
    spx = get_param("spx", "spiderX", "spider_x", default="/")
    path = get_param("path", default="/")
    host = get_param("host", default="")
    remark = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"Server-{address}"

    # Determine security mode gracefully
    if raw_security:
        security = raw_security
        if security == "reality" and not pbk:
            security = "tls"
    else:
        security = "reality" if pbk else "tls"

    if not flow and security == "reality":
        flow = "xtls-rprx-vision"

    return {
        "uuid": uuid,
        "address": address,
        "port": port,
        "transport": transport,
        "security": security,
        "flow": flow,
        "sni": sni,
        "fingerprint": fp,
        "publicKey": pbk,
        "shortId": sid,
        "spiderX": spx,
        "path": path,
        "host": host,
        "remark": remark,
    }


def read_vpn_profile() -> Dict[str, Any]:
    """Retrieve saved VPN profile from persistent state."""
    # 1. Check system state file
    cfg_file = CONFIG_DIR / "vpn.json"
    if cfg_file.exists():
        try:
            with open(cfg_file, "r") as f:
                data = json.load(f)
                if data and data.get("address"):
                    return data
        except Exception:
            pass

    # 2. Check local dev state file
    if LOCAL_STATE_FILE.exists():
        try:
            with open(LOCAL_STATE_FILE, "r") as f:
                data = json.load(f)
                if data and data.get("address"):
                    return data
        except Exception:
            pass

    # 3. Only return dummy profile if explicitly requested via ENABLE_MOCKS=1
    if os.environ.get("ENABLE_MOCKS") == "1":
        return {
            "uuid": "96c810f6-2895-46ae-886e-b3f5451a657c",
            "address": "185.196.220.14",
            "port": 443,
            "transport": "tcp",
            "security": "reality",
            "flow": "xtls-rprx-vision",
            "sni": "cloudflare.com",
            "fingerprint": "chrome",
            "publicKey": "J8p0sX5_m0ckKeyPlaceholderForTesting1234567890",
            "shortId": "1a2b3c4d",
            "spiderX": "/",
            "remark": "Primary VLESS Gateway",
        }

    return {}


def save_vpn_profile(profile: Dict[str, Any]) -> None:
    """Save profile to persistent state."""
    # Local dev state
    try:
        LOCAL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCAL_STATE_FILE, "w") as f:
            json.dump(profile, f, indent=2)
    except Exception:
        pass

    # System state
    if CONFIG_DIR.exists():
        try:
            with open(CONFIG_DIR / "vpn.json", "w") as f:
                json.dump(profile, f, indent=2)
        except Exception:
            pass


def generate_xray_config(profile: Dict[str, Any], routing_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate complete Xray JSON configuration.
    Sets up 'tun' inbound (xray0) for client routing, and VLESS/REALITY outbound.
    """
    uuid = profile.get("uuid", "")
    address = profile.get("address", "")
    port = int(profile.get("port", 443))
    transport = profile.get("transport", "tcp").lower()
    security = profile.get("security", "reality").lower()
    flow = profile.get("flow", "xtls-rprx-vision")
    sni = profile.get("sni", address)
    fp = profile.get("fingerprint", "chrome")
    pbk = profile.get("publicKey", "")
    sid = profile.get("shortId", "")
    spx = profile.get("spiderX", "/")

    # Stream settings
    stream_settings = {
        "network": transport,
        "security": security,
    }

    if security == "reality":
        stream_settings["realitySettings"] = {
            "show": False,
            "fingerprint": fp,
            "serverName": sni,
            "publicKey": pbk,
            "shortId": sid,
            "spiderX": spx,
        }
    elif security == "tls":
        stream_settings["tlsSettings"] = {
            "serverName": sni,
            "fingerprint": fp,
            "allowInsecure": False,
        }

    # Transport settings (e.g. ws, h2, tcp)
    if transport == "ws":
        stream_settings["wsSettings"] = {
            "path": profile.get("path", "/"),
            "headers": {"Host": profile.get("host", sni)},
        }

    config = {
        "log": {
            "loglevel": "warning",
        },
        "inbounds": [
            {
                "tag": "tun-in",
                "port": 0,
                "protocol": "dokodemo-door",
                "settings": {
                    "network": "tcp,udp",
                    "followRedirect": True,
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"],
                },
            }
        ],
        "outbounds": [
            {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": address,
                            "port": port,
                            "users": [
                                {
                                    "id": uuid,
                                    "encryption": "none",
                                    "flow": flow if transport in ("tcp", "kcp") else "",
                                }
                            ],
                        }
                    ]
                },
                "streamSettings": stream_settings,
            },
            {
                "tag": "direct",
                "protocol": "freedom",
                "settings": {},
            },
            {
                "tag": "block",
                "protocol": "blackhole",
                "settings": {
                    "response": {"type": "none"}
                },
            },
        ],
        "routing": routing.build_xray_routing_rules(routing_cfg),
    }

    return config


def sanitize_unsupported_geosite(config_dict: Dict[str, Any], missing_code: str) -> bool:
    """
    Remove all occurrences of geosite:<missing_code> from routing rules.
    Case-insensitive matching. Modifies config_dict in-place.
    Returns True if at least one tag was removed.
    """
    changed = False
    routing_obj = config_dict.get("routing", {})
    rules = routing_obj.get("rules", [])
    target = f"geosite:{missing_code}".lower()

    for rule in rules:
        if "domain" in rule and isinstance(rule["domain"], list):
            new_domains = [
                d for d in rule["domain"]
                if not (isinstance(d, str) and d.lower() == target)
            ]
            if len(new_domains) != len(rule["domain"]):
                rule["domain"] = new_domains
                changed = True
    return changed


def validate_xray_config(config_dict: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test Xray configuration syntax using 'xray -test' if installed.
    If 'xray -test' reports unsupported geosite codes (e.g. 'code not found in geosite.dat: RU'),
    automatically strips the missing geosite tags from the rules and retries.
    """
    if not shutil.which("xray"):
        # Syntactic checks in python
        if not config_dict.get("outbounds"):
            return False, "Configuration missing outbounds."
        return True, "Validated (native parser)"

    temp_path = Path("/tmp/xray_test_conf.json")
    try:
        max_attempts = 15
        last_err = ""
        for _ in range(max_attempts):
            with open(temp_path, "w") as f:
                json.dump(config_dict, f, indent=2)

            res = subprocess.run(["xray", "-test", "-config", str(temp_path)], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True, "Xray configuration is valid."

            last_err = res.stderr.strip() or res.stdout.strip()
            # Match patterns like:
            # - code not found in geosite.dat: RU
            # - failed to load geosite: RU
            # - failed to parse domain rule: geosite:ru
            match = re.search(r"(?:code not found in geosite\.dat:\s*|failed to load geosite:\s*|failed to parse domain rule:\s*geosite:)([A-Za-z0-9_-]+)", last_err, re.IGNORECASE)
            if match:
                missing_code = match.group(1).strip()
                if sanitize_unsupported_geosite(config_dict, missing_code):
                    continue  # Retry validation with missing code removed

            return False, f"Xray test failed: {last_err}"

        return False, f"Xray test failed after sanitizing: {last_err}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"
    finally:
        if temp_path.exists():
            temp_path.unlink()


def get_vpn_traffic() -> Tuple[str, str]:
    """Read RX/TX bytes on xray0 TUN or dev baseline."""
    if _is_linux() and os.path.exists("/proc/net/dev"):
        try:
            with open("/proc/net/dev", "r") as f:
                for line in f:
                    if "xray0:" in line:
                        stats = line.split(":", 1)[1].split()
                        rx = int(stats[0])
                        tx = int(stats[8])
                        from .clients import _format_bytes
                        return _format_bytes(rx), _format_bytes(tx)
        except Exception:
            pass

    if os.environ.get("ENABLE_MOCKS") == "1":
        return "4.2 GB", "832 MB"
    return "0 B", "0 B"


def get_vpn_uptime_str(is_active: bool) -> str:
    """Compute uptime since service was started."""
    global _vpn_start_time
    if not is_active:
        _vpn_start_time = None
        return "0m"

    if _vpn_start_time is None:
        _vpn_start_time = time.time()

    elapsed = int(time.time() - _vpn_start_time)
    hours, remainder = divmod(elapsed, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_vpn_status() -> Dict[str, Any]:
    """Full operational status for VPN page and Dashboard."""
    profile = read_vpn_profile()
    has_profile = bool(profile.get("address") and profile.get("uuid"))

    # Query systemctl
    is_active = False
    if _is_linux() and shutil.which("systemctl"):
        try:
            res = subprocess.run(["systemctl", "is-active", "xray.service"], capture_output=True, text=True, timeout=2)
            is_active = res.stdout.strip() == "active"
        except Exception:
            is_active = False
    elif os.environ.get("ENABLE_MOCKS") == "1" and has_profile:
        is_active = True

    if not has_profile:
        return {
            "status": "not_configured",
            "protocol": "VLESS",
            "transport": "—",
            "security": "—",
            "server": "Not Configured",
            "server_ip": "",
            "server_port": "",
            "sni": "",
            "flow": "",
            "fingerprint": "",
            "remark": "No VPN Profile",
            "masked_uuid": "—",
            "uptime": "0m",
            "traffic_down": "0 B",
            "traffic_up": "0 B",
            "latency_ms": 0,
        }

    traffic_down, traffic_up = get_vpn_traffic()

    # Measure real latency if server is active and accessible
    latency = 0
    if is_active and profile.get("address"):
        test_res = test_vpn_connection()
        latency = test_res.get("latency_ms", 0) if test_res.get("connected") else 0

    return {
        "status": "connected" if is_active else "disconnected",
        "protocol": "VLESS",
        "transport": profile.get("transport", "tcp").upper(),
        "security": profile.get("security", "reality").upper(),
        "server": f"{profile.get('address')}:{profile.get('port')}",
        "server_ip": profile.get("address"),
        "server_port": profile.get("port"),
        "sni": profile.get("sni"),
        "flow": profile.get("flow"),
        "fingerprint": profile.get("fingerprint"),
        "remark": profile.get("remark", "Default Server"),
        "masked_uuid": mask_uuid(profile.get("uuid", "")),
        "uptime": get_vpn_uptime_str(is_active),
        "traffic_down": traffic_down,
        "traffic_up": traffic_up,
        "latency_ms": latency,
    }


def test_vpn_connection() -> Dict[str, Any]:
    """Test TCP latency to active VLESS server."""
    profile = read_vpn_profile()
    address = profile.get("address", "1.1.1.1")
    port = int(profile.get("port", 443))

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        sock.connect((address, port))
        latency = int((time.time() - start) * 1000)
        sock.close()
        return {
            "success": True,
            "connected": True,
            "latency_ms": max(1, latency),
            "target": f"{address}:{port}",
            "message": f"Connection verified in {latency} ms",
        }
    except Exception as e:
        return {
            "success": False,
            "connected": False,
            "latency_ms": 0,
            "target": f"{address}:{port}",
            "error": f"Connection unreachable: {str(e)}",
        }


def set_vpn_state(action: str) -> Dict[str, Any]:
    """Start, stop, or restart Xray service."""
    global _vpn_start_time

    if action not in ("start", "stop", "restart"):
        return {"success": False, "error": f"Invalid action: {action}"}

    if _is_linux() and shutil.which("systemctl"):
        try:
            res = subprocess.run(["systemctl", action, "xray.service"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                if action in ("start", "restart"):
                    _vpn_start_time = time.time()
                else:
                    _vpn_start_time = None
                return {"success": True, "action": action, "status": "active" if action != "stop" else "inactive"}
            else:
                return {"success": False, "error": res.stderr.strip() or "Failed to control service"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Dev fallback
    if action in ("start", "restart"):
        _vpn_start_time = time.time()
    else:
        _vpn_start_time = None
    return {"success": True, "action": action, "message": "Action simulated in dev environment."}


def apply_vpn_config(vless_uri: str) -> Dict[str, Any]:
    """
    Parse vless link, validate config, atomically backup, apply new Xray configuration,
    and restart daemon with automatic rollback on failure.
    """
    try:
        profile = parse_vless_uri(vless_uri)
    except Exception as e:
        return {"success": False, "error": f"VLESS parsing error: {str(e)}"}

    xray_conf = generate_xray_config(profile)
    is_valid, val_msg = validate_xray_config(xray_conf)
    if not is_valid:
        return {"success": False, "error": f"Invalid Xray configuration: {val_msg}"}

    # Dev environment
    if not _is_linux() or not os.path.exists("/etc/xray"):
        save_vpn_profile(profile)
        return {
            "success": True,
            "message": "VLESS configuration imported successfully (dev mode).",
            "profile": {
                "server": profile["address"],
                "port": profile["port"],
                "security": profile["security"].upper(),
                "transport": profile["transport"].upper(),
                "sni": profile["sni"],
                "fingerprint": profile["fingerprint"],
                "flow": profile["flow"],
                "masked_uuid": mask_uuid(profile["uuid"]),
            },
        }

    # Production Linux workflow with Backup & Rollback
    target_file = XRAY_CONF_PATH
    backup_file = None

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if target_file.exists():
            timestamp = int(time.time())
            backup_file = BACKUP_DIR / f"xray_config.json.{timestamp}.bak"
            shutil.copy2(target_file, backup_file)

        # Atomic write
        temp_file = target_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(xray_conf, f, indent=2)
        temp_file.replace(target_file)

        # Restart xray daemon
        restart_res = subprocess.run(["systemctl", "restart", "xray.service"], capture_output=True, text=True, timeout=10)

        # Health check
        check_res = subprocess.run(["systemctl", "is-active", "xray.service"], capture_output=True, text=True, timeout=4)
        is_healthy = check_res.stdout.strip() == "active"

        if not is_healthy:
            # Rollback
            if backup_file and backup_file.exists():
                shutil.copy2(backup_file, target_file)
                subprocess.run(["systemctl", "restart", "xray.service"], capture_output=True, text=True, timeout=5)
            err = restart_res.stderr.strip() or "Xray failed to activate with the new VLESS profile. Rolled back."
            return {"success": False, "error": err}

        # Save profile
        save_vpn_profile(profile)

        return {
            "success": True,
            "message": "VLESS configuration applied and active.",
            "profile": {
                "server": profile["address"],
                "port": profile["port"],
                "security": profile["security"].upper(),
                "transport": profile["transport"].upper(),
                "sni": profile["sni"],
                "fingerprint": profile["fingerprint"],
                "flow": profile["flow"],
                "masked_uuid": mask_uuid(profile["uuid"]),
            },
        }

    except Exception as e:
        if backup_file and backup_file.exists() and target_file.exists():
            shutil.copy2(backup_file, target_file)
            subprocess.run(["systemctl", "restart", "xray.service"], capture_output=True, text=True, timeout=5)
        return {"success": False, "error": f"Failed to apply Xray config: {str(e)}"}


def reapply_vpn_with_routing(routing_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Regenerate Xray config for currently active VPN profile with updated routing rules,
    validate, apply, and restart daemon.
    """
    profile = read_vpn_profile()
    if not profile or not profile.get("address"):
        # No profile imported yet, routing settings saved for future imports
        return {
            "success": True,
            "reloaded": False,
            "message": "Маршрутизация сохранена. Применится автоматически при импорте или подключении VPN.",
        }

    xray_conf = generate_xray_config(profile, routing_cfg)
    is_valid, val_msg = validate_xray_config(xray_conf)
    if not is_valid:
        return {"success": False, "error": f"Некорректная конфигурация Xray: {val_msg}"}

    if not _is_linux() or not os.path.exists("/etc/xray"):
        return {
            "success": True,
            "reloaded": True,
            "message": "Правила маршрутизации успешно обновлены (dev mode).",
        }

    target_file = XRAY_CONF_PATH
    backup_file = None
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if target_file.exists():
            timestamp = int(time.time())
            backup_file = BACKUP_DIR / f"xray_config.json.{timestamp}.bak"
            shutil.copy2(target_file, backup_file)

        temp_file = target_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(xray_conf, f, indent=2)
        temp_file.replace(target_file)

        restart_res = subprocess.run(["systemctl", "restart", "xray.service"], capture_output=True, text=True, timeout=10)
        check_res = subprocess.run(["systemctl", "is-active", "xray.service"], capture_output=True, text=True, timeout=4)
        if check_res.stdout.strip() != "active":
            if backup_file and backup_file.exists():
                shutil.copy2(backup_file, target_file)
                subprocess.run(["systemctl", "restart", "xray.service"], capture_output=True, text=True, timeout=5)
            err = restart_res.stderr.strip() or "Служба Xray не смогла запуститься с новыми правилами. Выполнен откат."
            return {"success": False, "error": err}

        return {
            "success": True,
            "reloaded": True,
            "message": "Правила геозон применены, Xray перезапущен.",
        }
    except Exception as e:
        if backup_file and backup_file.exists() and target_file.exists():
            shutil.copy2(backup_file, target_file)
            subprocess.run(["systemctl", "restart", "xray.service"], capture_output=True, text=True, timeout=5)
        return {"success": False, "error": f"Ошибка обновления правил Xray: {str(e)}"}

