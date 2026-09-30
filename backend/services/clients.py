"""
Connected clients service for Linux VPN Gateway.
Aggregates DHCP leases from dnsmasq and Wi-Fi station information from hostapd / iw.
Calculates individual signal strength (dBm) and traffic metrics.
"""

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

LEASE_PATHS = [
    Path("/var/lib/misc/dnsmasq.leases"),
    Path("/tmp/dnsmasq.leases"),
    Path("/var/lib/dnsmasq/dnsmasq.leases"),
    Path("/var/run/dnsmasq.leases"),
]


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _format_bytes(num_bytes: int) -> str:
    """Format bytes to human-readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024**2:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024**3:
        return f"{num_bytes / (1024**2):.1f} MB"
    else:
        return f"{num_bytes / (1024**3):.1f} GB"


def _dbm_to_percent(dbm_val: int) -> int:
    """Convert dBm (-100 to -50) to quality percentage (0 to 100)."""
    if dbm_val <= -100:
        return 0
    elif dbm_val >= -50:
        return 100
    return int(2 * (dbm_val + 100))


def parse_dnsmasq_leases() -> Dict[str, Dict[str, str]]:
    """
    Parse dnsmasq lease file.
    Returns map of MAC (lowercase) -> { "ip": ip, "hostname": name, "expiry": ts }
    """
    leases = {}

    for path in LEASE_PATHS:
        if path.exists():
            try:
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split()
                        # Format: <expiry> <mac> <ip> <hostname> <client_id>
                        if len(parts) >= 4:
                            mac = parts[1].lower()
                            ip = parts[2]
                            hostname = parts[3]
                            if hostname == "*":
                                hostname = "Unknown Device"
                            leases[mac] = {
                                "mac": mac,
                                "ip": ip,
                                "hostname": hostname,
                            }
                break
            except Exception:
                continue

    return leases


def parse_iw_stations(iface: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse 'iw dev <iface> station dump'.
    Returns map of MAC (lowercase) -> { "signal_dbm": int, "rx_bytes": int, "tx_bytes": int }
    """
    stations = {}
    if not _is_linux() or not shutil.which("iw"):
        return stations

    try:
        res = subprocess.run(["iw", "dev", iface, "station", "dump"], capture_output=True, text=True, timeout=3)
        current_mac = None

        for line in res.stdout.splitlines():
            line = line.strip()
            # Station xx:xx:xx:xx:xx:xx (on wlp4s0)
            sta_match = re.match(r"^Station\s+([0-9a-fA-F:]{17})", line)
            if sta_match:
                current_mac = sta_match.group(1).lower()
                stations[current_mac] = {
                    "signal_dbm": -60,
                    "rx_bytes": 0,
                    "tx_bytes": 0,
                }
                continue

            if current_mac and current_mac in stations:
                if "signal:" in line:
                    sig_match = re.search(r"signal:\s+(-?\d+)\s+dBm", line)
                    if sig_match:
                        stations[current_mac]["signal_dbm"] = int(sig_match.group(1))
                elif "rx bytes:" in line:
                    rx_match = re.search(r"rx bytes:\s+(\d+)", line)
                    if rx_match:
                        stations[current_mac]["rx_bytes"] = int(rx_match.group(1))
                elif "tx bytes:" in line:
                    tx_match = re.search(r"tx bytes:\s+(\d+)", line)
                    if tx_match:
                        stations[current_mac]["tx_bytes"] = int(tx_match.group(1))
    except Exception:
        pass

    return stations


def get_connected_clients() -> List[Dict[str, Any]]:
    """
    Aggregate dnsmasq leases and active wireless stations.
    Returns list of connected client devices.
    """
    from .wifi import get_wifi_interface
    iface = get_wifi_interface()

    leases = parse_dnsmasq_leases()
    stations = parse_iw_stations(iface)

    # Combine stations and leases
    clients = []
    all_macs = set(leases.keys()).union(set(stations.keys()))

    for mac in sorted(all_macs):
        lease = leases.get(mac, {})
        sta = stations.get(mac, {})

        ip = lease.get("ip", "10.42.0.x")
        hostname = lease.get("hostname", "Wi-Fi Device")

        signal_dbm = sta.get("signal_dbm", -58)
        rx_bytes = sta.get("rx_bytes", 0)
        tx_bytes = sta.get("tx_bytes", 0)
        total_bytes = rx_bytes + tx_bytes

        clients.append({
            "device": hostname,
            "ip": ip,
            "mac": mac,
            "signal": f"{signal_dbm} dBm",
            "signal_dbm": signal_dbm,
            "signal_pct": _dbm_to_percent(signal_dbm),
            "traffic": _format_bytes(total_bytes) if total_bytes > 0 else "< 1 MB",
            "traffic_rx": _format_bytes(rx_bytes),
            "traffic_tx": _format_bytes(tx_bytes),
            "is_wifi": mac in stations or len(stations) == 0,
        })

    # Optional dev simulation only if explicitly enabled via environment variable
    if not clients and os.environ.get("ENABLE_MOCKS") == "1":
        return [
            {
                "device": "iPhone 15 Pro",
                "ip": "10.42.0.145",
                "mac": "3c:06:30:44:a1:8f",
                "signal": "-51 dBm",
                "signal_dbm": -51,
                "signal_pct": 98,
                "traffic": "2.1 GB",
                "traffic_rx": "1.8 GB",
                "traffic_tx": "340 MB",
                "is_wifi": True,
            },
            {
                "device": "MacBook Air",
                "ip": "10.42.0.101",
                "mac": "f4:d4:88:5c:21:0a",
                "signal": "-63 dBm",
                "signal_dbm": -63,
                "signal_pct": 74,
                "traffic": "840 MB",
                "traffic_rx": "710 MB",
                "traffic_tx": "130 MB",
                "is_wifi": True,
            },
            {
                "device": "Nintendo Switch",
                "ip": "10.42.0.120",
                "mac": "98:b6:e9:12:33:bb",
                "signal": "-57 dBm",
                "signal_dbm": -57,
                "signal_pct": 86,
                "traffic": "320 MB",
                "traffic_rx": "290 MB",
                "traffic_tx": "30 MB",
                "is_wifi": True,
            },
        ]

    return clients
