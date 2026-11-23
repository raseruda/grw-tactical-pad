"""Configuração global e persistência do Ghost Tactical Pad (Ghost Recon Wildlands)."""
from __future__ import annotations

import ctypes
import json
import locale
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any

_SETTINGS_LOCK = threading.RLock()
_PROGRESS_LOCK = threading.RLock()
_MARKERS_LOCK = threading.RLock()

ROOT_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DEFAULT_GAME_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Wildlands")
CACHE_DIR = ROOT_DIR / "cache"
TILES_CACHE_DIR = CACHE_DIR / "tiles"
ICONS_CACHE_DIR = CACHE_DIR / "icons"
MASKS_CACHE_DIR = CACHE_DIR / "masks"
DATA_DIR = ROOT_DIR / "data"
WEB_DIR = ROOT_DIR / "web"

SETTINGS_PATH = DATA_DIR / "settings.json"
PROGRESS_PATH = DATA_DIR / "progress.json"
USER_MARKERS_PATH = DATA_DIR / "user_markers.json"
META_PATH = CACHE_DIR / "meta.json"
MAP_DATA_PATH = CACHE_DIR / "map_data.json"
CATALOG_PATH = CACHE_DIR / "catalog.json"
CARTEL_PATH = CACHE_DIR / "cartel.json"

CACHE_VERSION = 1
DEFAULT_PORT = 8766

SUPPORTED_LANGUAGES: list[dict[str, str]] = [
    {"code": "en-US", "label": "English (US)", "forge": "LocalizationPackage_English(US)"},
    {"code": "pt-BR", "label": "Português (Brasil)", "forge": "LocalizationPackage_Portuguese(Brazil)"},
    {"code": "es-LA", "label": "Español (Latinoamérica)", "forge": "LocalizationPackage_Spanish(South America)"},
    {"code": "es-ES", "label": "Español (España)", "forge": "LocalizationPackage_Spanish(Spain)"},
    {"code": "fr-FR", "label": "Français", "forge": "LocalizationPackage_French(France)"},
    {"code": "de-DE", "label": "Deutsch", "forge": "LocalizationPackage_German"},
    {"code": "it-IT", "label": "Italiano", "forge": "LocalizationPackage_Italian"},
    {"code": "ru-RU", "label": "Русский", "forge": "LocalizationPackage_Russian"},
    {"code": "nl-NL", "label": "Nederlands", "forge": "LocalizationPackage_Dutch"},
    {"code": "pl-PL", "label": "Polski", "forge": "LocalizationPackage_Polish"},
    {"code": "cs-CZ", "label": "Čeština", "forge": "LocalizationPackage_Czech"},
    {"code": "ja-JP", "label": "日本語", "forge": "LocalizationPackage_Japanese"},
    {"code": "ko-KR", "label": "한국어", "forge": "LocalizationPackage_Korean"},
    {"code": "zh-CN", "label": "简体中文", "forge": "LocalizationPackage_Chinese"},
    {"code": "zh-TW", "label": "繁體中文", "forge": "LocalizationPackage_Chinese(Trad)"},
    {"code": "ar-SA", "label": "العربية", "forge": "LocalizationPackage_Arabic"},
]
_LANG_BY_LOWER: dict[str, str] = {x["code"].lower(): x["code"] for x in SUPPORTED_LANGUAGES}

DEFAULT_UI_PREFS: dict[str, Any] = {
    "activeTab": "map",
    "mapMode": "assist",
    "mapStyle": "satellite",
    "assistRadius": 350,
    "fogOfWar": False,
    "hideCompleted": False,
    "followPlayer": True,
    "showTrail": True,
    "showProvinces": True,
    "showCustom": True,
    "zoom": 0.28,
    "camU": 0.5,
    "camV": 0.5,
    "sidebarCollapsed": False,
    "nearbyOpen": True,
    "nearbyManuallyClosed": False,
    "nearbyFilter": "all",
    "enabledCats": None,
    # Tactical stealth, acoustics & witness overlays (all individually toggleable)
    "showEnemies": True,
    "showEnemyDirection": True,
    "showEnemyVisionCones": True,
    "showEnemyHearingRings": False,
    "showWeaponNoiseRing": True,
    "showSafeToFireHud": True,
    "showPlayerAimWarning": True,
    "showAlliesSolo": True,
    "showAlliesCoop": True,
    "showAllyAimWarning": True,
    "showAllySightlines": True,
    "showKillWitnessLines": True,
    "showDrone": True,
    "useTerrainLos": True,
    "alertSound": False,
    # Tactical detection & acoustic tuning
    "enemyVisionRangeM": 55,
    "enemyFovDeg": 110,
    "bulletImpactNoiseM": 12,
    "aimConeDeg": 2.8,
    "allyAimConeDeg": 3.5,
    "weaponOverrideClass": "auto",
    "weaponOverrideSuppressed": "auto",
    "allyAssumedSuppressed": True,
    # Sub-tab filters
    "wikiCat": "all",
    "wikiClassFilter": "all",
    "wikiMissingOnly": False,
    "cartelWingFilter": "all",
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "game_dir": str(DEFAULT_GAME_DIR),
    "lang": "auto",
    "port": DEFAULT_PORT,
    "world_bounds": {
        # Initial calibrated Bolivia bounding box in meters (refined live at runtime)
        "min_x": -10500.0,
        "max_x": 10500.0,
        "min_y": -10500.0,
        "max_y": 10500.0,
        "invert_y": True,
        "calibrated": False,
    },
    "ui_prefs": dict(DEFAULT_UI_PREFS),
}


