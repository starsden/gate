#!/usr/bin/env bash
# ==============================================================================
# Linux VPN Gateway Installer
# Automated deployment for x86 Wi-Fi router & VLESS/Xray VPN Gateway
# Target reference: ICL ThinRAY Th382 (ath9k AR9285, enp3s0, wlp4s0)
# ==============================================================================

set -euo pipefail

# Visual styling
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
RED="\033[0;31m"
RESET="\033[0m"

log_info()    { echo -e "${BLUE}[INFO]${RESET} $*"; }
log_success() { echo -e "${GREEN}[OK]${RESET} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${RESET} $*"; }
log_error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

# Paths & Source Resolution
INSTALL_DIR="/opt/vpn-gateway"
CONFIG_DIR="/etc/vpn-gateway"
SYSTEMD_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
SOURCE_DIR="${SCRIPT_DIR}"

# GitHub Settings for One-Line Remote Installer (curl -fsSL ... | sudo bash)
GITHUB_REPO="${GITHUB_REPO:-starsden/vpn-gateway}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"

# ------------------------------------------------------------------------------
# 1. Root & Environment Checks
# ------------------------------------------------------------------------------
check_privileges() {
    if [[ "${EUID}" -ne 0 ]]; then
        log_error "This script must be run as root. Please use: sudo bash $0"
        exit 1
    fi
}

check_os() {
    log_info "Detecting Operating System..."
    if [[ ! -f /etc/os-release ]]; then
        log_error "Unsupported OS. Missing /etc/os-release."
        exit 1
    fi

    # shellcheck source=/dev/null
    source /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_PRETTY="${PRETTY_NAME:-Linux}"

    log_success "Operating System: ${OS_PRETTY}"
    if [[ "${OS_ID}" != "debian" && "${OS_ID}" != "ubuntu" && "${ID_LIKE:-}" != *"debian"* ]]; then
        log_warn "This installer is optimized for Debian/Ubuntu. Proceeding with caution."
    fi
}

check_arch() {
    ARCH="$(uname -m)"
    log_info "Architecture: ${ARCH}"
    if [[ "${ARCH}" != "x86_64" && "${ARCH}" != "aarch64" ]]; then
        log_warn "Notice: Target machine architecture (${ARCH}) is not standard x86_64."
    fi
}

# ------------------------------------------------------------------------------
# 2. Hardware & Interface Detection
# ------------------------------------------------------------------------------
detect_interfaces() {
    log_info "Scanning network hardware..."

    # Detect Ethernet interface (WAN)
    WAN_IFACE=""
    # Priority: interface holding default route
    if command -v ip >/dev/null 2>&1; then
        WAN_IFACE="$(ip route show default 2>/dev/null | awk '/default/ {print $5}' | head -n1 || true)"
    fi
    # Fallback to enp* or eth*
    if [[ -z "${WAN_IFACE}" ]]; then
        for iface in /sys/class/net/en* /sys/class/net/eth*; do
            if [[ -d "${iface}" ]]; then
                WAN_IFACE="$(basename "${iface}")"
                break
            fi
        done
    fi
    WAN_IFACE="${WAN_IFACE:-enp3s0}"
    log_success "WAN Interface (Ethernet): ${BOLD}${WAN_IFACE}${RESET}"

    # Detect Wireless interface (LAN AP)
    WIFI_IFACE=""
    if command -v iw >/dev/null 2>&1; then
        WIFI_IFACE="$(iw dev 2>/dev/null | awk '/Interface/ {print $2}' | head -n1 || true)"
    fi
    if [[ -z "${WIFI_IFACE}" ]]; then
        for iface in /sys/class/net/wl*; do
            if [[ -d "${iface}" ]]; then
                WIFI_IFACE="$(basename "${iface}")"
                break
            fi
        done
    fi
    WIFI_IFACE="${WIFI_IFACE:-wlp4s0}"
    log_success "Wi-Fi Interface (Access Point): ${BOLD}${WIFI_IFACE}${RESET}"

    # Check AP mode support
    if command -v iw >/dev/null 2>&1; then
        if iw list 2>/dev/null | grep -E "^\s+\*\s+AP\b" >/dev/null 2>&1; then
            log_success "Wireless driver supports AP (Access Point) mode."
        else
            log_warn "Could not confirm AP mode support via 'iw list'. Ensure ath9k / compatible driver is loaded."
        fi
    fi
}

