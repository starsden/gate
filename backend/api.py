"""
FastAPI REST API router and SSE endpoints for Linux VPN Gateway.
Follows clean architecture: endpoints only call service methods.
"""

import asyncio
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .services import system as system_service
from .services import network as network_service
from .services import wifi as wifi_service
from .services import vpn as vpn_service
from .services import clients as clients_service
from .services import logs as logs_service
from .services import firewall as firewall_service
from .services import diagnostics as diagnostics_service
from .services import auth as auth_service
from .services import backups as backups_service
from .services import subscription as subscription_service
from .services import setup as setup_service

router = APIRouter(prefix="/api")


def get_current_token(request: Request) -> Optional[str]:
    """Extract session token from cookie or Authorization header."""
    cookie_token = request.cookies.get("session_token")
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


# Request models
class ServiceRestartRequest(BaseModel):
    service: str


# -------------------------------------------------------------
# REST Endpoints
# -------------------------------------------------------------

@router.get("/status")
def get_status() -> Dict[str, Any]:
    """Aggregated status overview for Dashboard."""
    sys_summary = system_service.get_dashboard_summary()
    wan = network_service.get_wan_status()
    rates = network_service.get_traffic_rates()
    vpn = vpn_service.get_vpn_status()
    wifi = wifi_service.get_wifi_status()
    clients = clients_service.get_connected_clients()

    return {
        "vpn": vpn,
        "internet": wan,
        "wifi": {
            "ssid": wifi["ssid"],
            "status": wifi["status"],
            "connected_devices": len(clients) or wifi.get("connected_devices", 0),
        },
        "traffic": {
            "download_mbps": rates["rx_mbps"],
            "upload_mbps": rates["tx_mbps"],
        },
        "system": sys_summary,
    }


@router.get("/system")
def get_system() -> Dict[str, Any]:
    """Comprehensive hardware, OS, resources, and services payload."""
    return system_service.get_full_system_payload()


@router.get("/network")
def get_network() -> Dict[str, Any]:
    """WAN, LAN, Table 100 policy routing, and firewall status."""
    return {
        "wan": network_service.get_wan_status(),
        "lan": network_service.get_lan_status(),
        "routes_table_100": network_service.get_policy_routes(),
        "rules": network_service.get_policy_rules(),
        "firewall": firewall_service.get_firewall_status(),
    }


@router.post("/network/routes/sync")
def sync_policy_routes() -> Dict[str, Any]:
    """Synchronize Table 100 direct VLESS routes and default xray0 rule."""
    res = network_service.sync_policy_routing()
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to sync routing"))
    return res


@router.post("/network/firewall/apply")
def apply_firewall() -> Dict[str, Any]:
    """Regenerate and reload nftables ruleset."""
    ifaces = network_service.get_default_interfaces()
    res = firewall_service.apply_firewall_ruleset(wan_iface=ifaces["wan"], lan_iface=ifaces["lan"])
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to apply firewall ruleset"))
    return res


@router.get("/wifi")
def get_wifi() -> Dict[str, Any]:
    """Wi-Fi Access Point parameters and operational state."""
    return wifi_service.get_wifi_status()


@router.get("/vpn")
def get_vpn() -> Dict[str, Any]:
    """Xray VLESS/REALITY details and stats."""
    return vpn_service.get_vpn_status()


@router.get("/clients")
def get_clients() -> Dict[str, Any]:
    """Connected Wi-Fi / LAN clients."""
    devices = clients_service.get_connected_clients()
    return {
        "count": len(devices),
        "clients": devices,
    }


@router.post("/system/services/{service_name}/restart")
def restart_system_service(service_name: str) -> Dict[str, Any]:
    """Safely restart an allowed system service."""
    res = system_service.restart_service(service_name)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Restart failed"))
    return res


@router.get("/logs/{service}")
def get_service_logs(service: str, lines: int = Query(default=100, ge=10, le=500)) -> Dict[str, Any]:
    """Retrieve journalctl logs for a service."""
    log_lines = logs_service.get_logs(service, lines)
    return {
        "service": service,
        "lines_count": len(log_lines),
        "logs": log_lines,
    }


# -------------------------------------------------------------
# Placeholders for Subsequent Phases (clean service contracts)
# -------------------------------------------------------------

@router.post("/vpn/restart")
def restart_vpn() -> Dict[str, Any]:
    res = vpn_service.set_vpn_state("restart")
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to restart VPN"))
    return res


