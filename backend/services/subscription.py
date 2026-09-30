"""
Subscription service for Linux VPN Gateway.
Manages VLESS subscription links (HTTP/HTTPS, raw Base64, and multiline URI lists),
persists parsed servers, measures server latencies concurrently, and switches active gateway endpoints.
"""

import base64
import concurrent.futures
import gzip
import hashlib
import json
import os
import platform
import re
import socket
import ssl
import time
import zlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .vpn import apply_vpn_config, mask_uuid, parse_vless_uri
from .network import sync_policy_routing

CONFIG_DIR = Path("/etc/vpn-gateway")
LOCAL_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "configs"
SUBSCRIPTION_FILE_SYSTEM = CONFIG_DIR / "subscription.json"
SUBSCRIPTION_FILE_LOCAL = LOCAL_CONFIG_DIR / "subscription.json"


def get_subscription_file() -> Path:
    if platform.system() == "Linux" and CONFIG_DIR.exists():
        return SUBSCRIPTION_FILE_SYSTEM
    LOCAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return SUBSCRIPTION_FILE_LOCAL


def generate_server_id(vless_uri: str, index: int) -> str:
    """Generate deterministic unique ID for a server profile."""
    h = hashlib.sha256(vless_uri.strip().encode("utf-8")).hexdigest()[:12]
    return f"srv_{index}_{h}"