# ------------------------------------------------------------------------------
# 3. Idempotency & Arguments Handling
# ------------------------------------------------------------------------------
handle_idempotency() {
    local arg="${1:-}"

    if [[ "${arg}" == "--help" || "${arg}" == "-h" ]]; then
        echo "Usage: sudo bash install.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  (none)            Interactive install / detect existing setup"
        echo "  --update          Non-interactive update (refreshes code & static assets, preserves configs)"
        echo "  --repair          Restore network rules, routing tables, and restart daemons"
        echo "  --reinstall       Fresh install with automatic backup of /etc/vpn-gateway"
        echo "  --reset-password  Reset admin password (triggers setup wizard on next UI open)"
        echo "  --factory-reset   Reset all Wi-Fi, VPN, and admin credentials to factory defaults"
        echo "  --uninstall       Stop services and remove /opt/vpn-gateway (keeps config)"
        echo "  --help, -h        Show this help message"
        exit 0
    fi

    if [[ "${arg}" == "--reset-password" ]]; then
        ACTION="reset-password"
        return 0
    fi

    if [[ "${arg}" == "--factory-reset" ]]; then
        ACTION="factory-reset"
        return 0
    fi

    if [[ "${arg}" == "--uninstall" ]]; then
        ACTION="uninstall"
        return 0
    fi

    if [[ -d "${INSTALL_DIR}" && -f "${INSTALL_DIR}/backend/app.py" ]]; then
        echo ""
        log_warn "Existing installation detected at ${INSTALL_DIR}."
        
        # Check non-interactive / flag mode
        if [[ "${NONINTERACTIVE:-0}" == "1" || "${arg}" == "--update" ]]; then
            CHOICE="1"
        elif [[ "${arg}" == "--repair" ]]; then
            CHOICE="2"
        elif [[ "${arg}" == "--reinstall" ]]; then
            CHOICE="3"
        else
            echo "Please select an action:"
            echo "  1) Update    - Update application code and restart services (keep config)"
            echo "  2) Repair    - Fix routes, verify dependencies and systemd units"
            echo "  3) Reinstall - Full clean re-installation (back up current config)"
            echo "  4) Cancel    - Exit installer"
            if [[ -t 0 ]]; then
                read -r -p "Enter choice [1-4] (default 1): " USER_CHOICE || USER_CHOICE=1
            elif [[ -c /dev/tty ]]; then
                read -r -p "Enter choice [1-4] (default 1): " USER_CHOICE </dev/tty || USER_CHOICE=1
            else
                USER_CHOICE=1
            fi
            CHOICE="${USER_CHOICE:-1}"
        fi

        case "${CHOICE}" in
            1)
                log_info "Performing Update..."
                ACTION="update"
                ;;
            2)
                log_info "Performing Repair..."
                ACTION="repair"
                ;;
            3)
                log_warn "Creating backup of current configurations..."
                BACKUP_PATH="/etc/vpn-gateway.backup-$(date +%Y%m%d%H%M%S)"
                cp -r "${CONFIG_DIR}" "${BACKUP_PATH}" 2>/dev/null || true
                log_success "Backup saved to: ${BACKUP_PATH}"
                ACTION="reinstall"
                ;;
            4|*)
                log_info "Installation cancelled by user."
                exit 0
                ;;
        esac
    else
        ACTION="install"
    fi
}

# ------------------------------------------------------------------------------
# -------------------------------------------------------------
# 4. Minimal Prerequisites for Web Controller
# -------------------------------------------------------------
install_minimal_packages() {
    log_info "Checking minimal dependencies for Web Controller..."
    local pkgs=()
    command -v python3 >/dev/null 2>&1 || pkgs+=("python3")
    if ! python3 -m venv --help >/dev/null 2>&1; then
        pkgs+=("python3-venv")
    fi
    command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1 || pkgs+=("python3-pip")
    command -v curl >/dev/null 2>&1 || pkgs+=("curl")
    command -v tar >/dev/null 2>&1 || pkgs+=("tar")

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        log_info "Installing minimal Python runtime: ${pkgs[*]}..."
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -y
        apt-get install -y --no-install-recommends \
            python3 \
            python3-venv \
            python3-pip \
            curl \
            tar \
            ca-certificates
        log_success "Minimal prerequisites installed."
    else
        log_success "Minimal Python 3 environment is already present."
    fi
}

