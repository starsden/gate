"""
Diagnostics and Auto-Repair service for Linux VPN Gateway.
Performs end-to-end health checks across WAN, Wi-Fi LAN, Xray TUN,
policy routing table 100, DNS resolution, and nftables firewall.
Provides one-click automatic self-healing and repair.
"""

import os
import platform
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .firewall import apply_firewall_ruleset, get_firewall_status
from .network import get_default_interfaces, get_wan_status, sync_policy_routing
from .system import get_service_status, restart_service
from .vpn import get_vpn_status, read_vpn_profile

SYSCTL_CONF = Path("/etc/sysctl.d/99-vpn-gateway.conf")


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _check_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Test if a TCP socket connects within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _check_udp_dns(dns_host: str = "127.0.0.1", port: int = 53, timeout: float = 1.0) -> bool:
    """Test if a DNS server replies to a standard A record query."""
    try:
        # Minimal DNS query for localhost/gateway test
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        # Standard query for gateway.local
        query = (
            b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x07gateway\x05local\x00\x00\x01\x00\x01"
        )
        sock.sendto(query, (dns_host, port))
        data, _ = sock.recvfrom(512)
        sock.close()
        return len(data) > 12
    except Exception:
        return False


def check_ip_forwarding() -> Tuple[bool, str]:
    """Check if Linux IPv4 forwarding is active."""
    if not _is_linux():
        return True, "1 (simulated dev environment)"
    
    proc_file = Path("/proc/sys/net/ipv4/ip_forward")
    if proc_file.exists():
        try:
            val = proc_file.read_text().strip()
            return val == "1", val
        except Exception as e:
            return False, str(e)
    return False, "Not available"


def check_interface_up(iface: str) -> Tuple[bool, str]:
    """Check if network interface is in UP operational state."""
    if not _is_linux():
        return True, "UP (simulated dev environment)"

    operstate_file = Path(f"/sys/class/net/{iface}/operstate")
    if operstate_file.exists():
        try:
            state = operstate_file.read_text().strip()
            return state in ("up", "unknown"), state
        except Exception as e:
            return False, str(e)

    if shutil.which("ip"):
        try:
            res = subprocess.run(["ip", "link", "show", iface], capture_output=True, text=True, timeout=2)
            if "state UP" in res.stdout or "state UNKNOWN" in res.stdout:
                return True, "UP"
            return False, res.stdout.strip()
        except Exception:
            pass

    return False, f"Interface {iface} not found"


def check_policy_rule() -> Tuple[bool, str]:
    """Check if 'from 10.42.0.0/24 lookup 100' exists in ip rules."""
    if not _is_linux() or not shutil.which("ip"):
        return True, "from 10.42.0.0/24 lookup 100 (simulated)"

    try:
        res = subprocess.run(["ip", "rule", "show"], capture_output=True, text=True, timeout=2)
        for line in res.stdout.splitlines():
            if "10.42.0.0/24" in line and "100" in line:
                return True, line.strip()
        return False, "Rule not found in ip rule list"
    except Exception as e:
        return False, str(e)


def check_table_100_routes() -> Dict[str, Any]:
    """Inspect Table 100 routes for default xray0 and VLESS server route."""
    if not _is_linux() or not shutil.which("ip"):
        profile = read_vpn_profile()
        vless_ip = profile.get("address", "185.196.220.14")
        return {
            "default_route_ok": True,
            "default_detail": "default dev xray0 table 100",
            "vless_route_ok": True,
            "vless_detail": f"{vless_ip} via 192.168.0.1 dev enp3s0 table 100",
        }

    profile = read_vpn_profile()
    vless_ip = profile.get("address", "")
    
    default_ok = False
    default_detail = "Missing default dev xray0 in table 100"
    vless_ok = False
    vless_detail = f"Missing route for {vless_ip} in table 100"

    try:
        res = subprocess.run(["ip", "route", "show", "table", "100"], capture_output=True, text=True, timeout=2)
        for line in res.stdout.splitlines():
            l = line.strip()
            if l.startswith("default") and "xray0" in l:
                default_ok = True
                default_detail = l
            if vless_ip and vless_ip in l:
                vless_ok = True
                vless_detail = l
    except Exception as e:
        default_detail = str(e)
        vless_detail = str(e)

    return {
        "default_route_ok": default_ok,
        "default_detail": default_detail,
        "vless_route_ok": vless_ok if vless_ip else True,
        "vless_detail": vless_detail if vless_ip else "No VLESS server configured",
    }