def decompress_payload(data: bytes) -> bytes:
    """Decompress gzip or zlib binary payload if detected."""
    if not data or not isinstance(data, (bytes, bytearray)):
        return data
    # Gzip magic number 1f 8b
    if data[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(data)
        except Exception:
            pass
    # Zlib magic headers
    if data[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda"):
        try:
            return zlib.decompress(data)
        except Exception:
            pass
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS)
    except Exception:
        pass
    return data


def try_b64_decode(raw_text: str) -> Optional[str]:
    """Clean and decode base64 or urlsafe-base64 text with gzip/zlib decompression."""
    s = raw_text.strip().replace("\r", "").replace("\n", "").replace(" ", "").replace("\t", "").replace('"', '').replace("'", "")
    if not s or len(s) < 4:
        return None

    missing_padding = len(s) % 4
    if missing_padding:
        s += "=" * (4 - missing_padding)

    decoded_bytes = None
    for b64_fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            decoded_bytes = b64_fn(s)
            if decoded_bytes:
                break
        except Exception:
            continue

    if not decoded_bytes:
        return None

    decompressed = decompress_payload(decoded_bytes)
    try:
        return decompressed.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return decompressed.decode("latin-1")
        except Exception:
            return decompressed.decode("utf-8", errors="replace")


def extract_vless_from_json(text: str) -> List[str]:
    """Parse Sing-box, Xray, or Happ JSON and convert outbounds to vless:// links."""
    links = []
    try:
        data = json.loads(text)
    except Exception:
        return []

    def process_item(item: Any):
        if not isinstance(item, dict):
            return

        # Sing-box format (type == "vless")
        if item.get("type") == "vless":
            addr = item.get("server")
            port = item.get("server_port", 443)
            uuid = item.get("uuid")
            tag = item.get("tag") or f"Server-{addr}"
            flow = item.get("flow", "")
            tls = item.get("tls", {})
            reality = tls.get("reality", {})
            utls = tls.get("utls", {})
            pbk = reality.get("public_key") or reality.get("publicKey", "")
            sid = reality.get("short_id") or reality.get("shortId", "")
            sni = tls.get("server_name") or tls.get("serverName") or addr
            fp = utls.get("fingerprint") or tls.get("fingerprint", "chrome")
            sec = "reality" if pbk else ("tls" if tls.get("enabled") else "none")

            if addr and uuid:
                q = {"encryption": "none", "security": sec, "type": "tcp"}
                if flow: q["flow"] = flow
                if sni: q["sni"] = sni
                if fp: q["fp"] = fp
                if pbk: q["pbk"] = pbk
                if sid: q["sid"] = sid
                links.append(f"vless://{uuid}@{addr}:{port}?{urllib.parse.urlencode(q)}#{urllib.parse.quote(str(tag))}")

        # Xray / V2Ray format (protocol == "vless")
        elif item.get("protocol") == "vless":
            tag = item.get("tag") or "Server"
            settings = item.get("settings", {})
            vnext = settings.get("vnext", [])
            if vnext:
                vn0 = vnext[0]
                addr = vn0.get("address")
                port = vn0.get("port", 443)
                users = vn0.get("users", [])
                if users and addr:
                    uuid = users[0].get("id")
                    flow = users[0].get("flow", "")
                    stream = item.get("streamSettings", {})
                    net = stream.get("network", "tcp")
                    sec = stream.get("security", "reality")
                    reality = stream.get("realitySettings", {})
                    tls = stream.get("tlsSettings", {})
                    sni = reality.get("serverName") or tls.get("serverName") or addr
                    fp = reality.get("fingerprint") or tls.get("fingerprint", "chrome")
                    pbk = reality.get("publicKey", "")
                    sid = reality.get("shortId", "")
                    q = {"encryption": "none", "security": sec, "type": net}
                    if flow: q["flow"] = flow
                    if sni: q["sni"] = sni
                    if fp: q["fp"] = fp
                    if pbk: q["pbk"] = pbk
                    if sid: q["sid"] = sid
                    links.append(f"vless://{uuid}@{addr}:{port}?{urllib.parse.urlencode(q)}#{urllib.parse.quote(str(tag))}")

    if isinstance(data, dict):
        for outb in data.get("outbounds", []):
            process_item(outb)
        for srv in data.get("servers", []):
            if isinstance(srv, str) and srv.startswith("vless://"):
                links.append(srv)
            elif isinstance(srv, dict):
                process_item(srv)
    elif isinstance(data, list):
        for elem in data:
            if isinstance(elem, str) and elem.startswith("vless://"):
                links.append(elem)
            elif isinstance(elem, dict):
                process_item(elem)

    return links


def decode_subscription_payload(raw_content: Any) -> List[str]:
    """
    Robust multi-format decoder for VLESS subscriptions.
    Extracts all vless:// links from:
    - Plain text multi-line links
    - Gzip/Deflate compressed binary payloads
    - Base64 encoded links (standard, urlsafe, missing padding, unpadded)
    - Base64 encoded Gzip compressed bytes
    - Double Base64 encoded payloads
    - Sing-box / Xray / Happ JSON configurations with VLESS outbounds
    - Clash / Mihomo YAML with VLESS proxies
    - HTML/XML/Markdown pages containing embedded vless:// links
    """
    if isinstance(raw_content, bytes):
        raw_content = decompress_payload(raw_content).decode("utf-8", errors="replace")

    clean_text = raw_content.strip()

    # 1. Direct regex scan in raw text (fastest, handles plain text, HTML, quotes, markdown)
    direct_links = re.findall(r'vless://[^\s<>"\'`]+', clean_text, re.IGNORECASE)
    if direct_links:
        return direct_links

    # 2. Check JSON directly
    json_links = extract_vless_from_json(clean_text)
    if json_links:
        return json_links

    # 3. Base64 decode attempt
    decoded_b64 = try_b64_decode(clean_text)
    if decoded_b64:
        # Regex search in base64 decoded text
        b64_links = re.findall(r'vless://[^\s<>"\'`]+', decoded_b64, re.IGNORECASE)
        if b64_links:
            return b64_links

        # Check if base64 decoded text is JSON
        json_b64_links = extract_vless_from_json(decoded_b64)
        if json_b64_links:
            return json_b64_links

        # Check if double-base64 encoded
        double_b64 = try_b64_decode(decoded_b64)
        if double_b64:
            d_links = re.findall(r'vless://[^\s<>"\'`]+', double_b64, re.IGNORECASE)
            if d_links:
                return d_links
            d_json_links = extract_vless_from_json(double_b64)
            if d_json_links:
                return d_json_links

    # 4. Check if multiple lines have individual base64 or vless lines
    chunk_links = []
    for line in clean_text.splitlines():
        line = line.strip()
        if not line:
            continue
        found = re.findall(r'vless://[^\s<>"\'`]+', line, re.IGNORECASE)
        if found:
            chunk_links.extend(found)
        else:
            dec = try_b64_decode(line)
            if dec:
                f_dec = re.findall(r'vless://[^\s<>"\'`]+', dec, re.IGNORECASE)
                if f_dec:
                    chunk_links.extend(f_dec)

    if chunk_links:
        return chunk_links

    # 5. Check if URL unquoting reveals vless links
    unquoted = urllib.parse.unquote(clean_text)
    if unquoted != clean_text:
        uq_links = re.findall(r'vless://[^\s<>"\'`]+', unquoted, re.IGNORECASE)
        if uq_links:
            return uq_links

    return []


def fetch_subscription_from_url(url: str, timeout: float = 12.0) -> str:
    """Download subscription text from HTTP/HTTPS endpoint with multi-UA and gzip support."""
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Invalid URL scheme: subscription link must start with http:// or https://")

    # Priority list of User-Agents:
    # 1. v2rayNG - standard for Russian telegram VPN bots (PagerVPN, Marzban, Remnawave)
    # 2. v2rayN - standard Windows desktop client
    # 3. Happ - popular iOS/Android client
    user_agents = [
        "v2rayNG/1.8.12 (Linux; Android 14; Pixel 7 Pro)",
        "v2rayN/6.23 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Happ/3.3.0 (iPhone; iOS 17.5)",
    ]

    last_error = None
    last_text = ""

    for ua in user_agents:
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, identity",
            "Connection": "close",
        }
        req = urllib.request.Request(url, headers=headers)

        content_bytes = None
        # 1. First attempt: standard verified SSL context (with certifi if available)
        try:
            ctx = ssl.create_default_context()
            try:
                import certifi
                ctx.load_verify_locations(cafile=certifi.where())
            except Exception:
                pass

            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                content_bytes = resp.read()
        except (urllib.error.URLError, ssl.SSLError, Exception) as first_err:
            last_error = first_err
            # 2. Fallback attempt: unverified SSL context
            try:
                unverified_ctx = ssl._create_unverified_context()
                unverified_req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(unverified_req, timeout=timeout, context=unverified_ctx) as resp:
                    content_bytes = resp.read()
            except Exception as e2:
                last_error = e2
                continue

        if content_bytes:
            decompressed = decompress_payload(content_bytes)
            try:
                text = decompressed.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = decompressed.decode("latin-1")
                except Exception:
                    text = decompressed.decode("utf-8", errors="replace")

            # If this User-Agent gave valid vless links, return immediately
            if decode_subscription_payload(text):
                return text

            last_text = text

    if last_text:
        return last_text

    if last_error:
        raise last_error

    raise ValueError("Failed to fetch subscription: empty response from server.")


