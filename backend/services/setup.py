"""
Setup service for Linux VPN Gateway.
Manages the multi-step onboarding wizard:
1. Missing system packages check and installation (hostapd, dnsmasq, nftables, xray, etc.)
2. Initial Wi-Fi configuration (SSID, password, channel, country)
3. Initial VPN configuration (VLESS / REALITY URI or subscription)
4. Dashboard administrator account configuration
5. Final system deployment with progress tracking (sysctl, hostapd, dnsmasq, nftables, routing, services)
"""

import json
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import auth as auth_service
from . import network as network_service
from . import wifi as wifi_service
from . import vpn as vpn_service
from . import subscription as subscription_service
from . import firewall as firewall_service

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_CONFIG_DIR = BASE_DIR / "configs"
SYS_CONFIG_DIR = Path("/etc/vpn-gateway")
SYSTEMD_DIR = Path("/etc/systemd/system")


def _is_linux() -> bool:
    return platform.system() == "Linux"


def get_config_dir() -> Path:
    if _is_linux() and SYS_CONFIG_DIR.exists():
        return SYS_CONFIG_DIR
    LOCAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return LOCAL_CONFIG_DIR


def get_setup_state_file() -> Path:
    return get_config_dir() / "setup_state.json"


# In-memory states for background jobs
_package_install_lock = threading.Lock()
_package_install_state: Dict[str, Any] = {
    "status": "idle",  # "idle" | "running" | "completed" | "error"
    "progress": 0,
    "message": "",
    "logs": [],
    "error": None,
}

_final_setup_lock = threading.Lock()
_final_setup_state: Dict[str, Any] = {
    "status": "idle",  # "idle" | "running" | "completed" | "error"
    "progress": 0,
    "current_task": "",
    "logs": [],
    "error": None,
    "token": None,
}


def load_setup_state() -> Dict[str, Any]:
    state_file = get_setup_state_file()
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except Exception:
            pass

    # Default state
    # If auth.json already has an established admin password from an existing installation,
    # we treat setup as completed to ensure backwards compatibility.
    is_existing = not auth_service.is_first_run()
    default_state = {
        "completed": is_existing,
        "completed_at": time.time() if is_existing else None,
        "current_step": 1 if not is_existing else 5,
        "packages_installed": is_existing,
        "wifi": {
            "ssid": "freedom",
            "password": "freedom123",
            "channel": 6,
            "country": "RU",
            "security": "WPA2",
        },
        "vpn": {
            "vless_uri": "",
            "skip": False,
        },
        "account": {
            "username": "admin",
        },
    }
    return default_state


def save_setup_state(state: Dict[str, Any]) -> None:
    state_file = get_setup_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_file)


def is_setup_completed() -> bool:
    state = load_setup_state()
    return bool(state.get("completed", False)) and not auth_service.is_first_run()


# ------------------------------------------------------------------------------
# 1. Packages Verification & Background Installation
# ------------------------------------------------------------------------------

REQUIRED_PACKAGES = [
    {
        "name": "hostapd",
        "title": "hostapd",
        "binary": "hostapd",
        "description": "Точка доступа Wi-Fi (IEEE 802.11 AP daemon)",
    },
    {
        "name": "dnsmasq",
        "title": "dnsmasq",
        "binary": "dnsmasq",
        "description": "Локальный DHCP и DNS сервер для Wi-Fi клиентов",
    },
    {
        "name": "nftables",
        "title": "nftables",
        "binary": "nft",
        "description": "Межсетевой экран ядра Linux и NAT-маскарадинг",
    },
    {
        "name": "iproute2",
        "title": "iproute2",
        "binary": "ip",
        "description": "Маршрутизация политик ядра Linux (ip rule / table 100)",
    },
    {
        "name": "iw",
        "title": "iw",
        "binary": "iw",
        "description": "Конфигурация беспроводных сетевых адаптеров",
    },
    {
        "name": "pciutils",
        "title": "pciutils",
        "binary": "lspci",
        "description": "Утилиты диагностики аппаратных сетевых чипсетов",
    },
    {
        "name": "procps",
        "title": "procps",
        "binary": "sysctl",
        "description": "Управление параметрами ядра и системными процессами",
    },
    {
        "name": "xray",
        "title": "Xray Core",
        "binary": "xray",
        "description": "Ядро проксирования VLESS / REALITY и TUN-маршрутизации",
    },
]