def check_dns_resolution(domain: str = "cloudflare.com") -> Tuple[bool, str]:
    """Check DNS resolution capability."""
    try:
        t0 = time.time()
        res = socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
        elapsed_ms = int((time.time() - t0) * 1000)
        if res and len(res) > 0:
            ip = res[0][4][0]
            return True, f"Resolved {domain} to {ip} ({elapsed_ms}ms)"
        return False, f"Empty resolution for {domain}"
    except Exception as e:
        return False, f"Resolution failed: {str(e)}"


def run_diagnostics() -> Dict[str, Any]:
    """
    Run complete system diagnostics checklist.
    Returns status of all services, network interfaces, routing tables, and connectivity.
    """
    ifaces = get_default_interfaces()
    wan_iface = ifaces["wan"]
    lan_iface = ifaces["lan"]
    tun_iface = "xray0"

    checks = []

    # 1. WAN Physical / Operational State
    wan_up, wan_msg = check_interface_up(wan_iface)
    checks.append({
        "id": "wan_interface",
        "category": "internet",
        "name": f"WAN Interface ({wan_iface})",
        "description": "Ethernet link carrier and operational state",
        "status": "healthy" if wan_up else "failed",
        "detail": wan_msg,
    })

    # 2. IPv4 Forwarding
    ip_fwd, ip_fwd_msg = check_ip_forwarding()
    checks.append({
        "id": "ip_forwarding",
        "category": "routing",
        "name": "Kernel IPv4 Forwarding",
        "description": "net.ipv4.ip_forward enabled for routing packets between interfaces",
        "status": "healthy" if ip_fwd else "failed",
        "detail": f"ip_forward = {ip_fwd_msg}",
    })

    # 3. Wi-Fi AP Service (hostapd)
    hostapd_svc = get_service_status("hostapd")
    hostapd_ok = hostapd_svc["status"] == "active"
    checks.append({
        "id": "hostapd_service",
        "category": "wifi",
        "name": "Wi-Fi Access Point (hostapd)",
        "description": "802.11 AP beacon and WPA2-PSK authenticator daemon",
        "status": "healthy" if hostapd_ok else "failed",
        "detail": f"systemd status: {hostapd_svc['status']} ({hostapd_svc['substate']})",
    })

    # 4. Wi-Fi Interface State
    wifi_up, wifi_msg = check_interface_up(lan_iface)
    checks.append({
        "id": "wifi_interface",
        "category": "wifi",
        "name": f"Wi-Fi Interface ({lan_iface})",
        "description": "Wireless network adapter operational status",
        "status": "healthy" if wifi_up else "failed",
        "detail": wifi_msg,
    })

    # 5. DHCP & DNS Server (dnsmasq)
    dnsmasq_svc = get_service_status("dnsmasq")
    dnsmasq_ok = dnsmasq_svc["status"] == "active"
    checks.append({
        "id": "dnsmasq_service",
        "category": "wifi",
        "name": "DHCP & Local DNS (dnsmasq)",
        "description": "IP address lease assigner for connected client devices",
        "status": "healthy" if dnsmasq_ok else "failed",
        "detail": f"systemd status: {dnsmasq_svc['status']} ({dnsmasq_svc['substate']})",
    })

    # 6. Xray Core Service
    xray_svc = get_service_status("xray")
    xray_ok = xray_svc["status"] == "active"
    checks.append({
        "id": "xray_service",
        "category": "vpn",
        "name": "Xray Core Daemon",
        "description": "VLESS / REALITY encrypted outbound tunnel manager",
        "status": "healthy" if xray_ok else "failed",
        "detail": f"systemd status: {xray_svc['status']} ({xray_svc['substate']})",
    })

    # 7. Xray TUN Interface (xray0)
    tun_up, tun_msg = check_interface_up(tun_iface)
    # If Xray is active, xray0 should be up
    tun_status = "healthy" if (tun_up or not _is_linux()) else "failed"
    checks.append({
        "id": "tun_interface",
        "category": "vpn",
        "name": f"TUN Virtual Device ({tun_iface})",
        "description": "Kernel virtual tunnel device created by Xray",
        "status": tun_status,
        "detail": tun_msg,
    })

    # 8. Table 100 Policy Rule
    rule_ok, rule_msg = check_policy_rule()
    checks.append({
        "id": "policy_rule",
        "category": "routing",
        "name": "Policy Routing Rule (Table 100)",
        "description": "ip rule directing LAN subnet (10.42.0.0/24) through routing table 100",
        "status": "healthy" if rule_ok else "failed",
        "detail": rule_msg,
    })

    # 9. Table 100 Default Route & Anti-Loop Route
    t100 = check_table_100_routes()
    checks.append({
        "id": "table_100_default",
        "category": "routing",
        "name": "Table 100 Default Gateway",
        "description": "Default route in table 100 directing traffic to xray0 TUN",
        "status": "healthy" if t100["default_route_ok"] else "failed",
        "detail": t100["default_detail"],
    })

    checks.append({
        "id": "vless_direct_route",
        "category": "routing",
        "name": "VLESS Anti-Loop Direct Route",
        "description": "Direct route to VPN server IP via Ethernet to prevent packet loop",
        "status": "healthy" if t100["vless_route_ok"] else "failed",
        "detail": t100["vless_detail"],
    })

    # 10. Firewall & NAT (nftables)
    fw_status = get_firewall_status()
    fw_ok = fw_status["ruleset_loaded"] and (fw_status["status"] == "active" or not _is_linux())
    checks.append({
        "id": "nftables_ruleset",
        "category": "firewall",
        "name": "Firewall & NAT (nftables)",
        "description": "Masquerade NAT and client packet forwarding chains",
        "status": "healthy" if fw_ok else "failed",
        "detail": f"{fw_status['rules_count']} rules loaded, NAT: {'Enabled' if fw_status['nat_enabled'] else 'Disabled'}",
    })

    # 11. DNS Resolution
    dns_ok, dns_msg = check_dns_resolution("cloudflare.com")
    checks.append({
        "id": "dns_resolution",
        "category": "connectivity",
        "name": "DNS Resolution Test",
        "description": "Testing lookup for public Internet domains",
        "status": "healthy" if dns_ok else "warning",
        "detail": dns_msg,
    })

    # Calculate overall health
    total_checks = len(checks)
    healthy_count = sum(1 for c in checks if c["status"] == "healthy")
    failed_count = sum(1 for c in checks if c["status"] == "failed")
    warning_count = sum(1 for c in checks if c["status"] == "warning")

    if failed_count > 0:
        overall_status = "issues_detected"
    elif warning_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "all_systems_operational"

    return {
        "timestamp": time.time(),
        "overall_status": overall_status,
        "summary": {
            "total": total_checks,
            "healthy": healthy_count,
            "failed": failed_count,
            "warnings": warning_count,
        },
        "checks": checks,
    }