def ensure_dirs() -> None:
    """Garante existência das pastas de cache e persistência."""
    for d in (CACHE_DIR, TILES_CACHE_DIR, ICONS_CACHE_DIR, MASKS_CACHE_DIR, DATA_DIR):
        d.mkdir(parents=True, exist_ok=True)


def normalize_locale(raw: str | None) -> str | None:
    """Converte código de idioma/locale (BCP-47 ou Windows) para código suportado."""
    if not raw:
        return None
    clean = str(raw).strip().strip('"').strip("'").split(".", 1)[0].split("@", 1)[0].strip()
    if not clean or clean.lower() == "auto":
        return None
    low = clean.lower().replace("_", "-")
    if low in _LANG_BY_LOWER:
        return _LANG_BY_LOWER[low]
    parts = [p for p in low.split("-") if p]
    if not parts:
        return None
    p0 = parts[0]
    sub = parts[1:]
    if p0 in ("pt", "brazilian", "portuguese"):
        return "pt-BR"
    if p0 in ("en", "english"):
        return "en-US"
    if p0 in ("es", "spanish"):
        if "es" in sub:
            return "es-ES"
        return "es-LA"
    if p0 in ("fr", "french"):
        return "fr-FR"
    if p0 in ("de", "german"):
        return "de-DE"
    if p0 in ("it", "italian"):
        return "it-IT"
    if p0 in ("ru", "russian"):
        return "ru-RU"
    if p0 in ("nl", "dutch"):
        return "nl-NL"
    if p0 in ("pl", "polish"):
        return "pl-PL"
    if p0 in ("cs", "czech"):
        return "cs-CZ"
    if p0 in ("ja", "japanese"):
        return "ja-JP"
    if p0 in ("ko", "korean"):
        return "ko-KR"
    if p0 in ("zh", "schinese", "tchinese"):
        if p0 == "tchinese" or any(r in sub for r in ("tw", "hk", "hant")):
            return "zh-TW"
        return "zh-CN"
    if p0 in ("ar", "arabic"):
        return "ar-SA"
    return None


def _read_steam_manifest_lang(game_dir: Path) -> str | None:
    """Tenta ler o idioma configurado no Steam (appmanifest_460930.acf)."""
    try:
        steamapps = game_dir.parent.parent
        acf = steamapps / "appmanifest_460930.acf"
        if acf.is_file():
            txt = acf.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'"language"\s+"([^"]+)"', txt, re.IGNORECASE)
            if m:
                return normalize_locale(m.group(1))
    except OSError:
        pass
    return None


def _read_windows_locale() -> str | None:
    try:
        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        loc = locale.windows_locale.get(lcid)
        if loc:
            return normalize_locale(loc)
    except Exception:
        pass
    return None


def detect_game_language(game_dir: Path | None = None) -> tuple[str, str]:
    """Detecta o idioma do jogo (env -> Steam ACF -> Windows UI -> en-US)."""
    for env_key in ("GRW_LANG", "GHOSTPAD_LANG"):
        val = os.environ.get(env_key)
        norm = normalize_locale(val)
        if norm:
            return norm, f"env:{env_key}"

    if game_dir:
        acf_lang = _read_steam_manifest_lang(game_dir)
        if acf_lang:
            return acf_lang, "steam:appmanifest_460930"

    win_lang = _read_windows_locale()
    if win_lang:
        return win_lang, "windows"

    return "en-US", "default"


def resolve_effective_language(settings: dict[str, Any] | None, game_dir: Path | None) -> tuple[str, str]:
    raw = str((settings or {}).get("lang") or "auto").strip()
    if raw and raw.lower() != "auto":
        norm = normalize_locale(raw)
        if norm:
            return norm, "settings"
    return detect_game_language(game_dir)