def is_binary_installed(binary: str) -> bool:
    if shutil.which(binary):
        return True
    standard_paths = [
        f"/usr/bin/{binary}",
        f"/usr/sbin/{binary}",
        f"/sbin/{binary}",
        f"/bin/{binary}",
        f"/usr/local/bin/{binary}",
        f"/usr/local/sbin/{binary}",
    ]
    for p in standard_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return True
    return False


def check_system_packages() -> Dict[str, Any]:
    packages_status = []
    missing_count = 0

    for pkg in REQUIRED_PACKAGES:
        installed = is_binary_installed(pkg["binary"])
        if not installed:
            missing_count += 1
        packages_status.append({
            "name": pkg["name"],
            "title": pkg["title"],
            "binary": pkg["binary"],
            "description": pkg["description"],
            "installed": installed,
            "required": True,
        })

    all_installed = (missing_count == 0)
    return {
        "all_installed": all_installed,
        "total": len(REQUIRED_PACKAGES),
        "installed_count": len(REQUIRED_PACKAGES) - missing_count,
        "missing_count": missing_count,
        "packages": packages_status,
    }


def _run_cmd_log(cmd: List[str], state_obj: Dict[str, Any], timeout: int = 180) -> bool:
    cmd_str = " ".join(cmd)
    state_obj["logs"].append(f"$ {cmd_str}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        if proc.stdout:
            for line in proc.stdout:
                clean_line = line.rstrip()
                if clean_line:
                    state_obj["logs"].append(clean_line)
                    # Keep max 150 lines
                    if len(state_obj["logs"]) > 150:
                        state_obj["logs"] = state_obj["logs"][-150:]
        proc.wait(timeout=timeout)
        if proc.returncode != 0:
            state_obj["logs"].append(f"Command exited with status {proc.returncode}")
            return False
        return True
    except Exception as e:
        state_obj["logs"].append(f"Execution error: {str(e)}")
        return False


def _package_installer_worker():
    global _package_install_state
    with _package_install_lock:
        _package_install_state["status"] = "running"
        _package_install_state["progress"] = 5
        _package_install_state["message"] = "Инициализация проверки системных пакетов..."
        _package_install_state["logs"] = ["Начало проверки и установки необходимых пакетов..."]
        _package_install_state["error"] = None

        if not _is_linux():
            # Non-Linux simulation for testing/development
            steps = [
                (20, "Обновление индексов пакетов (apt-get update)...", "Hit:1 http://deb.debian.org/debian bookworm InRelease"),
                (45, "Установка hostapd, dnsmasq, nftables, iproute2, iw...", "Setting up hostapd (2:2.10-12) ...\nSetting up dnsmasq (2.89-1) ...\nSetting up nftables (1.0.6-2) ..."),
                (75, "Загрузка и установка Xray Core...", "Xray v1.8.7 (Xray, Penetrates Everything.) installed to /usr/local/bin/xray"),
                (95, "Верификация установленных компонентов...", "Все пакеты успешно проверены."),
            ]
            for prog, msg, log_entry in steps:
                time.sleep(0.6)
                _package_install_state["progress"] = prog
                _package_install_state["message"] = msg
                _package_install_state["logs"].append(log_entry)

            _package_install_state["progress"] = 100
            _package_install_state["status"] = "completed"
            _package_install_state["message"] = "Все пакеты успешно установлены!"
            
            state = load_setup_state()
            state["packages_installed"] = True
            save_setup_state(state)
            return

        # Real Linux Execution
        try:
            # Step 1: apt-get update
            _package_install_state["progress"] = 15
            _package_install_state["message"] = "Обновление списков пакетов (apt-get update)..."
            env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
            subprocess.run(["apt-get", "update", "-y"], capture_output=True, env=env, timeout=120)

            # Step 2: apt-get install missing packages
            _package_install_state["progress"] = 35
            _package_install_state["message"] = "Установка системных сетевых утилит..."
            
            apt_pkgs = [
                "hostapd",
                "dnsmasq",
                "nftables",
                "iproute2",
                "iw",
                "pciutils",
                "procps",
                "ca-certificates",
                "curl",
                "tar",
            ]
            cmd = ["apt-get", "install", "-y", "--no-install-recommends"] + apt_pkgs
            _run_cmd_log(cmd, _package_install_state, timeout=300)

            # Step 3: Install Xray core
            _package_install_state["progress"] = 75
            _package_install_state["message"] = "Установка Xray-core..."
            if not is_binary_installed("xray"):
                _package_install_state["logs"].append("Загрузка официального инсталлятора Xray...")
                xray_cmd = ["bash", "-c", "curl -s -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh | bash -s -- install"]
                _run_cmd_log(xray_cmd, _package_install_state, timeout=180)
            else:
                _package_install_state["logs"].append("Xray-core уже установлен в системе.")

            # Create /etc/xray if not present
            Path("/etc/xray").mkdir(parents=True, exist_ok=True)

            # Final verify
            _package_install_state["progress"] = 95
            _package_install_state["message"] = "Проверка установленных компонентов..."
            chk = check_system_packages()
            
            _package_install_state["progress"] = 100
            _package_install_state["status"] = "completed"
            _package_install_state["message"] = f"Установка завершена! Установлено компонентов: {chk['installed_count']}/{chk['total']}"
            
            state = load_setup_state()
            state["packages_installed"] = True
            save_setup_state(state)

        except Exception as e:
            _package_install_state["status"] = "error"
            _package_install_state["error"] = str(e)
            _package_install_state["message"] = f"Ошибка установки: {str(e)}"
            _package_install_state["logs"].append(f"[ОШИБКА] {str(e)}")


def start_package_installation() -> Dict[str, Any]:
    global _package_install_state
    if _package_install_state["status"] == "running":
        return {"success": True, "message": "Установка уже выполняется", "status": "running"}

    worker = threading.Thread(target=_package_installer_worker, daemon=True)
    worker.start()
    return {"success": True, "message": "Процесс установки запущен", "status": "running"}


def get_package_install_status() -> Dict[str, Any]:
    global _package_install_state
    return dict(_package_install_state)


# ------------------------------------------------------------------------------
# 2. Wi-Fi Configuration Stage
# ------------------------------------------------------------------------------

def get_wifi_stage_data() -> Dict[str, Any]:
    state = load_setup_state()
    wifi_stage = state.get("wifi", {})
    iface = wifi_service.get_wifi_interface()
    hw_info = wifi_service.detect_wifi_hardware(iface)

    return {
        "interface": iface,
        "hardware": hw_info,
        "ssid": wifi_stage.get("ssid", "freedom"),
        "password": wifi_stage.get("password", "freedom123"),
        "channel": wifi_stage.get("channel", 6),
        "country": wifi_stage.get("country", "RU"),
        "security": wifi_stage.get("security", "WPA2"),
    }


def save_wifi_stage_data(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    ssid = str(payload.get("ssid", "")).strip()
    password = str(payload.get("password", "")).strip()
    channel = payload.get("channel", 6)
    country = str(payload.get("country", "RU")).strip().upper()

    if not ssid or len(ssid) > 32:
        return False, "SSID Wi-Fi сети должен быть от 1 до 32 символов."

    if len(password) < 8 or len(password) > 63:
        return False, "Пароль WPA2 должен содержать от 8 до 63 символов."

    try:
        channel_num = int(channel)
        if channel_num < 1 or channel_num > 14:
            return False, "Канал Wi-Fi должен быть в диапазоне 1-14."
    except Exception:
        return False, "Некорректный номер Wi-Fi канала."

    state = load_setup_state()
    state["wifi"] = {
        "ssid": ssid,
        "password": password,
        "channel": channel_num,
        "country": country or "RU",
        "security": "WPA2",
    }
    state["current_step"] = max(state.get("current_step", 1), 3)
    save_setup_state(state)
    return True, None


# ------------------------------------------------------------------------------
# 3. VPN Configuration Stage
# ------------------------------------------------------------------------------

def get_vpn_stage_data() -> Dict[str, Any]:
    state = load_setup_state()
    return state.get("vpn", {"vless_uri": "", "skip": False})


def save_vpn_stage_data(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    skip = bool(payload.get("skip", False))
    raw_uri = str(payload.get("vless_uri", "")).strip()

    if skip or not raw_uri:
        state = load_setup_state()
        state["vpn"] = {"vless_uri": "", "skip": True}
        state["current_step"] = max(state.get("current_step", 1), 4)
        save_setup_state(state)
        return True, None

    # Validate URI format
    if raw_uri.startswith("vless://"):
        try:
            profile = vpn_service.parse_vless_uri(raw_uri)
            state = load_setup_state()
            state["vpn"] = {
                "vless_uri": raw_uri,
                "skip": False,
                "server": profile.get("address"),
                "port": profile.get("port"),
                "remark": profile.get("remark"),
            }
            state["current_step"] = max(state.get("current_step", 1), 4)
            save_setup_state(state)
            return True, None
        except Exception as e:
            return False, f"Ошибка в ссылке VLESS: {str(e)}"
    elif raw_uri.startswith("http://") or raw_uri.startswith("https://") or ("\n" in raw_uri):
        # Subscription URL or multiline
        state = load_setup_state()
        state["vpn"] = {"vless_uri": raw_uri, "skip": False, "is_subscription": True}
        state["current_step"] = max(state.get("current_step", 1), 4)
        save_setup_state(state)
        return True, None
    else:
        return False, "Неверный формат. Ожидается vless:// или URL подписки."


# ------------------------------------------------------------------------------
# 4. Administrator Account Stage
# ------------------------------------------------------------------------------

def save_account_stage_data(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    username = str(payload.get("username", "admin")).strip() or "admin"
    password = str(payload.get("password", "")).strip()
    confirm_password = str(payload.get("confirm_password", "")).strip()

    if len(password) < 6:
        return False, "Пароль администратора должен быть не менее 6 символов."

    if password != confirm_password:
        return False, "Пароли не совпадают."

    state = load_setup_state()
    state["account"] = {
        "username": username,
        "password": password,
    }
    state["current_step"] = 5
    save_setup_state(state)
    return True, None


# ------------------------------------------------------------------------------
# 5. Final System Configuration with Progress Bar
# ------------------------------------------------------------------------------

def _final_setup_worker():
    global _final_setup_state
    with _final_setup_lock:
        _final_setup_state["status"] = "running"
        _final_setup_state["progress"] = 5
        _final_setup_state["current_task"] = "Инициализация конфигуратора..."
        _final_setup_state["logs"] = ["Запуск окончательной настройки системы VPN Gateway..."]
        _final_setup_state["error"] = None
        _final_setup_state["token"] = None

        state = load_setup_state()
        wifi_cfg = state.get("wifi", {})
        vpn_cfg = state.get("vpn", {})
        account_cfg = state.get("account", {})

        # Task 1: Detect interfaces (15%)
        _final_setup_state["progress"] = 15
        _final_setup_state["current_task"] = "Определение сетевых интерфейсов..."
        _final_setup_state["logs"].append("Сканирование сетевого оборудования...")
        
        wan_iface = "enp3s0"
        wifi_iface = wifi_service.get_wifi_interface()
        if _is_linux():
            ifaces = network_service.get_default_interfaces()
            wan_iface = ifaces.get("wan") or "enp3s0"
            wifi_iface = ifaces.get("lan") or wifi_iface

        _final_setup_state["logs"].append(f"Интерфейс WAN: {wan_iface}, Интерфейс Wi-Fi: {wifi_iface}")
        time.sleep(0.4)

        # Task 2: Kernel parameters / IPv4 Forwarding (30%)
        _final_setup_state["progress"] = 30
        _final_setup_state["current_task"] = "Включение маршрутизации ядра Linux (IPv4 forward)..."
        if _is_linux():
            try:
                sysctl_path = Path("/etc/sysctl.d/99-vpn-gateway.conf")
                sysctl_path.parent.mkdir(parents=True, exist_ok=True)
                with open(sysctl_path, "w") as f:
                    f.write("net.ipv4.ip_forward = 1\nnet.ipv6.conf.all.disable_ipv6 = 0\n")
                subprocess.run(["sysctl", "--system"], capture_output=True, timeout=5)
                subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], capture_output=True, timeout=5)
                _final_setup_state["logs"].append("IPv4 forwarding активирован в sysctl.")
            except Exception as e:
                _final_setup_state["logs"].append(f"Предупреждение sysctl: {str(e)}")
        else:
            _final_setup_state["logs"].append("[Dev] Симуляция включения IPv4 forwarding.")
        time.sleep(0.4)

        # Task 3: Write hostapd configuration (45%)
        _final_setup_state["progress"] = 45
        _final_setup_state["current_task"] = "Генерация конфигурации точки доступа Wi-Fi (hostapd)..."
        ssid = wifi_cfg.get("ssid", "freedom")
        password = wifi_cfg.get("password", "freedom123")
        channel = wifi_cfg.get("channel", 6)
        country = wifi_cfg.get("country", "RU")

        hostapd_content = f"""# /etc/hostapd/hostapd.conf
# Generated by VPN Gateway Setup Wizard
interface={wifi_iface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
country_code={country}
ieee80211d=1
ieee80211n=1
wmm_enabled=1
ht_capab=[HT20][SHORT-GI-20]
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        if _is_linux():
            try:
                hostapd_file = Path("/etc/hostapd/hostapd.conf")
                hostapd_file.parent.mkdir(parents=True, exist_ok=True)
                with open(hostapd_file, "w") as f:
                    f.write(hostapd_content)
                subprocess.run(["systemctl", "unmask", "hostapd"], capture_output=True, timeout=5)
                _final_setup_state["logs"].append(f"Конфигурация hostapd сохранена (SSID: {ssid}, Channel: {channel}).")
            except Exception as e:
                _final_setup_state["logs"].append(f"Предупреждение hostapd: {str(e)}")
        else:
            dev_hostapd = LOCAL_CONFIG_DIR / "hostapd.conf"
            dev_hostapd.parent.mkdir(parents=True, exist_ok=True)
            with open(dev_hostapd, "w") as f:
                f.write(hostapd_content)
            _final_setup_state["logs"].append(f"[Dev] Сохранена конфигурация hostapd.conf (SSID: {ssid}).")
        time.sleep(0.4)

        # Task 4: Write dnsmasq configuration (60%)
        _final_setup_state["progress"] = 60
        _final_setup_state["current_task"] = "Настройка служб DHCP и DNS (dnsmasq)..."
        dnsmasq_content = f"""# /etc/dnsmasq.d/vpn-gateway.conf
# Generated by VPN Gateway Setup Wizard
interface={wifi_iface}
bind-interfaces
listen-address=10.42.0.1
dhcp-range=10.42.0.10,10.42.0.200,255.255.255.0,24h
dhcp-option=3,10.42.0.1
dhcp-option=6,10.42.0.1
domain=lan
local=/lan/
server=1.1.1.1
server=8.8.8.8
log-dhcp
log-facility=/var/log/dnsmasq.log
"""
        if _is_linux():
            try:
                dnsmasq_file = Path("/etc/dnsmasq.d/vpn-gateway.conf")
                dnsmasq_file.parent.mkdir(parents=True, exist_ok=True)
                with open(dnsmasq_file, "w") as f:
                    f.write(dnsmasq_content)
                _final_setup_state["logs"].append("Конфигурация dnsmasq сохранена (Подсеть 10.42.0.0/24).")
            except Exception as e:
                _final_setup_state["logs"].append(f"Предупреждение dnsmasq: {str(e)}")
        else:
            dev_dnsmasq = LOCAL_CONFIG_DIR / "dnsmasq.conf"
            dev_dnsmasq.parent.mkdir(parents=True, exist_ok=True)
            with open(dev_dnsmasq, "w") as f:
                f.write(dnsmasq_content)
            _final_setup_state["logs"].append("[Dev] Сохранена конфигурация dnsmasq.conf.")
        time.sleep(0.4)

        # Task 5: Configure nftables firewall & NAT (72%)
        _final_setup_state["progress"] = 72
        _final_setup_state["current_task"] = "Настройка межсетевого экрана и NAT (nftables)..."
        nft_content = f"""#!/usr/sbin/nft -f
# /etc/nftables.conf
# Generated by VPN Gateway Setup Wizard

flush ruleset

table inet filter {{
    chain input {{
        type filter hook input priority filter; policy accept;
        iif "lo" accept
        ct state established,related accept
        
        # Allow DHCP, DNS, and Web UI on Wi-Fi LAN
        iif "{wifi_iface}" udp dport {{ 53, 67 }} accept
        iif "{wifi_iface}" tcp dport {{ 53, 80 }} accept
    }}

    chain forward {{
        type filter hook forward priority filter; policy accept;
        ct state established,related accept
        
        # Forward Wi-Fi client traffic to xray0 TUN
        iif "{wifi_iface}" oif "xray0" accept
        
        # Fallback forward to WAN Ethernet
        iif "{wifi_iface}" oif "{wan_iface}" accept
    }}

    chain output {{
        type filter hook output priority filter; policy accept;
    }}
}}

table ip nat {{
    chain postrouting {{
        type filter hook postrouting priority srcnat; policy accept;
        
        # Masquerade traffic going to Xray TUN
        oif "xray0" masquerade
        
        # Masquerade traffic going direct to WAN
        oif "{wan_iface}" masquerade
    }}
}}
"""
        if _is_linux():
            try:
                nft_file = Path("/etc/nftables.conf")
                with open(nft_file, "w") as f:
                    f.write(nft_content)
                subprocess.run(["nft", "-f", "/etc/nftables.conf"], capture_output=True, timeout=5)
                _final_setup_state["logs"].append("Правила nftables применены.")
            except Exception as e:
                _final_setup_state["logs"].append(f"Предупреждение nftables: {str(e)}")
        else:
            dev_nft = LOCAL_CONFIG_DIR / "nftables.conf"
            with open(dev_nft, "w") as f:
                f.write(nft_content)
            _final_setup_state["logs"].append("[Dev] Сохранена конфигурация nftables.conf.")
        time.sleep(0.4)

        # Task 6: Routing & VPN configuration (82%)
        _final_setup_state["progress"] = 82
        _final_setup_state["current_task"] = "Настройка маршрутов и профиля VPN..."
        vless_uri = vpn_cfg.get("vless_uri", "").strip()
        if vless_uri:
            try:
                if vpn_cfg.get("is_subscription"):
                    subscription_service.import_subscription(vless_uri)
                    _final_setup_state["logs"].append("Импортирована VPN подписка.")
                else:
                    vpn_res = vpn_service.apply_vpn_config(vless_uri)
                    if vpn_res.get("success"):
                        _final_setup_state["logs"].append("Профиль VLESS REALITY успешно настроен.")
                    else:
                        _final_setup_state["logs"].append(f"Предупреждение VLESS: {vpn_res.get('error')}")
            except Exception as e:
                _final_setup_state["logs"].append(f"Ошибка настройки VPN: {str(e)}")
        else:
            _final_setup_state["logs"].append("Настройка VPN пропущена (можно настроить в дашборде).")

        # Install systemd routing service
        if _is_linux():
            try:
                routes_src = BASE_DIR / "systemd" / "vpn-gateway-routes.service"
                if routes_src.exists():
                    shutil.copy2(routes_src, SYSTEMD_DIR / "vpn-gateway-routes.service")
                    subprocess.run(["systemctl", "daemon-reload"], capture_output=True, timeout=5)
                    subprocess.run(["systemctl", "enable", "vpn-gateway-routes.service"], capture_output=True, timeout=5)
                    _final_setup_state["logs"].append("Служба маршрутизации vpn-gateway-routes установлена.")
            except Exception as e:
                _final_setup_state["logs"].append(f"Предупреждение routes.service: {str(e)}")
        time.sleep(0.4)

        # Task 7: Start all system services (92%)
        _final_setup_state["progress"] = 92
        _final_setup_state["current_task"] = "Запуск системных демонов (hostapd, dnsmasq, nftables, xray)..."
        if _is_linux():
            services = ["hostapd", "dnsmasq", "nftables", "xray", "vpn-gateway-routes"]
            for s in services:
                try:
                    subprocess.run(["systemctl", "enable", f"{s}.service"], capture_output=True, timeout=5)
                    subprocess.run(["systemctl", "restart", f"{s}.service"], capture_output=True, timeout=10)
                    _final_setup_state["logs"].append(f"Служба {s}.service запущена.")
                except Exception as e:
                    _final_setup_state["logs"].append(f"Служба {s}: {str(e)}")
        else:
            _final_setup_state["logs"].append("[Dev] Демоны hostapd, dnsmasq, nftables, xray активированы.")
        time.sleep(0.4)

        # Task 8: Account setup & completion (100%)
        _final_setup_state["progress"] = 100
        _final_setup_state["current_task"] = "Создание учетной записи и финализация..."
        admin_pass = account_cfg.get("password") or "admin123"
        
        # Save password via auth service
        success, token, err = auth_service.setup_initial_password(admin_pass)
        if not success and not token:
            # If already set, authenticate to get token
            auth_ok, token, _ = auth_service.authenticate(admin_pass)

        # Mark setup as completed
        state["completed"] = True
        state["completed_at"] = time.time()
        save_setup_state(state)

        _final_setup_state["status"] = "completed"
        _final_setup_state["token"] = token
        _final_setup_state["current_task"] = "Окончательная настройка успешно завершена!"
        _final_setup_state["logs"].append("Все компоненты сконфигурированы. Переход в дашборд...")


def start_final_setup() -> Dict[str, Any]:
    global _final_setup_state
    if _final_setup_state["status"] == "running":
        return {"success": True, "message": "Окончательная настройка уже выполняется", "status": "running"}

    worker = threading.Thread(target=_final_setup_worker, daemon=True)
    worker.start()
    return {"success": True, "message": "Процесс окончательной настройки запущен", "status": "running"}


def get_final_setup_status() -> Dict[str, Any]:
    global _final_setup_state
    return dict(_final_setup_state)
