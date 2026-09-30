"""
Backup and rollback management service for Linux VPN Gateway.
Creates, lists, inspects, and restores full-configuration snapshots
(VPN profiles, Wi-Fi parameters, firewall ruleset, DHCP/DNS, and admin credentials).
Uses Python standard library tarfile and gzip with zero external dependencies.
"""

import gzip
import io
import json
import os
import platform
import shutil
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .firewall import apply_firewall_ruleset
from .system import restart_service

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_CONFIG_DIR = BASE_DIR / "configs"
SYS_CONFIG_DIR = Path("/etc/vpn-gateway")


def get_config_dir() -> Path:
    if platform.system() == "Linux" and SYS_CONFIG_DIR.exists():
        return SYS_CONFIG_DIR
    LOCAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return LOCAL_CONFIG_DIR


def get_backup_dir() -> Path:
    bdir = get_config_dir() / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    return bdir


def get_target_config_paths() -> Dict[str, Path]:
    """Map of internal configuration identifiers to filesystem locations."""
    cfg_dir = get_config_dir()
    is_linux = platform.system() == "Linux"

    return {
        "vpn_state": cfg_dir / "vpn_state.json",
        "wifi_state": cfg_dir / "wifi_state.json",
        "auth": cfg_dir / "auth.json",
        "hostapd": Path("/etc/hostapd/hostapd.conf") if is_linux else LOCAL_CONFIG_DIR / "hostapd.conf",
        "dnsmasq": Path("/etc/dnsmasq.conf") if is_linux else LOCAL_CONFIG_DIR / "dnsmasq.conf",
        "nftables": Path("/etc/nftables.conf") if is_linux else LOCAL_CONFIG_DIR / "nftables.conf",
        "xray": Path("/etc/xray/config.json") if is_linux else LOCAL_CONFIG_DIR / "xray_config.json",
    }


def list_backups() -> List[Dict[str, Any]]:
    """List all available backup snapshots ordered by newest first."""
    bdir = get_backup_dir()
    backups = []

    for item in bdir.glob("snapshot-*.tar.gz"):
        try:
            stat = item.stat()
            manifest = read_backup_manifest(item)
            
            backups.append({
                "id": item.name,
                "filename": item.name,
                "size_bytes": stat.st_size,
                "size_human": f"{stat.st_size / 1024:.1f} KB",
                "created_at": manifest.get("created_at", stat.st_mtime),
                "created_str": manifest.get("created_str", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))),
                "description": manifest.get("description", "Manual Snapshot"),
                "is_auto": manifest.get("is_auto", False),
                "files_count": len(manifest.get("files", [])),
                "manifest": manifest,
            })
        except Exception:
            continue

    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups


