"""Sincronização automática de progresso (armas, acessórios, províncias, missões e POIs) via UPLAY_SAVE e telemetria."""
from __future__ import annotations

import json
import math
import struct
import time
import zlib
from pathlib import Path
from typing import Any

from config import (
    CARTEL_PATH,
    CATALOG_PATH,
    FORGE_IDS_PATH,
    LIVE_SAVES_DIR,
    MAP_DATA_PATH,
    find_save_files,
)
from grw_catalog_db import BOSS_REWARD_PROVINCE_MAP


def _extract_zlib_chunks(blob: bytes) -> list[bytes]:
    """Descomprime streams zlib embutidos dentro de um buffer de save."""
    out: list[bytes] = []
    idx = 0
    limit = len(blob)
    while idx < limit - 2 and len(out) < 32:
        p = -1
        for sig in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            cand = blob.find(sig, idx)
            if cand != -1 and (p == -1 or cand < p):
                p = cand
        if p == -1:
            break
        try:
            d = zlib.decompressobj()
            dec = d.decompress(blob[p : min(limit, p + 524288)], 2 * 1024 * 1024)
            if len(dec) >= 16:
                out.append(dec)
        except zlib.error:
            pass
        idx = p + 2
    return out


class AutoProgressSync:
    """Monitora buffers desencriptados em data/live_saves/, saves no disco e proximidade do jogador."""

    def __init__(self, live_saves_dir: Path | None = None) -> None:
        self.live_saves_dir = live_saves_dir or LIVE_SAVES_DIR
        self._last_read_seq = -1
        self._last_write_seq = -1
        self._last_save_mtimes: dict[str, float] = {}
        self._last_live_file_mtimes: dict[str, float] = {}
        self._forge_ids: dict[str, Any] = {}
        self._provinces: list[dict[str, Any]] = []
        self._pois: list[dict[str, Any]] = []
        self._catalog_loaded = False
        self._last_sync_info: dict[str, Any] = {}

    def reload_index(self) -> None:
        if FORGE_IDS_PATH.is_file():
            try:
                self._forge_ids = json.loads(FORGE_IDS_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._forge_ids = {}
        if CARTEL_PATH.is_file():
            try:
                cr = json.loads(CARTEL_PATH.read_text(encoding="utf-8"))
                self._provinces = list(cr.get("provinces") or [])
            except (OSError, json.JSONDecodeError):
                self._provinces = []
        if MAP_DATA_PATH.is_file():
            try:
                md = json.loads(MAP_DATA_PATH.read_text(encoding="utf-8"))
                self._pois = list(md.get("pois") or [])
            except (OSError, json.JSONDecodeError):
                self._pois = []
        if not self._catalog_loaded and CATALOG_PATH.is_file():
            self._catalog_loaded = True

    def _ensure_loaded(self) -> None:
        if not self._forge_ids or not self._provinces or not self._pois:
            self.reload_index()

    def scan_plaintext_buffer(self, raw: bytes) -> dict[str, set[str]]:
        """Escaneia um buffer plaintext de save em busca de fid (64-bit LE) e tokens Anvil."""
        self._ensure_loaded()
        found_items: set[str] = set()
        found_provinces: set[str] = set()
        found_pois: set[str] = set()

        buffers = [raw] + _extract_zlib_chunks(raw)

        # Constroi mapa de fid(8B) -> (kind, id)
        fid_targets: list[tuple[bytes, str, str]] = []
        name_targets: list[tuple[bytes, str, str]] = []
        for kind_key, out_kind in (("weapons", "item"), ("attachments", "item"), ("provinces", "province")):
            bucket = self._forge_ids.get(kind_key) or {}
            for obj_id, recs in bucket.items():
                for r in recs:
                    fid = int(r.get("fid") or 0)
                    if fid > 0:
                        fid_targets.append((struct.pack("<Q", fid), out_kind, obj_id))
                    nm = str(r.get("name") or "")
                    if len(nm) >= 6:
                        name_targets.append((nm.encode("ascii", errors="ignore"), out_kind, obj_id))

        for buf in buffers:
            if not buf:
                continue
            for pat, kind, obj_id in fid_targets:
                if pat in buf:
                    if kind == "province":
                        found_provinces.add(obj_id)
                    else:
                        found_items.add(obj_id)
                        found_pois.add(f"poi_{obj_id}")
            for npat, kind, obj_id in name_targets:
                if npat in buf:
                    if kind == "province":
                        found_provinces.add(obj_id)
                    else:
                        found_items.add(obj_id)
                        found_pois.add(f"poi_{obj_id}")

        return {
            "items": found_items,
            "pois": found_pois,
            "provinces": found_provinces,
        }

    def scan_plaintext_saves(self) -> dict[str, Any]:
        """Varre todos os arquivos slot_*.bin em live_saves/."""
        items: set[str] = set()
        pois: set[str] = set()
        bosses: set[str] = set()
        provs: set[str] = set()
        missions: set[str] = set()
        slots_seen: list[str] = []

        if self.live_saves_dir.is_dir():
            for p in sorted(self.live_saves_dir.glob("slot_*.bin"), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    raw = p.read_bytes()
                    if not raw:
                        continue
                    slots_seen.append(p.name)
                    res = self.scan_plaintext_buffer(raw)
                    items |= res["items"]
                    pois |= res["pois"]
                    provs |= res["provinces"]
                    bosses |= res["provinces"]
                except OSError:
                    continue

        if slots_seen:
            # Save ativo garante equipamento inicial desbloqueado
            items.update(("wp_p416", "wp_p45t"))
            for wid, bprov in BOSS_REWARD_PROVINCE_MAP.items():
                if bprov in bosses:
                    items.add(wid)
                elif wid in items:
                    bosses.add(bprov)

        for pr in self._provinces:
            pid = pr["id"]
            if pid in bosses:
                for m in pr.get("missions") or []:
                    missions.add(m["id"])

        return {
            "items": items,
            "pois": pois,
            "bosses": bosses,
            "provinces": provs,
            "missions": missions,
            "slots_seen": slots_seen,
        }

    def _nearest_province(self, u: float, v: float) -> str | None:
        best_id = None
        best_d = 0.095
        for p in self._provinces:
            d = math.hypot(float(p["u"]) - u, float(p["v"]) - v)
            if d < best_d:
                best_d = d
                best_id = str(p["id"])
        return best_id

    @staticmethod
    def _merge_auto_field(cur_list: list[str], auto_list: list[str], newly_found: set[str]) -> tuple[list[str], list[str], bool]:
        """Adiciona apenas IDs recém-descobertos sem sobrescrever desmarcações manuais antigas."""
        cur_set = set(cur_list)
        auto_set = set(auto_list)
        added = newly_found - auto_set
        changed = False
        if added:
            for item in added:
                if item not in cur_set:
                    cur_set.add(item)
                    changed = True
            auto_set |= added
            changed = True
        return sorted(cur_set), sorted(auto_set), changed

    def process_live_tick(
        self,
        frame: dict[str, Any],
        current_progress: dict[str, Any],
        save_paths: list[Path] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Atualiza progresso automaticamente quando saves mudam ou player interage perto de POIs no jogo."""
        self._ensure_loaded()
        cur = {
            "collected_items": list(current_progress.get("collected_items") or []),
            "completed_pois": list(current_progress.get("completed_pois") or []),
            "discovered_provinces": list(current_progress.get("discovered_provinces") or ["itacua"]),
            "defeated_bosses": list(current_progress.get("defeated_bosses") or []),
            "completed_missions": list(current_progress.get("completed_missions") or []),
            "auto_collected_items": list(current_progress.get("auto_collected_items") or []),
            "auto_completed_pois": list(current_progress.get("auto_completed_pois") or []),
            "auto_completed_missions": list(current_progress.get("auto_completed_missions") or []),
            "auto_defeated_bosses": list(current_progress.get("auto_defeated_bosses") or []),
            "auto_sync_info": dict(current_progress.get("auto_sync_info") or {}),
        }
        changed = False

        mode = str(frame.get("mode") or "offline")
        rseq = int(frame.get("save_read_seq") or 0)
        wseq = int(frame.get("save_write_seq") or 0)

        live_file_changed = False
        if self.live_saves_dir.is_dir():
            for p in self.live_saves_dir.glob("slot_*.bin"):
                try:
                    mt = p.stat().st_mtime
                except OSError:
                    continue
                if self._last_live_file_mtimes.get(str(p)) != mt:
                    self._last_live_file_mtimes[str(p)] = mt
                    live_file_changed = True

        disk_save_changed = False
        files = save_paths if save_paths is not None else find_save_files()
        for sf in files:
            try:
                mt = sf.stat().st_mtime
            except OSError:
                continue
            prev = self._last_save_mtimes.get(str(sf))
            if prev is None:
                self._last_save_mtimes[str(sf)] = mt
            elif mt > prev:
                self._last_save_mtimes[str(sf)] = mt
                disk_save_changed = True

        should_scan_saves = (
            live_file_changed
            or (rseq != self._last_read_seq and rseq > 0)
            or (wseq != self._last_write_seq and wseq > 0)
        )
        self._last_read_seq = rseq
        self._last_write_seq = wseq

        found_items: set[str] = set()
        found_pois: set[str] = set()
        found_bosses: set[str] = set()
        found_missions: set[str] = set()
        found_provs: set[str] = set()

        player = frame.get("player")
        if mode == "live" and player:
            # Ao entrar em sessão ativa, garante armas iniciais
            found_items.update(("wp_p416", "wp_p45t"))
            pu = float(player.get("u", 0.5))
            pv = float(player.get("v", 0.5))
            near_prov = self._nearest_province(pu, pv)
            if near_prov:
                found_provs.add(near_prov)

        new_sync_meta: dict[str, Any] | None = None
        if should_scan_saves:
            scanned = self.scan_plaintext_saves()
            found_items |= scanned["items"]
            found_pois |= scanned["pois"]
            found_bosses |= scanned["bosses"]
            found_provs |= scanned["provinces"]
            found_missions |= scanned["missions"]
            if scanned["slots_seen"]:
                new_sync_meta = {
                    "source": "uplay_save",
                    "slots": scanned["slots_seen"],
                    "matched_count": len(scanned["items"]) + len(scanned["bosses"]),
                }

        # Correlação ao vivo: quando o jogo salva próximo a um POI (ex: abriu caixa ou chegou no Rally Point)
        if mode == "live" and player and (wseq > 0 and should_scan_saves or disk_save_changed):
            pu = float(player.get("u", 0.5))
            pv = float(player.get("v", 0.5))
            for poi in self._pois:
                d_m = math.hypot(float(poi["u"]) - pu, float(poi["v"]) - pv) * 21000.0
                if d_m <= 65.0:
                    pid = str(poi["id"])
                    found_pois.add(pid)
                    if poi.get("item_id"):
                        found_items.add(str(poi["item_id"]))
                    if poi.get("cat") == "boss_hq" and poi.get("province"):
                        found_bosses.add(str(poi["province"]))
            for pr in self._provinces:
                for m in pr.get("missions") or []:
                    d_m = math.hypot(float(m["u"]) - pu, float(m["v"]) - pv) * 21000.0
                    if d_m <= 75.0:
                        found_missions.add(str(m["id"]))
                        if m.get("is_boss"):
                            found_bosses.add(str(pr["id"]))
            new_sync_meta = dict(new_sync_meta or {})
            new_sync_meta["source"] = "uplay_save+proximity" if should_scan_saves else "save_proximity"

        if found_provs:
            prev_dp = set(cur["discovered_provinces"])
            if not found_provs.issubset(prev_dp):
                cur["discovered_provinces"] = sorted(prev_dp | found_provs)
                changed = True

        if found_items:
            ci, ai, ch = self._merge_auto_field(cur["collected_items"], cur["auto_collected_items"], found_items)
            if ch:
                cur["collected_items"] = ci
                cur["auto_collected_items"] = ai
                changed = True
                # Sincroniza POIs correspondentes
                for iid in found_items:
                    found_pois.add(f"poi_{iid}")

        if found_pois:
            cp, ap, ch = self._merge_auto_field(cur["completed_pois"], cur["auto_completed_pois"], found_pois)
            if ch:
                cur["completed_pois"] = cp
                cur["auto_completed_pois"] = ap
                changed = True

        if found_bosses:
            cb, ab, ch = self._merge_auto_field(cur["defeated_bosses"], cur["auto_defeated_bosses"], found_bosses)
            if ch:
                cur["defeated_bosses"] = cb
                cur["auto_defeated_bosses"] = ab
                changed = True

        if found_missions:
            cm, am, ch = self._merge_auto_field(cur["completed_missions"], cur["auto_completed_missions"], found_missions)
            if ch:
                cur["completed_missions"] = cm
                cur["auto_completed_missions"] = am
                changed = True

        if new_sync_meta:
            old_info = cur.get("auto_sync_info") or {}
            sig_new = (new_sync_meta.get("source"), new_sync_meta.get("slots"), new_sync_meta.get("matched_count"))
            sig_old = (old_info.get("source"), old_info.get("slots"), old_info.get("matched_count"))
            if changed or sig_new != sig_old:
                merged_info = dict(old_info)
                merged_info.update(new_sync_meta)
                merged_info["last_sync_ts"] = int(time.time())
                cur["auto_sync_info"] = merged_info
                changed = True

        return cur, changed

    def get_save_probe(self) -> dict[str, Any]:
        self._ensure_loaded()
        live_files = []
        if self.live_saves_dir.is_dir():
            for p in sorted(self.live_saves_dir.glob("slot_*.bin")):
                live_files.append({"name": p.name, "size": p.stat().st_size, "mtime": int(p.stat().st_mtime)})
        scanned = self.scan_plaintext_saves()
        return {
            "live_saves_dir": str(self.live_saves_dir),
            "live_files": live_files,
            "forge_ids_loaded": len(self._forge_ids.get("weapons") or {}),
            "scanned": {
                "items": sorted(scanned["items"]),
                "bosses": sorted(scanned["bosses"]),
                "missions_count": len(scanned["missions"]),
                "slots_seen": scanned["slots_seen"],
            },
        }