def parse_subscription_source(source: str) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Parse subscription from either HTTP/HTTPS URL or direct text.
    Returns: (servers_list, subscription_url_if_any, error_if_any)
    """
    source_clean = source.strip()
    is_url = source_clean.startswith("http://") or source_clean.startswith("https://")
    sub_url = source_clean if is_url else None

    raw_data = ""
    if is_url:
        try:
            raw_data = fetch_subscription_from_url(source_clean)
        except Exception as e:
            return [], sub_url, f"Failed to fetch subscription URL: {str(e)}"
    else:
        raw_data = source_clean

    vless_links = decode_subscription_payload(raw_data)

    # If no links found and it's a URL without query params, try ?format=v2ray or ?app=v2ray
    if not vless_links and is_url and "?" not in source_clean:
        for query_suffix in ("?format=v2ray", "?app=v2ray", "?client=v2ray"):
            try:
                alt_url = f"{source_clean}{query_suffix}"
                alt_data = fetch_subscription_from_url(alt_url)
                alt_links = decode_subscription_payload(alt_data)
                if alt_links:
                    vless_links = alt_links
                    raw_data = alt_data
                    break
            except Exception:
                continue

    if not vless_links:
        return [], sub_url, "No valid 'vless://' server links found in the provided subscription."

    servers = []
    errors = 0
    for idx, uri in enumerate(vless_links):
        try:
            parsed = parse_vless_uri(uri)
            server_entry = {
                "id": generate_server_id(uri, idx + 1),
                "remark": parsed.get("remark") or f"Server #{idx + 1}",
                "address": parsed.get("address"),
                "port": parsed.get("port"),
                "security": parsed.get("security", "reality").upper(),
                "transport": parsed.get("transport", "tcp").upper(),
                "flow": parsed.get("flow", ""),
                "sni": parsed.get("sni", ""),
                "masked_uuid": mask_uuid(parsed.get("uuid", "")),
                "vless_uri": uri,
                "latency_ms": None,
                "checked_at": None,
            }
            servers.append(server_entry)
        except Exception:
            errors += 1

    if not servers:
        return [], sub_url, f"Failed to parse any server profiles ({errors} links rejected)."

    return servers, sub_url, None


def load_subscription_data() -> Dict[str, Any]:
    """Read saved subscription state from disk."""
    fpath = get_subscription_file()
    if not fpath.exists():
        return {
            "has_subscription": False,
            "url": None,
            "updated_at": None,
            "auto_update": True,
            "active_server_id": None,
            "servers": [],
        }

    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["has_subscription"] = len(data.get("servers", [])) > 0
            return data
    except Exception:
        return {
            "has_subscription": False,
            "url": None,
            "updated_at": None,
            "auto_update": True,
            "active_server_id": None,
            "servers": [],
        }


def save_subscription_data(data: Dict[str, Any]) -> None:
    """Save subscription state atomically with secure permissions."""
    fpath = get_subscription_file()
    fpath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = fpath.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, fpath)
    try:
        os.chmod(fpath, 0o600)
    except Exception:
        pass


def ping_server_tcp(address: str, port: int, timeout: float = 2.0) -> Optional[int]:
    """Quick TCP connect test to measure latency in milliseconds."""
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((address, int(port)))
        elapsed_ms = int((time.time() - start) * 1000)
        sock.close()
        return max(1, elapsed_ms)
    except Exception:
        return None


def ping_servers_batch(servers: List[Dict[str, Any]], max_workers: int = 15) -> Dict[str, Optional[int]]:
    """Test ping for multiple servers concurrently using ThreadPoolExecutor."""
    results = {}

    def _probe(server):
        sid = server["id"]
        addr = server["address"]
        port = server["port"]
        ms = ping_server_tcp(addr, port, timeout=2.0)
        return sid, ms

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_server = {executor.submit(_probe, s): s for s in servers}
        for future in concurrent.futures.as_completed(future_to_server):
            try:
                sid, ms = future.result()
                results[sid] = ms
            except Exception:
                pass

    return results


def import_subscription(source: str, select_first: bool = True) -> Dict[str, Any]:
    """
    Import subscription from URL or text.
    Persists servers and optionally activates the first server if none is currently active.
    """
    servers, sub_url, error = parse_subscription_source(source)
    if error:
        return {"success": False, "error": error}

    existing = load_subscription_data()
    active_id = existing.get("active_server_id")

    # If previous active server exists in new list, keep it
    server_ids = [s["id"] for s in servers]
    if active_id not in server_ids:
        active_id = servers[0]["id"] if (select_first and servers) else None

    sub_record = {
        "url": sub_url,
        "updated_at": time.time(),
        "auto_update": True,
        "active_server_id": active_id,
        "servers": servers,
    }
    save_subscription_data(sub_record)

    # If an active server was selected, apply its configuration immediately
    if active_id:
        active_server = next((s for s in servers if s["id"] == active_id), None)
        if active_server:
            apply_vpn_config(active_server["vless_uri"])
            try:
                sync_policy_routing()
            except Exception:
                pass

    return {
        "success": True,
        "message": f"Successfully imported {len(servers)} servers from subscription.",
        "servers_count": len(servers),
        "count": len(servers),
        "url": sub_url,
        "active_server_id": active_id,
        "servers": servers,
    }


def refresh_subscription() -> Dict[str, Any]:
    """Fetch updated servers for currently configured subscription URL."""
    existing = load_subscription_data()
    url = existing.get("url")
    if not url:
        return {"success": False, "error": "No subscription URL configured to refresh."}

    servers, _, error = parse_subscription_source(url)
    if error:
        return {"success": False, "error": error}

    active_id = existing.get("active_server_id")
    server_ids = [s["id"] for s in servers]

    # Preserve latency data from existing servers if addresses match
    old_pings = {s["address"]: s.get("latency_ms") for s in existing.get("servers", []) if s.get("latency_ms")}
    for s in servers:
        if s["address"] in old_pings:
            s["latency_ms"] = old_pings[s["address"]]

    # Keep active server if still valid, otherwise switch to first
    if active_id not in server_ids and servers:
        active_id = servers[0]["id"]

    existing["updated_at"] = time.time()
    existing["servers"] = servers
    existing["active_server_id"] = active_id
    save_subscription_data(existing)

    # Re-apply active server profile
    if active_id:
        active_server = next((s for s in servers if s["id"] == active_id), None)
        if active_server:
            apply_vpn_config(active_server["vless_uri"])
            try:
                sync_policy_routing()
            except Exception:
                pass

    return {
        "success": True,
        "message": f"Subscription updated. {len(servers)} servers available.",
        "servers_count": len(servers),
        "count": len(servers),
        "active_server_id": active_id,
        "servers": servers,
    }


def activate_server(server_id: str) -> Dict[str, Any]:
    """Switch active VPN connection to the chosen server from subscription."""
    data = load_subscription_data()
    servers = data.get("servers", [])

    target_server = next((s for s in servers if s["id"] == server_id), None)
    if not target_server:
        return {"success": False, "error": f"Server ID '{server_id}' not found in subscription."}

    # Apply configuration and restart Xray
    res = apply_vpn_config(target_server["vless_uri"])
    if not res.get("success"):
        return {"success": False, "error": res.get("error", "Failed to apply VLESS config")}

    # Sync Table 100 anti-loop routes
    try:
        sync_policy_routing()
    except Exception:
        pass

    # Save active_server_id
    data["active_server_id"] = server_id
    save_subscription_data(data)

    return {
        "success": True,
        "message": f"Switched to '{target_server['remark']}' ({target_server['address']}).",
        "active_server_id": server_id,
        "server": target_server,
    }


def ping_subscription_servers(target_server_id: Optional[str] = None) -> Dict[str, Any]:
    """Measure latency for one or all servers in the subscription."""
    data = load_subscription_data()
    servers = data.get("servers", [])
    if not servers:
        return {"success": False, "error": "No servers in subscription to ping."}

    if target_server_id and target_server_id != "all":
        target = next((s for s in servers if s["id"] == target_server_id), None)
        if not target:
            return {"success": False, "error": "Server not found."}
        ms = ping_server_tcp(target["address"], target["port"], timeout=2.5)
        target["latency_ms"] = ms
        target["checked_at"] = time.time()
        save_subscription_data(data)
        return {
            "success": True,
            "results": {target_server_id: ms},
        }

    # Ping all servers concurrently
    pings = ping_servers_batch(servers)
    now = time.time()
    for s in servers:
        if s["id"] in pings:
            s["latency_ms"] = pings[s["id"]]
            s["checked_at"] = now

    save_subscription_data(data)
    return {
        "success": True,
        "results": pings,
        "servers": servers,
    }


def add_custom_vless(vless_uri: str) -> Dict[str, Any]:
    """Add a standalone single VLESS URI to the current list of servers."""
    try:
        parsed = parse_vless_uri(vless_uri)
    except Exception as e:
        return {"success": False, "error": f"Invalid VLESS link: {str(e)}"}

    data = load_subscription_data()
    servers = data.get("servers", [])

    idx = len(servers) + 1
    new_server = {
        "id": generate_server_id(vless_uri, idx),
        "remark": parsed.get("remark") or f"Custom Server #{idx}",
        "address": parsed.get("address"),
        "port": parsed.get("port"),
        "security": parsed.get("security", "reality").upper(),
        "transport": parsed.get("transport", "tcp").upper(),
        "flow": parsed.get("flow", ""),
        "sni": parsed.get("sni", ""),
        "masked_uuid": mask_uuid(parsed.get("uuid", "")),
        "vless_uri": vless_uri,
        "latency_ms": None,
        "checked_at": None,
    }
    servers.insert(0, new_server)
    data["servers"] = servers
    save_subscription_data(data)

    return {
        "success": True,
        "message": f"Added server '{new_server['remark']}' to list.",
        "server": new_server,
        "servers_count": len(servers),
    }


def delete_subscription_server(server_id: str) -> Dict[str, Any]:
    """Remove a server from the saved subscription list."""
    data = load_subscription_data()
    servers = data.get("servers", [])

    remaining = [s for s in servers if s["id"] != server_id]
    if len(remaining) == len(servers):
        return {"success": False, "error": "Server not found."}

    data["servers"] = remaining
    if data.get("active_server_id") == server_id:
        data["active_server_id"] = remaining[0]["id"] if remaining else None

    save_subscription_data(data)
    return {
        "success": True,
        "message": "Server removed.",
        "servers_count": len(remaining),
        "remaining_count": len(remaining),
        "active_server_id": data.get("active_server_id"),
    }
