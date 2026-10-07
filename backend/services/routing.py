"""
Geozones and routing service for Linux VPN Gateway.
Manages Xray geosite/geoip routing policies, presets, domain strategies,
and catalog of selectable geozones (Direct / Proxy / Block).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

ROUTING_CONFIG_PATH = Path("/etc/vpn-gateway/routing.json")
LOCAL_ROUTING_CONFIG = Path(__file__).resolve().parent.parent.parent / "configs" / "routing.json"

# Standard upstream XTLS/v2fly geosite tags present in vanilla geosite.dat
STANDARD_SAFE_GEOSITES = {
    "openai",
    "anthropic",
    "google",
    "youtube",
    "netflix",
    "twitch",
    "spotify",
    "discord",
    "telegram",
    "github",
    "docker",
    "notion",
    "medium",
    "instagram",
    "facebook",
    "twitter",
    "microsoft",
    "apple",
    "category-ads-all",
    "category-porn",
}

_cached_geosite_tags: Optional[set] = None
_cached_geosite_mtime: float = 0.0

GEOSITE_LOCATIONS = [
    Path(os.environ.get("XRAY_LOCATION_ASSET", "")) / "geosite.dat" if os.environ.get("XRAY_LOCATION_ASSET") else None,
    Path("/usr/local/share/xray/geosite.dat"),
    Path("/usr/share/xray/geosite.dat"),
    Path("/etc/xray/geosite.dat"),
    Path("/usr/local/bin/geosite.dat"),
    Path("/usr/bin/geosite.dat"),
]


def get_installed_geosite_tags() -> set:
    """
    Inspect local geosite.dat binary if present on disk, extracting all available
    category tags. Caches results based on file modification timestamp.
    """
    global _cached_geosite_tags, _cached_geosite_mtime
    for p in GEOSITE_LOCATIONS:
        if p and p.is_file():
            try:
                mtime = p.stat().st_mtime
                if _cached_geosite_tags is not None and _cached_geosite_mtime == mtime:
                    return _cached_geosite_tags

                tags = set()
                data = p.read_bytes()
                data_len = len(data)
                idx = 0
                # Protobuf GeoSiteList parser: each entry starts with field 1 (tag string):
                # 0x0a + varint length + ASCII name + 0x12 (field 2, items)
                while idx < data_len - 4:
                    pos = data.find(b"\x0a", idx)
                    if pos == -1 or pos >= data_len - 3:
                        break
                    str_len = data[pos + 1]
                    if 1 <= str_len <= 50 and pos + 2 + str_len < data_len:
                        tag_bytes = data[pos + 2 : pos + 2 + str_len]
                        if all(32 < b < 127 for b in tag_bytes):
                            next_byte = data[pos + 2 + str_len]
                            if next_byte == 0x12:
                                tags.add(tag_bytes.decode("ascii", errors="ignore").lower())
                                idx = pos + 2 + str_len
                                continue
                    idx = pos + 1

                _cached_geosite_tags = tags
                _cached_geosite_mtime = mtime
                return tags
            except Exception:
                pass
    return set()


def filter_safe_geosites(geosites: List[str]) -> List[str]:
    """
    Filter geosite tags so only tags verified in local geosite.dat (or in standard safe list)
    are output to Xray. Prevents 'code not found in geosite.dat: <TAG>' crashes.
    """
    if not geosites:
        return []

    installed_tags = get_installed_geosite_tags()
    safe_result: List[str] = []

    for g in geosites:
        if not g.startswith("geosite:"):
            continue
        tag = g.split(":", 1)[1].strip().lower()
        if installed_tags:
            if tag in installed_tags:
                safe_result.append(f"geosite:{tag}")
        else:
            if tag in STANDARD_SAFE_GEOSITES:
                safe_result.append(f"geosite:{tag}")

    return safe_result


# ------------------------------------------------------------------------------
# Geozone Categories Catalog
# ------------------------------------------------------------------------------

CATEGORIES_CATALOG: List[Dict[str, Any]] = [
    # Domestic (RU & CIS)
    {
        "id": "ru_services",
        "title": "Российские сервисы (.RU)",
        "subtitle": "Яндекс, VK, Mail.ru, Ozon, Wildberries, Авито",
        "group": "domestic",
        "icon": "🇷🇺",
        "tags": ["domain:ru", "domain:рф", "domain:su", "yandex", "vk"],
        "domains": [
            "domain:ru",
            "domain:рф",
            "domain:su",
            "domain:yandex",
            "domain:ya.ru",
            "domain:vk.com",
            "domain:vk.ru",
            "domain:vk-cdn.net",
            "domain:mail.ru",
            "domain:mirtesen.ru",
            "domain:dzen.ru",
            "domain:ok.ru",
            "domain:rutube.ru",
            "domain:ozon.ru",
            "domain:wildberries.ru",
            "domain:avito.ru",
            "domain:kinopoisk.ru",
            "domain:hh.ru",
            "domain:2gis.ru",
            "domain:auto.ru",
            "domain:cian.ru",
            "domain:aliexpress.ru",
            "domain:habr.com",
            "domain:pikabu.ru",
            "domain:rbc.ru",
            "domain:kommersant.ru",
            "domain:ria.ru",
            "domain:tass.ru",
            "domain:lenta.ru",
            "domain:rambler.ru",
        ],
        "geosites": ["geosite:ru", "geosite:yandex", "geosite:mailru", "geosite:vk"],
        "geoips": [],
        "description": "Сайты национальной доменной зоны .RU, .РФ, .SU и крупнейшие российские экосистемы напрямую.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "gov_ru",
        "title": "Госуслуги и Госсектор РФ",
        "subtitle": "Госуслуги, ФНС, Mos.ru, суды и ведомства",
        "group": "domestic",
        "icon": "🏛️",
        "tags": ["domain:gov.ru", "domain:gosuslugi.ru", "domain:mos.ru"],
        "domains": [
            "domain:gov.ru",
            "domain:gosuslugi.ru",
            "domain:gosuslugi.com",
            "domain:nalog.ru",
            "domain:nalog.gov.ru",
            "domain:mos.ru",
            "domain:spb.ru",
            "domain:kremlin.ru",
            "domain:duma.gov.ru",
            "domain:council.gov.ru",
            "domain:sudrf.ru",
            "domain:cbr.ru",
            "domain:sfr.gov.ru",
            "domain:pfr.gov.ru",
            "domain:fss.ru",
            "domain:zakupki.gov.ru",
            "domain:rosreestr.gov.ru",
            "domain:gibdd.ru",
            "domain:fsb.ru",
            "domain:customs.gov.ru",
            "domain:mvd.gov.ru",
            "domain:mil.ru",
            "domain:eais.rkn.gov.ru",
        ],
        "geosites": ["geosite:category-gov-ru"],
        "geoips": [],
        "description": "Порталы государственных услуг, налоговая служба, судебные и муниципальные ресурсы напрямую.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "banks_ru",
        "title": "Банки и Финансы РФ",
        "subtitle": "Сбер, Т-Банк, ВТБ, Альфа, НСПК Мир",
        "group": "domestic",
        "icon": "💳",
        "tags": ["domain:sberbank.ru", "domain:tinkoff.ru", "domain:vtb.ru"],
        "domains": [
            "domain:sberbank.ru",
            "domain:sberbank.com",
            "domain:sber.ru",
            "domain:tinkoff.ru",
            "domain:tbank.ru",
            "domain:vtb.ru",
            "domain:vtb24.ru",
            "domain:alfabank.ru",
            "domain:alfa-bank.ru",
            "domain:gazprombank.ru",
            "domain:raiffeisen.ru",
            "domain:open.ru",
            "domain:sovcombank.ru",
            "domain:psbank.ru",
            "domain:rosbank.ru",
            "domain:rshb.ru",
            "domain:pochtabank.ru",
            "domain:mkb.ru",
            "domain:nspk.ru",
            "domain:mir-pay.ru",
            "domain:sbp.nspk.ru",
        ],
        "geosites": ["geosite:category-bank-ru", "geosite:sberbank", "geosite:tinkoff"],
        "geoips": [],
        "description": "Российские банковские приложения, интернет-банкинг и платежные шлюзы без разрывов.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "ip_ru",
        "title": "Российские IP-адреса",
        "subtitle": "Все дата-центры, серверы и хостинги в РФ",
        "group": "domestic",
        "icon": "📍",
        "tags": ["geoip:ru"],
        "domains": [],
        "geosites": [],
        "geoips": ["geoip:ru"],
        "description": "Прямое подключение ко всем серверам и адресам, физически расположенным на территории РФ.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "by_kz",
        "title": "Беларусь и Казахстан",
        "subtitle": "Ресурсы стран ЕАЭС (.by, .kz)",
        "group": "domestic",
        "icon": "🇧🇾",
        "tags": ["domain:by", "domain:kz", "geoip:by", "geoip:kz"],
        "domains": [
            "domain:by",
            "domain:бел",
            "domain:kz",
            "domain:қаз",
        ],
        "geosites": ["geosite:by", "geosite:kz"],
        "geoips": ["geoip:by", "geoip:kz"],
        "description": "Сервисы, национальные домены и IP-диапазоны Беларуси и Казахстана.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },

    # Foreign Media & Blocked Resources
    {
        "id": "ai_chat",
        "title": "Искусственный интеллект (AI)",
        "subtitle": "ChatGPT, Claude, Perplexity, Midjourney",
        "group": "blocked_media",
        "icon": "🤖",
        "tags": ["geosite:openai", "geosite:anthropic", "domain:chatgpt.com"],
        "domains": [
            "domain:openai.com",
            "domain:chatgpt.com",
            "domain:anthropic.com",
            "domain:claude.ai",
            "domain:perplexity.ai",
            "domain:midjourney.com",
        ],
        "geosites": ["geosite:openai", "geosite:anthropic"],
        "geoips": [],
        "description": "Нейросети и генеративные платформы (OpenAI, Anthropic Claude, Perplexity).",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "social_media",
        "title": "Социальные сети",
        "subtitle": "Instagram, Facebook, X / Twitter, Threads",
        "group": "blocked_media",
        "icon": "📸",
        "tags": ["geosite:instagram", "geosite:facebook", "geosite:twitter"],
        "domains": [
            "domain:instagram.com",
            "domain:cdninstagram.com",
            "domain:facebook.com",
            "domain:fbcdn.net",
            "domain:twitter.com",
            "domain:x.com",
            "domain:twimg.com",
            "domain:threads.net",
        ],
        "geosites": ["geosite:instagram", "geosite:facebook", "geosite:twitter"],
        "geoips": [],
        "description": "Заблокированные зарубежные социальные платформы и медиа-сервисы.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "video_streaming",
        "title": "Видео и Музыка",
        "subtitle": "YouTube, Netflix, Twitch, Spotify",
        "group": "blocked_media",
        "icon": "📺",
        "tags": ["geosite:youtube", "geosite:netflix", "geosite:twitch", "geosite:spotify"],
        "domains": [
            "domain:youtube.com",
            "domain:googlevideo.com",
            "domain:ytimg.com",
            "domain:netflix.com",
            "domain:twitch.tv",
            "domain:spotify.com",
        ],
        "geosites": ["geosite:youtube", "geosite:netflix", "geosite:twitch", "geosite:spotify"],
        "geoips": [],
        "description": "Видеохостинги и потоковые музыкальные медиа-платформы с высокой скоростью через VPN.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "messengers",
        "title": "Мессенджеры и Связь",
        "subtitle": "Discord, Telegram Voice/CDNs, Signal",
        "group": "blocked_media",
        "icon": "💬",
        "tags": ["geosite:discord", "geosite:telegram"],
        "domains": [
            "domain:discord.com",
            "domain:discord.gg",
            "domain:discordapp.com",
            "domain:discordapp.net",
            "domain:telegram.org",
            "domain:t.me",
            "domain:telegra.ph",
            "domain:signal.org",
        ],
        "geosites": ["geosite:discord", "geosite:telegram"],
        "geoips": [],
        "description": "Голосовые каналы Discord, мультимедийные серверы Telegram и мессенджеры.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "dev_tools",
        "title": "IT и Разработка",
        "subtitle": "GitHub, Docker Hub, Notion, Medium",
        "group": "blocked_media",
        "icon": "💻",
        "tags": ["geosite:github", "geosite:docker", "geosite:notion", "geosite:medium"],
        "domains": [
            "domain:github.com",
            "domain:githubusercontent.com",
            "domain:docker.com",
            "domain:docker.io",
            "domain:notion.so",
            "domain:medium.com",
        ],
        "geosites": ["geosite:github", "geosite:docker", "geosite:notion", "geosite:medium"],
        "geoips": [],
        "description": "Инструменты разработчиков, репозитории пакетов и платформы документации.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "anticensorship",
        "title": "Антицензура и Трекеры",
        "subtitle": "RuTracker, заблокированные СМИ и энциклопедии",
        "group": "blocked_media",
        "icon": "🔓",
        "tags": ["domain:rutracker.org", "domain:meduza.io", "domain:zona.media"],
        "domains": [
            "domain:rutracker.org",
            "domain:rutracker.net",
            "domain:rutracker.cc",
            "domain:nnmclub.to",
            "domain:kinozal.tv",
            "domain:flibusta.is",
            "domain:meduza.io",
            "domain:zona.media",
            "domain:theins.ru",
            "domain:novayagazeta.eu",
            "domain:rferl.org",
            "domain:currenttime.tv",
            "domain:svoboda.org",
            "domain:dw.com",
            "domain:bbc.com",
        ],
        "geosites": ["geosite:category-anticensorship", "geosite:rutracker"],
        "geoips": [],
        "description": "База сайтов из реестра ограничений доступа, независимые СМИ и торрент-каталоги.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "google_meta",
        "title": "Зарубежные экосистемы",
        "subtitle": "Google, Microsoft, Apple, CDN инфраструктура",
        "group": "blocked_media",
        "icon": "🌐",
        "tags": ["geosite:google", "geosite:microsoft", "geosite:apple"],
        "domains": [
            "domain:google.com",
            "domain:googleapis.com",
            "domain:gstatic.com",
            "domain:microsoft.com",
            "domain:live.com",
            "domain:apple.com",
            "domain:icloud.com",
        ],
        "geosites": ["geosite:google", "geosite:microsoft", "geosite:apple"],
        "geoips": [],
        "description": "Глобальные сервисы Google, сервисы учетных записей Apple и Microsoft.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "direct"},
    },

    # Security & Content Filtering
    {
        "id": "adblock",
        "title": "Блокировка рекламы (AdBlock)",
        "subtitle": "Баннеры, аналитика, рекламные трекеры и телеметрия",
        "group": "security",
        "icon": "🚫",
        "tags": ["geosite:category-ads-all", "domain:doubleclick.net"],
        "domains": [
            "domain:adservice.google.com",
            "domain:pagead2.googlesyndication.com",
            "domain:doubleclick.net",
            "domain:an.yandex.ru",
        ],
        "geosites": ["geosite:category-ads-all"],
        "geoips": [],
        "description": "Снижает трафик и убирает навязчивую рекламу на всех подключенных устройствах.",
        "defaults": {"bypass_ru": "block", "all_vpn": "block", "only_blocked": "block"},
    },
    {
        "id": "porn",
        "title": "Родительский контроль (18+)",
        "subtitle": "Блокировка сайтов для взрослых и нежелательного контента",
        "group": "security",
        "icon": "🔞",
        "tags": ["geosite:category-porn"],
        "domains": [],
        "geosites": ["geosite:category-porn"],
        "geoips": [],
        "description": "Фильтрация взрослого контента на уровне шлюза для защиты детских устройств.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
]

# ------------------------------------------------------------------------------
# Presets Definitions
# ------------------------------------------------------------------------------

PRESETS: Dict[str, Dict[str, Any]] = {
    "bypass_ru": {
        "id": "bypass_ru",
        "name": "Обход блокировок (Bypass RU)",
        "badge": "Рекомендуется",
        "icon": "🚀",
        "description": (
            "Российские сервисы, банки, госсайты и IP РФ идут напрямую на максимальной скорости. "
            "Зарубежные и заблокированные сайты направляются через VPN. Встроенный AdBlock активен."
        ),
        "domain_strategy": "IPIfNonMatch",
        "default_outbound": "proxy",
    },
    "all_vpn": {
        "id": "all_vpn",
        "name": "Полный VPN (Global)",
        "badge": "Все через VPN",
        "icon": "🌐",
        "description": (
            "Весь внешний интернет-трафик полностью шифруется и направляется через VPN туннель "
            "(за исключением локальной сети LAN). Максимальная приватность."
        ),
        "domain_strategy": "IPIfNonMatch",
        "default_outbound": "proxy",
    },
    "only_blocked": {
        "id": "only_blocked",
        "name": "Только заблокированные",
        "badge": "Экономия VPN",
        "icon": "🛡️",
        "description": (
            "Обычный интернет идёт напрямую через провайдера без задержек. Через VPN туннель "
            "направляются только выбранные заблокированные ресурсы (Instagram, YouTube, Discord, AI и др.)."
        ),
        "domain_strategy": "IPIfNonMatch",
        "default_outbound": "direct",
    },
    "custom": {
        "id": "custom",
        "name": "Пользовательский",
        "badge": "Ручная настройка",
        "icon": "⚙️",
        "description": "Индивидуальный выбор действия (Direct, Proxy или Block) для каждой категории и геозоны.",
        "domain_strategy": "IPIfNonMatch",
        "default_outbound": "proxy",
    },
}


def get_default_routing_config() -> Dict[str, Any]:
    """Build default config based on recommended 'bypass_ru' preset."""
    cat_actions: Dict[str, str] = {}
    for item in CATEGORIES_CATALOG:
        cat_actions[item["id"]] = item["defaults"].get("bypass_ru", "direct")

    return {
        "mode": "bypass_ru",
        "domain_strategy": "IPIfNonMatch",
        "default_outbound": "proxy",
        "categories": cat_actions,
    }


def get_routing_config_file() -> Path:
    if ROUTING_CONFIG_PATH.parent.exists():
        return ROUTING_CONFIG_PATH
    return LOCAL_ROUTING_CONFIG


def load_routing_config() -> Dict[str, Any]:
    """Read routing config from persistent storage or return default."""
    cfg_file = get_routing_config_file()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "categories" in data:
                    # Merge with default to ensure all new categories exist
                    defaults = get_default_routing_config()
                    merged_categories = dict(defaults["categories"])
                    merged_categories.update(data.get("categories", {}))
                    data["categories"] = merged_categories
                    data.setdefault("mode", "bypass_ru")
                    data.setdefault("domain_strategy", "IPIfNonMatch")
                    data.setdefault("default_outbound", "proxy")
                    return data
        except Exception:
            pass

    return get_default_routing_config()


def save_routing_config(config: Dict[str, Any]) -> None:
    """Save routing config to file."""
    # Write to system path if parent exists
    if ROUTING_CONFIG_PATH.parent.exists():
        try:
            tmp = ROUTING_CONFIG_PATH.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            os.replace(tmp, ROUTING_CONFIG_PATH)
        except Exception:
            pass

    # Always write to local config as well
    try:
        LOCAL_ROUTING_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        tmp_local = LOCAL_ROUTING_CONFIG.with_suffix(".tmp")
        with open(tmp_local, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        os.replace(tmp_local, LOCAL_ROUTING_CONFIG)
    except Exception:
        pass


def apply_routing_preset(preset_id: str) -> Dict[str, Any]:
    """Generate configuration based on a given preset ID."""
    if preset_id not in PRESETS:
        raise ValueError(f"Unknown preset ID: {preset_id}")

    preset = PRESETS[preset_id]
    current = load_routing_config()

    cat_actions: Dict[str, str] = {}
    for item in CATEGORIES_CATALOG:
        cat_actions[item["id"]] = item["defaults"].get(preset_id, current["categories"].get(item["id"], "direct"))

    updated_config = {
        "mode": preset_id,
        "domain_strategy": preset["domain_strategy"],
        "default_outbound": preset["default_outbound"],
        "categories": cat_actions,
    }
    save_routing_config(updated_config)
    return updated_config


def build_xray_routing_rules(routing_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Construct complete Xray Core routing object with domainStrategy and rule chains.
    Rules follow evaluation order:
      1. LAN Direct (geoip:private)
      2. Block rules (ads, adult content, etc.)
      3. Direct rules (geosite:ru, geoip:ru, banks, gov, etc.)
      4. Proxy rules (geosite:openai, geosite:youtube, social, etc.)
      5. Fallback rule based on default_outbound
    """
    if not routing_cfg:
        routing_cfg = load_routing_config()

    domain_strategy = routing_cfg.get("domain_strategy", "IPIfNonMatch")
    default_outbound = routing_cfg.get("default_outbound", "proxy")
    if default_outbound not in ("proxy", "direct"):
        default_outbound = "proxy"

    cat_actions = routing_cfg.get("categories", {})

    # Categorize geosites and geoips
    direct_domains: List[str] = []
    direct_ips: List[str] = []
    proxy_domains: List[str] = []
    proxy_ips: List[str] = []
    block_domains: List[str] = []
    block_ips: List[str] = []

    for item in CATEGORIES_CATALOG:
        cid = item["id"]
        action = cat_actions.get(cid, item["defaults"].get("bypass_ru", "direct"))
        explicit_domains = list(item.get("domains", []))
        safe_geos = filter_safe_geosites(item.get("geosites", []))
        all_domains = explicit_domains + safe_geos
        gips = item.get("geoips", [])

        if action == "direct":
            direct_domains.extend(all_domains)
            direct_ips.extend(gips)
        elif action == "proxy":
            proxy_domains.extend(all_domains)
            proxy_ips.extend(gips)
        elif action == "block":
            block_domains.extend(all_domains)
            block_ips.extend(gips)

    rules: List[Dict[str, Any]] = [
        # 1. LAN / Private IPs are ALWAYS direct (prevents routing loops and keeps local gateway accessible)
        {
            "type": "field",
            "ip": ["geoip:private"],
            "outboundTag": "direct",
        }
    ]

    # 2. Block rules
    if block_domains:
        rules.append({
            "type": "field",
            "domain": list(dict.fromkeys(block_domains)),
            "outboundTag": "block",
        })
    if block_ips:
        rules.append({
            "type": "field",
            "ip": list(dict.fromkeys(block_ips)),
            "outboundTag": "block",
        })

    # 3. Direct rules
    if direct_domains:
        rules.append({
            "type": "field",
            "domain": list(dict.fromkeys(direct_domains)),
            "outboundTag": "direct",
        })
    if direct_ips:
        rules.append({
            "type": "field",
            "ip": list(dict.fromkeys(direct_ips)),
            "outboundTag": "direct",
        })

    # 4. Proxy rules
    if proxy_domains:
        rules.append({
            "type": "field",
            "domain": list(dict.fromkeys(proxy_domains)),
            "outboundTag": "proxy",
        })
    if proxy_ips:
        rules.append({
            "type": "field",
            "ip": list(dict.fromkeys(proxy_ips)),
            "outboundTag": "proxy",
        })

    # 5. Default fallback
    rules.append({
        "type": "field",
        "network": "tcp,udp",
        "outboundTag": default_outbound,
    })

    return {
        "domainStrategy": domain_strategy,
        "rules": rules,
    }


def get_routing_status() -> Dict[str, Any]:
    """Return complete status for UI rendering."""
    config = load_routing_config()
    cat_actions = config.get("categories", {})

    # Enrich catalog with active action
    enriched_catalog = []
    for item in CATEGORIES_CATALOG:
        cid = item["id"]
        action = cat_actions.get(cid, item["defaults"].get("bypass_ru", "direct"))
        enriched_catalog.append({
            **item,
            "current_action": action,
        })

    return {
        "success": True,
        "mode": config.get("mode", "bypass_ru"),
        "domain_strategy": config.get("domain_strategy", "IPIfNonMatch"),
        "default_outbound": config.get("default_outbound", "proxy"),
        "presets": list(PRESETS.values()),
        "categories": enriched_catalog,
        "summary": {
            "direct_count": sum(1 for c in enriched_catalog if c["current_action"] == "direct"),
            "proxy_count": sum(1 for c in enriched_catalog if c["current_action"] == "proxy"),
            "block_count": sum(1 for c in enriched_catalog if c["current_action"] == "block"),
            "total_count": len(enriched_catalog),
        },
    }
