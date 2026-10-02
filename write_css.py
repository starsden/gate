css = """
/* Reset & Base */
:root {
  /* Dark Theme (Default) */
  --bg: #0f0f10;
  --bg-subtle: #161618;
  --surface: #1c1c1e;
  --surface-card: #232326;
  --surface-hover: #2c2c30;
  --surface-active: #38383d;
  --border: rgba(255, 255, 255, 0.09);
  --border-strong: rgba(255, 255, 255, 0.18);
  --text-primary: #f2f2f7;
  --text-secondary: #aeaeb2;
  --text-muted: #636366;
  --accent: #8B5CF6;
  --accent-hover: #7C3AED;
  --accent-glow: rgba(139, 92, 246, 0.25);
  --success: #16A34A;
  --success-bg: rgba(22, 163, 74, 0.12);
  --warning: #D97706;
  --warning-bg: rgba(217, 119, 6, 0.12);
  --danger: #DC2626;
  --danger-bg: rgba(220, 38, 38, 0.12);
  --danger-hover: #B91C1C;
  --neutral-badge-bg: rgba(255, 255, 255, 0.07);
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
  --font-sans: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-display: 'Montserrat', 'Roboto', sans-serif;
  --font-mono: 'PT Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  --sidebar-width: 248px;
  --topbar-height: 60px;
  --transition-fast: 0.12s ease;
  --transition-normal: 0.22s cubic-bezier(0.16,1,0.3,1);
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.25);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 28px rgba(0,0,0,0.55);
}

[data-theme="light"] {
  --bg: #F8F8F5;
  --bg-subtle: #f1f1ee;
  --surface: #FFFFFF;
  --surface-card: #FFFFFF;
  --surface-hover: #f9f9f9;
  --surface-active: #f1f1f1;
  --border: rgba(0, 0, 0, 0.09);
  --border-strong: rgba(0, 0, 0, 0.18);
  --text-primary: #111827;
  --text-secondary: #4b5563;
  --text-muted: #9ca3af;
  --accent: #8B5CF6;
  --accent-hover: #7C3AED;
  --accent-glow: rgba(139, 92, 246, 0.25);
  --success: #16A34A;
  --success-bg: rgba(22, 163, 74, 0.12);
  --warning: #D97706;
  --warning-bg: rgba(217, 119, 6, 0.12);
  --danger: #DC2626;
  --danger-bg: rgba(220, 38, 38, 0.12);
  --danger-hover: #B91C1C;
  --neutral-badge-bg: rgba(0, 0, 0, 0.07);
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--bg);
  color: var(--text-primary);
  font-family: var(--font-sans);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5, h6 { font-family: var(--font-display); font-weight: 600; }
a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); }

/* Typography */
.font-mono { font-family: var(--font-mono); }
.font-bold { font-weight: bold; }
.text-right { text-align: right; }
.text-accent { color: var(--accent); }
.text-success { color: var(--success); }
.text-danger { color: var(--danger); }
.text-muted { color: var(--text-muted); }
.text-secondary { color: var(--text-secondary); }
.mb-3 { margin-bottom: 12px; }
.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }

/* Layout */
.app-layout { display: flex; height: 100vh; overflow: hidden; }

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background-color: #111111;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  z-index: 40;
}
[data-theme="light"] .sidebar { background-color: var(--surface); }

.sidebar-brand {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
}
.brand-icon-wrap { margin-right: 12px; }
.brand-text { display: flex; flex-direction: column; }
.brand-name { font-family: var(--font-display); font-weight: 700; font-size: 18px; }
.brand-subtitle { font-size: 12px; color: var(--text-muted); }

.sidebar-nav { flex: 1; overflow-y: auto; padding: 16px 8px; display: flex; flex-direction: column; gap: 4px; }
.nav-item {
  display: flex; align-items: center; padding: 8px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  transition: var(--transition-fast);
}
.nav-item:hover { background-color: var(--surface-hover); color: var(--text-primary); }
.nav-item.active {
  background-color: rgba(139, 92, 246, 0.12);
  color: var(--accent);
}
.nav-icon { width: 20px; height: 20px; margin-right: 12px; }
.nav-badge { margin-left: auto; background-color: var(--accent); color: #fff; padding: 2px 6px; border-radius: var(--radius-full); font-size: 12px; font-weight: 600; }
.nav-divider { height: 1px; background-color: var(--border); margin: 8px 0; }
.sidebar-footer { padding: 16px; border-top: 1px solid var(--border); }

/* Main Content */
.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar {
  height: var(--topbar-height);
  background-color: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
}
.topbar-title-wrap { display: flex; align-items: center; gap: 12px; }
.page-title { font-family: var(--font-display); font-size: 20px; font-weight: 600; margin: 0; }
.topbar-actions { display: flex; align-items: center; gap: 12px; }
.mobile-header { display: none; }
.mobile-brand { font-family: var(--font-display); font-weight: 700; font-size: 18px; }

.page-container { flex: 1; overflow-y: auto; padding: 24px; }
.page-section { display: none; animation: fadeIn var(--transition-normal); }
.page-section.active { display: block; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
.drawer-backdrop { display: none; }

/* Buttons */
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 8px 16px; border-radius: var(--radius-md);
  font-size: 14px; font-weight: 500; cursor: pointer;
  transition: var(--transition-fast);
  border: 1px solid transparent; background: transparent; color: var(--text-primary);
}
.btn-primary { background-color: var(--accent); color: #fff; border: none; }
.btn-primary:hover { background-color: var(--accent-hover); }
.btn-secondary { background-color: var(--surface-hover); border: 1px solid var(--border); }
.btn-secondary:hover { background-color: var(--surface-active); }
.btn-danger { background-color: var(--danger); color: #fff; }
.btn-danger:hover { background-color: var(--danger-hover); }
.btn-sm { padding: 4px 8px; font-size: 12px; }
.btn-icon { width: 32px; height: 32px; padding: 0; border-radius: var(--radius-sm); display: inline-flex; align-items: center; justify-content: center; background: transparent; border: 1px solid var(--border); color: var(--text-secondary); cursor: pointer; }
.btn-icon:hover { background-color: var(--surface-hover); color: var(--text-primary); }
.btn-refresh {}
.btn-theme-toggle {}
.btn-input-action {}

/* Cards */
.card { background-color: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; margin-bottom: 24px; }
.card-header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.card-body { padding: 24px; }
.card-footer { padding: 16px 24px; border-top: 1px solid var(--border); background-color: var(--surface); }
.card-icon-title { display: flex; align-items: center; gap: 8px; }
.card-icon { width: 24px; height: 24px; color: var(--accent); }
.card-title { font-size: 16px; font-weight: 600; margin: 0; }
.card-desc { font-size: 14px; color: var(--text-muted); margin-top: 4px; }
.card-link { color: var(--accent); font-size: 14px; text-decoration: none; }

/* Badges */
.status-badge, .hero-badge, .ping-badge { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }
.badge-success, .diag-badge-healthy { background-color: var(--success-bg); color: var(--success); }
.badge-active, .sub-server-badge-active { background-color: var(--success-bg); color: var(--success); }
.badge-danger, .diag-badge-failed { background-color: var(--danger-bg); color: var(--danger); }
.badge-warning, .diag-badge-warning { background-color: var(--warning-bg); color: var(--warning); }
.badge-neutral { background-color: var(--neutral-badge-bg); color: var(--text-secondary); }
.pill { border-radius: var(--radius-full); }
.pill-status { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }

/* Ping Badges */
.ping-badge.fast { background-color: var(--success-bg); color: var(--success); }
.ping-badge.medium { background-color: var(--warning-bg); color: var(--warning); }
.ping-badge.slow { background-color: var(--danger-bg); color: var(--danger); }
.ping-badge.none { background-color: var(--neutral-badge-bg); color: var(--text-secondary); }

/* Forms */
.form-group { margin-bottom: 16px; }
.form-label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; color: var(--text-secondary); }
.form-control { width: 100%; padding: 8px 12px; background-color: var(--bg-subtle); border: 1px solid var(--border); border-radius: var(--radius-md); color: var(--text-primary); font-family: var(--font-sans); font-size: 14px; transition: border-color var(--transition-fast); }
.form-control:focus { outline: none; border-color: var(--accent); }
.form-hint { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.form-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group-inline { display: flex; align-items: center; justify-content: space-between; }
.input-with-button { display: flex; gap: 8px; }
.input-filter-wrap { position: relative; }

/* Toggles & Switches */
.toggle-group { display: flex; flex-direction: column; gap: 16px; }
.toggle-inline { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); }
.toggle-inline:last-child { border-bottom: none; }
.toggle-info { display: flex; flex-direction: column; }
.toggle-title { font-size: 14px; font-weight: 500; }
.toggle-desc { font-size: 12px; color: var(--text-muted); }
.switch { position: relative; display: inline-block; width: 40px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: var(--surface-active); transition: .4s; border-radius: var(--radius-full); }
.slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; }
input:checked + .slider { background-color: var(--accent); }
input:checked + .slider:before { transform: translateX(16px); }

/* Tables */
.table-responsive { overflow-x: auto; }
.services-table, .devices-table, .subscription-table, .diag-table { width: 100%; border-collapse: collapse; text-align: left; }
.services-table th, .devices-table th, .subscription-table th, .diag-table th { padding: 12px 16px; background-color: var(--surface-active); color: var(--text-secondary); font-size: 12px; font-weight: 500; text-transform: uppercase; border-bottom: 1px solid var(--border); }
.services-table td, .devices-table td, .subscription-table td, .diag-table td { padding: 16px; border-bottom: 1px solid var(--border); font-size: 14px; }
.services-table tr:last-child td, .devices-table tr:last-child td, .subscription-table tr:last-child td, .diag-table tr:last-child td { border-bottom: none; }
.table-loading { text-align: center; padding: 32px !important; color: var(--text-muted); }

/* Dashboard / Paper */
.paper-banner { background-color: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }
.paper-banner-left { display: flex; flex-direction: column; gap: 8px; }
.paper-banner-eyebrow { font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--accent); letter-spacing: 0.5px; }
.paper-banner-title { font-family: var(--font-display); font-size: 24px; margin: 0; }
.paper-banner-meta { font-size: 14px; color: var(--text-secondary); display: flex; gap: 12px; }
.paper-banner-actions { display: flex; gap: 12px; }

.paper-chip, .paper-chip-success, .paper-chip-danger, .paper-chip-warning, .paper-chip-neutral { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; background: var(--surface-active); border: 1px solid var(--border); }
.paper-chip-success { background: var(--success-bg); color: var(--success); border-color: rgba(22,163,74,0.2); }
.paper-chip-danger { background: var(--danger-bg); color: var(--danger); border-color: rgba(220,38,38,0.2); }
.paper-chip-warning { background: var(--warning-bg); color: var(--warning); border-color: rgba(217,119,6,0.2); }
.paper-chip-neutral { background: var(--neutral-badge-bg); color: var(--text-secondary); }

.paper-btn, .paper-btn-primary, .paper-btn-ghost { display: inline-flex; align-items: center; padding: 8px 16px; border-radius: var(--radius-md); font-size: 14px; font-weight: 500; cursor: pointer; border: 1px solid transparent; background: transparent; color: var(--text-primary); transition: var(--transition-fast); }
.paper-btn-primary { background-color: var(--accent); color: #fff; }
.paper-btn-primary:hover { background-color: var(--accent-hover); }
.paper-btn-ghost { border-color: var(--border); }
.paper-btn-ghost:hover { background-color: var(--surface-hover); }

.paper-cards-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; margin-bottom: 24px; }
.paper-card { background-color: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; display: flex; flex-direction: column; }
.paper-card-head { padding: 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
.paper-card-label-group { display: flex; flex-direction: column; }
.paper-card-icon { color: var(--accent); width: 20px; height: 20px; }
.paper-card-title { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
.paper-card-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; flex: 1; }

.paper-kv-row, .paper-kv-last { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
.paper-kv-last { border-bottom: none; }
.paper-kv-key { color: var(--text-muted); }
.paper-kv-val { font-weight: 500; color: var(--text-primary); }

.paper-bw-body { display: flex; justify-content: space-around; align-items: center; padding: 16px 0; }
.paper-bw-block { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.paper-bw-arrow { display: flex; align-items: center; font-size: 24px; font-family: var(--font-mono); }
.paper-bw-down { color: var(--success); }
.paper-bw-up { color: var(--accent); }
.paper-bw-num { font-size: 24px; font-weight: bold; font-family: var(--font-mono); }
.paper-bw-unit { font-size: 12px; color: var(--text-muted); margin-left: 4px; }
.paper-bw-label { font-size: 12px; text-transform: uppercase; color: var(--text-secondary); }
.paper-bw-sep { width: 1px; height: 40px; background-color: var(--border); }

.paper-hw-card {}
.paper-hw-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.paper-meter { display: flex; flex-direction: column; gap: 8px; }
.paper-meter-head { display: flex; justify-content: space-between; align-items: baseline; }
.paper-meter-label { font-size: 14px; font-weight: 500; }
.paper-meter-val { font-size: 16px; font-family: var(--font-mono); font-weight: bold; }
.paper-meter-sub { font-size: 12px; color: var(--text-muted); }
.paper-track { height: 6px; background-color: var(--surface-active); border-radius: 3px; overflow: hidden; }
.paper-fill, .paper-fill-ram, .paper-fill-temp { height: 100%; background-color: var(--accent); border-radius: 3px; transition: width var(--transition-normal); }
.paper-fill-ram { background-color: var(--warning); }
.paper-fill-temp { background-color: var(--danger); }

.paper-uptime-meter { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px 0; }
.paper-uptime-val { font-size: 32px; font-weight: bold; font-family: var(--font-mono); color: var(--accent); }

.paper-text-link { color: var(--accent); text-decoration: none; font-size: 14px; }
.paper-text-link:hover { text-decoration: underline; }
.paper-mono { font-family: var(--font-mono); }
.paper-bold { font-weight: bold; }

/* System */
.system-grid, .detail-grid, .vpn-grid, .wifi-grid, .network-grid, .diag-stats-grid, .settings-grid { display: grid; gap: 24px; }
@media (min-width: 768px) {
  .system-grid, .vpn-grid, .settings-grid { grid-template-columns: 1fr 1fr; }
  .diag-stats-grid { grid-template-columns: repeat(4, 1fr); }
  .detail-grid { grid-template-columns: 1fr 1fr; }
}

.detail-item { padding: 12px 0; border-bottom: 1px solid var(--border); }
.detail-item:last-child { border-bottom: none; }
.detail-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.detail-value { font-size: 14px; font-weight: 500; }
.resource-meters-stack { display: flex; flex-direction: column; gap: 16px; }
.res-item { display: flex; flex-direction: column; gap: 8px; }
.res-header { display: flex; justify-content: space-between; font-size: 14px; }
.res-name { font-weight: 500; }
.res-pct { font-family: var(--font-mono); font-weight: bold; }
.res-sub { font-size: 12px; color: var(--text-muted); }
.progress-bar-wrap { height: 6px; background-color: var(--surface-active); border-radius: 3px; overflow: hidden; }
.progress-bar, .progress-temp { height: 100%; background-color: var(--accent); border-radius: 3px; }
.progress-temp { background-color: var(--danger); }
.services-card { grid-column: 1 / -1; }

/* VPN */
.vpn-status-card {}
.vpn-import-card {}
.vpn-subscription-card { grid-column: 1 / -1; }
.vpn-actions-footer { margin-top: 16px; display: flex; justify-content: flex-end; }
.vless-textarea { font-family: var(--font-mono); font-size: 12px; height: 100px; resize: vertical; }
.vless-summary-box { background: var(--bg-subtle); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px; margin-bottom: 16px; }
.summary-head { margin-bottom: 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
.summary-title { font-size: 14px; font-weight: 600; }
.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.summary-item { display: flex; flex-direction: column; }
.summary-label { font-size: 12px; color: var(--text-muted); }
.summary-value { font-size: 14px; font-family: var(--font-mono); word-break: break-all; }
.import-actions-row { display: flex; gap: 12px; justify-content: flex-end; }
.sub-header-actions { display: flex; gap: 12px; align-items: center; }
.sub-meta-bar { display: flex; justify-content: space-between; background: var(--surface-active); padding: 12px 16px; border-radius: var(--radius-md); margin-bottom: 16px; font-size: 12px; }
.sub-meta-left, .sub-meta-right { display: flex; gap: 16px; }
.sub-meta-label { color: var(--text-muted); margin-right: 4px; }
.sub-meta-url { color: var(--accent); font-family: var(--font-mono); }
.sub-meta-time { font-family: var(--font-mono); }
.sub-server-remark { font-weight: 500; display: flex; align-items: center; gap: 8px; }
.sub-action-buttons { display: flex; gap: 8px; }

/* WiFi */
.settings-form { display: flex; flex-direction: column; gap: 16px; }

/* Devices */
.devices-card-container { margin-bottom: 24px; }
.devices-header-actions { display: flex; gap: 12px; }

/* Diagnostics */
.diag-banner-card { background: var(--surface-card); padding: 24px; border-radius: var(--radius-md); border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.diag-banner-header { display: flex; flex-direction: column; gap: 8px; }
.diag-banner-info { display: flex; flex-direction: column; gap: 4px; }
.diag-badge-row { display: flex; gap: 8px; margin-bottom: 8px; }
.diag-banner-title { font-size: 20px; font-weight: 600; margin: 0; }
.diag-banner-desc { font-size: 14px; color: var(--text-muted); }
.diag-banner-actions { display: flex; gap: 12px; }
.diag-stat-box { background: var(--surface-card); border: 1px solid var(--border); padding: 16px; border-radius: var(--radius-md); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }
.diag-stat-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; }
.diag-stat-val { font-size: 24px; font-weight: bold; font-family: var(--font-mono); color: var(--text-primary); }
.repair-results-card { margin-top: 24px; }
.repair-actions-list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }

/* Logs */
.logs-container-card { display: flex; flex-direction: column; height: 600px; }
.logs-header { display: flex; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--border); background: var(--surface); }
.logs-controls-left, .logs-controls-right { display: flex; gap: 12px; align-items: center; }
.terminal-window { flex: 1; background-color: #000; border-radius: 0 0 var(--radius-md) var(--radius-md); display: flex; flex-direction: column; overflow: hidden; }
.terminal-bar { background-color: #1e1e1e; padding: 8px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; }
.terminal-dots { display: flex; gap: 6px; }
.dot, .dot-red, .dot-yellow, .dot-green { width: 12px; height: 12px; border-radius: 50%; }
.dot-red { background-color: #ff5f56; }
.dot-yellow { background-color: #ffbd2e; }
.dot-green { background-color: #27c93f; }
.terminal-title { font-family: var(--font-mono); font-size: 12px; color: #888; }
.terminal-status { font-family: var(--font-mono); font-size: 12px; color: #888; }
.terminal-body { flex: 1; padding: 16px; overflow-y: auto; font-family: var(--font-mono); font-size: 13px; color: #00ff00; line-height: 1.4; white-space: pre-wrap; word-break: break-all; }

/* Settings */
.auth-badge-row { margin-bottom: 16px; }
.auth-user-info { display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; }
.danger-card { border-color: rgba(220, 38, 38, 0.3); }
.danger-desc { font-size: 14px; color: var(--text-muted); margin-bottom: 16px; }
.danger-actions-row { display: flex; gap: 12px; }

/* Modals */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: none; align-items: center; justify-content: center; z-index: 100; backdrop-filter: blur(4px); }
.modal-backdrop.active { display: flex; }
.modal-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); width: 100%; max-width: 500px; box-shadow: var(--shadow-lg); overflow: hidden; display: flex; flex-direction: column; max-height: 90vh; }
.modal-header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.modal-title-row { display: flex; align-items: center; gap: 12px; }
.modal-title { font-size: 18px; font-weight: 600; margin: 0; }
.modal-body { padding: 24px; overflow-y: auto; }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 12px; background: var(--bg-subtle); }
.modal-warning-text { font-size: 14px; color: var(--danger); margin-bottom: 16px; background: var(--danger-bg); padding: 12px; border-radius: var(--radius-sm); }
.modal-diff-box { background: var(--bg-subtle); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 16px; font-family: var(--font-mono); font-size: 12px; margin-bottom: 16px; }
.modal-icon-badge { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: var(--radius-full); background: var(--accent-glow); color: var(--accent); }
.diff-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
.diff-row:last-child { margin-bottom: 0; }
.diff-label { color: var(--text-muted); }
.diff-val { color: var(--text-primary); }

/* Misc */
.hidden { display: none !important; }
.toast-container { position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; gap: 12px; z-index: 1000; }
.toast { background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px 16px; font-size: 14px; color: var(--text-primary); box-shadow: var(--shadow-md); display: flex; align-items: center; gap: 12px; min-width: 280px; animation: slideIn var(--transition-normal); }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.toast-success { border-left: 4px solid var(--success); }
.toast-error { border-left: 4px solid var(--danger); }
.toast-warning { border-left: 4px solid var(--warning); }
.backend-alert { background: var(--danger-bg); color: var(--danger); padding: 8px 16px; text-align: center; font-size: 14px; font-weight: 500; display: none; }
.beacon-pulse { animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
.connection-status { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
.status-dot, .status-indicator-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); }
.status-indicator-dot.offline { background: var(--danger); }

/* Mobile */
@media (max-width: 768px) {
  .sidebar { position: fixed; left: -100%; top: 0; bottom: 0; transition: left var(--transition-normal); }
  .sidebar.open { left: 0; }
  .mobile-header { display: flex; align-items: center; justify-content: space-between; padding: 16px; background: var(--surface); border-bottom: 1px solid var(--border); }
  .drawer-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 30; }
  .drawer-backdrop.active { display: block; }
  .topbar { display: none; }
}
"""
with open('/Users/den/Developer/gates/web/style.css', 'w') as f:
    f.write(css)
