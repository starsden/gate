"""
Wi-Fi service for Linux VPN Gateway.
Handles hardware detection (chipset, driver, AP mode), hostapd configuration,
atomic updates with backup/rollback, and live status inspection.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_DIR = Path("/etc/vpn-gateway")
BACKUP_DIR = CONFIG_DIR / "backups"
HOSTAPD_CONF_PATH = Path("/etc/hostapd/hostapd.conf")

# Dev fallback config path if /etc is not writable
LOCAL_DEV_CONFIG = Path(__file__).resolve().parent.parent.parent / "configs" / "hostapd.conf"
LOCAL_STATE_FILE = Path(__file__).resolve().parent.parent.parent / "configs" / "wifi_state.json"


def _is_linux() -> bool:
    return platform.system() == "Linux"


def get_wifi_interface() -> str:
    """Detect primary wireless interface (e.g., wlp4s0)."""
    # 1. Check /sys/class/net
    if os.path.exists("/sys/class/net"):
        for name in os.listdir("/sys/class/net"):
            if name.startswith("wl") or os.path.exists(f"/sys/class/net/{name}/wireless"):
                return name

    # 2. Try iw dev
    if shutil.which("iw"):
        try:
            res = subprocess.run(["iw", "dev"], capture_output=True, text=True, timeout=2)
            match = re.search(r"Interface\s+(\S+)", res.stdout)
            if match:
                return match.group(1)
        except Exception:
            pass

    return "wlp4s0"


def detect_wifi_hardware(iface: str) -> Dict[str, Any]:
    """Inspect wireless driver, chipset, and AP support via sysfs, lspci, and iw."""
    driver = "ath9k"
    chipset = "Qualcomm Atheros AR9285"
    ap_supported = True

    if _is_linux():
        # Driver from sysfs
        driver_path = Path(f"/sys/class/net/{iface}/device/driver")
        if driver_path.exists():
            try:
                driver = driver_path.resolve().name
            except Exception:
                pass

        # Chipset from lspci
        if shutil.which("lspci"):
            try:
                res = subprocess.run(["lspci"], capture_output=True, text=True, timeout=2)
                for line in res.stdout.splitlines():
                    if "Network controller" in line or "Wireless" in line:
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            chipset = parts[2].strip()
                            break
            except Exception:
                pass

        # AP mode support from iw
        if shutil.which("iw"):
            try:
                res = subprocess.run(["iw", "list"], capture_output=True, text=True, timeout=3)
                ap_supported = bool(re.search(r"^\s+\*\s+AP\b", res.stdout, re.MULTILINE))
            except Exception:
                pass

    return {
        "interface": iface,
        "driver": driver,
        "chipset": chipset,
        "ap_supported": ap_supported,
    }


def get_tx_power(iface: str) -> int:
    """Retrieve wireless transmission power in dBm."""
    if _is_linux() and shutil.which("iw"):
        try:
            res = subprocess.run(["iw", "dev", iface, "info"], capture_output=True, text=True, timeout=2)
            match = re.search(r"txpower\s+([\d\.]+)\s+dBm", res.stdout)
            if match:
                return int(float(match.group(1)))
        except Exception:
            pass
    return 15


def get_supported_channels() -> List[int]:
    """List 2.4 GHz supported channels."""
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


def read_current_config() -> Dict[str, Any]:
    """Parse hostapd.conf or cached json config."""
    conf_file = HOSTAPD_CONF_PATH if HOSTAPD_CONF_PATH.exists() else LOCAL_DEV_CONFIG

    config = {
        "ssid": "freedom",
        "channel": 6,
        "country": "RU",
        "ieee80211n": True,
        "security": "WPA2",
        "password": "freedompassword",
    }

    # Also check local state file if exists
    if LOCAL_STATE_FILE.exists():
        try:
            with open(LOCAL_STATE_FILE, "r") as f:
                saved = json.load(f)
                config.update(saved)
                return config
        except Exception:
            pass

    if conf_file.exists():
        try:
            with open(conf_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if k == "ssid":
                            config["ssid"] = v
                        elif k == "channel":
                            try:
                                config["channel"] = int(v)
                            except ValueError:
                                config["channel"] = 6
                        elif k == "country_code":
                            config["country"] = v.upper()
                        elif k == "ieee80211n":
                            config["ieee80211n"] = (v == "1")
                        elif k == "wpa_passphrase":
                            config["password"] = v
        except Exception:
            pass

    return config


def get_wifi_status() -> Dict[str, Any]:
    """Full operational and hardware status for Wi-Fi page and Dashboard."""
    iface = get_wifi_interface()
    hw = detect_wifi_hardware(iface)
    conf = read_current_config()
    tx_power = get_tx_power(iface)

    # Check daemon status
    is_running = False
    if _is_linux() and shutil.which("systemctl"):
        try:
            res = subprocess.run(["systemctl", "is-active", "hostapd.service"], capture_output=True, text=True, timeout=2)
            is_running = res.stdout.strip() == "active"
        except Exception:
            pass
    elif os.environ.get("ENABLE_MOCKS") == "1":
        is_running = True

    # Count connected devices
    from .clients import get_connected_clients
    clients = get_connected_clients()

    return {
        "status": "running" if is_running else "stopped",
        "interface": iface,
        "chipset": hw["chipset"],
        "driver": hw["driver"],
        "ap_supported": hw["ap_supported"],
        "ssid": conf["ssid"],
        "channel": conf["channel"],
        "frequency": "2.4 GHz",
        "channel_width": "20 MHz",
        "tx_power_dbm": tx_power,
        "security": "WPA2-PSK",
        "country": conf.get("country", "RU"),
        "ieee80211n": conf.get("ieee80211n", True),
        "connected_devices": len(clients),
        "supported_channels": get_supported_channels(),
        "supported_countries": ["RU", "US", "DE", "GB", "CN", "KZ", "BY"],
    }


def generate_hostapd_content(iface: str, ssid: str, password: str, channel: int, country: str, ieee80211n: bool) -> str:
    """Generate production-ready hostapd.conf text."""
    chan_str = str(channel) if channel > 0 else "0"
    ht_cap = "[HT20][SHORT-GI-20]" if ieee80211n else ""

    lines = [
        "# /etc/hostapd/hostapd.conf",
        "# Generated automatically by VPN Gateway",
        f"interface={iface}",
        "driver=nl80211",
        f"ssid={ssid}",
        "hw_mode=g",
        f"channel={chan_str}",
        f"country_code={country}",
        "ieee80211d=1",
        f"ieee80211n={1 if ieee80211n else 0}",
        "wmm_enabled=1",
    ]

    if ht_cap:
        lines.append(f"ht_capab={ht_cap}")

    lines.extend([
        "macaddr_acl=0",
        "auth_algs=1",
        "ignore_broadcast_ssid=0",
        "wpa=2",
        f"wpa_passphrase={password}",
        "wpa_key_mgmt=WPA-PSK",
        "wpa_pairwise=TKIP",
        "rsn_pairwise=CCMP",
    ])

    return "\n".join(lines) + "\n"


def apply_wifi_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate, backup, atomically apply hostapd configuration, and restart service.
    Implements health check with automatic rollback on failure.
    """
    ssid = str(payload.get("ssid", "")).strip()
    password = str(payload.get("password", "")).strip()
    channel = int(payload.get("channel", 6))
    country = str(payload.get("country", "RU")).strip().upper()[:2]
    ieee80211n = bool(payload.get("ieee80211n", True))

    # 1. Validation
    if not ssid or len(ssid) > 32:
        return {"success": False, "error": "SSID must be between 1 and 32 characters."}

    if len(password) < 8 or len(password) > 63:
        return {"success": False, "error": "WPA2 Password must be between 8 and 63 characters."}

    if channel not in [0] + get_supported_channels():
        return {"success": False, "error": f"Invalid channel {channel}. Must be 0 (Auto) or 1..13."}

    if len(country) != 2 or not country.isalpha():
        country = "RU"

    iface = get_wifi_interface()
    new_content = generate_hostapd_content(iface, ssid, password, channel, country, ieee80211n)

    # Dev environment handling
    if not _is_linux() or not os.path.exists("/etc/hostapd"):
        # Save to local dev state
        try:
            LOCAL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOCAL_STATE_FILE, "w") as f:
                json.dump({
                    "ssid": ssid,
                    "password": password,
                    "channel": channel,
                    "country": country,
                    "ieee80211n": ieee80211n,
                }, f, indent=2)
        except Exception:
            pass

        return {
            "success": True,
            "message": "Wi-Fi configuration saved (dev mode).",
            "ssid": ssid,
            "channel": channel,
        }

    # 2. Backup current config
    target_file = HOSTAPD_CONF_PATH
    backup_file = None

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if target_file.exists():
            timestamp = int(time.time())
            backup_file = BACKUP_DIR / f"hostapd.conf.{timestamp}.bak"
            shutil.copy2(target_file, backup_file)

        # 3. Write new config atomically via temporary file
        temp_file = target_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            f.write(new_content)
        temp_file.replace(target_file)

        # 4. Restart hostapd service
        restart_res = subprocess.run(["systemctl", "restart", "hostapd.service"], capture_output=True, text=True, timeout=12)

        # 5. Health Check: verify hostapd is active
        check_res = subprocess.run(["systemctl", "is-active", "hostapd.service"], capture_output=True, text=True, timeout=4)
        is_healthy = check_res.stdout.strip() == "active"

        if not is_healthy:
            # ROLLBACK!
            if backup_file and backup_file.exists():
                shutil.copy2(backup_file, target_file)
                subprocess.run(["systemctl", "restart", "hostapd.service"], capture_output=True, text=True, timeout=10)
            err_msg = restart_res.stderr.strip() or "hostapd failed to activate with the new settings. Rolled back."
            return {"success": False, "error": err_msg}

        # 6. Commit to config.json
        state_file = CONFIG_DIR / "config.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    app_cfg = json.load(f)
                app_cfg["wifi_ssid"] = ssid
                app_cfg["wifi_channel"] = channel
                app_cfg["wifi_country"] = country
                with open(state_file, "w") as f:
                    json.dump(app_cfg, f, indent=2)
            except Exception:
                pass

        return {
            "success": True,
            "message": "Wi-Fi configuration applied successfully.",
            "ssid": ssid,
            "channel": channel,
        }

    except Exception as e:
        # Rollback on unhandled exception
        if backup_file and backup_file.exists() and target_file.exists():
            shutil.copy2(backup_file, target_file)
            subprocess.run(["systemctl", "restart", "hostapd.service"], capture_output=True, text=True, timeout=5)
        return {"success": False, "error": f"Failed to apply Wi-Fi config: {str(e)}"}
