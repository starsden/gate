"""
Firewall service for Linux VPN Gateway.
Manages and inspects nftables ruleset for policy routing and NAT masquerading.
Supports ruleset generation, syntax verification, atomic updates, and rollback.
"""

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

NFTABLES_CONF_PATH = Path("/etc/nftables.conf")
CONFIG_DIR = Path("/etc/vpn-gateway")
BACKUP_DIR = CONFIG_DIR / "backups"


def _is_linux() -> bool:
    return platform.system() == "Linux"


def get_nft_binary() -> Optional[str]:
    """Resolve absolute path to nft binary, checking sbin directories."""
    which_path = shutil.which("nft")
    if which_path:
        return which_path
    for p in ["/usr/sbin/nft", "/sbin/nft", "/usr/bin/nft", "/usr/local/sbin/nft"]:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return None


def get_firewall_status() -> Dict[str, Any]:
    """Check nftables service status, ruleset existence, and NAT forwarding chains."""
    from .system import get_service_status
    svc = get_service_status("nftables")

    nft_bin = get_nft_binary()
    ruleset_loaded = False
    rules_count = 0
    nat_enabled = False

    if nft_bin and _is_linux():
        try:
            res = subprocess.run([nft_bin, "list", "ruleset"], capture_output=True, text=True, timeout=3)
            if "table" in res.stdout:
                ruleset_loaded = True
                rules_count = len([l for l in res.stdout.splitlines() if l.strip()])
                nat_enabled = "masquerade" in res.stdout
        except Exception:
            pass
    elif not _is_linux():
        # Dev simulated active status
        ruleset_loaded = True
        rules_count = 32
        nat_enabled = True

    return {
        "status": svc["status"],
        "substate": svc["substate"],
        "ruleset_loaded": ruleset_loaded,
        "rules_count": rules_count,
        "nat_enabled": nat_enabled,
        "masquerade_interfaces": ["xray0", "enp3s0"],
        "allowed_ports": [
            {"port": 80, "protocol": "tcp", "service": "Web UI (HTTP)"},
            {"port": 53, "protocol": "udp/tcp", "service": "DNS Resolver"},
            {"port": 67, "protocol": "udp", "service": "DHCP Server"},
        ],
    }


def generate_nftables_ruleset(wan_iface: str = "enp3s0", lan_iface: str = "wlp4s0", tun_iface: str = "xray0") -> str:
    """Generate production nftables ruleset for Gateway."""
    return f"""#!/usr/sbin/nft -f
# /etc/nftables.conf
# Managed by Linux VPN Gateway

flush ruleset

table inet filter {{
    chain input {{
        type filter hook input priority filter; policy accept;
        iifname "lo" accept
        ct state established,related accept
        
        # Allow DHCP, DNS, and Web UI on Wi-Fi LAN
        iifname "{lan_iface}" udp dport {{ 53, 67 }} accept
        iifname "{lan_iface}" tcp dport {{ 53, 80 }} accept
    }}

    chain forward {{
        type filter hook forward priority filter; policy accept;
        ct state established,related accept
        
        # Forward Wi-Fi client traffic to Xray TUN
        iifname "{lan_iface}" oifname "{tun_iface}" accept
        
        # Fallback forward to WAN Ethernet
        iifname "{lan_iface}" oifname "{wan_iface}" accept
    }}

    chain output {{
        type filter hook output priority filter; policy accept;
    }}
}}

table ip nat {{
    chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
        
        # Masquerade traffic going to Xray TUN
        oifname "{tun_iface}" masquerade
        
        # Masquerade traffic going direct to WAN
        oifname "{wan_iface}" masquerade
    }}
}}
"""


def apply_firewall_ruleset(wan_iface: str, lan_iface: str, tun_iface: str = "xray0") -> Dict[str, Any]:
    """
    Validate and apply nftables ruleset with backup and rollback.
    """
    new_rules = generate_nftables_ruleset(wan_iface, lan_iface, tun_iface)
    nft_bin = get_nft_binary()

    if not _is_linux() or not nft_bin:
        return {
            "success": True,
            "message": "Firewall rules generated and simulated (dev environment).",
            "wan": wan_iface,
            "lan": lan_iface,
            "tun": tun_iface,
        }

    target_file = NFTABLES_CONF_PATH
    backup_file = None

    try:
        # 1. Ensure kernel modules for NAT and masquerading are loaded
        for mod in ["nf_tables", "nf_nat", "nft_nat", "nft_masq"]:
            subprocess.run(["modprobe", mod], capture_output=True, timeout=2)
        try:
            mod_load_dir = Path("/etc/modules-load.d")
            mod_load_dir.mkdir(parents=True, exist_ok=True)
            (mod_load_dir / "vpn-gateway.conf").write_text("nft_nat\nnft_masq\nnf_nat\n")
        except Exception:
            pass

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if target_file.exists():
            timestamp = int(time.time())
            backup_file = BACKUP_DIR / f"nftables.conf.{timestamp}.bak"
            shutil.copy2(target_file, backup_file)

        # Syntax test using temporary file
        temp_file = Path("/tmp/nft_test.conf")
        with open(temp_file, "w") as f:
            f.write(new_rules)

        test_res = subprocess.run([nft_bin, "-c", "-f", str(temp_file)], capture_output=True, text=True, timeout=5)
        if test_res.returncode != 0:
            if temp_file.exists(): temp_file.unlink()
            return {"success": False, "error": f"nftables syntax check failed: {test_res.stderr.strip()}"}

        # Apply atomically
        temp_file.replace(target_file)

        # Reload nftables into kernel
        reload_res = subprocess.run([nft_bin, "-f", str(target_file)], capture_output=True, text=True, timeout=5)
        if reload_res.returncode != 0:
            # Rollback
            if backup_file and backup_file.exists():
                shutil.copy2(backup_file, target_file)
                subprocess.run([nft_bin, "-f", str(target_file)], check=False)
            return {"success": False, "error": f"Failed to reload nftables: {reload_res.stderr.strip()}"}

        # Enable and restart nftables service if systemd is active
        subprocess.run(["systemctl", "enable", "nftables.service"], check=False)
        subprocess.run(["systemctl", "restart", "nftables.service"], check=False)

        return {
            "success": True,
            "message": "Firewall ruleset applied successfully.",
            "rules_count": len(new_rules.splitlines()),
        }
    except Exception as e:
        if backup_file and backup_file.exists() and target_file.exists():
            shutil.copy2(backup_file, target_file)
            subprocess.run([nft_bin, "-f", str(target_file)], check=False)
        return {"success": False, "error": f"Firewall apply error: {str(e)}"}