def read_backup_manifest(archive_path: Path) -> Dict[str, Any]:
    """Extract manifest.json from a backup tar.gz without full extraction."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            try:
                member = tar.getmember("manifest.json")
                f = tar.extractfile(member)
                if f:
                    return json.load(f)
            except KeyError:
                pass
    except Exception:
        pass
    return {}


def create_backup(description: str = "Manual snapshot", is_auto: bool = False) -> Dict[str, Any]:
    """Create a new gzipped tarball containing all current gateway configurations."""
    bdir = get_backup_dir()
    timestamp = int(time.time())
    archive_name = f"snapshot-{timestamp}.tar.gz"
    archive_path = bdir / archive_name

    target_paths = get_target_config_paths()
    files_included = []

    manifest = {
        "id": archive_name,
        "created_at": timestamp,
        "created_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
        "description": description.strip() or "Manual snapshot",
        "is_auto": is_auto,
        "files": [],
    }

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            for key, path in target_paths.items():
                if path.exists() and path.is_file():
                    tar.add(path, arcname=f"configs/{key}.conf" if not key.endswith(".json") else f"configs/{key}")
                    files_included.append(key)

            # Write manifest
            manifest["files"] = files_included
            manifest_data = json.dumps(manifest, indent=2).encode("utf-8")
            ti = tarfile.TarInfo(name="manifest.json")
            ti.size = len(manifest_data)
            ti.mtime = timestamp
            tar.addfile(ti, io.BytesIO(manifest_data))

        return {
            "success": True,
            "backup_id": archive_name,
            "files_included": files_included,
            "manifest": manifest,
        }
    except Exception as e:
        if archive_path.exists():
            archive_path.unlink()
        return {
            "success": False,
            "error": f"Failed to create backup: {str(e)}",
        }


def restore_backup(backup_id: str) -> Dict[str, Any]:
    """Restore configuration from a selected snapshot archive and reload services."""
    bdir = get_backup_dir()
    archive_path = bdir / backup_id

    # Sanitize path traversal
    if archive_path.resolve().parent != bdir.resolve():
        return {"success": False, "error": "Invalid backup identifier."}

    if not archive_path.exists():
        return {"success": False, "error": f"Backup snapshot '{backup_id}' not found."}

    # Automatically create a safety snapshot of CURRENT state before overwriting
    create_backup(description=f"Auto safety snapshot before restoring {backup_id}", is_auto=True)

    target_paths = get_target_config_paths()
    restored_items = []

    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("configs/"):
                    filename = member.name.replace("configs/", "")
                    key = filename.replace(".conf", "")
                    
                    if key in target_paths:
                        dest = target_paths[key]
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        extracted = tar.extractfile(member)
                        if extracted:
                            content = extracted.read()
                            # Atomic replace
                            tmp = dest.with_suffix(".tmp")
                            with open(tmp, "wb") as f:
                                f.write(content)
                            os.replace(tmp, dest)
                            restored_items.append(key)

        # Reload services to pick up restored configs
        reloaded_services = []
        for svc in ("xray", "hostapd", "dnsmasq", "nftables"):
            res = restart_service(svc)
            if res.get("success"):
                reloaded_services.append(svc)

        # Apply firewall if restored
        if "nftables" in restored_items:
            try:
                apply_firewall_ruleset()
            except Exception:
                pass

        return {
            "success": True,
            "message": f"Successfully restored {len(restored_items)} configurations from {backup_id}.",
            "restored_items": restored_items,
            "reloaded_services": reloaded_services,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to restore backup: {str(e)}",
        }


def delete_backup(backup_id: str) -> Dict[str, Any]:
    """Delete a backup archive file."""
    bdir = get_backup_dir()
    archive_path = bdir / backup_id

    if archive_path.resolve().parent != bdir.resolve():
        return {"success": False, "error": "Invalid backup identifier."}

    if not archive_path.exists():
        return {"success": False, "error": f"Backup snapshot '{backup_id}' not found."}

    try:
        archive_path.unlink()
        return {"success": True, "message": f"Backup {backup_id} deleted."}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete backup: {str(e)}"}


def get_backup_filepath(backup_id: str) -> Optional[Path]:
    """Return validated filesystem path for file download."""
    bdir = get_backup_dir()
    archive_path = bdir / backup_id
    if archive_path.resolve().parent == bdir.resolve() and archive_path.exists():
        return archive_path
    return None


def execute_factory_reset() -> Dict[str, Any]:
    """Reset configuration back to fresh install defaults."""
    # 1. Take safety snapshot
    create_backup(description="Safety snapshot before Factory Reset", is_auto=True)

    # 2. Reset Wi-Fi configuration
    from .wifi import apply_wifi_config
    apply_wifi_config({
        "ssid": "freedom",
        "password": "changeme123",
        "channel": 6,
        "country": "RU",
        "hw_mode_11n": True,
    })

    # 3. Reset VPN profile
    from .vpn import get_vpn_state_file
    vpn_file = get_vpn_state_file()
    if vpn_file.exists():
        try:
            vpn_file.unlink()
        except Exception:
            pass

    # 4. Restart daemons
    for svc in ("xray", "hostapd", "dnsmasq", "nftables"):
        restart_service(svc)

    return {
        "success": True,
        "message": "Factory reset completed. Wi-Fi SSID reset to 'freedom' and VPN profile cleared.",
    }