def execute_auto_repair() -> Dict[str, Any]:
    """
    Execute complete automatic self-repair pipeline:
    1. Enforce kernel IPv4 forwarding
    2. Restart/recover dead essential services
    3. Recreate missing policy rules
    4. Sync table 100 routes (xray0 default + VLESS anti-loop route)
    5. Reapply nftables firewall rules
    6. Re-run diagnostics to confirm recovery
    """
    actions_taken: List[str] = []

    # 1. Enforce IPv4 forwarding
    try:
        if _is_linux():
            subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], capture_output=True, timeout=2)
            try:
                SYSCTL_CONF.parent.mkdir(parents=True, exist_ok=True)
                SYSCTL_CONF.write_text("net.ipv4.ip_forward = 1\n")
            except Exception:
                pass
        actions_taken.append("Kernel IPv4 packet forwarding enabled (net.ipv4.ip_forward = 1)")
    except Exception as e:
        actions_taken.append(f"Failed to set ip_forward: {str(e)}")

    ifaces = get_default_interfaces()
    lan_iface = ifaces["lan"]
    wan_iface = ifaces["wan"]

    # 2. Unblock RF, setup interface, and configure hostapd prerequisites
    if _is_linux():
        try:
            # Unblock rfkill
            subprocess.run(["rfkill", "unblock", "wifi"], capture_output=True, timeout=2)
            subprocess.run(["rfkill", "unblock", "all"], capture_output=True, timeout=2)

            # Prevent NetworkManager conflict
            nm_conf_dir = Path("/etc/NetworkManager/conf.d")
            if nm_conf_dir.exists():
                (nm_conf_dir / "99-unmanage-wlan.conf").write_text(f"[keyfile]\nunmanaged-devices=interface-name:{lan_iface}\n")
                subprocess.run(["systemctl", "reload", "NetworkManager"], capture_output=True, timeout=2)

            # Terminate conflicting client wpa_supplicant on AP interface
            subprocess.run(["wpa_cli", "-i", lan_iface, "terminate"], capture_output=True, timeout=2)

            # Fix hostapd configuration in /etc/default/hostapd (Debian requirement)
            def_hostapd = Path("/etc/default/hostapd")
            def_hostapd.parent.mkdir(parents=True, exist_ok=True)
            def_hostapd.write_text('DAEMON_CONF="/etc/hostapd/hostapd.conf"\n')
            subprocess.run(["systemctl", "unmask", "hostapd"], capture_output=True, timeout=2)
            subprocess.run(["systemctl", "daemon-reload"], capture_output=True, timeout=2)

            # Assign static IP and bring interface up
            subprocess.run(["ip", "link", "set", lan_iface, "up"], capture_output=True, timeout=3)
            subprocess.run(["ip", "addr", "replace", "10.42.0.1/24", "dev", lan_iface], capture_output=True, timeout=3)
            actions_taken.append(f"Interface {lan_iface} unblocked (rfkill) and configured with 10.42.0.1/24")
        except Exception as e:
            actions_taken.append(f"Wi-Fi interface prep warning: {str(e)}")

    # 3. Synchronize Table 100 Policy Routes
    sync_res = sync_policy_routing()
    if sync_res.get("success"):
        actions_taken.append("Synchronized Table 100 policy routes and VLESS server anti-loop route")
    else:
        actions_taken.append(f"Sync routes notice: {sync_res.get('error') or sync_res.get('message')}")

    # 4. Re-apply nftables ruleset
    fw_res = apply_firewall_ruleset(wan_iface=wan_iface, lan_iface=lan_iface)
    if fw_res.get("success"):
        actions_taken.append("Reloaded nftables ruleset with NAT masquerade")
    else:
        actions_taken.append(f"Firewall reload notice: {fw_res.get('error') or fw_res.get('message')}")

    # 5. Check and restart essential services
    for svc in ("nftables", "hostapd", "dnsmasq", "xray"):
        status = get_service_status(svc)
        if status["status"] != "active":
            res = restart_service(svc)
            if res.get("success"):
                actions_taken.append(f"Restarted inactive service {svc}.service")
            else:
                actions_taken.append(f"Attempted restart of {svc}.service: {res.get('error', 'error')}")

    # Allow a brief moment for daemons to settle
    time.sleep(0.5)

    # 5. Re-run diagnostics
    post_diag = run_diagnostics()

    return {
        "success": True,
        "message": "Automatic repair completed.",
        "actions_taken": actions_taken,
        "diagnostics": post_diag,
    }
