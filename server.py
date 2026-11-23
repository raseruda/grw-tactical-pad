"""Servidor HTTP local e stream SSE do Ghost Tactical Pad (Ghost Recon Wildlands)."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import mimetypes
import re
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import anvil_formats
import grw_asset_builder
from anvil_formats import HeightmapSampler, WmapReader
from config import (
    CARTEL_PATH,
    CATALOG_PATH,
    DEFAULT_PORT,
    DEFAULT_UI_PREFS,
    MAP_DATA_PATH,
    MASKS_CACHE_DIR,
    ICONS_CACHE_DIR,
    SUPPORTED_LANGUAGES,
    USER_MARKERS_PATH,
    WEB_DIR,
    detect_game_language,
    ensure_dirs,
    get_game_dir,
    load_progress,
    load_settings,
    normalize_locale,
    resolve_effective_language,
    save_progress,
    save_settings,
)
from grw_memory import GRWLiveReader
from grw_save_sync import AutoProgressSync
from tactical_engine import analyze_tactical_state

TILE_URL_RE = re.compile(r"^/api/tile/(satellite|heatmap)/([0-6])/(\d{1,3})/(\d{1,3})\.png$")
ICON_URL_RE = re.compile(r"^/api/icon/([A-Za-z0-9_\-]+)\.png$")
MASK_URL_RE = re.compile(r"^/api/mask/([A-Za-z0-9_\-]+)\.png$")
MARKER_ID_RE = re.compile(r"^/api/markers/([A-Za-z0-9_\-]+)$")

_ALLOWED_FACTIONS = frozenset({"santa_blanca", "unidad", "rebel", "civilian", "ghost"})

_UI_PREF_ENUMS: dict[str, tuple[str, ...]] = {
    "activeTab": ("map", "wiki", "cartel"),
    "mapMode": ("spoiler_free", "assist", "full"),
    "mapStyle": ("satellite", "heatmap"),
    "weaponOverrideClass": ("auto", "pistol", "smg", "ar", "lmg", "shotgun", "sniper"),
    "weaponOverrideSuppressed": ("auto", "suppressed", "unsuppressed"),
    "weaponNoiseRingMode": ("always", "aiming"),
}
_UI_PREF_BOOLS = (
    "fogOfWar",
    "hideCompleted",
    "followPlayer",
    "showTrail",
    "showProvinces",
    "showCustom",
    "sidebarCollapsed",
    "nearbyOpen",
    "nearbyManuallyClosed",
    "showEnemies",
    "showEnemyDirection",
    "showEnemyVisionCones",
    "showEnemyHearingRings",
    "showWeaponNoiseRing",
    "showFactionSantaBlanca",
    "showFactionUnidad",
    "showFactionRebel",
    "showFactionCivilian",
    "showSafeToFireHud",
    "showPlayerAimWarning",
    "showAlliesSolo",
    "showAlliesCoop",
    "showAllyAimWarning",
    "showAllySightlines",
    "showKillWitnessLines",
    "showDrone",
    "useTerrainLos",
    "alertSound",
    "allyAssumedSuppressed",
    "wikiMissingOnly",
)
_UI_PREF_FLOATS: dict[str, tuple[float, float]] = {
    "zoom": (0.015, 16.0),
    "camU": (0.0, 1.0),
    "camV": (0.0, 1.0),
    "assistRadius": (50.0, 2000.0),
    "enemyVisionRangeM": (15.0, 150.0),
    "enemyFovDeg": (40.0, 180.0),
    "bulletImpactNoiseM": (0.0, 35.0),
    "aimConeDeg": (0.8, 12.0),
    "allyAimConeDeg": (0.8, 15.0),
}
_UI_PREF_STRS = ("nearbyFilter", "wikiCat", "wikiClassFilter", "cartelWingFilter")


def _sanitize_ui_prefs(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for k, allowed in _UI_PREF_ENUMS.items():
        v = raw.get(k)
        if isinstance(v, str) and v in allowed:
            out[k] = v
    for k in _UI_PREF_BOOLS:
        v = raw.get(k)
        if isinstance(v, bool):
            out[k] = v
    for k, (lo, hi) in _UI_PREF_FLOATS.items():
        v = raw.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
            val = max(lo, min(hi, float(v)))
            out[k] = int(round(val)) if k in ("assistRadius", "enemyVisionRangeM", "enemyFovDeg", "bulletImpactNoiseM") else round(val, 5)
    for k in _UI_PREF_STRS:
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()[:32]
    if "selectedProvince" in raw:
        sp = raw.get("selectedProvince")
        out["selectedProvince"] = sp.strip()[:48] if isinstance(sp, str) and sp.strip() else None
    cats = raw.get("enabledCats")
    if cats is None and "enabledCats" in raw:
        out["enabledCats"] = None
    elif isinstance(cats, list):
        clean: list[str] = []
        seen: set[str] = set()
        for item in cats:
            if isinstance(item, str):
                s = item.strip()[:48]
                if s and s not in seen:
                    seen.add(s)
                    clean.append(s)
                    if len(clean) >= 64:
                        break
        out["enabledCats"] = clean
    for fkey in ("visionFactions", "soundFactions"):
        fval = raw.get(fkey)
        if isinstance(fval, list):
            clean_f: list[str] = []
            seen_f: set[str] = set()
            for item in fval:
                if isinstance(item, str):
                    s = item.strip()
                    if s in _ALLOWED_FACTIONS and s not in seen_f:
                        seen_f.add(s)
                        clean_f.append(s)
            out[fkey] = clean_f
    return out


def _get_lan_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


class GhostPadRuntime:
    """Gerencia leitores .wmap, cache estático, telemetria 15 Hz, análise furtiva e marcadores."""

    def __init__(
        self,
        game_dir: Path,
        lang: str = "pt-BR",
        lang_setting: str = "auto",
        lang_source: str = "default",
        lan: bool = False,
        port: int = DEFAULT_PORT,
        telemetry_ptr: int | None = None,
        allow_takeover: bool = False,
    ) -> None:
        ensure_dirs()
        self.game_dir = game_dir
        self.lang = lang
        self.lang_setting = lang_setting
        self.lang_source = lang_source
        self.lan = lan
        self.port = port
        self.allow_takeover = allow_takeover
        self.stop_event = threading.Event()

        self._build_lock = threading.Lock()
        self._build_status: dict[str, Any] = {"state": "idle", "progress": 0, "message": "Initializing..."}

        self._static_lock = threading.Lock()
        self._static_bytes: dict[str, bytes] = {}
        self._static_gz: dict[str, bytes] = {}

        settings = load_settings()
        self._ui_prefs: dict[str, Any] = dict(DEFAULT_UI_PREFS)
        self._ui_prefs.update(_sanitize_ui_prefs(settings.get("ui_prefs") or {}))

        self._wmap_sat = WmapReader(game_dir / "gr.wmap")
        self._wmap_heat = WmapReader(game_dir / "gr_h.wmap")
        self._heightmap = HeightmapSampler()
        self._live_reader = GRWLiveReader(telemetry_ptr=telemetry_ptr, world_bounds=settings.get("world_bounds"))
        self._save_sync = AutoProgressSync()

        self._state_lock = threading.Lock()
        self._sse_cond = threading.Condition(self._state_lock)
        self._live_seq = 0
        self._progress_version = 1
        self._latest_live: dict[str, Any] = {
            "mode": "offline",
            "status": "offline",
            "lang": self.lang,
            "progress_version": self._progress_version,
            "player": None,
            "drone": None,
            "allies": [],
            "enemies": [],
            "rebels": [],
            "civilians": [],
            "npcs": [],
            "trail": [],
            "tactical": analyze_tactical_state({}, self._heightmap, self._ui_prefs),
        }

        self._markers_lock = threading.Lock()
        self._markers: list[dict[str, Any]] = self._load_markers()
        self._progress: dict[str, Any] = load_progress()

    def close(self) -> None:
        self.stop_event.set()
        self._wmap_sat.close()
        self._wmap_heat.close()

    def _load_markers(self) -> list[dict[str, Any]]:
        if USER_MARKERS_PATH.is_file():
            try:
                data = json.loads(USER_MARKERS_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return []

    def _save_markers(self) -> None:
        tmp = USER_MARKERS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._markers, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(USER_MARKERS_PATH)

    def get_markers(self) -> list[dict[str, Any]]:
        with self._markers_lock:
            return list(self._markers)

    def add_marker(self, body: dict[str, Any]) -> dict[str, Any]:
        u = max(0.0, min(1.0, float(body.get("u", 0.5))))
        v = max(0.0, min(1.0, float(body.get("v", 0.5))))
        marker = {
            "id": uuid.uuid4().hex[:10],
            "title": str(body.get("title") or "Tactical Pin")[:80],
            "note": str(body.get("note") or "")[:1000],
            "icon": str(body.get("icon") or "crosshair")[:32],
            "color": str(body.get("color") or "#38bdf8")[:16],
            "u": round(u, 5),
            "v": round(v, 5),
            "createdAt": int(time.time()),
        }
        with self._markers_lock:
            self._markers.append(marker)
            self._save_markers()
        return marker

    def update_marker(self, mid: str, body: dict[str, Any]) -> dict[str, Any] | None:
        with self._markers_lock:
            for m in self._markers:
                if m.get("id") == mid:
                    if "title" in body:
                        m["title"] = str(body["title"] or "Tactical Pin")[:80]
                    if "note" in body:
                        m["note"] = str(body["note"] or "")[:1000]
                    if "icon" in body:
                        m["icon"] = str(body["icon"] or "crosshair")[:32]
                    if "color" in body:
                        m["color"] = str(body["color"] or "#38bdf8")[:16]
                    if "u" in body:
                        m["u"] = round(max(0.0, min(1.0, float(body["u"]))), 5)
                    if "v" in body:
                        m["v"] = round(max(0.0, min(1.0, float(body["v"]))), 5)
                    self._save_markers()
                    return dict(m)
        return None

    def delete_marker(self, mid: str) -> bool:
        with self._markers_lock:
            before = len(self._markers)
            self._markers = [m for m in self._markers if m.get("id") != mid]
            if len(self._markers) != before:
                self._save_markers()
                return True
        return False

    def get_progress(self) -> dict[str, Any]:
        with self._state_lock:
            return dict(self._progress)

    def update_progress(self, body: dict[str, Any]) -> dict[str, Any]:
        with self._state_lock:
            cur = dict(self._progress)
            if "toggle_item" in body:
                iid = str(body["toggle_item"])
                items = set(cur.get("collected_items") or [])
                if iid in items:
                    items.remove(iid)
                else:
                    items.add(iid)
                cur["collected_items"] = sorted(items)
            if "toggle_poi" in body:
                pid = str(body["toggle_poi"])
                pois = set(cur.get("completed_pois") or [])
                if pid in pois:
                    pois.remove(pid)
                else:
                    pois.add(pid)
                cur["completed_pois"] = sorted(pois)
            if "toggle_boss" in body:
                bid = str(body["toggle_boss"])
                bosses = set(cur.get("defeated_bosses") or [])
                if bid in bosses:
                    bosses.remove(bid)
                else:
                    bosses.add(bid)
                cur["defeated_bosses"] = sorted(bosses)
            if "toggle_province" in body:
                pr = str(body["toggle_province"])
                provs = set(cur.get("discovered_provinces") or [])
                if pr in provs:
                    provs.remove(pr)
                else:
                    provs.add(pr)
                cur["discovered_provinces"] = sorted(provs)
            if "toggle_mission" in body:
                mid = str(body["toggle_mission"])
                miss = set(cur.get("completed_missions") or [])
                if mid in miss:
                    miss.remove(mid)
                else:
                    miss.add(mid)
                cur["completed_missions"] = sorted(miss)
            for key in ("collected_items", "completed_pois", "discovered_provinces", "defeated_bosses", "completed_missions"):
                if isinstance(body.get(key), list):
                    cur[key] = body[key]
            self._progress = save_progress(cur)
            self._progress_version += 1
            return dict(self._progress)

    def _load_static_caches(self) -> None:
        if not grw_asset_builder.is_cache_valid(self.lang, self.game_dir):
            return
        with self._static_lock:
            for key, path in (("map_data", MAP_DATA_PATH), ("catalog", CATALOG_PATH), ("cartel", CARTEL_PATH)):
                if key not in self._static_bytes and path.is_file():
                    raw = path.read_bytes()
                    self._static_bytes[key] = raw
                    self._static_gz[key] = gzip.compress(raw, compresslevel=5)

    def get_static_payload(self, name: str, accept_gzip: bool) -> tuple[bytes, bool] | None:
        self._load_static_caches()
        with self._static_lock:
            if name not in self._static_bytes:
                return None
            if accept_gzip and name in self._static_gz:
                return self._static_gz[name], True
            return self._static_bytes[name], False

    def _run_builder(self, force: bool = False) -> None:
        def cb(pct: int, msg: str) -> None:
            with self._build_lock:
                self._build_status = {"state": "building" if pct < 100 else "ready", "progress": pct, "message": msg}

        try:
            cb(5, "Starting cache builder...")
            grw_asset_builder.ensure_cache_built(self.game_dir, lang=self.lang, force=force, progress_cb=cb)
            with self._static_lock:
                self._static_bytes.clear()
                self._static_gz.clear()
            self._load_static_caches()
            self._save_sync.reload_index()
            cb(100, "Ready")
        except Exception as exc:
            with self._build_lock:
                self._build_status = {"state": "error", "progress": 0, "message": str(exc)}

    def start_background_tasks(self, force_rebuild: bool = False) -> None:
        if not force_rebuild and grw_asset_builder.is_cache_valid(self.lang, self.game_dir):
            self._load_static_caches()
            self._save_sync.reload_index()
            with self._build_lock:
                self._build_status = {"state": "ready", "progress": 100, "message": "Ready"}
        else:
            threading.Thread(target=self._run_builder, args=(force_rebuild,), daemon=True, name="GRWBuilder").start()
        threading.Thread(target=self._poll_loop, daemon=True, name="GRWPoller").start()

    def trigger_rebuild(self) -> None:
        threading.Thread(target=self._run_builder, args=(True,), daemon=True, name="GRWBuilder").start()

    def get_settings(self) -> dict[str, Any]:
        cfg = load_settings()
        prefs = dict(DEFAULT_UI_PREFS)
        prefs.update(_sanitize_ui_prefs(cfg.get("ui_prefs") or {}))
        return {
            "lang": self.lang,
            "lang_setting": self.lang_setting,
            "lang_source": self.lang_source,
            "world_bounds": cfg.get("world_bounds"),
            "ui_prefs": prefs,
        }

    def update_settings(self, body: dict[str, Any]) -> dict[str, Any]:
        cur = load_settings()
        changed = False
        lang_requested = "lang" in body
        if lang_requested:
            raw_lang = str(body.get("lang") or "auto").strip()
            norm = normalize_locale(raw_lang)
            cur["lang"] = "auto" if (not raw_lang or raw_lang.lower() == "auto" or norm is None) else norm
            changed = True

        if isinstance(body.get("ui_prefs"), dict):
            merged = dict(DEFAULT_UI_PREFS)
            merged.update(_sanitize_ui_prefs(cur.get("ui_prefs") or {}))
            merged.update(_sanitize_ui_prefs(body["ui_prefs"]))
            cur["ui_prefs"] = merged
            with self._state_lock:
                self._ui_prefs.update(merged)
            changed = True

        if isinstance(body.get("world_bounds"), dict):
            wb = body["world_bounds"]
            cur_wb = dict(cur.get("world_bounds") or {})
            for k in ("min_x", "max_x", "min_y", "max_y"):
                if isinstance(wb.get(k), (int, float)):
                    cur_wb[k] = float(wb[k])
            if "invert_y" in wb:
                cur_wb["invert_y"] = bool(wb["invert_y"])
            cur["world_bounds"] = cur_wb
            self._live_reader.set_world_bounds(cur_wb)
            changed = True

        cfg = save_settings(cur) if changed else cur
        rebuilding = False
        if lang_requested:
            eff_lang, src = resolve_effective_language(cfg, self.game_dir)
            self.lang_setting = str(cfg.get("lang") or "auto")
            self.lang_source = src
            if eff_lang != self.lang or not grw_asset_builder.is_cache_valid(eff_lang, self.game_dir):
                self.lang = eff_lang
                self.trigger_rebuild()
                rebuilding = True

        out_prefs = dict(DEFAULT_UI_PREFS)
        out_prefs.update(_sanitize_ui_prefs(cfg.get("ui_prefs") or {}))
        return {
            "ok": True,
            "lang": self.lang,
            "lang_setting": self.lang_setting,
            "lang_source": self.lang_source,
            "rebuilding": rebuilding,
            "ui_prefs": out_prefs,
        }

    def get_tile_png(self, style: str, lod: int, col: int, row: int) -> bytes | None:
        rd = self._wmap_heat if style == "heatmap" else self._wmap_sat
        return rd.get_tile_png(lod, col, row)

    def _poll_loop(self) -> None:
        tick = 0
        while not self.stop_event.is_set():
            frame = self._live_reader.read_live_frame()
            lang_changed = False
            if self.lang_setting == "auto" and tick % 45 == 0:
                eff_lang, src = detect_game_language(self.game_dir)
                if eff_lang != self.lang:
                    self.lang = eff_lang
                    self.lang_source = src
                    lang_changed = True
                    self.trigger_rebuild()

            with self._state_lock:
                prefs = dict(self._ui_prefs)
                cur_prog_snap = dict(self._progress)

            new_prog, prog_changed = self._save_sync.process_live_tick(frame, cur_prog_snap)
            if prog_changed:
                saved = save_progress(new_prog)
                with self._state_lock:
                    self._progress = saved
                    self._progress_version += 1

            tac = analyze_tactical_state(frame, heightmap=self._heightmap, prefs=prefs)
            frame["tactical"] = tac
            with self._sse_cond:
                prev_mode = self._latest_live.get("mode")
                frame["progress_version"] = self._progress_version
                frame["lang"] = self.lang
                self._latest_live = frame
                if (
                    frame.get("mode") == "live"
                    or prev_mode != frame.get("mode")
                    or prog_changed
                    or lang_changed
                    or tick % 10 == 0
                ):
                    self._live_seq += 1
                    self._sse_cond.notify_all()
            tick += 1
            self.stop_event.wait(0.066)  # ~15 Hz

    def get_status(self) -> dict[str, Any]:
        with self._state_lock:
            live = dict(self._latest_live)
        with self._build_lock:
            bstat = dict(self._build_status)
        lan_ip = _get_lan_ip() if self.lan else None
        return {
            "build": bstat,
            "connection_mode": live.get("mode", "offline"),
            "game_status": live.get("status", "offline"),
            "hooks_mask": live.get("hooks_mask", 0),
            "game_dir": str(self.game_dir),
            "lang": self.lang,
            "lang_setting": self.lang_setting,
            "lang_source": self.lang_source,
            "supported_languages": SUPPORTED_LANGUAGES,
            "has_wmap": self._wmap_sat.valid,
            "has_heatmap": self._wmap_heat.valid,
            "lan_url": f"http://{lan_ip}:{self.port}" if lan_ip else None,
        }

    def get_live(self) -> dict[str, Any]:
        with self._state_lock:
            return dict(self._latest_live)


class GhostPadHTTPHandler(BaseHTTPRequestHandler):
    server_version = "GhostTacticalPad/1.0"

    @property
    def runtime(self) -> GhostPadRuntime:
        return self.server.runtime  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_bytes(self, code: int, ctype: str, body: bytes, cache_control: str = "no-store", gzipped: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        if gzipped:
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, data: Any) -> None:
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(code, "application/json; charset=utf-8", raw)

    def _read_json_body(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > 1024 * 1024:
            return None
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/api/status":
            self._send_json(200, self.runtime.get_status())
            return
        if path == "/api/settings":
            self._send_json(200, self.runtime.get_settings())
            return
        if path == "/api/live":
            self._send_json(200, self.runtime.get_live())
            return
        if path == "/api/progress":
            self._send_json(200, self.runtime.get_progress())
            return
        if path == "/api/markers":
            self._send_json(200, {"markers": self.runtime.get_markers()})
            return
        if path == "/api/debug/probe":
            self._send_json(200, self.runtime._live_reader.get_debug_probe())
            return
        if path == "/api/debug/save_probe":
            self._send_json(200, self.runtime._save_sync.get_save_probe())
            return
        if path == "/api/stream":
            self._handle_sse()
            return

        if path in ("/api/static/map_data", "/api/static/catalog", "/api/static/cartel"):
            key = path.rsplit("/", 1)[-1]
            accept_gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
            payload = self.runtime.get_static_payload(key, accept_gz)
            if payload is None:
                self._send_json(503, {"error": "Cache em preparação"})
                return
            body, is_gz = payload
            self._send_bytes(200, "application/json; charset=utf-8", body, cache_control="no-cache", gzipped=is_gz)
            return

        m_tile = TILE_URL_RE.match(path)
        if m_tile:
            style, lod_s, col_s, row_s = m_tile.groups()
            png = self.runtime.get_tile_png(style, int(lod_s), int(col_s), int(row_s))
            if not png:
                self._send_bytes(404, "text/plain", b"Tile not found")
                return
            self._send_bytes(200, "image/png", png, cache_control="public, max-age=86400")
            return

        m_mask = MASK_URL_RE.match(path)
        if m_mask:
            mpath = (MASKS_CACHE_DIR / f"{m_mask.group(1)}.png").resolve()
            if mpath.parent != MASKS_CACHE_DIR.resolve() or not mpath.is_file():
                self._send_bytes(404, "text/plain", b"Mask not found")
                return
            self._send_bytes(200, "image/png", mpath.read_bytes(), cache_control="public, max-age=86400")
            return

        m_icon = ICON_URL_RE.match(path)
        if m_icon:
            ipath = (ICONS_CACHE_DIR / f"{m_icon.group(1)}.png").resolve()
            if ipath.parent != ICONS_CACHE_DIR.resolve() or not ipath.is_file():
                self._send_bytes(404, "text/plain", b"Icon not found")
                return
            self._send_bytes(200, "image/png", ipath.read_bytes(), cache_control="public, max-age=86400")
            return

        rel = "index.html" if path == "/" else path.lstrip("/")
        target = (WEB_DIR / rel).resolve()
        if target.parent != WEB_DIR.resolve() or not target.is_file():
            self._send_bytes(404, "text/plain; charset=utf-8", b"Not found")
            return
        ctype, _ = mimetypes.guess_type(str(target))
        if target.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif target.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif target.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        self._send_bytes(200, ctype or "application/octet-stream", target.read_bytes(), cache_control="no-cache")

    def do_POST(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/api/settings":
            body = self._read_json_body()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            self._send_json(200, self.runtime.update_settings(body))
            return
        if path == "/api/progress":
            body = self._read_json_body()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            self._send_json(200, self.runtime.update_progress(body))
            return
        if path == "/api/markers":
            body = self._read_json_body()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            self._send_json(201, self.runtime.add_marker(body))
            return
        if path == "/api/rebuild":
            self.runtime.trigger_rebuild()
            self._send_json(202, {"status": "rebuilding"})
            return
        if path == "/api/debug/simulate":
            body = self._read_json_body()
            self.runtime._live_reader.set_simulated_frame(body if body and body.get("enabled", True) else None)
            self._send_json(200, {"ok": True})
            return
        if path == "/api/shutdown":
            client_ip = self.client_address[0] if self.client_address else ""
            if not self.runtime.allow_takeover or client_ip not in ("127.0.0.1", "::1"):
                self._send_json(403, {"error": "Shutdown refused"})
                return
            self._send_json(200, {"ok": True, "stopping": True})
            threading.Timer(0.05, self.runtime.stop_event.set).start()
            return
        self._send_json(404, {"error": "Route not found"})

    def do_PUT(self) -> None:
        path = unquote(urlparse(self.path).path)
        m = MARKER_ID_RE.match(path)
        if not m:
            self._send_json(404, {"error": "Route not found"})
            return
        body = self._read_json_body()
        if body is None:
            self._send_json(400, {"error": "Invalid JSON"})
            return
        updated = self.runtime.update_marker(m.group(1), body)
        if not updated:
            self._send_json(404, {"error": "Marker not found"})
            return
        self._send_json(200, updated)

    def do_DELETE(self) -> None:
        path = unquote(urlparse(self.path).path)
        m = MARKER_ID_RE.match(path)
        if not m:
            self._send_json(404, {"error": "Route not found"})
            return
        if not self.runtime.delete_marker(m.group(1)):
            self._send_json(404, {"error": "Marker not found"})
            return
        self._send_json(200, {"deleted": m.group(1)})

    def _handle_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        last_seq = -1
        try:
            while not self.runtime.stop_event.is_set():
                with self.runtime._sse_cond:
                    if self.runtime._live_seq == last_seq:
                        self.runtime._sse_cond.wait(timeout=1.0)
                    last_seq = self.runtime._live_seq
                    payload = json.dumps(self.runtime._latest_live, ensure_ascii=False, separators=(",", ":"))
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            return


class GhostPadHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], runtime: GhostPadRuntime) -> None:
        self.runtime = runtime
        super().__init__(server_address, GhostPadHTTPHandler)


def create_server(
    game_dir: Path | None = None,
    port: int = DEFAULT_PORT,
    lan: bool = False,
    rebuild: bool = False,
    telemetry_ptr: int | None = None,
    allow_takeover: bool = False,
) -> tuple[GhostPadHTTPServer, GhostPadRuntime]:
    settings = load_settings()
    gdir = game_dir or get_game_dir()
    eff_lang, lang_source = resolve_effective_language(settings, gdir)
    lang_setting = str(settings.get("lang") or "auto")
    host = "0.0.0.0" if lan else "127.0.0.1"
    runtime = GhostPadRuntime(
        gdir,
        lang=eff_lang,
        lang_setting=lang_setting,
        lang_source=lang_source,
        lan=lan,
        port=port,
        telemetry_ptr=telemetry_ptr,
        allow_takeover=allow_takeover,
    )
    srv = GhostPadHTTPServer((host, port), runtime)
    runtime.port = srv.server_address[1]
    runtime.start_background_tasks(force_rebuild=rebuild)
    return srv, runtime


def main() -> None:
    ap = argparse.ArgumentParser(description="Servidor Ghost Tactical Pad para Ghost Recon Wildlands.")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--lan", action="store_true", help="Escuta em 0.0.0.0 para celular/tablet na rede local")
    ap.add_argument("--game-dir", default=None)
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    srv, runtime = create_server(
        game_dir=Path(args.game_dir) if args.game_dir else None,
        port=args.port,
        lan=args.lan,
        rebuild=args.rebuild,
    )
    print(f"Ghost Tactical Pad ouvindo em http://127.0.0.1:{runtime.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.close()
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    main()