# ------------------------------------------------------------------------------
# 6. Ensure Repository Source Files (Local or GitHub Remote)
# ------------------------------------------------------------------------------
ensure_source_files() {
    # 1. Local execution inside repository clone
    if [[ -n "${SCRIPT_DIR}" && -f "${SCRIPT_DIR}/backend/app.py" && -d "${SCRIPT_DIR}/web" ]]; then
        SOURCE_DIR="${SCRIPT_DIR}"
        log_success "Using local source tree at: ${SOURCE_DIR}"
        return 0
    fi

    # 2. Existing installation in /opt/vpn-gateway (e.g. for repair)
    if [[ "${ACTION:-install}" == "repair" && -f "${INSTALL_DIR}/backend/app.py" ]]; then
        SOURCE_DIR="${INSTALL_DIR}"
        log_info "Using existing installation at: ${SOURCE_DIR}"
        return 0
    fi

    # 3. Running via curl pipe or standalone installer: download from GitHub
    log_info "Source files not found locally. Downloading from GitHub..."
    local tmp_dir="/tmp/vpn-gateway-src"
    rm -rf "${tmp_dir}"
    mkdir -p "${tmp_dir}"

    local downloaded=0

    # Candidate repos to probe
    local repos_to_try=("${GITHUB_REPO}")
    if [[ "${GITHUB_REPO}" != "starsden/vpn-gateway" ]]; then
        repos_to_try+=("starsden/vpn-gateway")
    fi
    if [[ "${GITHUB_REPO}" != "starsden/gates" ]]; then
        repos_to_try+=("starsden/gates")
    fi

    for repo in "${repos_to_try[@]}"; do
        log_info "Checking repository: ${repo} (branch: ${GITHUB_BRANCH})..."

        # Attempt A: git clone
        if command -v git >/dev/null 2>&1; then
            if git clone --depth 1 -b "${GITHUB_BRANCH}" "https://github.com/${repo}.git" "${tmp_dir}" 2>/dev/null; then
                if [[ -f "${tmp_dir}/backend/app.py" ]]; then
                    downloaded=1
                    GITHUB_REPO="${repo}"
                    break
                fi
            fi
        fi

        # Attempt B: GitHub tarball via curl / wget
        local tarball_url="https://github.com/${repo}/archive/refs/heads/${GITHUB_BRANCH}.tar.gz"
        rm -rf "${tmp_dir}" && mkdir -p "${tmp_dir}"
        if command -v curl >/dev/null 2>&1; then
            if curl -fsSL "${tarball_url}" 2>/dev/null | tar -xz -C "${tmp_dir}" --strip-components=1 2>/dev/null; then
                if [[ -f "${tmp_dir}/backend/app.py" ]]; then
                    downloaded=1
                    GITHUB_REPO="${repo}"
                    break
                fi
            fi
        elif command -v wget >/dev/null 2>&1; then
            if wget -qO- "${tarball_url}" 2>/dev/null | tar -xz -C "${tmp_dir}" --strip-components=1 2>/dev/null; then
                if [[ -f "${tmp_dir}/backend/app.py" ]]; then
                    downloaded=1
                    GITHUB_REPO="${repo}"
                    break
                fi
            fi
        fi
    done

    if [[ "${downloaded}" -eq 1 && -f "${tmp_dir}/backend/app.py" ]]; then
        SOURCE_DIR="${tmp_dir}"
        log_success "Source tree downloaded successfully from https://github.com/${GITHUB_REPO}."
    else
        log_error "Could not download repository source from GitHub."
        log_error "Checked repositories: ${repos_to_try[*]} on branch '${GITHUB_BRANCH}'."
        log_error "Please check internet connectivity or specify custom repo: GITHUB_REPO=username/repo bash $0"
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# 7. Deploy Application & Python Environment
# ------------------------------------------------------------------------------
deploy_app() {
    log_info "Setting up application in ${INSTALL_DIR}..."
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${CONFIG_DIR}/backups"
    chmod 700 "${CONFIG_DIR}"
    chmod 700 "${CONFIG_DIR}/backups" 2>/dev/null || true

    # Copy files from SOURCE_DIR
    cp -r "${SOURCE_DIR}/backend" "${INSTALL_DIR}/"
    cp -r "${SOURCE_DIR}/web" "${INSTALL_DIR}/"
    cp -r "${SOURCE_DIR}/configs" "${INSTALL_DIR}/"
    cp "${SOURCE_DIR}/install.sh" "${INSTALL_DIR}/" 2>/dev/null || true
    cp "${SOURCE_DIR}/update.sh" "${INSTALL_DIR}/" 2>/dev/null || true
    chmod +x "${INSTALL_DIR}/install.sh" "${INSTALL_DIR}/update.sh" 2>/dev/null || true

    # Setup Python virtual environment
    if [[ ! -d "${INSTALL_DIR}/venv" ]]; then
        log_info "Creating Python virtual environment in ${INSTALL_DIR}/venv..."
        python3 -m venv "${INSTALL_DIR}/venv"
    fi

    log_info "Installing backend dependencies (FastAPI, Uvicorn)..."
    "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
    "${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/backend/requirements.txt"
    log_success "Backend dependencies installed."
}

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# 8. Configure Networking & Services (Optional / Repair only)
# ------------------------------------------------------------------------------
configure_networking() {
    log_info "Enabling IPv4 forwarding..."
    cat <<EOF > /etc/sysctl.d/99-vpn-gateway.conf
net.ipv4.ip_forward = 1
net.ipv6.conf.all.disable_ipv6 = 0
EOF
    sysctl --system >/dev/null 2>&1 || true

    # Prepare default state config
    if [[ ! -f "${CONFIG_DIR}/config.json" ]]; then
        cat <<EOF > "${CONFIG_DIR}/config.json"
{
  "wan_interface": "${WAN_IFACE}",
  "lan_interface": "${WIFI_IFACE}",
  "gateway_ip": "10.42.0.1",
  "subnet": "10.42.0.0/24",
  "wifi_ssid": "freedom",
  "wifi_channel": 6,
  "wifi_security": "WPA2"
}
EOF
    fi

    # Hostapd config
    mkdir -p /etc/hostapd
    sed -e "s/interface=wlp4s0/interface=${WIFI_IFACE}/g" \
        "${SOURCE_DIR}/configs/hostapd.conf" > /etc/hostapd/hostapd.conf
    # Unmask hostapd on Debian
    systemctl unmask hostapd 2>/dev/null || true

    # Dnsmasq config
    mkdir -p /etc/dnsmasq.d
    sed -e "s/interface=wlp4s0/interface=${WIFI_IFACE}/g" \
        "${SOURCE_DIR}/configs/dnsmasq.conf" > /etc/dnsmasq.d/vpn-gateway.conf

    # Nftables config
    if [[ -f "${SOURCE_DIR}/configs/nftables.conf" ]]; then
        sed -e "s/wlp4s0/${WIFI_IFACE}/g" -e "s/enp3s0/${WAN_IFACE}/g" \
            "${SOURCE_DIR}/configs/nftables.conf" > /etc/nftables.conf
    fi
}

# ------------------------------------------------------------------------------
# 9. Start Web Controller Service
# ------------------------------------------------------------------------------
setup_web_service() {
    log_info "Installing Web Controller systemd service..."

    cp "${SOURCE_DIR}/systemd/vpn-gateway.service" "${SYSTEMD_DIR}/"

    systemctl daemon-reload
    systemctl enable vpn-gateway.service
    systemctl restart vpn-gateway.service

    log_success "vpn-gateway.service is enabled and running."
}

# ------------------------------------------------------------------------------
# 10. Success Banner
# ------------------------------------------------------------------------------
show_completion_banner() {
    local HOST_IP=""
    if command -v ip >/dev/null 2>&1; then
        HOST_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7}' | head -n1 || true)"
        if [[ -z "${HOST_IP}" ]]; then
            HOST_IP="$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n1 || true)"
        fi
    fi
    HOST_IP="${HOST_IP:-10.42.0.1}"

    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${GREEN}${BOLD}║              VPN GATEWAY WEB PANEL LAUNCHED                  ║${RESET}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "Web interface available at:"
    echo -e "  ${BOLD}${BLUE}http://${HOST_IP}${RESET}  (or http://10.42.0.1 / http://localhost)"
    if [[ -n "${WAN_IFACE:-}" ]]; then
        echo -e "  WAN Interface:    ${BOLD}${WAN_IFACE}${RESET}"
    fi
    if [[ -n "${WIFI_IFACE:-}" ]]; then
        echo -e "  Wi-Fi Interface:  ${BOLD}${WIFI_IFACE}${RESET}"
    fi
    echo ""
    echo -e "Next steps (Web-Based Onboarding):"
    echo -e "  1. Open ${BOLD}http://${HOST_IP}${RESET} in your browser."
    echo -e "  2. Confirm checking & installation of missing packages (hostapd, dnsmasq, nftables, xray)."
    echo -e "  3. Configure your Wi-Fi Access Point."
    echo -e "  4. Configure your VLESS / REALITY VPN link."
    echo -e "  5. Set your administrator account password."
    echo -e "  6. System will automatically apply settings with a progress bar and open the dashboard."
    echo ""
    echo -e "Web service status:"
    echo -e "  systemctl status vpn-gateway.service"
    echo ""
}

