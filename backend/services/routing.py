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
        "tags": ["geosite:ru", "geosite:yandex", "geosite:mailru", "geosite:vk"],
        "geosites": ["geosite:ru", "geosite:yandex", "geosite:mailru", "geosite:vk"],
        "geoips": [],
        "description": "Сайты национальной доменной зоны .RU, .РФ и крупнейшие российские экосистемы.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "gov_ru",
        "title": "Госуслуги и Госсектор РФ",
        "subtitle": "Госуслуги, ФНС, Mos.ru, суды и ведомства",
        "group": "domestic",
        "icon": "🏛️",
        "tags": ["geosite:category-gov-ru"],
        "geosites": ["geosite:category-gov-ru"],
        "geoips": [],
        "description": "Порталы государственных услуг, налоговая служба, судебные и муниципальные ресурсы.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "banks_ru",
        "title": "Банки и Финансы РФ",
        "subtitle": "Сбер, Т-Банк, ВТБ, Альфа, НСПК Мир",
        "group": "domestic",
        "icon": "💳",
        "tags": ["geosite:category-bank-ru", "geosite:sberbank", "geosite:tinkoff"],
        "geosites": ["geosite:category-bank-ru", "geosite:sberbank", "geosite:tinkoff"],
        "geoips": [],
        "description": "Российские банковские приложения, интернет-банкинг и платежные шлюзы.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "ip_ru",
        "title": "Российские IP-адреса",
        "subtitle": "Все дата-центры, серверы и хостинги в РФ",
        "group": "domestic",
        "icon": "📍",
        "tags": ["geoip:ru"],
        "geosites": [],
        "geoips": ["geoip:ru"],
        "description": "Прямое подключение к любым серверам, физически расположенным на территории РФ.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },
    {
        "id": "by_kz",
        "title": "Беларусь и Казахстан",
        "subtitle": "Ресурсы стран ЕАЭС (.by, .kz)",
        "group": "domestic",
        "icon": "🇧🇾",
        "tags": ["geosite:by", "geosite:kz", "geoip:by", "geoip:kz"],
        "geosites": ["geosite:by", "geosite:kz"],
        "geoips": ["geoip:by", "geoip:kz"],
        "description": "Сервисы и IP-диапазоны Беларуси и Казахстана.",
        "defaults": {"bypass_ru": "direct", "all_vpn": "proxy", "only_blocked": "direct"},
    },

    # Foreign Media & Blocked Resources
    {
        "id": "ai_chat",
        "title": "Искусственный интеллект (AI)",
        "subtitle": "ChatGPT, Claude, Perplexity, Midjourney",
        "group": "blocked_media",
        "icon": "🤖",
        "tags": ["geosite:openai", "geosite:anthropic"],
        "geosites": ["geosite:openai", "geosite:anthropic"],
        "geoips": [],
        "description": "Нейросети и генеративные платформы (OpenAI, Anthropic Claude).",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "social_media",
        "title": "Социальные сети",
        "subtitle": "Instagram, Facebook, X / Twitter, Threads",
        "group": "blocked_media",
        "icon": "📸",
        "tags": ["geosite:instagram", "geosite:facebook", "geosite:twitter"],
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
        "geosites": ["geosite:youtube", "geosite:netflix", "geosite:twitch", "geosite:spotify"],
        "geoips": [],
        "description": "Видеохостинги и потоковые музыкальные медиа-платформы с высокой скоростью.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "messengers",
        "title": "Мессенджеры и Связь",
        "subtitle": "Discord, Telegram Voice/CDNs, Signal",
        "group": "blocked_media",
        "icon": "💬",
        "tags": ["geosite:discord", "geosite:telegram"],
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
        "tags": ["geosite:category-anticensorship", "geosite:rutracker"],
        "geosites": ["geosite:category-anticensorship", "geosite:rutracker"],
        "geoips": [],
        "description": "База сайтов из реестра ограничений доступа и торрент-каталоги.",
        "defaults": {"bypass_ru": "proxy", "all_vpn": "proxy", "only_blocked": "proxy"},
    },
    {
        "id": "google_meta",
        "title": "Зарубежные экосистемы",
        "subtitle": "Google, Microsoft, Apple, CDN инфраструктура",
        "group": "blocked_media",
        "icon": "🌐",
        "tags": ["geosite:google", "geosite:microsoft", "geosite:apple"],
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
        "tags": ["geosite:category-ads-all"],
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
        geos = item.get("geosites", [])
        gips = item.get("geoips", [])

        if action == "direct":
            direct_domains.extend(geos)
            direct_ips.extend(gips)
        elif action == "proxy":
            proxy_domains.extend(geos)
            proxy_ips.extend(gips)
        elif action == "block":
            block_domains.extend(geos)
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
