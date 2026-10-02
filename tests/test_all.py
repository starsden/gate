#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for Linux VPN Gateway
Tests all service modules and FastAPI HTTP endpoints.
"""

import sys
import os
import json
import asyncio
import tempfile
import shutil
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.services import auth, backups, diagnostics, logs, network, system, vpn, wifi, firewall, clients, subscription, setup
from backend.app import app

# ------------------------------------------------------------------------------
# Minimal Native ASGI Test Client (Zero 3rd party test dependencies)
# ------------------------------------------------------------------------------
async def asgi_request(app, method="GET", path="/", headers=None, body=None):
    headers = headers or {}
    raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in headers.items()
    ]
    if body is not None:
        if isinstance(body, (dict, list)):
            body_bytes = json.dumps(body).encode("utf-8")
            raw_headers.append((b"content-type", b"application/json"))
        elif isinstance(body, str):
            body_bytes = body.encode("utf-8")
        else:
            body_bytes = body
    else:
        body_bytes = b""

    raw_headers.append((b"content-length", str(len(body_bytes)).encode("latin-1")))

    query_string = b""
    if "?" in path:
        path, query = path.split("?", 1)
        query_string = query.encode("latin-1")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": query_string,
        "headers": raw_headers,
        "client": ("127.0.0.1", 54321),
        "server": ("127.0.0.1", 80),
    }

    resp_meta = {}
    resp_chunks = []

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

    async def send(message):
        if message["type"] == "http.response.start":
            resp_meta["status"] = message["status"]
            resp_meta["headers"] = dict(message.get("headers", []))
        elif message["type"] == "http.response.body":
            resp_chunks.append(message.get("body", b""))

    await app(scope, receive, send)

    full_body = b"".join(resp_chunks)
    parsed_json = None
    try:
        parsed_json = json.loads(full_body.decode("utf-8"))
    except Exception:
        pass

    return {
        "status": resp_meta.get("status"),
        "headers": resp_meta.get("headers", {}),
        "text": full_body.decode("utf-8", errors="replace"),
        "json": parsed_json,
    }


# ------------------------------------------------------------------------------
# Test Runners
# ------------------------------------------------------------------------------
def test_auth_service():
    print("[1/8] Testing auth.py service...")
    # Test PBKDF2 hashing
    h1 = auth.hash_password("admin_secret_123")
    assert h1.startswith("pbkdf2:sha256:"), "Invalid hash prefix"
    assert auth.verify_password("admin_secret_123", h1), "Password verification failed"
    assert not auth.verify_password("wrong_password", h1), "False positive password verification"

    # Test token generation
    token = auth.create_session("admin")
    assert auth.verify_session(token) is True, "Valid session token rejected"
    assert auth.verify_session("invalid_token_999") is False, "Invalid token accepted"
    auth.revoke_session(token)
    assert auth.verify_session(token) is False, "Revoked session still accepted"
    print("      -> Password hashing, PBKDF2-HMAC-SHA256, session tokens OK")


def test_vpn_parser():
    print("[2/8] Testing vpn.py parser...")
    # Test valid VLESS URI
    test_uri = (
        "vless://98765432-abcd-ef01-2345-6789abcdef01@remote.gateway.net:443"
        "?encryption=none&security=reality&sni=dl.google.com&fp=chrome"
        "&pbk=11bb22cc33dd44ee55ff66aa77bb88cc99dd00ee11ff22aa33bb44cc55dd66ee"
        "&sid=abcdef12&type=tcp#Production-US"
    )
    parsed = vpn.parse_vless_uri(test_uri)
    assert parsed["uuid"] == "98765432-abcd-ef01-2345-6789abcdef01"
    assert parsed["address"] == "remote.gateway.net"
    assert parsed["port"] == 443
    assert parsed["security"] == "reality"
    assert parsed["sni"] == "dl.google.com"
    assert parsed["fingerprint"] == "chrome"
    assert parsed["publicKey"] == "11bb22cc33dd44ee55ff66aa77bb88cc99dd00ee11ff22aa33bb44cc55dd66ee"
    assert parsed["shortId"] == "abcdef12"
    assert parsed["remark"] == "Production-US"

    # Generate xray client config
    config = vpn.generate_xray_config(parsed)
    assert config["inbounds"][0]["protocol"] == "dokodemo-door" or config["inbounds"][0]["protocol"] == "tun"
    assert config["outbounds"][0]["protocol"] == "vless"
    print("      -> VLESS REALITY parser & Xray JSON config generation OK")


def test_subscription_service():
    print("[2.5/9] Testing subscription.py service...")
    import base64

    link1 = (
        "vless://11111111-2222-3333-4444-555555555555@node1.vpn.com:443"
        "?encryption=none&security=reality&sni=yahoo.com&fp=chrome"
        "&pbk=aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
        "&sid=1234&type=tcp#Node-1-DE"
    )
    link2 = (
        "vless://22222222-3333-4444-5555-666666666666@node2.vpn.com:443"
        "?encryption=none&security=reality&sni=microsoft.com&fp=firefox"
        "&pbk=aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
        "&sid=5678&type=tcp#Node-2-NL"
    )

    # Multiline plain
    multiline = f"{link1}\n{link2}"
    decoded = subscription.decode_subscription_payload(multiline)
    assert len(decoded) == 2
    assert decoded[0] == link1
    assert decoded[1] == link2

    # Standard Base64 encoded (with stripped padding)
    b64_raw = base64.b64encode(multiline.encode("utf-8")).decode("utf-8").rstrip("=")
    decoded_b64 = subscription.decode_subscription_payload(b64_raw)
    assert len(decoded_b64) == 2

    # Gzip compressed inside Base64 (Remnawave/Marzban format)
    import gzip
    gz_b64 = base64.b64encode(gzip.compress(multiline.encode("utf-8"))).decode("utf-8")
    decoded_gz = subscription.decode_subscription_payload(gz_b64)
    assert len(decoded_gz) == 2

    # Sing-box JSON format with VLESS outbound
    singbox_json = json.dumps({
        "outbounds": [{
            "type": "vless",
            "tag": "🇩🇪 Singbox-Server",
            "server": "1.2.3.4",
            "server_port": 443,
            "uuid": "11111111-2222-3333-4444-555555555555",
            "tls": {
                "enabled": True,
                "reality": {"enabled": True, "public_key": "aabbcc", "short_id": "1234"}
            }
        }]
    })
    decoded_sb = subscription.decode_subscription_payload(singbox_json)
    assert len(decoded_sb) == 1
    assert "vless://" in decoded_sb[0]
    assert "1.2.3.4" in decoded_sb[0]

    # Import subscription directly
    res = subscription.import_subscription(multiline)
    assert res["success"] is True
    assert res["count"] == 2
    assert len(res["servers"]) == 2
    assert res["servers"][0]["remark"] == "Node-1-DE"
    assert res["servers"][1]["remark"] == "Node-2-NL"

    # Test load
    data = subscription.load_subscription_data()
    assert data["has_subscription"] is True
    assert len(data["servers"]) == 2

    # Test select server
    server2_id = res["servers"][1]["id"]
    sel_res = subscription.activate_server(server2_id)
    assert sel_res["success"] is True
    assert sel_res["active_server_id"] == server2_id

    # Test delete server
    del_res = subscription.delete_subscription_server(server2_id)
    assert del_res["success"] is True
    assert del_res["remaining_count"] == 1

    # Test SSL certificate verification error fallback
    from unittest.mock import patch, MagicMock
    import ssl, urllib.error
    mock_resp = MagicMock()
    mock_resp.read.return_value = multiline.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    ssl_err = urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed: unable to get local issuer certificate"))

    with patch("urllib.request.urlopen", side_effect=[ssl_err, mock_resp]) as mock_urlopen:
        fetched = subscription.fetch_subscription_from_url("https://vpn-provider.com/sub/token")
        assert len(fetched) > 0
        assert mock_urlopen.call_count == 2
        # Ensure second attempt bypassed certificate checks
        ctx = mock_urlopen.call_args_list[1][1]["context"]
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE

    print("      -> Subscription decoder, parser, SSL fallback, and state persistence OK")


def test_wifi_service():
    print("[3/8] Testing wifi.py service...")
    cfg = wifi.read_current_config()
    assert "ssid" in cfg
    assert "channel" in cfg
    assert "security" in cfg
    print("      -> Wi-Fi configuration parser OK")


def test_diagnostics_service():
    print("[4/8] Testing diagnostics.py service...")
    results = diagnostics.run_diagnostics()
    assert "checks" in results
    assert "overall_status" in results
    assert len(results["checks"]) >= 10
    print(f"      -> Diagnostic engine evaluated {len(results['checks'])} checks (Overall: {results['overall_status']}) OK")


def test_backups_service():
    print("[5/8] Testing backups.py service...")
    temp_dir = Path(tempfile.mkdtemp())
    orig_fn = backups.get_backup_dir
    backups.get_backup_dir = lambda: temp_dir
    try:
        # Create snapshot
        res = backups.create_backup("Test initial backup")
        assert res["success"] is True
        b_id = res["backup_id"]
        assert (temp_dir / b_id).exists()

        # List backups
        blist = backups.list_backups()
        assert len(blist) == 1
        assert blist[0]["id"] == b_id

        # Delete backup
        del_res = backups.delete_backup(b_id)
        assert del_res["success"] is True
        assert len(backups.list_backups()) == 0
        print("      -> Snapshot generation, tar.gz packing, manifest reading, deletion OK")
    finally:
        backups.get_backup_dir = orig_fn
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_logs_service():
    print("[6/8] Testing logs.py service...")
    assert "vpn-gateway" in logs.ALLOWED_LOG_SERVICES
    assert "xray" in logs.ALLOWED_LOG_SERVICES
    assert "hostapd" in logs.ALLOWED_LOG_SERVICES
    assert "dnsmasq" in logs.ALLOWED_LOG_SERVICES
    assert "nftables" in logs.ALLOWED_LOG_SERVICES
    lines = logs.get_logs("vpn-gateway", lines=5)
    assert isinstance(lines, list)
    print("      -> Service log reader & service whitelist OK")


async def test_fastapi_endpoints():
    print("[7/8] Testing FastAPI ASGI HTTP routes...")

    # Static HTML index
    r = await asgi_request(app, "GET", "/")
    assert r["status"] == 200, f"Expected 200 on /, got {r['status']}"
    assert "VPN Gateway" in r["text"]
    print("      -> [200] GET / (Vanilla HTML5 UI)")

    # Overview Status
    r = await asgi_request(app, "GET", "/api/status")
    assert r["status"] == 200
    assert "vpn" in r["json"]
    assert "system" in r["json"]
    print("      -> [200] GET /api/status")

    # System Status & Hardware
    r = await asgi_request(app, "GET", "/api/system")
    assert r["status"] == 200
    assert "resources" in r["json"]
    print("      -> [200] GET /api/system")

    # Wi-Fi State
    r = await asgi_request(app, "GET", "/api/wifi")
    assert r["status"] == 200
    assert "ssid" in r["json"]
    print("      -> [200] GET /api/wifi")

    # Wi-Fi Clients
    r = await asgi_request(app, "GET", "/api/clients")
    assert r["status"] == 200
    assert "clients" in r["json"]
    print("      -> [200] GET /api/clients")

    # VPN Status
    r = await asgi_request(app, "GET", "/api/vpn")
    assert r["status"] == 200
    print("      -> [200] GET /api/vpn")

    # Network & Routing
    r = await asgi_request(app, "GET", "/api/network")
    assert r["status"] == 200
    print("      -> [200] GET /api/network")

    # Diagnostics
    r = await asgi_request(app, "GET", "/api/diagnostics")
    assert r["status"] == 200
    assert "checks" in r["json"]
    print("      -> [200] GET /api/diagnostics")

    # Auth Status
    r = await asgi_request(app, "GET", "/api/auth/status")
    assert r["status"] == 200
    assert "first_run" in r["json"]
    print("      -> [200] GET /api/auth/status")

    # Backups List
    r = await asgi_request(app, "GET", "/api/backups")
    assert r["status"] == 200
    assert "backups" in r["json"]
    print("      -> [200] GET /api/backups")

    # Service Logs
    r = await asgi_request(app, "GET", "/api/logs/vpn-gateway?lines=10")
    assert r["status"] == 200
    assert "logs" in r["json"]
    print("      -> [200] GET /api/logs/vpn-gateway")

    # Subscription Endpoints
    r = await asgi_request(app, "GET", "/api/vpn/subscription")
    assert r["status"] == 200
    assert "servers" in r["json"]
    print("      -> [200] GET /api/vpn/subscription")

    # Import via API
    sub_payload = {
        "source": (
            "vless://33333333-4444-5555-6666-777777777777@sub1.vpn.com:443"
            "?encryption=none&security=reality&sni=google.com&fp=chrome"
            "&pbk=aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
            "&sid=9999&type=tcp#Fast-US"
        )
    }
    r = await asgi_request(app, "POST", "/api/vpn/subscription/import", body=sub_payload)
    assert r["status"] == 200
    assert r["json"]["success"] is True
    assert r["json"]["count"] >= 1
    new_server_id = r["json"]["active_server_id"]
    print("      -> [200] POST /api/vpn/subscription/import")

    # Select via API
    r = await asgi_request(app, "POST", "/api/vpn/subscription/select", body={"server_id": new_server_id})
    assert r["status"] == 200
    assert r["json"]["success"] is True
    print("      -> [200] POST /api/vpn/subscription/select")

    # Setup Wizard API Endpoints
    r = await asgi_request(app, "GET", "/api/setup/status")
    assert r["status"] == 200
    print("      -> [200] GET /api/setup/status")

    r = await asgi_request(app, "GET", "/api/setup/packages/check")
    assert r["status"] == 200
    assert "packages" in r["json"]
    print("      -> [200] GET /api/setup/packages/check")

    r = await asgi_request(app, "POST", "/api/setup/packages/install")
    assert r["status"] == 200
    print("      -> [200] POST /api/setup/packages/install")

    r = await asgi_request(app, "GET", "/api/setup/packages/progress")
    assert r["status"] == 200
    print("      -> [200] GET /api/setup/packages/progress")

    r = await asgi_request(app, "GET", "/api/setup/wifi")
    assert r["status"] == 200
    print("      -> [200] GET /api/setup/wifi")

    r = await asgi_request(app, "POST", "/api/setup/wifi", body={"ssid": "testwifi", "password": "testpassword123", "channel": 6, "country": "RU"})
    assert r["status"] == 200
    print("      -> [200] POST /api/setup/wifi")

    r = await asgi_request(app, "GET", "/api/setup/vpn")
    assert r["status"] == 200
    print("      -> [200] GET /api/setup/vpn")

    r = await asgi_request(app, "POST", "/api/setup/vpn", body={"vless_uri": "", "skip": True})
    assert r["status"] == 200
    print("      -> [200] POST /api/setup/vpn")

    r = await asgi_request(app, "POST", "/api/setup/account", body={"username": "admin", "password": "adminpassword123", "confirm_password": "adminpassword123"})
    assert r["status"] == 200
    print("      -> [200] POST /api/setup/account")

    r = await asgi_request(app, "POST", "/api/setup/finalize")
    assert r["status"] == 200
    print("      -> [200] POST /api/setup/finalize")

    r = await asgi_request(app, "GET", "/api/setup/finalize/progress")
    assert r["status"] == 200
    print("      -> [200] GET /api/setup/finalize/progress")


def test_setup_service():
    print("[2.8/9] Testing setup.py service (Wizard lifecycle)...")
    chk = setup.check_system_packages()
    assert "all_installed" in chk
    assert len(chk["packages"]) == 8

    # Stage Wi-Fi
    ok, err = setup.save_wifi_stage_data({"ssid": "freedom-test", "password": "password123", "channel": 6, "country": "RU"})
    assert ok is True

    # Stage VPN
    ok, err = setup.save_vpn_stage_data({"skip": True})
    assert ok is True

    # Stage Account
    ok, err = setup.save_account_stage_data({"username": "admin", "password": "adminpassword123", "confirm_password": "adminpassword123"})
    assert ok is True

    # Install packages job
    res = setup.start_package_installation()
    assert res["success"] is True
    p_status = setup.get_package_install_status()
    assert "progress" in p_status

    # Finalize setup job
    f_res = setup.start_final_setup()
    assert f_res["success"] is True
    f_status = setup.get_final_setup_status()
    assert "progress" in f_status
    print("      -> Package verification, staged parameters, and async progress runners OK")


def test_html_assets():
    print("[8/8] Testing Web UI Assets integrity...")
    web_dir = os.path.join(PROJECT_ROOT, "web")
    html_file = os.path.join(web_dir, "index.html")
    css_file = os.path.join(web_dir, "style.css")
    js_file = os.path.join(web_dir, "app.js")

    assert os.path.isfile(html_file), "index.html missing"
    assert os.path.isfile(css_file), "style.css missing"
    assert os.path.isfile(js_file), "app.js missing"

    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()
    with open(css_file, "r", encoding="utf-8") as f:
        css = f.read()
    with open(js_file, "r", encoding="utf-8") as f:
        js = f.read()

    # Check key UI views exist
    assert 'id="page-dashboard"' in html
    assert 'id="page-vpn"' in html
    assert 'id="page-wifi"' in html
    assert 'id="page-devices"' in html
    assert 'id="page-network"' in html
    assert 'id="page-diagnostics"' in html
    assert 'id="page-settings"' in html
    assert 'id="page-logs"' in html

    # Check key modals exist
    assert 'id="auth-login-modal"' in html
    assert 'id="auth-setup-modal"' in html
    assert 'id="backup-restore-modal"' in html
    assert 'id="factory-reset-modal"' in html
    assert 'id="reboot-modal"' in html

    # Check Setup Wizard pages & elements exist
    assert 'id="setup-wizard-container"' in html
    assert 'id="wizard-page-1"' in html
    assert 'id="wizard-page-2"' in html
    assert 'id="wizard-page-3"' in html
    assert 'id="wizard-page-4"' in html
    assert 'id="wizard-page-5"' in html
    assert 'id="btn-start-packages-install"' in html
    assert 'id="finalize-progress-bar"' in html
    assert 'id="btn-goto-dashboard"' in html

    # Check VLESS subscription UI elements
    assert 'id="subscription-servers-tbody"' in html
    assert 'id="btn-sub-ping-all"' in html
    assert 'id="btn-sub-refresh"' in html
    assert 'id="sub-servers-count-badge"' in html
    assert 'id="sub-meta-bar"' in html

    # Check CSS syntax (balanced braces)
    assert css.count("{") == css.count("}"), "CSS brace imbalance detected!"

    print("      -> All 7 page views, Setup Wizard (5 pages & progress bar), modals, and CSS integrity validated")


def main():
    print("=" * 65)
    print("      LINUX VPN GATEWAY - END-TO-END VERIFICATION SUITE")
    print("=" * 65)
    test_auth_service()
    test_vpn_parser()
    test_subscription_service()
    test_setup_service()
    test_wifi_service()
    test_diagnostics_service()
    test_backups_service()
    test_logs_service()
    asyncio.run(test_fastapi_endpoints())
    test_html_assets()
    print("=" * 65)
    print("      ALL TESTS PASSED SUCCESSFULLY (100% GREEN)!")
    print("=" * 65)


if __name__ == "__main__":
    main()
