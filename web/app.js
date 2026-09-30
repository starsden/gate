/**
 * Linux VPN Gateway - Vanilla JavaScript Client Controller
 * Lightweight SPA navigation, Server-Sent Events (SSE) telemetry, Wi-Fi configuration,
 * connected devices monitor, Xray VLESS management, and service management.
 */

(function () {
  "use strict";

  // Application State
  const state = {
    activePage: "dashboard",
    sseConnected: false,
    backendOnline: true,
    lastSystemData: null,
    lastWifiData: null,
    lastDevicesData: null,
    lastVpnData: null,
  };

  // DOM Elements Cache
  const elements = {
    // Navigation
    sidebar: document.getElementById("sidebar"),
    menuToggle: document.getElementById("menu-toggle"),
    drawerBackdrop: document.getElementById("drawer-backdrop"),
    navItems: document.querySelectorAll(".nav-item"),
    pageSections: document.querySelectorAll(".page-section"),
    pageTitle: document.getElementById("page-title"),
    navClientsBadge: document.getElementById("nav-clients-badge"),
    
    // Status Banners & Indicators
    backendAlert: document.getElementById("backend-alert"),
    sidebarSseStatus: document.getElementById("sidebar-sse-status"),
    topbarVpnPill: document.getElementById("topbar-vpn-pill"),
    topbarVpnDot: document.getElementById("topbar-vpn-dot"),
    topbarVpnText: document.getElementById("topbar-vpn-text"),
    mobileVpnBeacon: document.getElementById("mobile-vpn-beacon"),
    brandBeacon: document.getElementById("brand-beacon"),
    btnRefresh: document.getElementById("btn-refresh"),

    // Dashboard Hero & Metrics
    dashMasterBadge: document.getElementById("dash-master-badge"),
    dashMasterStatus: document.getElementById("dash-master-status"),
    dashHeroProto: document.getElementById("dash-hero-proto"),
    dashHeroLatency: document.getElementById("dash-hero-latency"),
    btnDashRestartVpn: document.getElementById("btn-dash-restart-vpn"),

    // Internet Card
    dashWanBadge: document.getElementById("dash-wan-badge"),
    dashWanIface: document.getElementById("dash-wan-iface"),
    dashWanIp: document.getElementById("dash-wan-ip"),
    dashWanGw: document.getElementById("dash-wan-gw"),

    // VPN Card (Dashboard)
    dashVpnBadge: document.getElementById("dash-vpn-badge"),
    dashVpnServer: document.getElementById("dash-vpn-server"),
    dashVpnSni: document.getElementById("dash-vpn-sni"),
    dashVpnTraffic: document.getElementById("dash-vpn-traffic"),

    // Wi-Fi Card (Dashboard)
    dashWifiBadge: document.getElementById("dash-wifi-badge"),
    dashWifiSsid: document.getElementById("dash-wifi-ssid"),
    dashWifiChannel: document.getElementById("dash-wifi-channel"),
    dashWifiClients: document.getElementById("dash-wifi-clients"),

    // Speed Card
    dashSpeedDown: document.getElementById("dash-speed-down"),
    dashSpeedUp: document.getElementById("dash-speed-up"),
    dashLatencyBadge: document.getElementById("dash-latency-badge"),

    // Dashboard System Meters
    dashCpuPct: document.getElementById("dash-cpu-pct"),
    dashCpuBar: document.getElementById("dash-cpu-bar"),
    dashRamPct: document.getElementById("dash-ram-pct"),
    dashRamBar: document.getElementById("dash-ram-bar"),
    dashRamSub: document.getElementById("dash-ram-sub"),
    dashTempVal: document.getElementById("dash-temp-val"),
    dashTempBar: document.getElementById("dash-temp-bar"),
    dashUptimeVal: document.getElementById("dash-uptime-val"),

    // System Page
    sysHostname: document.getElementById("sys-hostname"),
    sysOs: document.getElementById("sys-os"),
    sysKernel: document.getElementById("sys-kernel"),
    sysArch: document.getElementById("sys-arch"),
    sysArchBadge: document.getElementById("sys-arch-badge"),
    sysUptime: document.getElementById("sys-uptime"),
    sysCores: document.getElementById("sys-cores"),
    sysCpuVal: document.getElementById("sys-cpu-val"),
    sysCpuBar: document.getElementById("sys-cpu-bar"),
    sysRamVal: document.getElementById("sys-ram-val"),
    sysRamBar: document.getElementById("sys-ram-bar"),
    sysRamText: document.getElementById("sys-ram-text"),
    sysDiskVal: document.getElementById("sys-disk-val"),
    sysDiskBar: document.getElementById("sys-disk-bar"),
    sysDiskText: document.getElementById("sys-disk-text"),
    sysTempVal: document.getElementById("sys-temp-val"),
    sysTempBar: document.getElementById("sys-temp-bar"),
    servicesTableBody: document.getElementById("services-table-body"),

    // VPN Page Elements
    vpnPageStatusBadge: document.getElementById("vpn-page-status-badge"),
    vpnInfoProto: document.getElementById("vpn-info-proto"),
    vpnInfoSecurity: document.getElementById("vpn-info-security"),
    vpnInfoTransport: document.getElementById("vpn-info-transport"),
    vpnInfoServer: document.getElementById("vpn-info-server"),
    vpnInfoSni: document.getElementById("vpn-info-sni"),
    vpnInfoFlow: document.getElementById("vpn-info-flow"),
    vpnInfoFp: document.getElementById("vpn-info-fp"),
    vpnInfoUuid: document.getElementById("vpn-info-uuid"),
    vpnInfoUptime: document.getElementById("vpn-info-uptime"),
    vpnInfoTraffic: document.getElementById("vpn-info-traffic"),
    vpnInfoLatency: document.getElementById("vpn-info-latency"),
    btnVpnRestart: document.getElementById("btn-vpn-restart"),
    btnVpnToggle: document.getElementById("btn-vpn-toggle"),
    btnVpnTest: document.getElementById("btn-vpn-test"),
    vlessInputUri: document.getElementById("vless-input-uri"),
    btnVlessImport: document.getElementById("btn-vless-import"),
    btnVlessClear: document.getElementById("btn-vless-clear"),
    vlessSummaryBox: document.getElementById("vless-summary-box"),
    summaryProtoBadge: document.getElementById("summary-proto-badge"),
    sumServer: document.getElementById("sum-server"),
    sumPort: document.getElementById("sum-port"),
    sumSecurity: document.getElementById("sum-security"),
    sumTransport: document.getElementById("sum-transport"),
    sumSni: document.getElementById("sum-sni"),
    sumFp: document.getElementById("sum-fp"),
    sumFlow: document.getElementById("sum-flow"),
    sumUuid: document.getElementById("sum-uuid"),

    // VPN Subscription Elements
    subServersTbody: document.getElementById("subscription-servers-tbody"),
    subServersCountBadge: document.getElementById("sub-servers-count-badge"),
    btnSubPingAll: document.getElementById("btn-sub-ping-all"),
    btnSubRefresh: document.getElementById("btn-sub-refresh"),
    subMetaBar: document.getElementById("sub-meta-bar"),
    subMetaUrlVal: document.getElementById("sub-meta-url-val"),
    subMetaTimeVal: document.getElementById("sub-meta-time-val"),

    // Wi-Fi Page Elements
    wifiStatusBadge: document.getElementById("wifi-status-badge"),
    wifiInfoIface: document.getElementById("wifi-info-iface"),
    wifiInfoChipset: document.getElementById("wifi-info-chipset"),
    wifiInfoDriver: document.getElementById("wifi-info-driver"),
    wifiInfoAp: document.getElementById("wifi-info-ap"),
    wifiInfoFreq: document.getElementById("wifi-info-freq"),
    wifiInfoChannel: document.getElementById("wifi-info-channel"),
    wifiInfoWidth: document.getElementById("wifi-info-width"),
    wifiInfoTxpower: document.getElementById("wifi-info-txpower"),
    wifiInfoSecurity: document.getElementById("wifi-info-security"),
    wifiInfoDevicesLink: document.getElementById("wifi-info-devices-link"),
    wifiInputSsid: document.getElementById("wifi-input-ssid"),
    wifiInputPass: document.getElementById("wifi-input-pass"),
    btnToggleWifiPass: document.getElementById("btn-toggle-wifi-pass"),
    wifiSelectChannel: document.getElementById("wifi-select-channel"),
    wifiSelectCountry: document.getElementById("wifi-select-country"),
    wifiToggle11n: document.getElementById("wifi-toggle-11n"),
    btnWifiApply: document.getElementById("btn-wifi-apply"),

    // Wi-Fi Confirmation Modal
    wifiConfirmModal: document.getElementById("wifi-confirm-modal"),
    modalDiffSsid: document.getElementById("modal-diff-ssid"),
    modalDiffChannel: document.getElementById("modal-diff-channel"),
    modalDiffCountry: document.getElementById("modal-diff-country"),
    modalDiff11n: document.getElementById("modal-diff-11n"),
    btnModalWifiCancel: document.getElementById("btn-modal-wifi-cancel"),
    btnModalWifiConfirm: document.getElementById("btn-modal-wifi-confirm"),

    // Devices Page Elements
    devicesCountPill: document.getElementById("devices-count-pill"),
    btnRefreshDevices: document.getElementById("btn-refresh-devices"),
    devicesTableBody: document.getElementById("devices-table-body"),

    // Network Page Elements
    netWanBadge: document.getElementById("net-wan-badge"),
    netWanIface: document.getElementById("net-wan-iface"),
    netWanIp: document.getElementById("net-wan-ip"),
    netWanSubnet: document.getElementById("net-wan-subnet"),
    netWanGw: document.getElementById("net-wan-gw"),
    netWanDns: document.getElementById("net-wan-dns"),

    netLanBadge: document.getElementById("net-lan-badge"),
    netLanIface: document.getElementById("net-lan-iface"),
    netLanGw: document.getElementById("net-lan-gw"),
    netLanNet: document.getElementById("net-lan-net"),
    netLanDhcp: document.getElementById("net-lan-dhcp"),
    netLanLease: document.getElementById("net-lan-lease"),

    routesTableBody: document.getElementById("routes-table-body"),
    btnSyncRoutes: document.getElementById("btn-sync-routes"),

    netNftBadge: document.getElementById("net-nft-badge"),
    netNftNat: document.getElementById("net-nft-nat"),
    netNftForward: document.getElementById("net-nft-forward"),
    netNftPorts: document.getElementById("net-nft-ports"),
    netNftRulesCount: document.getElementById("net-nft-rules-count"),
    btnReloadNft: document.getElementById("btn-reload-nft"),

    // Diagnostics Page Elements
    diagMasterBadge: document.getElementById("diag-master-badge"),
    diagLastScan: document.getElementById("diag-last-scan"),
    btnRefreshDiag: document.getElementById("btn-refresh-diag"),
    btnRunRepair: document.getElementById("btn-run-repair"),
    diagStatPassed: document.getElementById("diag-stat-passed"),
    diagStatIssues: document.getElementById("diag-stat-issues"),
    diagStatRouting: document.getElementById("diag-stat-routing"),
    repairResultsBox: document.getElementById("repair-results-box"),
    repairActionsList: document.getElementById("repair-actions-list"),
    btnDismissRepair: document.getElementById("btn-dismiss-repair"),
    diagTableBody: document.getElementById("diag-table-body"),
    navDiagBadge: document.getElementById("nav-diag-badge"),

    // Settings & Auth Page Elements (Phase 6)
    authStatusBadge: document.getElementById("auth-status-badge"),
    authUserName: document.getElementById("auth-user-name"),
    btnAuthLogout: document.getElementById("btn-auth-logout"),
    formChangePassword: document.getElementById("form-change-password"),
    inputOldPass: document.getElementById("input-old-pass"),
    inputNewPass: document.getElementById("input-new-pass"),
    inputConfirmPass: document.getElementById("input-confirm-pass"),
    btnSavePassword: document.getElementById("btn-save-password"),
    inputSnapshotNote: document.getElementById("input-snapshot-note"),
    btnCreateBackup: document.getElementById("btn-create-backup"),
    btnRefreshBackups: document.getElementById("btn-refresh-backups"),
    backupsTableBody: document.getElementById("backups-table-body"),
    btnTriggerReboot: document.getElementById("btn-trigger-reboot"),
    btnTriggerFactoryReset: document.getElementById("btn-trigger-factory-reset"),

    // Phase 6 Modals
    authSetupModal: document.getElementById("auth-setup-modal"),
    formInitialSetup: document.getElementById("form-initial-setup"),
    setupInputPass: document.getElementById("setup-input-pass"),
    setupInputConfirm: document.getElementById("setup-input-confirm"),
    btnSubmitSetup: document.getElementById("btn-submit-setup"),

    authLoginModal: document.getElementById("auth-login-modal"),
    formLogin: document.getElementById("form-login"),
    loginInputPass: document.getElementById("login-input-pass"),
    btnSubmitLogin: document.getElementById("btn-submit-login"),

    backupRestoreModal: document.getElementById("backup-restore-modal"),
    modalRestoreId: document.getElementById("modal-restore-id"),
    modalRestoreDate: document.getElementById("modal-restore-date"),
    modalRestoreDesc: document.getElementById("modal-restore-desc"),
    btnModalRestoreCancel: document.getElementById("btn-modal-restore-cancel"),
    btnModalRestoreConfirm: document.getElementById("btn-modal-restore-confirm"),

    factoryResetModal: document.getElementById("factory-reset-modal"),
    btnModalResetCancel: document.getElementById("btn-modal-reset-cancel"),
    btnModalResetConfirm: document.getElementById("btn-modal-reset-confirm"),

    rebootModal: document.getElementById("reboot-modal"),
    rebootProgressBar: document.getElementById("reboot-progress-bar"),

    // Logs Page Elements (Phase 7)
    logsSelectService: document.getElementById("logs-select-service"),
    logsSelectLines: document.getElementById("logs-select-lines"),
    logsFilterInput: document.getElementById("logs-filter-input"),
    logsToggleAutotail: document.getElementById("logs-toggle-autotail"),
    btnRefreshLogs: document.getElementById("btn-refresh-logs"),
    btnClearLogs: document.getElementById("btn-clear-logs"),
    terminalServiceTitle: document.getElementById("terminal-service-title"),
    terminalStatus: document.getElementById("terminal-status"),
    logsPreOutput: document.getElementById("logs-pre-output"),

    // Theme & Toasts
    themeToggle: document.getElementById("theme-toggle"),
    mobileThemeToggle: document.getElementById("mobile-theme-toggle"),
    toastContainer: document.getElementById("toast-container"),
  };

  // --------------------------------------------------------------------------
  // Navigation & Routing (SPA)
  // --------------------------------------------------------------------------

  function initNavigation() {
    window.addEventListener("hashchange", handleHashChange);
    
    // Initial route check
    const currentHash = window.location.hash.replace("#", "");
    navigateToPage(currentHash || "dashboard");

    // Drawer toggles
    if (elements.menuToggle) {
      elements.menuToggle.addEventListener("click", toggleMobileDrawer);
    }
    if (elements.drawerBackdrop) {
      elements.drawerBackdrop.addEventListener("click", closeMobileDrawer);
    }

    // Refresh button
    if (elements.btnRefresh) {
      elements.btnRefresh.addEventListener("click", () => {
        elements.btnRefresh.classList.add("spinning");
        fetchInitialData().finally(() => {
          setTimeout(() => elements.btnRefresh.classList.remove("spinning"), 500);
        });
      });
    }

    // Quick restart VPN button on Dashboard
    if (elements.btnDashRestartVpn) {
      elements.btnDashRestartVpn.addEventListener("click", () => {
        restartService("xray", elements.btnDashRestartVpn);
      });
    }

    // Refresh devices button
    if (elements.btnRefreshDevices) {
      elements.btnRefreshDevices.addEventListener("click", () => {
        fetchDevicesData();
      });
    }
  }

  function handleHashChange() {
    const hash = window.location.hash.replace("#", "") || "dashboard";
    navigateToPage(hash);
  }

  function navigateToPage(pageId) {
    const targetSection = document.getElementById(`page-${pageId}`);
    if (!targetSection) {
      pageId = "dashboard";
    }

    state.activePage = pageId;

    // Toggle nav active state
    elements.navItems.forEach((item) => {
      if (item.getAttribute("data-page") === pageId) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    // Toggle page containers
    elements.pageSections.forEach((section) => {
      if (section.id === `page-${pageId}`) {
        section.classList.add("active");
      } else {
        section.classList.remove("active");
      }
    });

    // Update Header Title
    const titleMap = {
      dashboard: "Dashboard",
      vpn: "VPN Management",
      wifi: "Wi-Fi Access Point",
      devices: "Connected Devices",
      network: "Network & Interfaces",
      diagnostics: "Diagnostics & Automatic Repair",
      logs: "System Logs",
      system: "System Diagnostics & Services",
      settings: "Gateway Settings",
    };
    if (elements.pageTitle) {
      elements.pageTitle.textContent = titleMap[pageId] || "Dashboard";
    }

    closeMobileDrawer();

    // Trigger page-specific data refresh
    if (pageId === "system") {
      fetchSystemData();
    } else if (pageId === "dashboard") {
      fetchDashboardStatus();
    } else if (pageId === "wifi") {
      fetchWifiData();
    } else if (pageId === "devices") {
      fetchDevicesData();
    } else if (pageId === "vpn") {
      fetchVpnData();
      fetchSubscriptionData();
    } else if (pageId === "network") {
      fetchNetworkData();
    } else if (pageId === "diagnostics") {
      fetchDiagnosticsData();
    } else if (pageId === "settings") {
      fetchBackupsData();
    } else if (pageId === "logs") {
      fetchLogsData();
    }
  }

  function toggleMobileDrawer() {
    elements.sidebar.classList.toggle("open");
    elements.drawerBackdrop.classList.toggle("active");
  }

  function closeMobileDrawer() {
    elements.sidebar.classList.remove("open");
    elements.drawerBackdrop.classList.remove("active");
  }

  // --------------------------------------------------------------------------
  // Theme Management (Dark / Light)
  // --------------------------------------------------------------------------

  function initTheme() {
    const savedTheme = localStorage.getItem("vg_theme") || "dark";
    applyTheme(savedTheme);

    const toggleHandler = () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
    };

    if (elements.themeToggle) elements.themeToggle.addEventListener("click", toggleHandler);
    if (elements.mobileThemeToggle) elements.mobileThemeToggle.addEventListener("click", toggleHandler);
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("vg_theme", theme);
  }

  // --------------------------------------------------------------------------
  // Real-time Telemetry (SSE & Polling Fallback)
  // --------------------------------------------------------------------------

  let eventSource = null;
  let sseReconnectTimer = null;
  let fallbackPollingInterval = null;

  function initRealtimeStream() {
    if (typeof EventSource === "undefined") {
      console.warn("EventSource not supported. Falling back to HTTP polling.");
      startPollingFallback();
      return;
    }

    connectSSE();
  }

  function connectSSE() {
    if (eventSource) {
      eventSource.close();
    }

    try {
      eventSource = new EventSource("/api/events");

      eventSource.onopen = () => {
        setOnlineState(true);
        setSseConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleLiveMetrics(data);
        } catch (err) {
          console.error("Failed to parse SSE payload", err);
        }
      };

      eventSource.onerror = () => {
        setSseConnected(false);
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        clearTimeout(sseReconnectTimer);
        sseReconnectTimer = setTimeout(connectSSE, 3000);
        startPollingFallback();
      };
    } catch (err) {
      console.error("SSE connection error", err);
      startPollingFallback();
    }
  }

  function startPollingFallback() {
    if (fallbackPollingInterval) return;
    fallbackPollingInterval = setInterval(() => {
      fetchDashboardStatus();
      if (state.activePage === "system") {
        fetchSystemData();
      } else if (state.activePage === "devices") {
        fetchDevicesData();
      } else if (state.activePage === "vpn") {
        fetchVpnData();
      } else if (state.activePage === "network") {
        fetchNetworkData();
      } else if (state.activePage === "diagnostics") {
        fetchDiagnosticsData();
      }
    }, 3000);
  }

  function setSseConnected(connected) {
    state.sseConnected = connected;
    if (elements.sidebarSseStatus) {
      if (connected) {
        elements.sidebarSseStatus.classList.remove("offline");
        elements.sidebarSseStatus.querySelector(".status-text").textContent = "Live Sync";
      } else {
        elements.sidebarSseStatus.classList.add("offline");
        elements.sidebarSseStatus.querySelector(".status-text").textContent = "Reconnecting...";
      }
    }
  }

  function setOnlineState(online) {
    state.backendOnline = online;
    if (elements.backendAlert) {
      if (online) {
        elements.backendAlert.classList.add("hidden");
      } else {
        elements.backendAlert.classList.remove("hidden");
      }
    }
  }

  function handleLiveMetrics(data) {
    setOnlineState(true);
    const { system, traffic, vpn_status, vpn_latency, services, wifi } = data;

    // 1. Dashboard System Meters
    if (system) {
      if (elements.dashCpuPct) elements.dashCpuPct.textContent = `${system.cpu_percent}%`;
      if (elements.dashCpuBar) elements.dashCpuBar.style.width = `${Math.min(100, system.cpu_percent)}%`;

      if (elements.dashRamPct) elements.dashRamPct.textContent = `${system.ram_percent}%`;
      if (elements.dashRamBar) elements.dashRamBar.style.width = `${Math.min(100, system.ram_percent)}%`;
      if (elements.dashRamSub) elements.dashRamSub.textContent = `${system.ram_used_gb} / ${system.ram_total_gb} GB`;

      if (elements.dashTempVal) {
        elements.dashTempVal.textContent = system.temperature_c !== null ? `${system.temperature_c}°C` : "N/A";
      }
      if (elements.dashTempBar && system.temperature_c !== null) {
        elements.dashTempBar.style.width = `${Math.min(100, (system.temperature_c / 90) * 100)}%`;
      }

      if (elements.dashUptimeVal) elements.dashUptimeVal.textContent = system.uptime || "--";

      // Also update System page meters if visible
      if (elements.sysCpuVal) elements.sysCpuVal.textContent = `${system.cpu_percent}%`;
      if (elements.sysCpuBar) elements.sysCpuBar.style.width = `${Math.min(100, system.cpu_percent)}%`;
      if (elements.sysRamVal) elements.sysRamVal.textContent = `${system.ram_percent}%`;
      if (elements.sysRamBar) elements.sysRamBar.style.width = `${Math.min(100, system.ram_percent)}%`;
      if (elements.sysRamText) elements.sysRamText.textContent = `${system.ram_used_gb} / ${system.ram_total_gb} GB`;
      if (elements.sysTempVal && system.temperature_c !== null) {
        elements.sysTempVal.textContent = `${system.temperature_c}°C`;
      }
      if (elements.sysTempBar && system.temperature_c !== null) {
        elements.sysTempBar.style.width = `${Math.min(100, (system.temperature_c / 90) * 100)}%`;
      }
    }

    // 2. Traffic Rates
    if (traffic) {
      if (elements.dashSpeedDown) elements.dashSpeedDown.textContent = traffic.rx_mbps.toFixed(1);
      if (elements.dashSpeedUp) elements.dashSpeedUp.textContent = traffic.tx_mbps.toFixed(1);
    }

    // 3. Latency
    if (vpn_latency !== undefined) {
      const latStr = `${vpn_latency} ms`;
      if (elements.dashHeroLatency) elements.dashHeroLatency.textContent = latStr;
      if (elements.dashLatencyBadge) elements.dashLatencyBadge.textContent = latStr;
      if (elements.vpnInfoLatency) elements.vpnInfoLatency.textContent = latStr;
    }

    // 4. VPN State
    if (vpn_status) {
      updateVpnIndicator(vpn_status);
    }

    // 5. Wi-Fi & Devices telemetry
    if (wifi) {
      if (elements.dashWifiSsid) elements.dashWifiSsid.textContent = wifi.ssid;
      if (elements.dashWifiChannel) elements.dashWifiChannel.textContent = `${wifi.channel} (2.4 GHz)`;
      if (wifi.connected_devices !== undefined) {
        const count = wifi.connected_devices;
        if (elements.dashWifiClients) {
          elements.dashWifiClients.textContent = `${count} ${count === 1 ? "device" : "devices"}`;
        }
        if (elements.navClientsBadge) elements.navClientsBadge.textContent = count;
        if (elements.wifiInfoDevicesLink) {
          elements.wifiInfoDevicesLink.textContent = `${count} ${count === 1 ? "device" : "devices"} →`;
        }
      }
    }

    // 6. Update service table statuses dynamically if present
    if (services && state.activePage === "system") {
      updateServiceStatusesInTable(services);
    }
  }

  function updateVpnIndicator(status) {
    const isConnected = status === "connected";
    const statusText = isConnected ? "VPN Connected" : (status === "connecting" ? "VPN Connecting" : "VPN Disconnected");

    if (elements.topbarVpnText) elements.topbarVpnText.textContent = statusText;
    if (elements.dashMasterStatus) elements.dashMasterStatus.textContent = statusText;
    
    const dotClass = isConnected ? "" : (status === "connecting" ? "warning" : "error");

    if (elements.topbarVpnDot) elements.topbarVpnDot.className = `status-indicator-dot ${dotClass}`.trim();
    if (elements.mobileVpnBeacon) elements.mobileVpnBeacon.className = `status-indicator-dot ${dotClass}`.trim();
    if (elements.brandBeacon) {
      elements.brandBeacon.style.backgroundColor = isConnected ? "var(--success)" : (status === "connecting" ? "var(--warning)" : "var(--danger)");
    }

    if (elements.dashMasterBadge) {
      elements.dashMasterBadge.className = isConnected ? "hero-badge badge-active" : "hero-badge badge-danger";
      elements.dashMasterBadge.textContent = isConnected ? "● Active" : "● Offline";
    }

    if (elements.vpnPageStatusBadge) {
      elements.vpnPageStatusBadge.className = isConnected ? "status-badge badge-success" : "status-badge badge-danger";
      elements.vpnPageStatusBadge.textContent = isConnected ? "● Connected" : "○ Disconnected";
    }

    if (elements.btnVpnToggle) {
      if (isConnected) {
        elements.btnVpnToggle.className = "btn btn-danger btn-sm";
        elements.btnVpnToggle.textContent = "Disconnect";
      } else {
        elements.btnVpnToggle.className = "btn btn-primary btn-sm";
        elements.btnVpnToggle.textContent = "Connect";
      }
    }
  }

  // --------------------------------------------------------------------------
  // Data Fetching: REST Endpoints
  // --------------------------------------------------------------------------

  async function fetchInitialData() {
    await Promise.allSettled([
      fetchDashboardStatus(),
      fetchSystemData(),
      fetchWifiData(),
      fetchDevicesData(),
      fetchVpnData(),
      fetchSubscriptionData(),
      fetchNetworkData(),
      fetchDiagnosticsData(),
      fetchBackupsData(),
      checkAuthStatus(),
    ]);
  }

  async function fetchDashboardStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);

      // VPN Info
      if (data.vpn) {
        updateVpnIndicator(data.vpn.status);
        if (elements.dashHeroProto) elements.dashHeroProto.textContent = `${data.vpn.protocol} / ${data.vpn.security}`;
        if (elements.dashVpnBadge) elements.dashVpnBadge.textContent = `${data.vpn.protocol} / ${data.vpn.security}`;
        if (elements.dashVpnServer) elements.dashVpnServer.textContent = data.vpn.server || "--";
        if (elements.dashVpnSni) elements.dashVpnSni.textContent = data.vpn.sni || "--";
        if (elements.dashVpnTraffic) {
          elements.dashVpnTraffic.textContent = `↓ ${data.vpn.traffic_down}   ↑ ${data.vpn.traffic_up}`;
        }
      }

      // Internet Info
      if (data.internet) {
        if (elements.dashWanIface) elements.dashWanIface.textContent = data.internet.interface;
        if (elements.dashWanIp) elements.dashWanIp.textContent = data.internet.ip;
        if (elements.dashWanGw) elements.dashWanGw.textContent = data.internet.gateway;
        if (elements.dashWanBadge) {
          const isWanUp = data.internet.status === "connected";
          elements.dashWanBadge.className = isWanUp ? "status-badge badge-success" : "status-badge badge-danger";
          elements.dashWanBadge.textContent = isWanUp ? "Connected" : "Disconnected";
        }
      }

      // Wi-Fi Info
      if (data.wifi) {
        if (elements.dashWifiSsid) elements.dashWifiSsid.textContent = data.wifi.ssid;
        if (elements.dashWifiClients) {
          const clientCount = data.wifi.connected_devices;
          elements.dashWifiClients.textContent = `${clientCount} ${clientCount === 1 ? "device" : "devices"}`;
          if (elements.navClientsBadge) elements.navClientsBadge.textContent = clientCount;
        }
      }

      // Bandwidth
      if (data.traffic) {
        if (elements.dashSpeedDown) elements.dashSpeedDown.textContent = data.traffic.download_mbps.toFixed(1);
        if (elements.dashSpeedUp) elements.dashSpeedUp.textContent = data.traffic.upload_mbps.toFixed(1);
      }
    } catch (err) {
      console.error("Failed to fetch /api/status:", err);
      setOnlineState(false);
    }
  }

  async function fetchSystemData() {
    try {
      const res = await fetch("/api/system");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);
      state.lastSystemData = data;

      // Platform Info
      if (data.hardware) {
        const hw = data.hardware;
        if (elements.sysHostname) elements.sysHostname.textContent = hw.hostname;
        if (elements.sysOs) elements.sysOs.textContent = hw.os;
        if (elements.sysKernel) elements.sysKernel.textContent = hw.kernel;
        if (elements.sysArch) elements.sysArch.textContent = hw.arch;
        if (elements.sysArchBadge) elements.sysArchBadge.textContent = hw.arch;
        if (elements.sysUptime) elements.sysUptime.textContent = hw.uptime;
      }

      // Resources
      if (data.resources) {
        const r = data.resources;
        if (elements.sysCores) elements.sysCores.textContent = `${r.cpu_cores} Cores`;
        if (elements.sysCpuVal) elements.sysCpuVal.textContent = `${r.cpu_percent}%`;
        if (elements.sysCpuBar) elements.sysCpuBar.style.width = `${Math.min(100, r.cpu_percent)}%`;

        if (r.ram) {
          if (elements.sysRamVal) elements.sysRamVal.textContent = `${r.ram.percent}%`;
          if (elements.sysRamBar) elements.sysRamBar.style.width = `${Math.min(100, r.ram.percent)}%`;
          if (elements.sysRamText) elements.sysRamText.textContent = `${r.ram.used_gb} / ${r.ram.total_gb} GB`;
        }

        if (r.disk) {
          if (elements.sysDiskVal) elements.sysDiskVal.textContent = `${r.disk.percent}%`;
          if (elements.sysDiskBar) elements.sysDiskBar.style.width = `${Math.min(100, r.disk.percent)}%`;
          if (elements.sysDiskText) elements.sysDiskText.textContent = `${r.disk.used_gb} / ${r.disk.total_gb} GB`;
        }

        if (elements.sysTempVal) {
          elements.sysTempVal.textContent = r.temperature_c !== null ? `${r.temperature_c}°C` : "N/A";
        }
        if (elements.sysTempBar && r.temperature_c !== null) {
          elements.sysTempBar.style.width = `${Math.min(100, (r.temperature_c / 90) * 100)}%`;
        }
      }

      // Services Table
      if (data.services) {
        renderServicesTable(data.services);
      }
    } catch (err) {
      console.error("Failed to fetch /api/system:", err);
      setOnlineState(false);
    }
  }

  // --------------------------------------------------------------------------
  // VPN & VLESS Management (Phase 3)
  // --------------------------------------------------------------------------

  async function fetchVpnData() {
    try {
      const res = await fetch("/api/vpn");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);
      state.lastVpnData = data;

      const isConnected = data.status === "connected";
      updateVpnIndicator(data.status);

      if (elements.vpnInfoProto) elements.vpnInfoProto.textContent = data.protocol || "VLESS";
      if (elements.vpnInfoSecurity) elements.vpnInfoSecurity.textContent = data.security || "REALITY";
      if (elements.vpnInfoTransport) elements.vpnInfoTransport.textContent = data.transport || "TCP";
      if (elements.vpnInfoServer) elements.vpnInfoServer.textContent = data.server || "--";
      if (elements.vpnInfoSni) elements.vpnInfoSni.textContent = data.sni || "--";
      if (elements.vpnInfoFlow) elements.vpnInfoFlow.textContent = data.flow || "--";
      if (elements.vpnInfoFp) elements.vpnInfoFp.textContent = data.fingerprint || "--";
      if (elements.vpnInfoUuid) elements.vpnInfoUuid.textContent = data.masked_uuid || "••••••••";
      if (elements.vpnInfoUptime) elements.vpnInfoUptime.textContent = data.uptime || "--";
      if (elements.vpnInfoTraffic) {
        elements.vpnInfoTraffic.textContent = `↓ ${data.traffic_down}   ↑ ${data.traffic_up}`;
      }
      if (elements.vpnInfoLatency) {
        elements.vpnInfoLatency.textContent = data.latency_ms ? `${data.latency_ms} ms` : "--";
      }

      // Populate summary preview if present
      if (elements.sumServer) elements.sumServer.textContent = data.server_ip || "--";
      if (elements.sumPort) elements.sumPort.textContent = String(data.server_port || "443");
      if (elements.sumSecurity) elements.sumSecurity.textContent = data.security || "REALITY";
      if (elements.sumTransport) elements.sumTransport.textContent = data.transport || "TCP";
      if (elements.sumSni) elements.sumSni.textContent = data.sni || "--";
      if (elements.sumFp) elements.sumFp.textContent = data.fingerprint || "--";
      if (elements.sumFlow) elements.sumFlow.textContent = data.flow || "--";
      if (elements.sumUuid) elements.sumUuid.textContent = data.masked_uuid || "••••••••";
      if (elements.summaryProtoBadge) elements.summaryProtoBadge.textContent = `${data.protocol} / ${data.security}`;

    } catch (err) {
      console.error("Failed to fetch /api/vpn:", err);
      setOnlineState(false);
    }
  }

  // --------------------------------------------------------------------------
  // VLESS Subscription Manager
  // --------------------------------------------------------------------------

  function getLatencyClass(latency) {
    if (latency === null || latency === undefined) return "none";
    if (latency <= 100) return "fast";
    if (latency <= 250) return "medium";
    return "slow";
  }

  function formatTimestamp(isoStr) {
    if (!isoStr) return "--";
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return isoStr;
    }
  }

  async function fetchSubscriptionData() {
    try {
      const res = await fetch("/api/vpn/subscription");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderSubscriptionData(data);
    } catch (err) {
      console.error("Failed to fetch subscription data:", err);
    }
  }

  function renderSubscriptionData(data) {
    const servers = data.servers || [];
    const activeId = data.active_server_id;

    if (elements.subServersCountBadge) {
      elements.subServersCountBadge.textContent = `${servers.length} Server${servers.length === 1 ? "" : "s"}`;
    }

    if (elements.subMetaBar) {
      if (data.url || data.updated_at) {
        elements.subMetaBar.classList.remove("hidden");
        if (elements.subMetaUrlVal) elements.subMetaUrlVal.textContent = data.url || "Custom links bundle";
        if (elements.subMetaTimeVal) elements.subMetaTimeVal.textContent = formatTimestamp(data.updated_at);
      } else {
        elements.subMetaBar.classList.add("hidden");
      }
    }

    if (!elements.subServersTbody) return;

    if (servers.length === 0) {
      elements.subServersTbody.innerHTML = `
        <tr>
          <td colspan="6" class="table-loading">
            No servers imported yet. Paste your subscription link or VLESS links above to load servers.
          </td>
        </tr>
      `;
      return;
    }

    let rowsHtml = "";
    for (const s of servers) {
      const isActive = s.id === activeId;
      const statusBadge = isActive
        ? `<span class="sub-server-badge-active">● Active</span>`
        : `<span class="badge-neutral">Standby</span>`;

      const latClass = getLatencyClass(s.latency_ms);
      const latBadge = s.latency_ms !== null && s.latency_ms !== undefined
        ? `<span class="ping-badge ${latClass}">${s.latency_ms} ms</span>`
        : `<span class="ping-badge none">--</span>`;

      const connectBtn = isActive
        ? `<button type="button" class="btn btn-secondary btn-sm" disabled>Connected</button>`
        : `<button type="button" class="btn btn-primary btn-sm btn-sub-connect" data-id="${escapeHtml(s.id)}" title="Switch VPN tunnel to this server">Connect</button>`;

      rowsHtml += `
        <tr class="sub-server-row ${isActive ? "active-server-row" : ""}" data-id="${escapeHtml(s.id)}">
          <td>${statusBadge}</td>
          <td>
            <div class="sub-server-remark">
              <span>${escapeHtml(s.remark || "Server")}</span>
            </div>
          </td>
          <td class="font-mono text-muted" style="font-size: 12px;">${escapeHtml(s.address)}:${s.port}</td>
          <td><span class="badge-neutral">${escapeHtml(s.security || "REALITY")}</span></td>
          <td>${latBadge}</td>
          <td>
            <div class="sub-action-buttons">
              ${connectBtn}
              <button type="button" class="btn btn-secondary btn-sm btn-sub-ping" data-id="${escapeHtml(s.id)}" title="Ping server">⚡</button>
              <button type="button" class="btn btn-secondary btn-sm btn-sub-delete" data-id="${escapeHtml(s.id)}" title="Delete server">✕</button>
            </div>
          </td>
        </tr>
      `;
    }

    elements.subServersTbody.innerHTML = rowsHtml;
  }

  function initVpnActions() {
    // Restart VPN
    if (elements.btnVpnRestart) {
      elements.btnVpnRestart.addEventListener("click", async () => {
        elements.btnVpnRestart.disabled = true;
        showToast("Restarting Xray VPN tunnel...", "info", 2000);
        try {
          const res = await fetch("/api/vpn/restart", { method: "POST" });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || "Failed to restart VPN");
          showToast("Xray VPN restarted successfully", "success", 3000);
          await fetchVpnData();
          await fetchDashboardStatus();
        } catch (err) {
          showToast(`VPN Restart failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnVpnRestart.disabled = false;
        }
      });
    }

    // Connect / Disconnect Toggle
    if (elements.btnVpnToggle) {
      elements.btnVpnToggle.addEventListener("click", async () => {
        const isConnected = state.lastVpnData && state.lastVpnData.status === "connected";
        const endpoint = isConnected ? "/api/vpn/disconnect" : "/api/vpn/connect";
        const actionName = isConnected ? "Disconnecting" : "Connecting";

        elements.btnVpnToggle.disabled = true;
        showToast(`${actionName} VPN...`, "info", 2000);

        try {
          const res = await fetch(endpoint, { method: "POST" });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || "Failed to change VPN state");
          showToast(`VPN ${isConnected ? "disconnected" : "connected"}`, "success", 3000);
          await fetchVpnData();
          await fetchDashboardStatus();
        } catch (err) {
          showToast(`Action failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnVpnToggle.disabled = false;
        }
      });
    }

    // Test Connection Latency
    if (elements.btnVpnTest) {
      elements.btnVpnTest.addEventListener("click", async () => {
        elements.btnVpnTest.disabled = true;
        elements.btnVpnTest.innerHTML = `<span style="display:inline-block;animation:spin 0.8s linear infinite;">⏳</span> Testing...`;
        showToast("Testing VLESS server latency...", "info", 1500);

        try {
          const res = await fetch("/api/vpn/test", { method: "POST" });
          const data = await res.json();
          if (data.connected) {
            showToast(`Connection active: ${data.latency_ms} ms latency to ${data.target}`, "success", 4000);
            if (elements.vpnInfoLatency) elements.vpnInfoLatency.textContent = `${data.latency_ms} ms`;
            if (elements.dashHeroLatency) elements.dashHeroLatency.textContent = `${data.latency_ms} ms`;
          } else {
            showToast(`Connection test failed: ${data.error || "Unreachable"}`, "danger", 4000);
          }
        } catch (err) {
          showToast(`Test error: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnVpnTest.disabled = false;
          elements.btnVpnTest.textContent = "Test Connection";
        }
      });
    }

    // Clear VLESS input
    if (elements.btnVlessClear && elements.vlessInputUri) {
      elements.btnVlessClear.addEventListener("click", () => {
        elements.vlessInputUri.value = "";
        if (elements.vlessSummaryBox) elements.vlessSummaryBox.classList.add("hidden");
      });
    }

    // Import VLESS or Subscription Configuration
    if (elements.btnVlessImport && elements.vlessInputUri) {
      elements.btnVlessImport.addEventListener("click", async () => {
        const raw = elements.vlessInputUri.value.trim();
        if (!raw) {
          showToast("Please paste a subscription URL, Base64 bundle, or VLESS links", "danger");
          elements.vlessInputUri.focus();
          return;
        }

        elements.btnVlessImport.disabled = true;
        elements.btnVlessImport.textContent = "Importing & Parsing...";
        showToast("Importing and parsing server configurations...", "info", 2000);

        try {
          const res = await fetch("/api/vpn/subscription/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: raw }),
          });

          const result = await res.json();
          if (!res.ok) {
            throw new Error(result.detail || result.error || "Failed to import subscription or VLESS");
          }

          // Populate summary box if profile exists
          const prof = result.profile || (result.active_server ? {
            server: result.active_server.address,
            port: result.active_server.port,
            security: result.active_server.security,
            transport: result.active_server.transport,
            sni: result.active_server.sni,
            flow: result.active_server.flow,
            fingerprint: result.active_server.fingerprint || "--",
            masked_uuid: result.active_server.masked_uuid,
          } : null);

          if (prof) {
            if (elements.sumServer) elements.sumServer.textContent = prof.server;
            if (elements.sumPort) elements.sumPort.textContent = String(prof.port);
            if (elements.sumSecurity) elements.sumSecurity.textContent = prof.security;
            if (elements.sumTransport) elements.sumTransport.textContent = prof.transport;
            if (elements.sumSni) elements.sumSni.textContent = prof.sni || "--";
            if (elements.sumFp) elements.sumFp.textContent = prof.fingerprint || "--";
            if (elements.sumFlow) elements.sumFlow.textContent = prof.flow || "--";
            if (elements.sumUuid) elements.sumUuid.textContent = prof.masked_uuid || "••••••••";
            if (elements.summaryProtoBadge) elements.summaryProtoBadge.textContent = `${prof.security}`;
            if (elements.vlessSummaryBox) elements.vlessSummaryBox.classList.remove("hidden");
          }

          const count = result.count !== undefined ? result.count : (result.servers ? result.servers.length : 1);
          showToast(`Successfully imported ${count} server${count === 1 ? "" : "s"}!`, "success", 4000);

          await fetchSubscriptionData();
          await fetchVpnData();
          await fetchDashboardStatus();
        } catch (err) {
          console.error("Import error:", err);
          showToast(`Import failed: ${err.message}`, "danger", 5000);
        } finally {
          elements.btnVlessImport.disabled = false;
          elements.btnVlessImport.textContent = "Import & Parse";
        }
      });
    }

    // Ping All Servers
    if (elements.btnSubPingAll) {
      elements.btnSubPingAll.addEventListener("click", async () => {
        elements.btnSubPingAll.disabled = true;
        const originalText = elements.btnSubPingAll.innerHTML;
        elements.btnSubPingAll.innerHTML = "⚡ Pinging...";
        showToast("Testing latency to all servers...", "info", 3000);

        try {
          const res = await fetch("/api/vpn/subscription/ping", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || "Failed to ping servers");

          await fetchSubscriptionData();
          showToast("Latency check completed", "success", 3000);
        } catch (err) {
          showToast(`Ping failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnSubPingAll.disabled = false;
          elements.btnSubPingAll.innerHTML = originalText;
        }
      });
    }

    // Refresh Subscription
    if (elements.btnSubRefresh) {
      elements.btnSubRefresh.addEventListener("click", async () => {
        elements.btnSubRefresh.disabled = true;
        const originalText = elements.btnSubRefresh.innerHTML;
        elements.btnSubRefresh.innerHTML = "🔄 Refreshing...";
        showToast("Fetching latest subscription updates...", "info", 2000);

        try {
          const res = await fetch("/api/vpn/subscription/refresh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || "Failed to refresh subscription");

          const count = result.count !== undefined ? result.count : (result.servers ? result.servers.length : 0);
          showToast(`Subscription refreshed: ${count} servers available`, "success", 4000);

          await fetchSubscriptionData();
          await fetchVpnData();
          await fetchDashboardStatus();
        } catch (err) {
          showToast(`Refresh failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnSubRefresh.disabled = false;
          elements.btnSubRefresh.innerHTML = originalText;
        }
      });
    }

    // Table Event Delegation (Connect, Ping, Delete)
    if (elements.subServersTbody) {
      elements.subServersTbody.addEventListener("click", async (e) => {
        const target = e.target;

        // Connect button
        const connectBtn = target.closest(".btn-sub-connect");
        if (connectBtn) {
          const serverId = connectBtn.dataset.id;
          if (!serverId) return;
          connectBtn.disabled = true;
          connectBtn.textContent = "Connecting...";
          showToast("Switching active server...", "info", 2000);

          try {
            const res = await fetch("/api/vpn/subscription/select", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ server_id: serverId }),
            });
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || "Failed to switch server");

            showToast(`Connected to server: ${result.server ? result.server.remark : serverId}`, "success", 3000);
            await fetchSubscriptionData();
            await fetchVpnData();
            await fetchDashboardStatus();
          } catch (err) {
            showToast(`Switch failed: ${err.message}`, "danger", 4000);
            connectBtn.disabled = false;
            connectBtn.textContent = "Connect";
          }
          return;
        }

        // Ping button
        const pingBtn = target.closest(".btn-sub-ping");
        if (pingBtn) {
          const serverId = pingBtn.dataset.id;
          if (!serverId) return;
          pingBtn.disabled = true;
          pingBtn.textContent = "⋯";

          try {
            const res = await fetch("/api/vpn/subscription/ping", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ server_id: serverId }),
            });
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || "Failed to test server latency");

            await fetchSubscriptionData();
          } catch (err) {
            showToast(`Ping failed: ${err.message}`, "danger", 3000);
            pingBtn.disabled = false;
            pingBtn.textContent = "⚡";
          }
          return;
        }

        // Delete button
        const deleteBtn = target.closest(".btn-sub-delete");
        if (deleteBtn) {
          const serverId = deleteBtn.dataset.id;
          if (!serverId) return;
          if (!confirm("Are you sure you want to remove this server from the list?")) return;

          deleteBtn.disabled = true;
          try {
            const res = await fetch(`/api/vpn/subscription/servers/${encodeURIComponent(serverId)}`, {
              method: "DELETE",
            });
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || "Failed to delete server");

            showToast("Server removed", "info", 2000);
            await fetchSubscriptionData();
          } catch (err) {
            showToast(`Delete failed: ${err.message}`, "danger", 3000);
            deleteBtn.disabled = false;
          }
          return;
        }
      });
    }
  }

  // --------------------------------------------------------------------------
  // Wi-Fi Access Point Management (Phase 2)
  // --------------------------------------------------------------------------

  async function fetchWifiData() {
    try {
      const res = await fetch("/api/wifi");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);
      state.lastWifiData = data;

      // Status card
      if (elements.wifiStatusBadge) {
        const isRunning = data.status === "running";
        elements.wifiStatusBadge.className = isRunning ? "status-badge badge-success" : "status-badge badge-danger";
        elements.wifiStatusBadge.textContent = isRunning ? "● Running" : "○ Stopped";
      }

      if (elements.wifiInfoIface) elements.wifiInfoIface.textContent = data.interface || "wlp4s0";
      if (elements.wifiInfoChipset) elements.wifiInfoChipset.textContent = data.chipset || "Qualcomm Atheros AR9285";
      if (elements.wifiInfoDriver) elements.wifiInfoDriver.textContent = data.driver || "ath9k";
      if (elements.wifiInfoAp) {
        elements.wifiInfoAp.textContent = data.ap_supported ? "Supported (✓)" : "Not Supported (✕)";
        elements.wifiInfoAp.className = data.ap_supported ? "stat-val font-bold text-success" : "stat-val font-bold text-danger";
      }
      if (elements.wifiInfoFreq) elements.wifiInfoFreq.textContent = data.frequency || "2.4 GHz";
      if (elements.wifiInfoChannel) elements.wifiInfoChannel.textContent = data.channel;
      if (elements.wifiInfoWidth) elements.wifiInfoWidth.textContent = data.channel_width || "20 MHz";
      if (elements.wifiInfoTxpower) elements.wifiInfoTxpower.textContent = `${data.tx_power_dbm} dBm`;
      if (elements.wifiInfoSecurity) elements.wifiInfoSecurity.textContent = data.security || "WPA2-PSK";
      if (elements.wifiInfoDevicesLink) {
        const count = data.connected_devices || 0;
        elements.wifiInfoDevicesLink.textContent = `${count} ${count === 1 ? "device" : "devices"} →`;
      }

      // Populate form if not currently being edited by user
      if (elements.wifiInputSsid && document.activeElement !== elements.wifiInputSsid) {
        elements.wifiInputSsid.value = data.ssid || "freedom";
      }
      if (elements.wifiSelectChannel) {
        elements.wifiSelectChannel.value = String(data.channel);
      }
      if (elements.wifiSelectCountry && data.country) {
        elements.wifiSelectCountry.value = data.country;
      }
      if (elements.wifiToggle11n) {
        elements.wifiToggle11n.checked = Boolean(data.ieee80211n);
      }
    } catch (err) {
      console.error("Failed to fetch /api/wifi:", err);
      setOnlineState(false);
    }
  }

  function initWifiForm() {
    // Password visibility toggle
    if (elements.btnToggleWifiPass && elements.wifiInputPass) {
      elements.btnToggleWifiPass.addEventListener("click", () => {
        const isPass = elements.wifiInputPass.type === "password";
        elements.wifiInputPass.type = isPass ? "text" : "password";
        elements.btnToggleWifiPass.textContent = isPass ? "🙈" : "👁";
      });
    }

    // Open confirmation modal on Apply button
    if (elements.btnWifiApply) {
      elements.btnWifiApply.addEventListener("click", () => {
        const ssid = elements.wifiInputSsid.value.trim();
        const pass = elements.wifiInputPass.value.trim();
        const channel = elements.wifiSelectChannel.value;
        const country = elements.wifiSelectCountry.value;
        const ieee80211n = elements.wifiToggle11n.checked;

        if (!ssid) {
          showToast("Please enter a valid Wi-Fi SSID", "danger");
          elements.wifiInputSsid.focus();
          return;
        }

        if (pass.length > 0 && pass.length < 8) {
          showToast("Password must be at least 8 characters", "danger");
          elements.wifiInputPass.focus();
          return;
        }

        // Fill modal preview
        if (elements.modalDiffSsid) elements.modalDiffSsid.textContent = ssid;
        if (elements.modalDiffChannel) elements.modalDiffChannel.textContent = channel === "0" ? "Auto" : channel;
        if (elements.modalDiffCountry) elements.modalDiffCountry.textContent = country;
        if (elements.modalDiff11n) elements.modalDiff11n.textContent = ieee80211n ? "ON" : "OFF";

        // Show modal
        if (elements.wifiConfirmModal) {
          elements.wifiConfirmModal.classList.remove("hidden");
        }
      });
    }

    // Close modal on Cancel
    if (elements.btnModalWifiCancel && elements.wifiConfirmModal) {
      elements.btnModalWifiCancel.addEventListener("click", () => {
        elements.wifiConfirmModal.classList.add("hidden");
      });
    }

    // Execute apply on Confirm
    if (elements.btnModalWifiConfirm) {
      elements.btnModalWifiConfirm.addEventListener("click", async () => {
        const ssid = elements.wifiInputSsid.value.trim();
        const pass = elements.wifiInputPass.value.trim() || (state.lastWifiData ? "freedompassword" : "freedompassword");
        const channel = parseInt(elements.wifiSelectChannel.value, 10);
        const country = elements.wifiSelectCountry.value;
        const ieee80211n = elements.wifiToggle11n.checked;

        elements.btnModalWifiConfirm.disabled = true;
        elements.btnModalWifiConfirm.textContent = "Applying...";

        try {
          const res = await fetch("/api/wifi/apply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ssid: ssid,
              password: pass,
              channel: channel,
              country: country,
              ieee80211n: ieee80211n,
            }),
          });

          const result = await res.json();
          if (!res.ok) {
            throw new Error(result.detail || result.error || "Failed to apply configuration");
          }

          if (elements.wifiConfirmModal) elements.wifiConfirmModal.classList.add("hidden");
          showToast("Wi-Fi settings applied successfully!", "success", 4000);

          await fetchWifiData();
          await fetchDashboardStatus();
        } catch (err) {
          console.error("Wi-Fi apply error:", err);
          showToast(`Apply failed: ${err.message}`, "danger", 5000);
        } finally {
          elements.btnModalWifiConfirm.disabled = false;
          elements.btnModalWifiConfirm.textContent = "Apply";
        }
      });
    }
  }

  // --------------------------------------------------------------------------
  // Connected Devices Management (Phase 2)
  // --------------------------------------------------------------------------

  async function fetchDevicesData() {
    try {
      const res = await fetch("/api/clients");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);
      state.lastDevicesData = data;

      const devices = data.clients || [];
      const count = devices.length;

      // Update pills and badges
      if (elements.devicesCountPill) {
        elements.devicesCountPill.textContent = `${count} ${count === 1 ? "Device" : "Devices"}`;
      }
      if (elements.navClientsBadge) elements.navClientsBadge.textContent = count;
      if (elements.dashWifiClients) {
        elements.dashWifiClients.textContent = `${count} ${count === 1 ? "device" : "devices"}`;
      }

      renderDevicesTable(devices);
    } catch (err) {
      console.error("Failed to fetch /api/clients:", err);
      setOnlineState(false);
    }
  }

  function renderDevicesTable(devices) {
    if (!elements.devicesTableBody) return;

    if (!devices || devices.length === 0) {
      elements.devicesTableBody.innerHTML = `
        <tr>
          <td colspan="5" class="table-loading">
            No devices currently connected to the Wi-Fi gateway.
          </td>
        </tr>
      `;
      return;
    }

    elements.devicesTableBody.innerHTML = devices
      .map((dev) => {
        const signalPct = dev.signal_pct || 70;
        const barsActive = signalPct > 75 ? 4 : (signalPct > 50 ? 3 : (signalPct > 25 ? 2 : 1));

        return `
          <tr>
            <td>
              <div class="service-name-cell">${escapeHtml(dev.device)}</div>
            </td>
            <td>
              <span class="font-mono">${escapeHtml(dev.ip)}</span>
            </td>
            <td>
              <div class="device-signal-cell">
                <div class="signal-bars">
                  <span class="signal-bar bar-1 ${barsActive >= 1 ? "active" : ""}"></span>
                  <span class="signal-bar bar-2 ${barsActive >= 2 ? "active" : ""}"></span>
                  <span class="signal-bar bar-3 ${barsActive >= 3 ? "active" : ""}"></span>
                  <span class="signal-bar bar-4 ${barsActive >= 4 ? "active" : ""}"></span>
                </div>
                <span class="font-mono text-secondary">${escapeHtml(dev.signal)}</span>
              </div>
            </td>
            <td>
              <span class="font-mono font-bold">${escapeHtml(dev.traffic)}</span>
            </td>
            <td class="text-right">
              <span class="font-mono text-muted" style="font-size:11px;">${escapeHtml(dev.mac)}</span>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  // --------------------------------------------------------------------------
  // Network Page (WAN, LAN, Policy Routing, nftables - Phase 4)
  // --------------------------------------------------------------------------

  async function fetchNetworkData() {
    try {
      const res = await fetch("/api/network");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);
      state.lastNetworkData = data;

      // WAN (Internet)
      if (data.wan) {
        if (elements.netWanIface) elements.netWanIface.textContent = data.wan.interface || "--";
        if (elements.netWanIp) elements.netWanIp.textContent = data.wan.ip || "--";
        if (elements.netWanSubnet) elements.netWanSubnet.textContent = data.wan.subnet || "--";
        if (elements.netWanGw) elements.netWanGw.textContent = data.wan.gateway || "--";
        if (elements.netWanDns) {
          elements.netWanDns.textContent = Array.isArray(data.wan.dns) ? data.wan.dns.join(", ") : (data.wan.dns || "--");
        }
        if (elements.netWanBadge) {
          const isUp = data.wan.is_connected !== false;
          elements.netWanBadge.className = `status-badge ${isUp ? "badge-success" : "badge-danger"}`;
          elements.netWanBadge.textContent = isUp ? "● Connected" : "○ Disconnected";
        }
      }

      // LAN (Wi-Fi Local Network)
      if (data.lan) {
        if (elements.netLanIface) elements.netLanIface.textContent = data.lan.interface || "--";
        if (elements.netLanGw) elements.netLanGw.textContent = data.lan.ip || "--";
        if (elements.netLanNet) elements.netLanNet.textContent = data.lan.subnet || "--";
        if (elements.netLanDhcp) elements.netLanDhcp.textContent = data.lan.dhcp_range || "--";
        if (elements.netLanLease) elements.netLanLease.textContent = data.lan.lease_time || "24h";
        if (elements.netLanBadge) {
          elements.netLanBadge.textContent = `● ${data.lan.ip || "10.42.0.1"}`;
        }
      }

      // Table 100 Policy Routes
      renderRoutesTable(data.routes_table_100);

      // Firewall (nftables)
      if (data.firewall) {
        if (elements.netNftBadge) {
          const isLoaded = data.firewall.ruleset_loaded;
          elements.netNftBadge.className = `status-badge ${isLoaded ? "badge-success" : "badge-neutral"}`;
          elements.netNftBadge.textContent = isLoaded ? "● Active" : "○ Inactive";
        }
        if (elements.netNftNat) {
          elements.netNftNat.textContent = data.firewall.masquerade_interfaces?.join(", ") || "xray0, enp3s0";
        }
        if (elements.netNftForward) {
          const lan = data.lan?.interface || "wlp4s0";
          const wan = data.wan?.interface || "enp3s0";
          elements.netNftForward.textContent = `${lan} → xray0, ${lan} → ${wan}`;
        }
        if (elements.netNftPorts) {
          if (Array.isArray(data.firewall.allowed_ports)) {
            elements.netNftPorts.textContent = data.firewall.allowed_ports.map((p) => `${p.protocol.toUpperCase()} ${p.port}`).join(", ");
          }
        }
        if (elements.netNftRulesCount) {
          elements.netNftRulesCount.textContent = `${data.firewall.rules_count || 0} active rules`;
        }
      }
    } catch (err) {
      console.error("Failed to fetch /api/network:", err);
      setOnlineState(false);
    }
  }

  function renderRoutesTable(routes) {
    if (!elements.routesTableBody) return;

    if (!routes || routes.length === 0) {
      elements.routesTableBody.innerHTML = `
        <tr>
          <td colspan="4" class="table-loading">
            No policy routes currently found in Table 100. Click 'Sync Routes' to initialize.
          </td>
        </tr>
      `;
      return;
    }

    elements.routesTableBody.innerHTML = routes
      .map((r) => {
        const isDefault = r.destination === "default";
        const isVless = r.is_vless_server || false;
        const destClass = isDefault ? "font-bold text-accent" : (isVless ? "font-bold text-success" : "");
        const devBadge = r.dev === "xray0" ? "badge-active" : "badge-neutral";

        return `
          <tr>
            <td>
              <span class="font-mono ${destClass}">${escapeHtml(r.destination)}</span>
              ${isVless ? `<span class="pill badge-success" style="font-size:10px; margin-left:6px;">VLESS Direct</span>` : ""}
            </td>
            <td>
              <span class="status-badge ${devBadge} font-mono">${escapeHtml(r.dev)}</span>
            </td>
            <td>
              <span class="font-mono text-secondary">${escapeHtml(r.gateway || "direct")}</span>
            </td>
            <td class="text-right">
              <span class="font-mono text-muted" style="font-size:11px;">${escapeHtml(r.scope || "global")}</span>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function initNetworkActions() {
    if (elements.btnSyncRoutes) {
      elements.btnSyncRoutes.addEventListener("click", async () => {
        elements.btnSyncRoutes.disabled = true;
        elements.btnSyncRoutes.innerHTML = `<span style="display:inline-block;animation:spin 0.8s linear infinite;">⏳</span> Syncing...`;
        showToast("Synchronizing Table 100 routes...", "info", 2000);

        try {
          const res = await fetch("/api/network/routes/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || data.error || "Failed to sync routes");
          showToast("Table 100 routes synchronized successfully", "success", 3000);
          await fetchNetworkData();
        } catch (err) {
          console.error("Error syncing routes:", err);
          showToast(`Sync failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnSyncRoutes.disabled = false;
          elements.btnSyncRoutes.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Sync Routes
          `;
        }
      });
    }

    if (elements.btnReloadNft) {
      elements.btnReloadNft.addEventListener("click", async () => {
        elements.btnReloadNft.disabled = true;
        elements.btnReloadNft.textContent = "Reloading...";
        showToast("Reloading nftables ruleset...", "info", 2000);

        try {
          const res = await fetch("/api/network/firewall/apply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || data.error || "Failed to reload firewall");
          showToast("Firewall ruleset applied successfully", "success", 3000);
          await fetchNetworkData();
        } catch (err) {
          console.error("Error reloading firewall:", err);
          showToast(`Firewall reload failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnReloadNft.disabled = false;
          elements.btnReloadNft.textContent = "Reload Firewall Ruleset";
        }
      });
    }
  }

  // --------------------------------------------------------------------------
  // Diagnostics & Automatic Repair (Phase 5)
  // --------------------------------------------------------------------------

  async function fetchDiagnosticsData() {
    try {
      const res = await fetch("/api/diagnostics");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);
      state.lastDiagnosticsData = data;

      // Master Badge & Scan Time
      const overall = data.overall_status || "all_systems_operational";
      const isHealthy = overall === "all_systems_operational";
      const isDegraded = overall === "degraded";

      if (elements.diagMasterBadge) {
        if (isHealthy) {
          elements.diagMasterBadge.className = "status-badge badge-success";
          elements.diagMasterBadge.textContent = "● All Systems Operational";
        } else if (isDegraded) {
          elements.diagMasterBadge.className = "status-badge badge-warning";
          elements.diagMasterBadge.textContent = "⚠️ Minor Warnings Detected";
        } else {
          elements.diagMasterBadge.className = "status-badge badge-danger";
          elements.diagMasterBadge.textContent = "✕ Subsystem Issues Detected";
        }
      }

      if (elements.diagLastScan) {
        const d = new Date();
        elements.diagLastScan.textContent = `Last checked: ${d.toLocaleTimeString()}`;
      }

      // Sidebar warning indicator
      if (elements.navDiagBadge) {
        if (!isHealthy && !isDegraded) {
          elements.navDiagBadge.classList.remove("hidden");
        } else {
          elements.navDiagBadge.classList.add("hidden");
        }
      }

      // Stats
      if (data.summary) {
        if (elements.diagStatPassed) {
          elements.diagStatPassed.textContent = `${data.summary.healthy} / ${data.summary.total}`;
        }
        if (elements.diagStatIssues) {
          const totalIssues = (data.summary.failed || 0) + (data.summary.warnings || 0);
          elements.diagStatIssues.textContent = `${totalIssues}`;
          elements.diagStatIssues.className = totalIssues > 0 ? "diag-stat-val text-danger" : "diag-stat-val text-success";
        }
      }

      // Table 100 check indicator
      if (elements.diagStatRouting) {
        const tableCheck = (data.checks || []).find((c) => c.id === "table_100_default");
        const isTableOk = tableCheck && tableCheck.status === "healthy";
        elements.diagStatRouting.textContent = isTableOk ? "Table 100 OK" : "Routing Issue";
        elements.diagStatRouting.className = isTableOk ? "diag-stat-val font-mono text-success" : "diag-stat-val font-mono text-danger";
      }

      // Render Checklist
      renderDiagTable(data.checks || []);
    } catch (err) {
      console.error("Failed to fetch /api/diagnostics:", err);
      setOnlineState(false);
    }
  }

  function renderDiagTable(checks) {
    if (!elements.diagTableBody) return;

    if (!checks || checks.length === 0) {
      elements.diagTableBody.innerHTML = `
        <tr>
          <td colspan="4" class="table-loading">No diagnostic checks performed.</td>
        </tr>
      `;
      return;
    }

    elements.diagTableBody.innerHTML = checks
      .map((c) => {
        const isHealthy = c.status === "healthy";
        const isWarn = c.status === "warning";
        const badgeClass = isHealthy ? "diag-badge-healthy" : (isWarn ? "diag-badge-warning" : "diag-badge-failed");
        const statusLabel = isHealthy ? "✓ Pass" : (isWarn ? "⚠️ Warn" : "✕ Fail");

        return `
          <tr data-check-id="${escapeHtml(c.id)}">
            <td style="width: 110px;">
              <span class="status-badge ${badgeClass} font-bold">${statusLabel}</span>
            </td>
            <td>
              <div class="service-name-cell">${escapeHtml(c.name)}</div>
              <div class="service-unit">${escapeHtml(c.description)}</div>
            </td>
            <td>
              <span class="font-mono text-secondary" style="font-size:12px;">${escapeHtml(c.detail)}</span>
            </td>
            <td class="text-right">
              ${!isHealthy ? `
                <button type="button" class="btn btn-secondary btn-sm btn-fix-check" data-check="${escapeHtml(c.id)}">
                  Fix
                </button>
              ` : `
                <span class="text-success font-mono" style="font-size:11px;">OK</span>
              `}
            </td>
          </tr>
        `;
      })
      .join("");

    // Bind individual fix buttons if any
    elements.diagTableBody.querySelectorAll(".btn-fix-check").forEach((btn) => {
      btn.addEventListener("click", () => {
        runAutoRepair();
      });
    });
  }

  async function runAutoRepair() {
    if (elements.btnRunRepair) {
      elements.btnRunRepair.disabled = true;
      elements.btnRunRepair.innerHTML = `<span style="display:inline-block;animation:spin 0.8s linear infinite;">⏳</span> Repairing...`;
    }
    showToast("Running self-healing auto-repair pipeline...", "info", 3000);

    try {
      const res = await fetch("/api/repair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || result.error || "Repair execution failed");

      showToast("Auto-repair completed successfully!", "success", 4000);

      // Populate repair actions list
      if (elements.repairResultsBox && elements.repairActionsList) {
        const actions = result.actions_taken || [];
        if (actions.length > 0) {
          elements.repairActionsList.innerHTML = actions
            .map((act) => `
              <li class="repair-action-item">
                <span class="repair-check-icon">✓</span>
                <span>${escapeHtml(act)}</span>
              </li>
            `)
            .join("");
          elements.repairResultsBox.classList.remove("hidden");
        }
      }

      // Re-fetch all data
      await fetchDiagnosticsData();
      await fetchDashboardStatus();
      await fetchNetworkData();
    } catch (err) {
      console.error("Auto-repair error:", err);
      showToast(`Repair error: ${err.message}`, "danger", 5000);
    } finally {
      if (elements.btnRunRepair) {
        elements.btnRunRepair.disabled = false;
        elements.btnRunRepair.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
          </svg>
          Run Auto-Repair
        `;
      }
    }
  }

  function initDiagnosticsActions() {
    if (elements.btnRefreshDiag) {
      elements.btnRefreshDiag.addEventListener("click", () => {
        elements.btnRefreshDiag.classList.add("spinning");
        fetchDiagnosticsData().finally(() => {
          setTimeout(() => elements.btnRefreshDiag.classList.remove("spinning"), 500);
        });
      });
    }

    if (elements.btnRunRepair) {
      elements.btnRunRepair.addEventListener("click", () => {
        runAutoRepair();
      });
    }

    if (elements.btnDismissRepair && elements.repairResultsBox) {
      elements.btnDismissRepair.addEventListener("click", () => {
        elements.repairResultsBox.classList.add("hidden");
      });
    }
  }

  // --------------------------------------------------------------------------
  // Authentication & Configuration Backups (Phase 6)
  // --------------------------------------------------------------------------

  async function checkAuthStatus() {
    try {
      const res = await fetch("/api/auth/status");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.isFirstRun = data.first_run;
      state.isAuthenticated = data.authenticated;

      if (elements.authUserName) {
        elements.authUserName.textContent = data.username || "admin";
      }

      if (elements.authStatusBadge) {
        if (data.authenticated) {
          elements.authStatusBadge.className = "status-badge badge-success";
          elements.authStatusBadge.textContent = "● Authenticated";
        } else {
          elements.authStatusBadge.className = "status-badge badge-warning";
          elements.authStatusBadge.textContent = "○ Session Inactive";
        }
      }

      if (data.first_run) {
        // Open first-run onboarding password dialog
        if (elements.authSetupModal) elements.authSetupModal.classList.remove("hidden");
        if (elements.authLoginModal) elements.authLoginModal.classList.add("hidden");
      } else if (!data.authenticated) {
        // Open login lockscreen
        if (elements.authSetupModal) elements.authSetupModal.classList.add("hidden");
        if (elements.authLoginModal) elements.authLoginModal.classList.remove("hidden");
      } else {
        // Authenticated
        if (elements.authSetupModal) elements.authSetupModal.classList.add("hidden");
        if (elements.authLoginModal) elements.authLoginModal.classList.add("hidden");
      }
    } catch (err) {
      console.error("Failed to check auth status:", err);
    }
  }

  async function fetchBackupsData() {
    try {
      const res = await fetch("/api/backups");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOnlineState(true);
      state.lastBackupsData = data.backups || [];
      renderBackupsTable(state.lastBackupsData);
    } catch (err) {
      console.error("Failed to fetch /api/backups:", err);
    }
  }

  function renderBackupsTable(backups) {
    if (!elements.backupsTableBody) return;

    if (!backups || backups.length === 0) {
      elements.backupsTableBody.innerHTML = `
        <tr>
          <td colspan="4" class="table-loading">
            No configuration snapshots saved yet. Click 'Create Snapshot Now' above to save current state.
          </td>
        </tr>
      `;
      return;
    }

    elements.backupsTableBody.innerHTML = backups
      .map((b) => {
        const isAuto = b.is_auto;
        const autoBadge = isAuto ? `<span class="pill badge-neutral" style="font-size:10px; margin-left:6px;">Auto Safety</span>` : "";

        return `
          <tr data-backup-id="${escapeHtml(b.id)}">
            <td>
              <span class="font-mono font-bold">${escapeHtml(b.created_str || b.id)}</span>
              ${autoBadge}
            </td>
            <td>
              <span class="text-secondary">${escapeHtml(b.description || "Manual snapshot")}</span>
            </td>
            <td>
              <span class="font-mono text-muted">${escapeHtml(b.size_human)}</span>
            </td>
            <td class="text-right">
              <div class="backup-actions-cell">
                <button type="button" class="btn btn-primary btn-sm btn-restore-backup" data-id="${escapeHtml(b.id)}" data-desc="${escapeHtml(b.description)}" data-date="${escapeHtml(b.created_str)}">
                  Restore
                </button>
                <a href="/api/backups/${encodeURIComponent(b.id)}/download" class="btn btn-secondary btn-sm" download="${escapeHtml(b.id)}">
                  Download
                </a>
                <button type="button" class="btn btn-secondary btn-sm btn-delete-backup" data-id="${escapeHtml(b.id)}">
                  ✕
                </button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");

    // Bind Restore buttons
    elements.backupsTableBody.querySelectorAll(".btn-restore-backup").forEach((btn) => {
      btn.addEventListener("click", () => {
        const bid = btn.getAttribute("data-id");
        const bdesc = btn.getAttribute("data-desc");
        const bdate = btn.getAttribute("data-date");
        state.activeRestoreId = bid;

        if (elements.modalRestoreId) elements.modalRestoreId.textContent = bid;
        if (elements.modalRestoreDate) elements.modalRestoreDate.textContent = bdate;
        if (elements.modalRestoreDesc) elements.modalRestoreDesc.textContent = bdesc;

        if (elements.backupRestoreModal) elements.backupRestoreModal.classList.remove("hidden");
      });
    });

    // Bind Delete buttons
    elements.backupsTableBody.querySelectorAll(".btn-delete-backup").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const bid = btn.getAttribute("data-id");
        if (!confirm(`Are you sure you want to permanently delete snapshot ${bid}?`)) return;

        try {
          const res = await fetch(`/api/backups/${encodeURIComponent(bid)}`, { method: "DELETE" });
          const resData = await res.json();
          if (!res.ok) throw new Error(resData.detail || resData.error || "Failed to delete backup");
          showToast(`Snapshot ${bid} deleted`, "info", 3000);
          await fetchBackupsData();
        } catch (err) {
          showToast(`Delete failed: ${err.message}`, "danger", 4000);
        }
      });
    });
  }

  function initAuthAndSettingsActions() {
    // 1. First-Run Setup Form
    if (elements.formInitialSetup) {
      elements.formInitialSetup.addEventListener("submit", async (e) => {
        e.preventDefault();
        const p1 = elements.setupInputPass?.value || "";
        const p2 = elements.setupInputConfirm?.value || "";

        if (p1.length < 6) {
          showToast("Password must be at least 6 characters.", "danger", 3000);
          return;
        }
        if (p1 !== p2) {
          showToast("Passwords do not match.", "danger", 3000);
          return;
        }

        elements.btnSubmitSetup.disabled = true;
        elements.btnSubmitSetup.textContent = "Setting Password...";

        try {
          const res = await fetch("/api/auth/setup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password: p1 }),
          });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || result.error || "Setup failed");

          showToast("Admin password configured successfully! Welcome to VPN Gateway.", "success", 4000);
          if (elements.authSetupModal) elements.authSetupModal.classList.add("hidden");
          state.isAuthenticated = true;
          state.isFirstRun = false;
          await checkAuthStatus();
          await fetchInitialData();
        } catch (err) {
          showToast(`Setup error: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnSubmitSetup.disabled = false;
          elements.btnSubmitSetup.textContent = "Set Password & Enter Gateway";
        }
      });
    }

    // 2. Admin Login Form
    if (elements.formLogin) {
      elements.formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const pwd = elements.loginInputPass?.value || "";
        if (!pwd) return;

        elements.btnSubmitLogin.disabled = true;
        elements.btnSubmitLogin.textContent = "Verifying...";

        try {
          const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password: pwd }),
          });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || result.error || "Invalid password");

          showToast("Welcome back, Administrator.", "success", 3000);
          if (elements.authLoginModal) elements.authLoginModal.classList.add("hidden");
          if (elements.loginInputPass) elements.loginInputPass.value = "";
          state.isAuthenticated = true;
          await checkAuthStatus();
          await fetchInitialData();
        } catch (err) {
          showToast(`Login failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnSubmitLogin.disabled = false;
          elements.btnSubmitLogin.textContent = "Unlock Gateway";
        }
      });
    }

    // 3. Logout Button
    if (elements.btnAuthLogout) {
      elements.btnAuthLogout.addEventListener("click", async () => {
        try {
          await fetch("/api/auth/logout", { method: "POST" });
          showToast("Logged out successfully.", "info", 2000);
          state.isAuthenticated = false;
          await checkAuthStatus();
        } catch (err) {
          console.error("Logout error:", err);
        }
      });
    }

    // 4. Change Password Form
    if (elements.formChangePassword) {
      elements.formChangePassword.addEventListener("submit", async (e) => {
        e.preventDefault();
        const oldP = elements.inputOldPass?.value || "";
        const newP = elements.inputNewPass?.value || "";
        const confP = elements.inputConfirmPass?.value || "";

        if (newP.length < 6) {
          showToast("New password must be at least 6 characters.", "danger", 3000);
          return;
        }
        if (newP !== confP) {
          showToast("New passwords do not match.", "danger", 3000);
          return;
        }

        elements.btnSavePassword.disabled = true;
        elements.btnSavePassword.textContent = "Updating...";

        try {
          const res = await fetch("/api/auth/change-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_password: oldP, new_password: newP }),
          });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || result.error || "Password change failed");

          showToast("Admin password successfully updated.", "success", 4000);
          if (elements.inputOldPass) elements.inputOldPass.value = "";
          if (elements.inputNewPass) elements.inputNewPass.value = "";
          if (elements.inputConfirmPass) elements.inputConfirmPass.value = "";
        } catch (err) {
          showToast(`Update failed: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnSavePassword.disabled = false;
          elements.btnSavePassword.textContent = "Update Password";
        }
      });
    }

    // 5. Create Backup Button
    if (elements.btnCreateBackup) {
      elements.btnCreateBackup.addEventListener("click", async () => {
        const note = elements.inputSnapshotNote?.value || "Manual snapshot";
        elements.btnCreateBackup.disabled = true;
        elements.btnCreateBackup.textContent = "Creating Snapshot...";

        try {
          const res = await fetch("/api/backups", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ description: note }),
          });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || result.error || "Failed to create backup");

          showToast(`Snapshot ${result.backup_id} created successfully!`, "success", 3000);
          if (elements.inputSnapshotNote) elements.inputSnapshotNote.value = "";
          await fetchBackupsData();
        } catch (err) {
          showToast(`Backup error: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnCreateBackup.disabled = false;
          elements.btnCreateBackup.textContent = "Create Snapshot Now";
        }
      });
    }

    // 6. Refresh Backups
    if (elements.btnRefreshBackups) {
      elements.btnRefreshBackups.addEventListener("click", () => {
        elements.btnRefreshBackups.classList.add("spinning");
        fetchBackupsData().finally(() => {
          setTimeout(() => elements.btnRefreshBackups.classList.remove("spinning"), 500);
        });
      });
    }

    // 7. Modal Restore Confirm / Cancel
    if (elements.btnModalRestoreCancel && elements.backupRestoreModal) {
      elements.btnModalRestoreCancel.addEventListener("click", () => {
        elements.backupRestoreModal.classList.add("hidden");
        state.activeRestoreId = null;
      });
    }

    if (elements.btnModalRestoreConfirm) {
      elements.btnModalRestoreConfirm.addEventListener("click", async () => {
        if (!state.activeRestoreId) return;

        elements.btnModalRestoreConfirm.disabled = true;
        elements.btnModalRestoreConfirm.textContent = "Restoring...";

        try {
          const res = await fetch(`/api/backups/${encodeURIComponent(state.activeRestoreId)}/restore`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || result.error || "Restore failed");

          showToast(result.message || "Configuration successfully restored!", "success", 4000);
          if (elements.backupRestoreModal) elements.backupRestoreModal.classList.add("hidden");
          state.activeRestoreId = null;

          await fetchInitialData();
        } catch (err) {
          showToast(`Restore error: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnModalRestoreConfirm.disabled = false;
          elements.btnModalRestoreConfirm.textContent = "Restore & Reload";
        }
      });
    }

    // 8. Factory Reset
    if (elements.btnTriggerFactoryReset && elements.factoryResetModal) {
      elements.btnTriggerFactoryReset.addEventListener("click", () => {
        elements.factoryResetModal.classList.remove("hidden");
      });
    }

    if (elements.btnModalResetCancel && elements.factoryResetModal) {
      elements.btnModalResetCancel.addEventListener("click", () => {
        elements.factoryResetModal.classList.add("hidden");
      });
    }

    if (elements.btnModalResetConfirm) {
      elements.btnModalResetConfirm.addEventListener("click", async () => {
        elements.btnModalResetConfirm.disabled = true;
        elements.btnModalResetConfirm.textContent = "Resetting...";

        try {
          const res = await fetch("/api/backups/factory-reset", { method: "POST" });
          const result = await res.json();
          if (!res.ok) throw new Error(result.detail || result.error || "Factory reset failed");

          showToast("Factory reset complete. Configurations reverted to defaults.", "info", 5000);
          if (elements.factoryResetModal) elements.factoryResetModal.classList.add("hidden");
          await fetchInitialData();
        } catch (err) {
          showToast(`Reset error: ${err.message}`, "danger", 4000);
        } finally {
          elements.btnModalResetConfirm.disabled = false;
          elements.btnModalResetConfirm.textContent = "Yes, Reset Gateway";
        }
      });
    }

    // 9. Gateway Reboot
    if (elements.btnTriggerReboot && elements.rebootModal) {
      elements.btnTriggerReboot.addEventListener("click", async () => {
        if (!confirm("Reboot Linux VPN Gateway now? Network and Wi-Fi will temporarily drop.")) return;

        elements.rebootModal.classList.remove("hidden");
        let progress = 0;
        const interval = setInterval(() => {
          progress = Math.min(100, progress + 4);
          if (elements.rebootProgressBar) elements.rebootProgressBar.style.width = `${progress}%`;
          if (progress >= 100) {
            clearInterval(interval);
            setTimeout(() => window.location.reload(), 1500);
          }
        }, 1000);

        try {
          await fetch("/api/system/reboot", { method: "POST" });
        } catch (err) {
          console.warn("Reboot initiated (connection may drop):", err);
        }
      });
    }
  }

  // --------------------------------------------------------------------------
  // Logs Viewer (Phase 7)
  // --------------------------------------------------------------------------

  let cachedLogLines = [];

  async function fetchLogsData() {
    const service = elements.logsSelectService?.value || "gateway";
    const lines = elements.logsSelectLines?.value || "100";

    if (elements.terminalServiceTitle) {
      const titleMap = {
        gateway: "vpn-gateway.service",
        xray: "xray.service",
        hostapd: "hostapd.service",
        dnsmasq: "dnsmasq.service",
        nftables: "nftables.service",
        system: "journalctl (system)",
      };
      elements.terminalServiceTitle.textContent = titleMap[service] || `${service}.service`;
    }

    try {
      const res = await fetch(`/api/logs/${encodeURIComponent(service)}?lines=${encodeURIComponent(lines)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      cachedLogLines = data.logs || [];
      renderLogsOutput();
    } catch (err) {
      console.error("Failed to fetch logs:", err);
      if (elements.logsPreOutput) {
        elements.logsPreOutput.textContent = `Error fetching journal logs: ${err.message}`;
      }
    }
  }

  function renderLogsOutput() {
    if (!elements.logsPreOutput) return;

    const filterText = (elements.logsFilterInput?.value || "").toLowerCase().trim();
    let displayLines = cachedLogLines;

    if (filterText) {
      displayLines = cachedLogLines.filter((l) => l.toLowerCase().includes(filterText));
    }

    if (displayLines.length === 0) {
      elements.logsPreOutput.textContent = filterText
        ? `No log lines match filter '${filterText}'.`
        : "No log lines available.";
      return;
    }

    elements.logsPreOutput.textContent = displayLines.join("\n");

    // Auto-scroll to bottom if autotail enabled
    if (elements.logsToggleAutotail && elements.logsToggleAutotail.checked) {
      elements.logsPreOutput.scrollTop = elements.logsPreOutput.scrollHeight;
    }
  }

  function initLogsActions() {
    if (elements.logsSelectService) {
      elements.logsSelectService.addEventListener("change", () => fetchLogsData());
    }

    if (elements.logsSelectLines) {
      elements.logsSelectLines.addEventListener("change", () => fetchLogsData());
    }

    if (elements.logsFilterInput) {
      elements.logsFilterInput.addEventListener("input", () => renderLogsOutput());
    }

    if (elements.btnRefreshLogs) {
      elements.btnRefreshLogs.addEventListener("click", () => {
        elements.btnRefreshLogs.classList.add("spinning");
        fetchLogsData().finally(() => {
          setTimeout(() => elements.btnRefreshLogs.classList.remove("spinning"), 500);
        });
      });
    }

    if (elements.btnClearLogs) {
      elements.btnClearLogs.addEventListener("click", () => {
        cachedLogLines = [];
        if (elements.logsPreOutput) elements.logsPreOutput.textContent = "--- View cleared ---";
      });
    }

    // Auto-tail poller
    setInterval(() => {
      if (state.activePage === "logs" && elements.logsToggleAutotail && elements.logsToggleAutotail.checked) {
        fetchLogsData();
      }
    }, 3500);
  }

  // --------------------------------------------------------------------------
  // System Services Table & Restart Actions
  // --------------------------------------------------------------------------

  function renderServicesTable(services) {
    if (!elements.servicesTableBody) return;

    if (!services || services.length === 0) {
      elements.servicesTableBody.innerHTML = `<tr><td colspan="5" class="table-loading">No managed services found.</td></tr>`;
      return;
    }

    elements.servicesTableBody.innerHTML = services
      .map((svc) => {
        const isActive = svc.status === "active";
        const isFailed = svc.status === "failed" || svc.status === "error";
        const badgeClass = isActive ? "badge-success" : (isFailed ? "badge-danger" : "badge-neutral");
        const statusLabel = isActive ? "● Active" : (isFailed ? "✕ Failed" : "○ Inactive");

        return `
          <tr data-service="${svc.name}">
            <td>
              <div class="service-name-cell">${escapeHtml(svc.title)}</div>
              <div class="service-unit">${escapeHtml(svc.name)}.service</div>
            </td>
            <td>
              <span class="text-secondary">${escapeHtml(svc.description)}</span>
            </td>
            <td>
              <span class="status-badge ${badgeClass}" id="svc-status-${svc.name}">${statusLabel}</span>
            </td>
            <td>
              <span class="font-mono text-muted" id="svc-sub-${svc.name}">${escapeHtml(svc.substate)}</span>
            </td>
            <td class="text-right">
              <button class="btn btn-secondary btn-sm btn-restart-svc" data-service="${svc.name}">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
                </svg>
                Restart
              </button>
            </td>
          </tr>
        `;
      })
      .join("");

    // Bind restart button clicks
    elements.servicesTableBody.querySelectorAll(".btn-restart-svc").forEach((btn) => {
      btn.addEventListener("click", () => {
        const serviceName = btn.getAttribute("data-service");
        restartService(serviceName, btn);
      });
    });
  }

  function updateServiceStatusesInTable(statusMap) {
    for (const [svcName, status] of Object.entries(statusMap)) {
      const badge = document.getElementById(`svc-status-${svcName}`);
      if (badge) {
        const isActive = status === "active";
        const isFailed = status === "failed" || status === "error";
        badge.className = `status-badge ${isActive ? "badge-success" : (isFailed ? "badge-danger" : "badge-neutral")}`;
        badge.textContent = isActive ? "● Active" : (isFailed ? "✕ Failed" : "○ Inactive");
      }
    }
  }

  async function restartService(serviceName, buttonEl) {
    if (!serviceName) return;

    if (buttonEl) {
      buttonEl.disabled = true;
      buttonEl.innerHTML = `<span style="display:inline-block;animation:spin 0.8s linear infinite;">⏳</span> Restarting...`;
    }

    showToast(`Restarting ${serviceName}.service...`, "info", 2000);

    try {
      const res = await fetch(`/api/system/services/${encodeURIComponent(serviceName)}/restart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const result = await res.json();
      if (!res.ok) {
        throw new Error(result.detail || result.error || "Failed to restart service");
      }

      showToast(`Successfully restarted ${serviceName}.service`, "success", 3000);
      
      // Refresh system state
      await fetchSystemData();
      await fetchDashboardStatus();
    } catch (err) {
      console.error(`Error restarting ${serviceName}:`, err);
      showToast(`Restart failed: ${err.message}`, "danger", 4000);
    } finally {
      if (buttonEl) {
        buttonEl.disabled = false;
        buttonEl.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
          </svg>
          Restart
        `;
      }
    }
  }

  // --------------------------------------------------------------------------
  // Toast Notification System
  // --------------------------------------------------------------------------

  function showToast(message, type = "info", duration = 3000) {
    if (!elements.toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const iconMap = {
      success: "✓",
      danger: "✕",
      info: "ℹ",
    };

    toast.innerHTML = `
      <span style="font-weight:700;">${iconMap[type] || "•"}</span>
      <span>${escapeHtml(message)}</span>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(8px)";
      toast.style.transition = "all 0.25s ease";
      setTimeout(() => toast.remove(), 250);
    }, duration);
  }

  function escapeHtml(str) {
    if (typeof str !== "string") return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // --------------------------------------------------------------------------
  // Application Bootstrap
  // --------------------------------------------------------------------------

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initNavigation();
    initWifiForm();
    initVpnActions();
    initNetworkActions();
    initDiagnosticsActions();
    initAuthAndSettingsActions();
    initLogsActions();
    fetchInitialData();
    initRealtimeStream();
  });

})();
