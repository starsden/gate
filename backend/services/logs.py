"""
Logs service for Linux VPN Gateway.
Fetches systemd journal logs for services without shell injection.
"""

import shutil
import subprocess
from typing import List

ALLOWED_LOG_SERVICES = {
    "xray": "xray.service",
    "hostapd": "hostapd.service",
    "dnsmasq": "dnsmasq.service",
    "gateway": "vpn-gateway.service",
    "vpn-gateway": "vpn-gateway.service",
    "nftables": "nftables.service",
    "system": None,  # System journal
}


def get_logs(service_name: str, lines: int = 100) -> List[str]:
    """Retrieve recent journal lines for the requested service."""
    service_key = service_name.lower()
    if service_key not in ALLOWED_LOG_SERVICES:
        return [f"Log request for '{service_name}' rejected: unknown service."]

    has_journalctl = shutil.which("journalctl") is not None
    if not has_journalctl:
        return [
            f"--- Live logs for {service_name} ---",
            "journalctl is not available in current environment.",
            "In production on Debian/Ubuntu, journalctl logs are streamed here.",
        ]

    cmd = ["journalctl", "-n", str(min(lines, 300)), "--no-pager"]
    unit = ALLOWED_LOG_SERVICES[service_key]
    if unit:
        cmd.extend(["-u", unit])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output_lines = proc.stdout.splitlines()
        return output_lines if output_lines else ["No log entries found for this service."]
    except Exception as e:
        return [f"Error retrieving logs: {str(e)}"]
