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
LIVE_SAVES_DIR = DATA_DIR / "live_saves"
WEB_DIR = ROOT_DIR / "web"

SETTINGS_PATH = DATA_DIR / "settings.json"
PROGRESS_PATH = DATA_DIR / "progress.json"
USER_MARKERS_PATH = DATA_DIR / "user_markers.json"
META_PATH = CACHE_DIR / "meta.json"
MAP_DATA_PATH = CACHE_DIR / "map_data.json"
CATALOG_PATH = CACHE_DIR / "catalog.json"
CARTEL_PATH = CACHE_DIR / "cartel.json"
FORGE_IDS_PATH = CACHE_DIR / "forge_ids.json"

CACHE_VERSION = 4
DEFAULT_PORT = 8766

# Enum interno verificado em GRW.exe (0x3ab39c0 / 0x3b16480) para LAUNCHER_GAME_LANGUAGE
GRW_LAUNCHER_LANG_MAP: dict[int, str] = {
    1: "en-US",
    2: "fr-FR",
    3: "it-IT",
    4: "de-DE",
    5: "ru-RU",
    6: "es-ES",
    7: "es-LA",
    8: "pt-BR",
    9: "ja-JP",
    10: "ar-SA",
    11: "nl-NL",
    12: "cs-CZ",
    13: "pl-PL",
    14: "zh-TW",
    15: "zh-CN",
    16: "ko-KR",
}

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
    "showTrail": False,
    "showProvinces": True,
    "showCustom": True,
    "zoom": 0.28,
    "camU": 0.5,
    "camV": 0.5,
    "sidebarCollapsed": False,
    "nearbyOpen": True,
    "nearbyManuallyClosed": False,
    "nearbyFilter": "all",
    "nearbyCats": [
        "weapon_case",
        "attachment_case",
        "bonus_medal",
        "skill_point",
        "kingslayer",
        "rebel_op",
        "mission",
    ],
    "enabledCats": None,
    # Tactical stealth, acoustics & witness overlays (all individually toggleable)
    "showEnemies": True,
    "showEnemyDirection": True,
    "showEnemyVisionCones": True,
    "showEnemyHearingRings": False,
    "showWeaponNoiseRing": True,
    "weaponNoiseRingMode": "always",  # always | aiming
    "visionFactions": ["santa_blanca", "unidad"],
    "soundFactions": ["santa_blanca", "unidad"],
    "showFactionSantaBlanca": True,
    "showFactionUnidad": True,
    "showFactionRebel": True,
    "showFactionCivilian": True,
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
    "selectedProvince": None,
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "game_dir": str(DEFAULT_GAME_DIR),
    "lang": "auto",
    "port": DEFAULT_PORT,
    "world_bounds": {
        # Exact AnvilNext 2.0 Bolivia world bounds in meters (16384m x 16384m = 2.0 px/m on 32K gr.wmap)
        "min_x": -8192.0,
        "max_x": 8192.0,
        "min_y": -8192.0,
        "max_y": 8192.0,
        "invert_y": True,
        "calibrated": True,
    },
    "ui_prefs": dict(DEFAULT_UI_PREFS),
}


def ensure_dirs() -> None:
    """Garante existência das pastas de cache e persistência."""
    for d in (CACHE_DIR, TILES_CACHE_DIR, ICONS_CACHE_DIR, MASKS_CACHE_DIR, DATA_DIR, LIVE_SAVES_DIR):
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


def _get_my_documents_dir() -> Path | None:
    """Resolve a pasta Documentos do usuário via CSIDL_PERSONAL (suporta redirecionamento OneDrive)."""
    try:
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
            p = Path(buf.value)
            if p.is_dir():
                return p
    except Exception:
        pass
    home_docs = Path.home() / "Documents"
    return home_docs if home_docs.is_dir() else None