# ------------------------------------------------------------------------------
# Main Flow
# ------------------------------------------------------------------------------
main() {
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: sudo bash install.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  (none)            Launch web panel and begin web-based setup wizard"
        echo "  --update          Non-interactive update (refreshes code & static assets, preserves configs)"
        echo "  --repair          Restore network rules, routing tables, and restart daemons"
        echo "  --reinstall       Fresh install with automatic backup of /etc/vpn-gateway"
        echo "  --reset-password  Reset admin password (triggers setup wizard on next UI open)"
        echo "  --factory-reset   Reset all Wi-Fi, VPN, and admin credentials to factory defaults"
        echo "  --uninstall       Stop services and remove /opt/vpn-gateway (keeps config)"
        echo "  --help, -h        Show this help message"
        exit 0
    fi

    check_privileges
    check_os
    check_arch
    detect_interfaces
    handle_idempotency "${1:-}"

    case "${ACTION}" in
        reset-password)
            log_info "Resetting administrator credentials..."
            rm -f "${CONFIG_DIR}/auth.json" "${CONFIG_DIR}/setup_state.json"
            systemctl restart vpn-gateway.service 2>/dev/null || true
            log_success "Admin password reset successfully! Open the Web UI to set a new password."
            exit 0
            ;;
        factory-reset)
            log_warn "Performing full factory reset..."
            rm -f "${CONFIG_DIR}/auth.json" "${CONFIG_DIR}/vpn.json" "${CONFIG_DIR}/wifi_state.json" "${CONFIG_DIR}/setup_state.json"
            ensure_source_files
            configure_networking
            setup_web_service
            systemctl restart hostapd.service dnsmasq.service 2>/dev/null || true
            log_success "Factory reset completed! Open the Web UI to begin setup."
            exit 0
            ;;
        update)
            ensure_source_files
            deploy_app
            setup_web_service
            show_completion_banner
            ;;
        repair)
            ensure_source_files
            configure_networking
            setup_web_service
            "${INSTALL_DIR}/venv/bin/python" -m backend.services.network || true
            log_success "Repair complete. Network routing and systemd services restored."
            ;;
        uninstall)
            log_warn "Stopping and removing systemd units..."
            systemctl stop vpn-gateway.service vpn-gateway-routes.service hostapd.service dnsmasq.service 2>/dev/null || true
            systemctl disable vpn-gateway.service vpn-gateway-routes.service 2>/dev/null || true
            rm -f "${SYSTEMD_DIR}/vpn-gateway.service" "${SYSTEMD_DIR}/vpn-gateway-routes.service"
            systemctl daemon-reload
            rm -rf "${INSTALL_DIR}"
            log_success "VPN Gateway uninstalled. Configuration in /etc/vpn-gateway preserved."
            exit 0
            ;;
        install|reinstall|*)
            install_minimal_packages
            ensure_source_files
            deploy_app
            setup_web_service
            show_completion_banner
            ;;
    esac
}

main "$@"
