<div align="center">

```
  ██████╗  █████╗ ████████╗███████╗
 ██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝
 ██║  ███╗███████║   ██║   █████╗  
 ██║   ██║██╔══██║   ██║   ██╔══╝  
 ╚██████╔╝██║  ██║   ██║   ███████╗
  ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
   L I N U X   V P N   G A T E W A Y
```

### ⚡ Transform any x86/ARM mini-PC into a high-performance Wi-Fi Router & VLESS/REALITY Gateway
### ⚡ Превратите любой x86/ARM мини-ПК или тонкий клиент в Wi-Fi роутер и VLESS/REALITY шлюз

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Debian%20%7C%20Ubuntu-E95420.svg?style=for-the-badge&logo=debian)](https://www.debian.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=for-the-badge&logo=python)](https://python.org)
[![Xray-Core](https://img.shields.io/badge/Core-Xray--Core-2B579A.svg?style=for-the-badge)](https://github.com/XTLS/Xray-core)
[![Zero Dependencies](https://img.shields.io/badge/Frontend-0%20External%20Deps-success.svg?style=for-the-badge)](web/)

---

[📖 English](#-english-version) &nbsp;•&nbsp; [🇷🇺 Русский](#-русская-версия)

---

</div>

<br>

<a name="-english-version"></a>
# 🇺🇸 English Version

**GATE** is an all-in-one, turnkey Linux VPN Gateway and Wi-Fi router controller designed for x86 mini-PCs, thin clients (e.g. *ICL ThinRAY*, *Dell Wyse*, *HP Thin Client*, *Intel NUC*), and standard headless servers running **Debian 12+** or **Ubuntu 22.04+**.

It routes all local Wi-Fi clients (`10.42.0.0/24`) through an encrypted **VLESS / REALITY** proxy tunnel (`xray0`) with automated anti-loop routing, transparent policy routing (`table 100`), DNS sinkhole / forwarding, DHCP server, and an ultra-lightweight web control panel.

---

### ✨ Key Features

* 🚀 **1-Command Zero-Touch Setup**: Install minimal runtime, deploy the web panel, and onboard through an intuitive 5-step wizard.
* 📶 **Wi-Fi Access Point (hostapd)**: Auto-detects wireless hardware (e.g. Atheros `ath9k` AR9285), unblocks RF (`rfkill`), configures WPA2-PSK, channels (1–13), and regulatory domains.
* 🛡️ **Modern Firewall & NAT (nftables)**: Dynamic ruleset with `oifname` & `iifname` masquerading, client isolation, and zero packet leaks.
* 🔄 **Transparent Policy Routing (Table 100)**:
  * Traffic from LAN (`10.42.0.0/24`) routed directly through `xray0` TUN interface.
  * Direct route to VPN server via Ethernet WAN gateway to **prevent routing loops**.
  * Local LAN & WAN subnets accessible without VPN latency.
* 🌐 **VLESS / REALITY & Subscription Support**:
  * Parse and import standard `vless://` links directly.
  * Support for Base64 subscription URLs with automated 24-hour auto-updates.
* 🩺 **One-Click Diagnostics & Auto-Repair**: End-to-end status inspector with self-healing buttons for WAN, Wi-Fi, TUN, routes, hostapd, and nftables.
* 🎨 **Paper Design System UI**:
  * 100% vanilla HTML5, CSS3, and ES6+ JavaScript.
  * **0 external CDN dependencies** — loads instantaneously, even when offline.
  * Adaptive Dark / Light theme with smooth transitions.
  * Live SSE throughput meter, connected client viewer, and real-time logs.
* 💾 **Instant Backup & Rollback**: Create and restore `.tar.gz` configuration snapshots with manifests.

---

### 🏛️ Architecture Overview

```
                      ┌─────────────────────────────────────┐
                      │    Client Devices (Phones/Laptops)  │
                      └──────────────────┬──────────────────┘
                                         │ Wi-Fi 802.11 b/g/n (WPA2)
                                         ▼
                             ┌───────────────────────┐
                             │  wlp4s0 (10.42.0.1)   │  ◄── dnsmasq (DHCP/DNS)
                             └───────────┬───────────┘
                                         │
                                         ▼
                      ┌─────────────────────────────────────┐
                      │      nftables (NAT Masquerade)      │
                      └──────────────────┬──────────────────┘
                                         │
                                         ▼
                      ┌─────────────────────────────────────┐
                      │   Kernel Policy Routing Table 100   │
                      │  from 10.42.0.0/24 lookup 100       │
                      └──────────┬────────────────────┬─────┘
                                 │                    │
                  VPN Server IP  │                    │ All other traffic
               Anti-Loop Bypass  │                    │ (Default route)
                                 ▼                    ▼
                      ┌─────────────────────┐  ┌─────────────────────┐
                      │  enp3s0 (WAN Gate)  │  │   xray0 (TUN Dev)   │
                      └──────────┬──────────┘  └──────────┬──────────┘
                                 │ Direct                 │ VLESS REALITY
                                 ▼                        ▼
                      ┌─────────────────────────────────────┐
                      │           Public Internet           │
                      └─────────────────────────────────────┘
```

---

### ⚡ Quick Start

#### 1. One-Line Installation (Remote)
Run this single command as `root` on your server:

```bash
curl -fsSL https://raw.githubusercontent.com/starsden/gate/main/install.sh | sudo bash
```

#### 2. Open the Web Controller
Point your browser to your gateway's IP address:
```
http://<your-server-ip>   (e.g., http://192.168.0.23 or http://10.42.0.1)
```

The **Setup Wizard** will guide you through:
1. Verifying & installing missing system packages (`hostapd`, `dnsmasq`, `nftables`, `xray`, `rfkill`).
2. Setting your Wi-Fi network name (SSID), password, and channel.
3. Pasting your `vless://` key or subscription URL.
4. Creating your administrator account.
5. Automated system finalization with progress tracking.

---

### 🔧 CLI Management & Maintenance

The installer provides built-in lifecycle commands:

| Command | Action | Description |
| :--- | :--- | :--- |
| `sudo bash update.sh` | **Update** | Pulls latest code, recompiles dependencies, reloads network configs |
| `sudo bash install.sh --repair` | **Repair** | Fixes routing tables, unblocks Wi-Fi radio, and restores daemons |
| `sudo bash install.sh --reset-password` | **Reset Admin** | Clears admin password, triggering setup on next web visit |
| `sudo bash install.sh --factory-reset` | **Factory Reset** | Resets all Wi-Fi, VPN, and credentials to clean state |
| `sudo bash install.sh --uninstall` | **Uninstall** | Stops units and removes app files while preserving `/etc/vpn-gateway` |

---

### 💻 System Requirements

* **Architecture**: x86_64 or aarch64
* **Operating System**: Debian 12 (Bookworm) *(recommended)* or Ubuntu 22.04+ LTS
* **RAM**: 512 MB minimum (1 GB recommended)
* **Storage**: 2 GB free disk space
* **Network Hardware**:
  * 1 × Ethernet Network Interface (WAN, e.g. `enp3s0`, `eth0`)
  * 1 × Wi-Fi Adapter with AP mode support (e.g. Qualcomm Atheros `ath9k` AR9285, Intel, Realtek)

---

<br>
<hr>
<br>

<a name="-русская-версия"></a>
# 🇷🇺 Русская Версия

**GATE** — это готовое open-source решение для превращения любого x86/ARM мини-ПК, старого ноутбука или тонкого клиента (например, *ICL ThinRAY*, *Dell Wyse*, *HP Thin Client*, *Intel NUC*) в полноценный Wi-Fi роутер и шлюз с прозрачным проксированием всего трафика через **VLESS / REALITY**.

Все подключённые к Wi-Fi клиенты (`10.42.0.0/24`) автоматически выходят в интернет через зашифрованный туннель без необходимости устанавливать VPN-клиенты на телефоны, телевизоры или компьютеры.

---

### 🚀 Главные возможности

* 📦 **Установка за 1 команду**: Скрипт поднимает веб-интерфейс, после чего вся настройка проходит через удобный пошаговый мастер из 5 страниц.
* 📡 **Точка доступа Wi-Fi (hostapd)**: Автоматическое определение чипсета (Atheros `ath9k` AR9285 и др.), снятие аппаратных и программных блокировок (`rfkill`), режим 802.11n, WPA2-PSK и выбор регуляторного домена.
* 🔥 **Безопасный фаервол (nftables)**: Быстрый маскарадинг NAT через модули ядра `nft_masq`, изоляция клиентов и динамические селекторы `oifname`.
* 🛤️ **Маршрутизация политик ядра (Таблица 100)**:
  * Трафик Wi-Fi клиентов направляется в виртуальный TUN-интерфейс `xray0`.
  * **Защита от петель (Anti-Loop)**: прямой маршрут к IP-адресу VPN-сервера через физический Ethernet шлюз.
  * Локальные подсети доступны напрямую без потерь скорости.
* 🔑 **Поддержка VLESS / REALITY и подписок**:
  * Вставка готовых ссылок `vless://...`.
  * Импорт Base64-подписок с возможностью выбора сервера и автообновлением каждые 24 часа.
* 🩺 **Автоматическая диагностика и починка (Auto-Repair)**: Проверка WAN, Wi-Fi адаптера, TUN-устройства, DNS, nftables, hostapd и кнопка «Fix» для исправления сбоев в один клик.
* 🎨 **Интерфейс Paper Design System**:
  * Чистый HTML5 / CSS3 / JavaScript без сторонних библиотек и CDN.
  * **100% автономность**: панель мгновенно открывается даже при отсутствии интернета.
  * Переключение Тёмной и Светлой темы.
  * Графики трафика в реальном времени (SSE), список клиентов и просмотр системных логов.
* 💾 **Резервные копии**: Создание `.tar.gz` архивов конфигураций и восстановление в один клик.

---

### ⚡ Быстрый старт

#### 1. Установка одной командой
Запустите команду в терминале сервера от имени `root`:

```bash
curl -fsSL https://raw.githubusercontent.com/starsden/gate/main/install.sh | sudo bash
```

#### 2. Запуск мастера настройки
Откройте браузер на любом устройстве в той же локальной сети:
```
http://<IP-вашего-сервера>   (например: http://192.168.0.23 или http://10.42.0.1)
```

**Мастер первичной настройки (5 шагов):**
1. **Проверка пакетов**: установка `hostapd`, `dnsmasq`, `nftables`, `xray`, `rfkill` в фоне.
2. **Настройка Wi-Fi**: имя сети (SSID), пароль WPA2, номер канала.
3. **Настройка VPN**: ссылка `vless://` или URL подписки (можно пропустить).
4. **Аккаунт**: логин и пароль администратора для входа в панель.
5. **Финализация**: автоматическое применение настроек с статус-баром и переход в дашборд.

---

### 🛠️ Управление и обслуживание через консоль

| Команда | Действие | Описание |
| :--- | :--- | :--- |
| `sudo bash update.sh` | **Обновление** | Скачивает свежий код из репозитория и перезапускает сервисы |
| `sudo bash install.sh --repair` | **Починка** | Восстанавливает маршруты, разблокирует радиомодули и перезапускает демоны |
| `sudo bash install.sh --reset-password` | **Сброс пароля** | Сбрасывает пароль администратора и перезапускает мастер настройки |
| `sudo bash install.sh --factory-reset` | **Сброс настроек** | Полный сброс Wi-Fi, VPN и конфигураций к заводским |
| `sudo bash install.sh --uninstall` | **Удаление** | Отключает службы и удаляет приложение (конфиги сохраняются) |

---

### 📋 Системные требования

* **Платформа**: x86_64 или aarch64 (ARM)
* **Операционная система**: Debian 12 Bookworm *(рекомендуется)* или Ubuntu 22.04+ LTS
* **ОЗУ**: от 512 МБ (рекомендуется 1 ГБ)
* **Диск**: от 2 ГБ свободного места
* **Сетевые интерфейсы**:
  * 1 × Ethernet порт (WAN для подключения к домашнему провайдеру/роутеру)
  * 1 × Беспроводной Wi-Fi адаптер с поддержкой режима точки доступа (AP mode), например Atheros AR9285 (`ath9k`), Intel, Realtek и др.

---

### 🛡️ Безопасность

* Веб-контроллер защищён хешированием паролей **PBKDF2-HMAC-SHA256** с солью и безопасными криптографическими сессионными токенами.
* Системная служба `vpn-gateway.service` изолирована правами `ProtectHome=true` и `PrivateTmp=true`.
* Автоматическая защита от разрыва соединений при редактировании конфигов: валидация синтаксиса перед применением и автоматический откат (rollback) в случае ошибок.

---

### 📄 Лицензия

Распространяется под свободной лицензией **MIT License**. См. подробности в файле [LICENSE](LICENSE).

<div align="center">
  <sub>Создано с ❤️ для свободного и быстрого интернета.</sub>
</div>