@router.post("/vpn/connect")
def connect_vpn() -> Dict[str, Any]:
    res = vpn_service.set_vpn_state("start")
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to connect VPN"))
    return res


@router.post("/vpn/disconnect")
def disconnect_vpn() -> Dict[str, Any]:
    res = vpn_service.set_vpn_state("stop")
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to disconnect VPN"))
    return res


@router.post("/vpn/test")
def test_vpn() -> Dict[str, Any]:
    return vpn_service.test_vpn_connection()


@router.post("/vpn/parse")
def parse_vless(payload: Dict[str, str]) -> Dict[str, Any]:
    uri = payload.get("vless_uri", "").strip()
    if not uri:
        raise HTTPException(status_code=400, detail="Missing 'vless_uri' in request body.")
    try:
        profile = vpn_service.parse_vless_uri(uri)
        return {
            "success": True,
            "profile": {
                "server": profile["address"],
                "port": profile["port"],
                "security": profile["security"].upper(),
                "transport": profile["transport"].upper(),
                "sni": profile["sni"],
                "fingerprint": profile["fingerprint"],
                "flow": profile["flow"],
                "remark": profile["remark"],
                "masked_uuid": vpn_service.mask_uuid(profile["uuid"]),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse VLESS URI: {str(e)}")


@router.post("/vpn/import")
def import_vless(payload: Dict[str, str]) -> Dict[str, Any]:
    uri = payload.get("vless_uri", "").strip()
    if not uri:
        raise HTTPException(status_code=400, detail="Missing 'vless_uri' in request body.")

    # Auto-detect if user pasted a subscription URL or multiline / Base64 payload
    if uri.startswith("http://") or uri.startswith("https://") or ("\n" in uri) or (not uri.startswith("vless://")):
        sub_res = subscription_service.import_subscription(uri)
        if sub_res.get("success"):
            return sub_res

    res = vpn_service.apply_vpn_config(uri)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to import and apply VLESS"))
    # Also add custom server to current server list
    try:
        subscription_service.add_custom_vless(uri)
    except Exception:
        pass
    return res


# -------------------------------------------------------------
# VLESS Subscription Endpoints
# -------------------------------------------------------------

@router.get("/vpn/subscription")
def get_subscription() -> Dict[str, Any]:
    """Retrieve saved subscription state and list of servers."""
    return subscription_service.load_subscription_data()


@router.post("/vpn/subscription/import")
def import_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Import subscription from URL, raw Base64, or multiline links."""
    source = (payload.get("source") or payload.get("url") or payload.get("vless_uri") or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="Missing subscription 'source' or 'url' in payload.")
    res = subscription_service.import_subscription(source)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to import subscription"))
    return res


@router.post("/vpn/subscription/refresh")
def refresh_subscription() -> Dict[str, Any]:
    """Refresh servers from the active subscription URL."""
    res = subscription_service.refresh_subscription()
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to refresh subscription"))
    return res


@router.post("/vpn/subscription/select")
def select_subscription_server(payload: Dict[str, str]) -> Dict[str, Any]:
    """Activate a specific server ID from the subscription."""
    server_id = payload.get("server_id", "").strip()
    if not server_id:
        raise HTTPException(status_code=400, detail="Missing 'server_id' in request.")
    res = subscription_service.activate_server(server_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to switch active server"))
    return res


@router.post("/vpn/subscription/ping")
def ping_subscription_servers(payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """Probe latency for one or all servers in subscription."""
    target_id = (payload or {}).get("server_id", "all")
    res = subscription_service.ping_subscription_servers(target_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Ping probe failed"))
    return res


@router.delete("/vpn/subscription/servers/{server_id}")
def delete_subscription_server(server_id: str) -> Dict[str, Any]:
    """Remove a server from the subscription list."""
    res = subscription_service.delete_subscription_server(server_id)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "Server not found"))
    return res


@router.post("/wifi/apply")
def apply_wifi(payload: Dict[str, Any]) -> Dict[str, Any]:
    res = wifi_service.apply_wifi_config(payload)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to apply Wi-Fi configuration"))
    return res


@router.post("/network/apply")
def apply_network(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": True,
        "message": "Network configuration applied (Phase 4)",
    }


@router.get("/diagnostics")
def get_diagnostics() -> Dict[str, Any]:
    """Run full diagnostic checklist and report system health."""
    return diagnostics_service.run_diagnostics()


@router.post("/repair")
def run_auto_repair() -> Dict[str, Any]:
    """Execute automatic self-healing repair pipeline."""
    res = diagnostics_service.execute_auto_repair()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("message", "Repair failed"))
    return res


# -------------------------------------------------------------
# Setup Wizard Endpoints (Multi-step Onboarding)
# -------------------------------------------------------------

@router.get("/setup/status")
def get_setup_wizard_status() -> Dict[str, Any]:
    """Retrieve setup wizard progress, step, and flags."""
    state = setup_service.load_setup_state()
    return {
        "completed": setup_service.is_setup_completed(),
        "state": state,
    }


@router.get("/setup/packages/check")
def check_packages_endpoint() -> Dict[str, Any]:
    """Inspect missing system packages and tools."""
    return setup_service.check_system_packages()


@router.post("/setup/packages/install")
def install_packages_endpoint() -> Dict[str, Any]:
    """Trigger background installation of missing packages."""
    return setup_service.start_package_installation()


@router.get("/setup/packages/progress")
def get_packages_progress_endpoint() -> Dict[str, Any]:
    """Poll installation status and logs."""
    return setup_service.get_package_install_status()


@router.get("/setup/packages/stream")
async def stream_packages_progress():
    """SSE real-time stream of package installation progress."""
    async def event_generator():
        while True:
            data = setup_service.get_package_install_status()
            yield f"data: {json.dumps(data)}\n\n"
            if data["status"] in ("completed", "error"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/setup/wifi")
def get_setup_wifi_endpoint() -> Dict[str, Any]:
    """Retrieve hardware detection and staged Wi-Fi parameters."""
    return setup_service.get_wifi_stage_data()


@router.post("/setup/wifi")
def save_setup_wifi_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save Wi-Fi parameters for initial configuration."""
    success, err = setup_service.save_wifi_stage_data(payload)
    if not success:
        raise HTTPException(status_code=400, detail=err or "Invalid Wi-Fi parameters")
    return {"success": True, "message": "Wi-Fi parameters saved"}


@router.get("/setup/vpn")
def get_setup_vpn_endpoint() -> Dict[str, Any]:
    """Retrieve staged VPN parameters."""
    return setup_service.get_vpn_stage_data()


@router.post("/setup/vpn")
def save_setup_vpn_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save initial VPN parameters (or skip)."""
    success, err = setup_service.save_vpn_stage_data(payload)
    if not success:
        raise HTTPException(status_code=400, detail=err or "Invalid VPN URI")
    return {"success": True, "message": "VPN configuration saved"}


@router.post("/setup/account")
def save_setup_account_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save dashboard administrator credentials."""
    success, err = setup_service.save_account_stage_data(payload)
    if not success:
        raise HTTPException(status_code=400, detail=err or "Invalid account parameters")
    return {"success": True, "message": "Admin credentials staged"}


@router.post("/setup/finalize")
def finalize_setup_endpoint() -> Dict[str, Any]:
    """Execute final system configuration tasks in background."""
    return setup_service.start_final_setup()


@router.get("/setup/finalize/progress")
def get_finalize_progress_endpoint(response: Response) -> Dict[str, Any]:
    """Poll final setup execution status, progress, and logs."""
    res = setup_service.get_final_setup_status()
    if res.get("token") and res.get("status") == "completed":
        response.set_cookie(
            key="session_token",
            value=res["token"],
            path="/",
            httponly=True,
            samesite="lax",
            max_age=auth_service.SESSION_TTL_SECONDS,
        )
    return res


@router.get("/setup/finalize/stream")
async def stream_finalize_progress():
    """SSE real-time stream of final setup execution."""
    async def event_generator():
        while True:
            data = setup_service.get_final_setup_status()
            yield f"data: {json.dumps(data)}\n\n"
            if data["status"] in ("completed", "error"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# -------------------------------------------------------------
# Authentication Endpoints (Phase 6)
# -------------------------------------------------------------

@router.get("/auth/status")
def auth_status(request: Request) -> Dict[str, Any]:
    token = get_current_token(request)
    status = auth_service.get_auth_status(token)
    status["setup_required"] = not setup_service.is_setup_completed()
    return status


@router.post("/auth/setup")
def auth_setup(payload: Dict[str, str], response: Response) -> Dict[str, Any]:
    pwd = payload.get("password", "").strip()
    success, token, err = auth_service.setup_initial_password(pwd)
    if not success:
        raise HTTPException(status_code=400, detail=err or "Setup failed")
    response.set_cookie(key="session_token", value=token, path="/", httponly=True, samesite="lax", max_age=auth_service.SESSION_TTL_SECONDS)
    return {"success": True, "token": token, "username": "admin"}


@router.post("/auth/login")
def auth_login(payload: Dict[str, str], response: Response) -> Dict[str, Any]:
    pwd = payload.get("password", "").strip()
    success, token, err = auth_service.authenticate(pwd)
    if not success:
        raise HTTPException(status_code=401, detail=err or "Invalid credentials")
    response.set_cookie(key="session_token", value=token, path="/", httponly=True, samesite="lax", max_age=auth_service.SESSION_TTL_SECONDS)
    return {"success": True, "token": token, "username": "admin"}


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response) -> Dict[str, Any]:
    token = get_current_token(request)
    auth_service.revoke_session(token)
    response.delete_cookie(key="session_token", path="/")
    return {"success": True, "message": "Logged out successfully"}


@router.post("/auth/change-password")
def auth_change_password(payload: Dict[str, str], request: Request) -> Dict[str, Any]:
    token = get_current_token(request)
    if not auth_service.is_first_run() and not auth_service.verify_session(token):
        raise HTTPException(status_code=401, detail="Authentication required")
    old_p = payload.get("old_password", "").strip()
    new_p = payload.get("new_password", "").strip()
    success, err = auth_service.change_password(old_p, new_p)
    if not success:
        raise HTTPException(status_code=400, detail=err or "Password change failed")
    return {"success": True, "message": "Admin password updated successfully"}


# -------------------------------------------------------------
# Backups and Rollback Endpoints (Phase 6)
# -------------------------------------------------------------

@router.get("/backups")
def get_backups() -> Dict[str, Any]:
    return {"backups": backups_service.list_backups()}


@router.post("/backups")
def create_backup(payload: Dict[str, Any] = None) -> Dict[str, Any]:
    desc = (payload or {}).get("description", "Manual snapshot")
    res = backups_service.create_backup(description=desc)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Backup failed"))
    return res


@router.post("/backups/{backup_id}/restore")
def restore_backup(backup_id: str) -> Dict[str, Any]:
    res = backups_service.restore_backup(backup_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Restore failed"))
    return res


@router.delete("/backups/{backup_id}")
def delete_backup(backup_id: str) -> Dict[str, Any]:
    res = backups_service.delete_backup(backup_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Delete failed"))
    return res


@router.get("/backups/{backup_id}/download")
def download_backup(backup_id: str):
    fpath = backups_service.get_backup_filepath(backup_id)
    if not fpath or not fpath.exists():
        raise HTTPException(status_code=404, detail="Backup archive not found")
    return FileResponse(path=str(fpath), filename=backup_id, media_type="application/gzip")


@router.post("/backups/factory-reset")
def factory_reset() -> Dict[str, Any]:
    return backups_service.execute_factory_reset()


@router.post("/system/reboot")
def reboot_gateway() -> Dict[str, Any]:
    """Graceful reboot of the gateway device."""
    import subprocess
    if platform.system() == "Linux":
        try:
            subprocess.Popen(["systemctl", "reboot"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Reboot command failed: {str(e)}")
    return {"success": True, "message": "Gateway reboot initiated"}


# -------------------------------------------------------------
# Server-Sent Events (SSE) Real-time Stream
# -------------------------------------------------------------

@router.get("/events")
async def events_stream():
    """SSE endpoint streaming live metrics every 1.5 seconds."""
    async def event_generator():
        try:
            while True:
                # Gather live metrics
                sys_summary = system_service.get_dashboard_summary()
                rates = network_service.get_traffic_rates()
                vpn = vpn_service.get_vpn_status()
                services = system_service.get_all_services()
                clients = clients_service.get_connected_clients()
                wifi = wifi_service.get_wifi_status()

                event_data = {
                    "system": sys_summary,
                    "traffic": {
                        "rx_mbps": rates["rx_mbps"],
                        "tx_mbps": rates["tx_mbps"],
                    },
                    "vpn_status": vpn["status"],
                    "vpn_latency": vpn.get("latency_ms", 0),
                    "services": {s["name"]: s["status"] for s in services},
                    "wifi": {
                        "ssid": wifi["ssid"],
                        "status": wifi["status"],
                        "channel": wifi["channel"],
                        "connected_devices": len(clients),
                    },
                }

                yield f"data: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            # Client disconnected
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