def read_grw_launcher_language(docs_dir: Path | None = None) -> str | None:
    """Lê o idioma ativo do jogo em <Documentos>/My Games/Ghost Recon Wildlands/LAUNCHER_GAME_LANGUAGE."""
    base_docs = docs_dir or _get_my_documents_dir()
    if base_docs is None:
        return None
    grw_docs = base_docs / "My Games" / "Ghost Recon Wildlands"
    for fname in ("LAUNCHER_GAME_LANGUAGE", "BOOT"):
        fpath = grw_docs / fname
        try:
            if not fpath.is_file():
                continue
            raw = fpath.read_bytes()
            if not raw:
                continue
            if 1 <= len(raw) <= 4:
                code_int = int.from_bytes(raw[:4], "little", signed=False)
                if len(raw) == 1:
                    code_int = raw[0]
                elif raw[1:] == b"\x00" * (len(raw) - 1):
                    code_int = raw[0]
                if code_int in GRW_LAUNCHER_LANG_MAP:
                    return GRW_LAUNCHER_LANG_MAP[code_int]
            txt = raw.decode("utf-8", errors="ignore").strip("\x00\r\n\t ")
            if txt.isdigit() and int(txt) in GRW_LAUNCHER_LANG_MAP:
                return GRW_LAUNCHER_LANG_MAP[int(txt)]
            norm = normalize_locale(txt)
            if norm:
                return norm
        except OSError:
            continue
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
    """Detecta o idioma do jogo (env -> GRW LAUNCHER_GAME_LANGUAGE -> Steam ACF -> Windows UI -> en-US)."""
    for env_key in ("GRW_LANG", "GHOSTPAD_LANG"):
        val = os.environ.get(env_key)
        norm = normalize_locale(val)
        if norm:
            return norm, f"env:{env_key}"

    grw_lang = read_grw_launcher_language()
    if grw_lang:
        return grw_lang, "grw:LAUNCHER_GAME_LANGUAGE"

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
        "prefs_migrated_v3": True,
    }
    for k, v in raw.items():
        if k == "ui_prefs" and isinstance(v, dict):
            merged["ui_prefs"].update(v)
        elif k == "world_bounds" and isinstance(v, dict):
            merged["world_bounds"].update(v)
        else:
            merged[k] = v

    # Migra world_bounds antigo (-10500..+10500 não calibrado) para o tamanho real [-8192..+8192]
    wb = merged["world_bounds"]
    if not wb.get("calibrated") or abs(float(wb.get("min_x", 0.0)) - (-10500.0)) < 1.0:
        merged["world_bounds"] = dict(DEFAULT_SETTINGS["world_bounds"])

    # Desativa trilha da sessão por padrão ao migrar instalações anteriores à v3
    if not raw.get("prefs_migrated_v3"):
        merged["ui_prefs"]["showTrail"] = False
        merged["prefs_migrated_v3"] = True
    return merged


def load_settings() -> dict[str, Any]:
    ensure_dirs()
    with _SETTINGS_LOCK:
        if SETTINGS_PATH.is_file():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged = _merge_settings_defaults(data)
                    if (
                        not data.get("prefs_migrated_v3")
                        or not (data.get("world_bounds") or {}).get("calibrated")
                    ):
                        tmp = SETTINGS_PATH.with_suffix(".tmp")
                        tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
                        tmp.replace(SETTINGS_PATH)
                    return merged
            except (OSError, json.JSONDecodeError):
                pass
        return _merge_settings_defaults({})


def save_settings(data: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    with _SETTINGS_LOCK:
        merged = _merge_settings_defaults(data)
        merged["prefs_migrated_v3"] = True
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(SETTINGS_PATH)
        return merged


def load_progress() -> dict[str, Any]:
    """Lê lista de itens/POIs/missões marcados manualmente ou sincronizados do jogo."""
    ensure_dirs()
    with _PROGRESS_LOCK:
        if PROGRESS_PATH.is_file():
            try:
                data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    sync_info = data.get("auto_sync_info")
                    return {
                        "collected_items": list(data.get("collected_items") or []),
                        "completed_pois": list(data.get("completed_pois") or []),
                        "discovered_provinces": list(data.get("discovered_provinces") or []),
                        "defeated_bosses": list(data.get("defeated_bosses") or []),
                        "completed_missions": list(data.get("completed_missions") or []),
                        "auto_collected_items": list(data.get("auto_collected_items") or []),
                        "auto_completed_pois": list(data.get("auto_completed_pois") or []),
                        "auto_completed_missions": list(data.get("auto_completed_missions") or []),
                        "auto_defeated_bosses": list(data.get("auto_defeated_bosses") or []),
                        "auto_sync_info": dict(sync_info) if isinstance(sync_info, dict) else {},
                    }
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "collected_items": [],
            "completed_pois": [],
            "discovered_provinces": ["itacua"],
            "defeated_bosses": [],
            "completed_missions": [],
            "auto_collected_items": [],
            "auto_completed_pois": [],
            "auto_completed_missions": [],
            "auto_defeated_bosses": [],
            "auto_sync_info": {},
        }


def save_progress(data: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    with _PROGRESS_LOCK:
        sync_info = data.get("auto_sync_info")
        clean = {
            "collected_items": sorted(set(str(x) for x in (data.get("collected_items") or []))),
            "completed_pois": sorted(set(str(x) for x in (data.get("completed_pois") or []))),
            "discovered_provinces": sorted(set(str(x) for x in (data.get("discovered_provinces") or []))),
            "defeated_bosses": sorted(set(str(x) for x in (data.get("defeated_bosses") or []))),
            "completed_missions": sorted(set(str(x) for x in (data.get("completed_missions") or []))),
            "auto_collected_items": sorted(set(str(x) for x in (data.get("auto_collected_items") or []))),
            "auto_completed_pois": sorted(set(str(x) for x in (data.get("auto_completed_pois") or []))),
            "auto_completed_missions": sorted(set(str(x) for x in (data.get("auto_completed_missions") or []))),
            "auto_defeated_bosses": sorted(set(str(x) for x in (data.get("auto_defeated_bosses") or []))),
            "auto_sync_info": dict(sync_info) if isinstance(sync_info, dict) else {},
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