def _merge_settings_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "game_dir": str(DEFAULT_GAME_DIR),
        "lang": "auto",
        "port": DEFAULT_PORT,
        "world_bounds": dict(DEFAULT_SETTINGS["world_bounds"]),
        "ui_prefs": dict(DEFAULT_UI_PREFS),
    }
    for k, v in raw.items():
        if k == "ui_prefs" and isinstance(v, dict):
            merged["ui_prefs"].update(v)
        elif k == "world_bounds" and isinstance(v, dict):
            merged["world_bounds"].update(v)
        else:
            merged[k] = v
    return merged


def load_settings() -> dict[str, Any]:
    ensure_dirs()
    with _SETTINGS_LOCK:
        if SETTINGS_PATH.is_file():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return _merge_settings_defaults(data)
            except (OSError, json.JSONDecodeError):
                pass
        return _merge_settings_defaults({})


def save_settings(data: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    with _SETTINGS_LOCK:
        merged = _merge_settings_defaults(data)
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(SETTINGS_PATH)
        return merged


def load_progress() -> dict[str, Any]:
    """Lê lista de itens/POIs/missões marcados pelo jogador como concluídos/coletados."""
    ensure_dirs()
    with _PROGRESS_LOCK:
        if PROGRESS_PATH.is_file():
            try:
                data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {
                        "collected_items": list(data.get("collected_items") or []),
                        "completed_pois": list(data.get("completed_pois") or []),
                        "discovered_provinces": list(data.get("discovered_provinces") or []),
                        "defeated_bosses": list(data.get("defeated_bosses") or []),
                    }
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "collected_items": [],
            "completed_pois": [],
            "discovered_provinces": ["itacua"],
            "defeated_bosses": [],
        }


def save_progress(data: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    with _PROGRESS_LOCK:
        clean = {
            "collected_items": sorted(set(str(x) for x in (data.get("collected_items") or []))),
            "completed_pois": sorted(set(str(x) for x in (data.get("completed_pois") or []))),
            "discovered_provinces": sorted(set(str(x) for x in (data.get("discovered_provinces") or []))),
            "defeated_bosses": sorted(set(str(x) for x in (data.get("defeated_bosses") or []))),
        }
        tmp = PROGRESS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(PROGRESS_PATH)
        return clean


def _is_valid_game_dir(p: Path) -> bool:
    return p.is_dir() and ((p / "GRW.exe").is_file() or (p / "gr.wmap").is_file())


def get_game_dir(cli_game_dir: str | None = None) -> Path:
    """Resolve automaticamente a pasta de instalação de Ghost Recon Wildlands."""
    candidates: list[Path] = []
    if cli_game_dir:
        candidates.append(Path(cli_game_dir))
    env_gd = os.environ.get("GRW_GAME_DIR")
    if env_gd:
        candidates.append(Path(env_gd))
    # Se instalado em <Wildlands>\GhostPad\, o pai é a pasta do jogo
    candidates.append(ROOT_DIR.parent)
    candidates.append(ROOT_DIR)

    settings = load_settings()
    if settings.get("game_dir"):
        candidates.append(Path(settings["game_dir"]))

    candidates.extend([
        DEFAULT_GAME_DIR,
        Path(r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\games\Tom Clancy's Ghost Recon Wildlands"),
        Path(r"C:\Program Files\Ubisoft\Ubisoft Game Launcher\games\Tom Clancy's Ghost Recon Wildlands"),
        Path(r"D:\SteamLibrary\steamapps\common\Wildlands"),
        Path(r"D:\Games\Wildlands"),
    ])

    for c in candidates:
        if _is_valid_game_dir(c):
            return c.resolve()
    return DEFAULT_GAME_DIR


def find_save_files() -> list[Path]:
    """Localiza arquivos *.save do Ghost Recon Wildlands na pasta do Ubisoft Connect."""
    bases = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Ubisoft" / "Ubisoft Game Launcher" / "savegames",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Ubisoft" / "Ubisoft Game Launcher" / "savegames",
    ]
    found: list[Path] = []
    for b in bases:
        if not b.is_dir():
            continue
        for uid_dir in b.iterdir():
            if not uid_dir.is_dir():
                continue
            for app_id in ("3559", "1771"):
                sdir = uid_dir / app_id
                if sdir.is_dir():
                    found.extend(sorted(sdir.glob("*.save"), key=lambda p: p.stat().st_mtime, reverse=True))
    return found
