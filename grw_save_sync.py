"""Sincronização automática de progresso (armas, acessórios, províncias, missões e POIs) via saves encriptados, UPLAY_SAVE e telemetria."""
from __future__ import annotations

import json
import math
import re
import struct
import time
import zlib
from pathlib import Path
from typing import Any

from anvil_formats import ForgeArchive, lzo1x_decompress
from config import (
    CARTEL_PATH,
    CATALOG_PATH,
    FORGE_IDS_PATH,
    LIVE_SAVES_DIR,
    MAP_DATA_PATH,
    find_save_files,
)
from grw_catalog_db import (
    ANVIL_PROVINCE_SYNC,
    BOSS_REWARD_PROVINCE_MAP,
    match_gbs_attachment_ids,
    match_gbs_weapon_ids,
)

GRW_SAVE_MAGIC = 0x1004FA9957FBAA33
GRW_CHUNK_MAGIC_BYTES = struct.pack("<Q", GRW_SAVE_MAGIC)
GRW_QUARTILE_MASKS = (0x44, 0xED, 0x7C, 0xB1)
GRW_TEA_DELTA = 0x9E3779B9

CID_CAMPAIGN_PROGRESS = 0x1FE25FCB
CID_INVENTORY_UNLOCKS = 0x8A9136AA
CID_PROFILE_UNLOCKS = 0x595FB7DD
CID_WORLD_PICKUPS = 0x8C28B28A
CID_WORLD_STATE_LIST = 0x42709AEA

_MISSION_SKIP_RE = re.compile(
    r"(?:_Body|_Intro|_IntroBody|_BodyCrowdlife|Fake|MIG|Investigation|GatherIntel|gatherIntels|IntelGathering|Unlock|_Timer)$",
    re.IGNORECASE,
)


def _ran3(seed: int):
    """Gerador pseudoaleatório subtrativo de Knuth (Numerical Recipes ran3, módulo 10_000_000)."""
    n = -seed if seed > 0 else seed
    mj = (161803398 - abs(n)) % 10000000
    if mj < 0:
        mj += 10000000
    ma = [0] * 56
    ma[55] = mj
    mk = 1
    for i in range(1, 55):
        ii = (21 * i) % 55
        ma[ii] = mk
        mk = mj - mk
        if mk < 0:
            mk += 10000000
        mj = ma[ii]
    for _ in range(4):
        for k in range(1, 56):
            ma[k] -= ma[1 + (k + 30) % 55]
            if ma[k] < 0:
                ma[k] += 10000000
    inext, inextp = 0, 31
    while True:
        inext = 1 if inext + 1 == 56 else inext + 1
        inextp = 1 if inextp + 1 == 56 else inextp + 1
        val = ma[inext] - ma[inextp]
        if val < 0:
            val += 10000000
        ma[inext] = val
        yield val


def decrypt_grw_payload(raw: bytes) -> bytes:
    """Desencripta payload GRW (sem cabeçalho Ubisoft de 552 bytes) via 4 camadas limpas em Python puro."""
    if len(raw) < 68:
        raise ValueError("Payload de save GRW muito curto")
    a = bytearray(raw)
    n = len(a)
    q = n >> 2
    h = q >> 1
    if h + 3 * q >= n - 4:
        raise ValueError("Tamanho inválido para camada de quartis GRW")
    for i, m in enumerate(GRW_QUARTILE_MASKS):
        idx = h + i * q
        a[idx] ^= m
        a[idx], a[n - 1 - i] = a[n - 1 - i], a[idx]

    b = bytes(a[:-4])
    if len(b) < 40 or (len(b) % 8) != 0:
        raise ValueError("Bloco TEA inválido no payload GRW")

    out = bytearray(len(b))
    for off in range(0, len(b), 8):
        v0, v1 = struct.unpack_from("<2I", b, off)
        s = (32 * GRW_TEA_DELTA) & 0xFFFFFFFF
        for _ in range(32):
            v1 = (v1 - ((((v0 << 4) ^ (v0 >> 5)) & 0xFFFFFFFF) ^ ((v0 + s) & 0xFFFFFFFF))) & 0xFFFFFFFF
            v0 = (v0 - ((((v1 << 4) ^ (v1 >> 5)) & 0xFFFFFFFF) ^ ((v1 + s) & 0xFFFFFFFF))) & 0xFFFFFFFF
            s = (s - GRW_TEA_DELTA) & 0xFFFFFFFF
        struct.pack_into("<2I", out, off, v0, v1)

    pad_len = struct.unpack_from("<Q", out, len(out) - 40)[0]
    if pad_len > len(out) - 40 - 12:
        raise ValueError("Comprimento de padding inválido após TEA GRW")
    s2 = bytes(out[: len(out) - 40 - pad_len])
    spad, bsz, seed2 = struct.unpack_from("<3I", s2, len(s2) - 12)
    if bsz <= 1 or len(s2) < 12 or ((len(s2) - 12) % bsz) != 0 or spad >= len(s2) - 12:
        raise ValueError("Metadados de embaralhamento inválidos no payload GRW")

    arr = bytearray(s2[:-12])
    gen2 = _ran3(seed2)
    for off in range(0, len(arr), bsz):
        swaps = [0] * (bsz - 1)
        for j in range(bsz - 1, 0, -1):
            swaps[j - 1] = next(gen2) % (j + 1)
        for k in range(1, bsz):
            si = swaps[k - 1]
            arr[off + k], arr[off + si] = arr[off + si], arr[off + k]

    s1 = bytes(arr[: len(arr) - spad])
    if len(s1) < 4:
        raise ValueError("Seed de XOR ausente no payload GRW")
    seed1 = struct.unpack_from("<I", s1, len(s1) - 4)[0]
    plain = bytearray(s1[:-4])
    gen1 = _ran3(seed1)
    key = 0
    for i in range(len(plain)):
        if (i & 3) == 0:
            key = next(gen1)
        plain[i] ^= (key >> (8 * (i & 3))) & 0xFF
    return bytes(plain)


def encrypt_grw_payload(plain: bytes, seed1: int = 12345, seed2: int = 67890, bsz: int = 16) -> bytes:
    """Encripta um plaintext GRW usando o inverso exato das 4 camadas (usado em testes)."""
    if bsz <= 1:
        raise ValueError("bsz deve ser > 1")
    buf1 = bytearray(plain)
    gen1 = _ran3(seed1)
    key = 0
    for i in range(len(buf1)):
        if (i & 3) == 0:
            key = next(gen1)
        buf1[i] ^= (key >> (8 * (i & 3))) & 0xFF
    s1 = bytes(buf1) + struct.pack("<I", seed1)

    rem = len(s1) % bsz
    spad = (bsz - rem) % bsz
    arr = bytearray(s1 + b"\x00" * spad)
    gen2 = _ran3(seed2)
    for off in range(0, len(arr), bsz):
        for j in range(bsz - 1, 0, -1):
            si = next(gen2) % (j + 1)
            arr[off + j], arr[off + si] = arr[off + si], arr[off + j]
    s2 = bytes(arr) + struct.pack("<3I", spad, bsz, seed2)

    rem8 = (len(s2) + 40) % 8
    pad_len = (8 - rem8) % 8
    b = bytearray(s2 + b"\x00" * pad_len + struct.pack("<Q", pad_len) + b"\x00" * 32)
    out = bytearray(len(b))
    for off in range(0, len(b), 8):
        v0, v1 = struct.unpack_from("<2I", b, off)
        s = 0
        for _ in range(32):
            s = (s + GRW_TEA_DELTA) & 0xFFFFFFFF
            v0 = (v0 + ((((v1 << 4) ^ (v1 >> 5)) & 0xFFFFFFFF) ^ ((v1 + s) & 0xFFFFFFFF))) & 0xFFFFFFFF
            v1 = (v1 + ((((v0 << 4) ^ (v0 >> 5)) & 0xFFFFFFFF) ^ ((v0 + s) & 0xFFFFFFFF))) & 0xFFFFFFFF
        struct.pack_into("<2I", out, off, v0, v1)

    a = bytearray(bytes(out) + b"\x00\x00\x00\x00")
    n = len(a)
    q = n >> 2
    h = q >> 1
    for i in range(len(GRW_QUARTILE_MASKS) - 1, -1, -1):
        m = GRW_QUARTILE_MASKS[i]
        idx = h + i * q
        a[idx], a[n - 1 - i] = a[n - 1 - i], a[idx]
        a[idx] ^= m
    return bytes(a)


def decrypt_grw_save_bytes(raw: bytes) -> bytes:
    """Aceita um arquivo `.save` completo (cabeçalho Ubisoft de 552 bytes) ou payload `UPLAY_SAVE` sem cabeçalho."""
    if len(raw) > 552 and struct.unpack_from("<I", raw, 0)[0] == 548:
        return decrypt_grw_payload(raw[552:])
    return decrypt_grw_payload(raw)


def decompress_grw_chunks(plaintext: bytes) -> list[tuple[int, bytes]]:
    """Extrai e descomprime (LZO1X / raw) todos os chunks `0x1004FA9957FBAA33` de um save GRW."""
    out_list: list[tuple[int, bytes]] = []
    pos = 0
    total_len = len(plaintext)
    while True:
        idx = plaintext.find(GRW_CHUNK_MAGIC_BYTES, pos)
        if idx == -1:
            break
        if idx < 8 or idx + 15 > total_len:
            pos = idx + 8
            continue
        tusz = struct.unpack_from("<I", plaintext, idx - 4)[0]
        cid = struct.unpack_from("<I", plaintext, idx - 8)[0]
        p = idx + 15
        out = bytearray()
        while p + 13 <= total_len:
            is_comp = plaintext[p]
            csz, usz, _csum = struct.unpack_from("<3I", plaintext, p + 1)
            if is_comp not in (0, 1) or csz == 0 or p + 13 + csz > total_len:
                break
            blk = plaintext[p + 13 : p + 13 + csz]
            p += 13 + csz
            if is_comp == 0 or csz == usz:
                out.extend(blk)
            else:
                out.extend(lzo1x_decompress(blk, usz))
            if tusz > 0 and len(out) >= tusz:
                break
        out_list.append((cid, bytes(out)))
        pos = max(p, idx + 8)
    return out_list


def _extract_zlib_chunks(blob: bytes) -> list[bytes]:
    """Descomprime streams zlib embutidos dentro de um buffer de save legado."""
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
    """Monitora saves encriptados no disco (.save), buffers em data/live_saves/ e proximidade do jogador."""

    def __init__(self, live_saves_dir: Path | None = None, game_dir: Path | None = None) -> None:
        self.live_saves_dir = live_saves_dir or LIVE_SAVES_DIR
        self.game_dir = game_dir
        self._last_read_seq = -1
        self._last_write_seq = -1
        self._last_save_sigs: dict[str, tuple[int, int]] = {}
        self._last_live_file_sigs: dict[str, tuple[int, int]] = {}
        self._last_disk_poll_ts = 0.0
        self._forge_ids: dict[str, Any] = {}
        self._t1_missions: dict[int, str] = {}
        self._t1_lo4: dict[int, list[tuple[int, str]]] = {}
        self._t2_items: dict[int, str] = {}
        self._t2_lo4: dict[int, list[tuple[int, str]]] = {}
        self._provinces: list[dict[str, Any]] = []
        self._pois: list[dict[str, Any]] = []
        self._wm_coords_cache: dict[str, list[float]] | None = None
        self._catalog_loaded = False

    def set_context(self, game_dir: Path | None = None, pois: list[dict[str, Any]] | None = None) -> None:
        if game_dir is not None:
            self.game_dir = game_dir
        if pois is not None:
            self._pois = list(pois)

    def reload_index(self) -> None:
        if FORGE_IDS_PATH.is_file():
            try:
                self._forge_ids = json.loads(FORGE_IDS_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._forge_ids = {}
        else:
            self._forge_ids = {}

        t1_raw = self._forge_ids.get("table1_missions") or {}
        t2_raw = self._forge_ids.get("table2_items") or {}
        self._t1_missions = {int(k): str(v) for k, v in t1_raw.items()}
        self._t2_items = {int(k): str(v) for k, v in t2_raw.items()}
        self._t1_lo4 = {}
        for vid, nm in self._t1_missions.items():
            self._t1_lo4.setdefault(vid & 0xFFFFFFFF, []).append((vid, nm))
        self._t2_lo4 = {}
        for vid, nm in self._t2_items.items():
            self._t2_lo4.setdefault(vid & 0xFFFFFFFF, []).append((vid, nm))

        if CARTEL_PATH.is_file():
            try:
                cr = json.loads(CARTEL_PATH.read_text(encoding="utf-8"))
                self._provinces = list(cr.get("provinces") or [])
            except (OSError, json.JSONDecodeError):
                self._provinces = []
        if not self._pois and MAP_DATA_PATH.is_file():
            try:
                md = json.loads(MAP_DATA_PATH.read_text(encoding="utf-8"))
                self._pois = list(md.get("pois") or [])
            except (OSError, json.JSONDecodeError):
                self._pois = []
        if not self._catalog_loaded and CATALOG_PATH.is_file():
            self._catalog_loaded = True

    def _ensure_loaded(self) -> None:
        if self._catalog_loaded:
            return
        if not self._forge_ids or (not self._t1_missions and not self._t2_items) or not self._provinces or not self._pois:
            self.reload_index()

    def _resolve_wm_pickup_coords(self, vids: list[int]) -> dict[int, tuple[float, float]]:
        """Resolve IDs de colecionáveis no `GRN_WorldMap` para coordenadas normalizadas (u, v), com cache em disco."""
        if not vids or self.game_dir is None:
            return {}
        coords_cache_path = FORGE_IDS_PATH.parent / "wm_pickup_coords.json"
        if self._wm_coords_cache is None:
            if coords_cache_path.is_file():
                try:
                    raw = json.loads(coords_cache_path.read_text(encoding="utf-8"))
                    self._wm_coords_cache = raw if isinstance(raw, dict) else {}
                except (OSError, json.JSONDecodeError):
                    self._wm_coords_cache = {}
            else:
                self._wm_coords_cache = {}

        cache = self._wm_coords_cache
        missing = [vid for vid in vids if str(vid) not in cache]
        if missing:
            wm_forge_path = self.game_dir / "DataPC_GRN_WorldMap_patch_01.forge"
            if not wm_forge_path.is_file():
                wm_forge_path = self.game_dir / "DataPC_GRN_WorldMap.forge"
            if wm_forge_path.is_file():
                try:
                    fa = ForgeArchive(wm_forge_path)
                    entries = fa.find_by_name("GRN_WorldMap")
                    if entries:
                        wm = b"".join(fa.read_payload_sets(entries[0]))
                        pat = re.compile(b"|".join(re.escape(struct.pack("<Q", v)) for v in missing))
                        for m in pat.finditer(wm):
                            vid = struct.unpack_from("<Q", wm, m.start())[0]
                            skey = str(vid)
                            if skey in cache and cache[skey]:
                                continue
                            p = m.start()
                            lo = max(0, p - 48)
                            hi = min(len(wm) - 12, p + 48)
                            found_uv: list[float] | None = None
                            for fo in range(lo, hi):
                                x, y, z = struct.unpack_from("<fff", wm, fo)
                                if (
                                    math.isfinite(x)
                                    and math.isfinite(y)
                                    and math.isfinite(z)
                                    and -8192.0 <= x <= 8192.0
                                    and -8192.0 <= y <= 8192.0
                                    and abs(x) > 1.0
                                    and abs(y) > 1.0
                                    and 50.0 <= z <= 6000.0
                                ):
                                    u = (x + 8192.0) / 16384.0
                                    v = 1.0 - (y + 8192.0) / 16384.0
                                    found_uv = [round(u, 6), round(v, 6)]
                                    break
                            cache[skey] = found_uv if found_uv is not None else []
                        for vid in missing:
                            cache.setdefault(str(vid), [])
                        try:
                            coords_cache_path.parent.mkdir(parents=True, exist_ok=True)
                            coords_cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                        except OSError:
                            pass
                except Exception:
                    pass

        out: dict[int, tuple[float, float]] = {}
        for vid in vids:
            val = cache.get(str(vid))
            if isinstance(val, list) and len(val) == 2:
                out[vid] = (float(val[0]), float(val[1]))
        return out

    def _scan_table1_campaign(self, buf: bytes) -> dict[str, Any]:
        """Extrai províncias descobertas, missões concluídas e buchones derrotados do chunk 0x1FE25FCB."""
        discovered: set[str] = set()
        bosses: set[str] = set()
        completed_states: set[str] = set()
        province_missions: dict[str, dict[str, int]] = {}

        if not buf or not self._t1_missions:
            return {
                "discovered_provinces": discovered,
                "defeated_bosses": bosses,
                "mission_names": completed_states,
                "province_missions": province_missions,
            }

        t1 = self._t1_missions
        lo4 = self._t1_lo4
        states: dict[str, tuple[int, bytes]] = {}
        limit = len(buf) - 16
        for off in range(0, limit):
            lo = struct.unpack_from("<I", buf, off)[0]
            if lo not in lo4:
                continue
            vid = struct.unpack_from("<Q", buf, off)[0]
            nm = t1.get(vid)
            if nm is None:
                continue
            sub = buf[off + 8 : min(len(buf), off + 64)]
            st_val = -1
            k19 = sub.find(b"\x19\x00\x0b")
            if k19 >= 0 and k19 + 7 <= len(sub):
                st_val = struct.unpack_from("<I", sub, k19 + 3)[0]
            val_bytes = b""
            j = sub.find(b"\x1d\x00\x0b")
            if j >= 0 and j + 8 <= len(sub):
                blen = struct.unpack_from("<I", sub, j + 4)[0]
                if 1 <= blen <= 32 and j + 8 + blen <= len(sub):
                    val_bytes = sub[j + 8 : j + 8 + blen]
            states[nm] = (st_val, val_bytes)

        for pid, cfg in ANVIL_PROVINCE_SYNC.items():
            root = cfg.get("root")
            pref = cfg.get("prefix")
            boss_ms = cfg.get("boss_mission")
            if root and root in states:
                _st, val_b = states[root]
                if len(val_b) >= 1 and val_b[0] == 1:
                    discovered.add(pid)
            if boss_ms and boss_ms in states:
                bst, bval = states[boss_ms]
                if bst == 2 or (bval and all(b == 1 for b in bval) and len(bval) >= 4):
                    bosses.add(pid)
                    discovered.add(pid)
            if pref and re.match(r"^(?:INF|PRO|SEC|SMU)_\d+$", pref):
                total_m = 0
                done_m = 0
                for nm, (mst, _mval) in states.items():
                    if not nm.startswith(pref + "_"):
                        continue
                    if not re.match(r"^(?:INF|PRO|SEC|SMU)_\d+_M\d+", nm):
                        continue
                    if _MISSION_SKIP_RE.search(nm):
                        continue
                    total_m += 1
                    if mst == 2:
                        done_m += 1
                        completed_states.add(nm)
                if total_m > 0:
                    province_missions[pid] = {"done": done_m, "total": total_m}

        return {
            "discovered_provinces": discovered,
            "defeated_bosses": bosses,
            "mission_names": completed_states,
            "province_missions": province_missions,
        }

    def _scan_table2_unlocks(self, buf: bytes) -> set[str]:
        """Extrai todos os nomes GBS Table 2 desbloqueados encontrados em chunks de inventário."""
        out: set[str] = set()
        if not buf or not self._t2_items:
            return out
        t2 = self._t2_items
        lo4 = self._t2_lo4
        limit = len(buf) - 8
        for off in range(0, limit):
            lo = struct.unpack_from("<I", buf, off)[0]
            if lo not in lo4:
                continue
            vid = struct.unpack_from("<Q", buf, off)[0]
            nm = t2.get(vid)
            if nm is not None:
                out.add(nm)
        return out

    def _scan_world_pickup_chunk(self, buf: bytes, allowed_provinces: set[str]) -> tuple[set[str], set[str]]:
        """Extrai caixas/medalhas/POIs abertos a partir do chunk 0x8C28B28A (`9d 04 0b 01`)."""
        items: set[str] = set()
        pois_done: set[str] = set()
        if not buf or not self._pois:
            return items, pois_done
        pm = buf.find(b"\x9d\x04\x0b\x01")
        if pm < 0 or pm + 8 > len(buf):
            return items, pois_done
        cnt = struct.unpack_from("<I", buf, pm + 4)[0]
        if cnt < 10 or cnt > 2500 or pm + 8 + cnt * 8 > len(buf):
            return items, pois_done
        vids = list(struct.unpack_from(f"<{cnt}Q", buf, pm + 8))
        resolved = self._resolve_wm_pickup_coords(vids)
        if not resolved:
            return items, pois_done

        valid_cats = {"weapon_case", "attachment_case", "bonus_medal", "skill_point", "kingslayer", "rebel_op"}
        for vid, (u, v) in resolved.items():
            best_poi: dict[str, Any] | None = None
            best_dist = 180.0
            for poi in self._pois:
                if poi.get("cat") not in valid_cats:
                    continue
                if allowed_provinces and poi.get("province") not in allowed_provinces:
                    continue
                d_m = math.hypot((float(poi["u"]) - u) * 16384.0, (float(poi["v"]) - v) * 16384.0)
                if d_m < best_dist:
                    best_dist = d_m
                    best_poi = poi
            if best_poi is not None:
                pois_done.add(str(best_poi["id"]))
                iid = best_poi.get("item_id")
                if iid and best_poi.get("cat") in ("bonus_medal", "weapon_case", "attachment_case"):
                    items.add(str(iid))
        return items, pois_done

    def parse_decrypted_chunks(
        self,
        chunks: list[tuple[int, bytes]],
        include_state_list_unlocks: bool = False,
    ) -> dict[str, Any]:
        """Interpreta chunks descomprimidos de um save de campanha ou perfil."""
        self._ensure_loaded()
        items: set[str] = set()
        pois: set[str] = set()
        bosses: set[str] = set()
        discovered_provs: set[str] = set()
        missions: set[str] = set()
        province_missions: dict[str, dict[str, int]] = {}
        unlocked_t2_names: set[str] = set()
        has_campaign_chunk = False
        world_pickup_chunks: list[bytes] = []

        for cid, buf in chunks:
            if cid == CID_CAMPAIGN_PROGRESS:
                has_campaign_chunk = True
                res_t1 = self._scan_table1_campaign(buf)
                discovered_provs |= res_t1["discovered_provinces"]
                bosses |= res_t1["defeated_bosses"]
                province_missions.update(res_t1["province_missions"])
            elif cid == CID_INVENTORY_UNLOCKS or cid == CID_PROFILE_UNLOCKS:
                unlocked_t2_names |= self._scan_table2_unlocks(buf)
            elif include_state_list_unlocks and cid == CID_WORLD_STATE_LIST:
                unlocked_t2_names |= self._scan_table2_unlocks(buf)
            elif cid == CID_WORLD_PICKUPS:
                world_pickup_chunks.append(buf)
            elif cid == CID_WORLD_STATE_LIST and b"\x9d\x04\x0b\x01" in buf:
                world_pickup_chunks.append(buf)

        if unlocked_t2_names:
            items |= match_gbs_weapon_ids(unlocked_t2_names)
            items |= match_gbs_attachment_ids(unlocked_t2_names)

        for buf in world_pickup_chunks:
            p_items, p_pois = self._scan_world_pickup_chunk(buf, discovered_provs)
            items |= p_items
            pois |= p_pois

        if has_campaign_chunk:
            items.update(("wp_p416", "wp_p45t"))
            for wid, bprov in BOSS_REWARD_PROVINCE_MAP.items():
                if bprov in bosses:
                    items.add(wid)
                elif wid in items:
                    bosses.add(bprov)
                    discovered_provs.add(bprov)

            for pr in self._provinces:
                pid = str(pr["id"])
                pm_info = province_missions.get(pid)
                pr_missions = pr.get("missions") or []
                if pid in bosses:
                    for m in pr_missions:
                        missions.add(str(m["id"]))
                elif pm_info and pm_info["done"] > 0:
                    # Marca proporcionalmente missões da província conforme progresso do save
                    limit_n = min(len(pr_missions), pm_info["done"])
                    for m in pr_missions[:limit_n]:
                        missions.add(str(m["id"]))

        for iid in list(items):
            pois.add(f"poi_{iid}")

        return {
            "has_campaign": has_campaign_chunk,
            "items": items,
            "pois": pois,
            "bosses": bosses,
            "provinces": discovered_provs,
            "missions": missions,
            "province_missions": province_missions,
        }

    def scan_plaintext_buffer(self, raw: bytes) -> dict[str, set[str]]:
        """Escaneia um buffer já descriptografado (chunks GRW ou legado `slot_*.bin`)."""
        self._ensure_loaded()
        chunks = decompress_grw_chunks(raw)
        if chunks:
            parsed = self.parse_decrypted_chunks(chunks)
            return {
                "items": set(parsed["items"]),
                "pois": set(parsed["pois"]),
                "provinces": set(parsed["provinces"]),
                "bosses": set(parsed["bosses"]),
                "missions": set(parsed["missions"]),
            }

        found_items: set[str] = set()
        found_provinces: set[str] = set()
        found_pois: set[str] = set()
        buffers = [raw] + _extract_zlib_chunks(raw)
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
            "bosses": set(found_provinces),
            "missions": set(),
        }

    def scan_all_saves(self, save_paths: list[Path] | None = None) -> dict[str, Any]:
        """Lê saves encriptados no disco (.save) e dumps em `live_saves/` priorizando a campanha mais recente."""
        self._ensure_loaded()
        candidates: list[tuple[float, str, bytes]] = []

        if self.live_saves_dir.is_dir():
            for p in sorted(self.live_saves_dir.glob("slot_*.bin"), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    raw = p.read_bytes()
                    if raw:
                        candidates.append((p.stat().st_mtime, f"live:{p.name}", raw))
                except OSError:
                    continue

        disk_files = save_paths if save_paths is not None else find_save_files()
        for sf in disk_files:
            try:
                raw = sf.read_bytes()
                if raw:
                    candidates.append((sf.stat().st_mtime, sf.name, raw))
            except OSError:
                continue

        candidates.sort(key=lambda item: item[0], reverse=True)

        items: set[str] = set()
        pois: set[str] = set()
        bosses: set[str] = set()
        provs: set[str] = set()
        missions: set[str] = set()
        province_missions: dict[str, dict[str, int]] = {}
        sources_used: list[str] = []
        campaign_loaded = False
        profile_loaded = False

        for _mt, label, raw in candidates:
            plaintext: bytes | None = None
            chunks: list[tuple[int, bytes]] = []
            try:
                plaintext = decrypt_grw_save_bytes(raw)
                chunks = decompress_grw_chunks(plaintext)
            except Exception:
                # Se já for um buffer plaintext de slot_*.bin ou teste
                chunks = decompress_grw_chunks(raw)
                if not chunks:
                    plaintext = raw

            if chunks:
                cids = {cid for cid, _ in chunks}
                is_campaign = CID_CAMPAIGN_PROGRESS in cids
                if is_campaign and campaign_loaded:
                    # Não mistura outro slot de campanha mais antigo com o slot ativo mais recente
                    continue
                if is_campaign:
                    parsed = self.parse_decrypted_chunks(chunks, include_state_list_unlocks=False)
                    campaign_loaded = True
                    sources_used.append(label)
                    items |= parsed["items"]
                    pois |= parsed["pois"]
                    bosses |= parsed["bosses"]
                    provs |= parsed["provinces"]
                    missions |= parsed["missions"]
                    province_missions.update(parsed["province_missions"])
                elif CID_PROFILE_UNLOCKS in cids and not profile_loaded:
                    # Save global de conta/loja mais recente (ex: 1.save/2.save): lê somente inventário de campanha
                    parsed = self.parse_decrypted_chunks(chunks, include_state_list_unlocks=False)
                    if parsed["items"]:
                        profile_loaded = True
                        sources_used.append(label)
                        items |= parsed["items"]
                        pois |= parsed["pois"]
            elif plaintext is not None and label.startswith("live:"):
                legacy = self.scan_plaintext_buffer(plaintext)
                if legacy["items"] or legacy["provinces"]:
                    sources_used.append(label)
                    items |= legacy["items"]
                    pois |= legacy["pois"]
                    provs |= legacy["provinces"]
                    bosses |= legacy["bosses"]
                    missions |= legacy["missions"]

        for wid, bprov in BOSS_REWARD_PROVINCE_MAP.items():
            if bprov in bosses:
                items.add(wid)
            elif wid in items and campaign_loaded:
                bosses.add(bprov)
                provs.add(bprov)

        for pr in self._provinces:
            if str(pr["id"]) in bosses:
                for m in pr.get("missions") or []:
                    missions.add(str(m["id"]))

        for iid in list(items):
            pois.add(f"poi_{iid}")

        return {
            "has_campaign": campaign_loaded,
            "items": items,
            "pois": pois,
            "bosses": bosses,
            "provinces": provs,
            "missions": missions,
            "province_missions": province_missions,
            "sources": sources_used,
        }

    def scan_plaintext_saves(self) -> dict[str, Any]:
        """Compatibilidade com chamadas legadas que esperam `slots_seen`."""
        res = self.scan_all_saves(save_paths=[])
        res["slots_seen"] = list(res.get("sources") or [])
        return res

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

    def _apply_save_scan_to_progress(self, cur: dict[str, Any], scanned: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        changed = False
        sync_ver = int((cur.get("auto_sync_info") or {}).get("sync_version") or 0)
        upgrading_v2 = sync_ver < 2
        if upgrading_v2:
            # Limpa IDs gerados pela heurística antiga v1 mantendo edições manuais do usuário
            for k_cur, k_auto in (
                ("collected_items", "auto_collected_items"),
                ("completed_pois", "auto_completed_pois"),
                ("completed_missions", "auto_completed_missions"),
                ("defeated_bosses", "auto_defeated_bosses"),
            ):
                old_auto = set(cur.get(k_auto) or [])
                if old_auto:
                    cur[k_cur] = [x for x in (cur.get(k_cur) or []) if x not in old_auto]
                    cur[k_auto] = []
                    changed = True
            if scanned.get("has_campaign") and scanned.get("provinces"):
                cur["discovered_provinces"] = sorted(scanned["provinces"])
                changed = True

        found_items: set[str] = set(scanned.get("items") or set())
        found_pois: set[str] = set(scanned.get("pois") or set())
        found_bosses: set[str] = set(scanned.get("bosses") or set())
        found_missions: set[str] = set(scanned.get("missions") or set())
        found_provs: set[str] = set(scanned.get("provinces") or set())

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

        if scanned.get("sources") or upgrading_v2:
            old_info = dict(cur.get("auto_sync_info") or {})
            new_info = {
                "sync_version": 2,
                "sources": list(scanned.get("sources") or []),
                "weapons_found": len(found_items),
                "bosses_found": len(found_bosses),
                "provinces_discovered": len(found_provs),
                "province_missions": dict(scanned.get("province_missions") or {}),
                "last_sync_ts": int(time.time()),
            }
            sig_new = (new_info["sync_version"], new_info["sources"], new_info["weapons_found"], new_info["bosses_found"], new_info["provinces_discovered"])
            sig_old = (old_info.get("sync_version"), old_info.get("sources"), old_info.get("weapons_found"), old_info.get("bosses_found"), old_info.get("provinces_discovered"))
            if changed or sig_new != sig_old:
                cur["auto_sync_info"] = new_info
                changed = True

        return cur, changed

    def _collect_signatures(self, save_paths: list[Path] | None = None) -> tuple[bool, bool, dict[str, tuple[int, int]], dict[str, tuple[int, int]]]:
        live_changed = False
        live_sigs: dict[str, tuple[int, int]] = {}
        if self.live_saves_dir.is_dir():
            for p in self.live_saves_dir.glob("slot_*.bin"):
                try:
                    st = p.stat()
                    sig = (int(st.st_mtime_ns), int(st.st_size))
                except OSError:
                    continue
                live_sigs[str(p)] = sig
                if self._last_live_file_sigs.get(str(p)) != sig:
                    live_changed = True

        disk_changed = False
        disk_sigs: dict[str, tuple[int, int]] = {}
        files = save_paths if save_paths is not None else find_save_files()
        for sf in files:
            try:
                st = sf.stat()
                sig = (int(st.st_mtime_ns), int(st.st_size))
            except OSError:
                continue
            disk_sigs[str(sf)] = sig
            if self._last_save_sigs.get(str(sf)) != sig:
                disk_changed = True

        return live_changed, disk_changed, live_sigs, disk_sigs

    def sync_disk_saves(
        self,
        current_progress: dict[str, Any],
        save_paths: list[Path] | None = None,
        force: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """Sincroniza imediatamente a partir dos arquivos `.save` no disco (mesmo com GRW.exe fechado)."""
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
        sync_ver = int(cur["auto_sync_info"].get("sync_version") or 0)
        live_changed, disk_changed, live_sigs, disk_sigs = self._collect_signatures(save_paths)
        if not force and sync_ver >= 2 and not live_changed and not disk_changed:
            return cur, False

        self._last_live_file_sigs = live_sigs
        self._last_save_sigs = disk_sigs
        scanned = self.scan_all_saves(save_paths=save_paths)
        return self._apply_save_scan_to_progress(cur, scanned)

    def process_live_tick(
        self,
        frame: dict[str, Any],
        current_progress: dict[str, Any],
        save_paths: list[Path] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Atualiza progresso automaticamente quando saves mudam ou player salva perto de POIs no jogo."""
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
        seq_changed = (rseq != self._last_read_seq and rseq > 0) or (wseq != self._last_write_seq and wseq > 0)
        self._last_read_seq = rseq
        self._last_write_seq = wseq

        now = time.monotonic()
        need_v2_upgrade = int(cur["auto_sync_info"].get("sync_version") or 0) < 2
        if seq_changed or need_v2_upgrade or (now - self._last_disk_poll_ts) >= 5.0:
            self._last_disk_poll_ts = now
            live_changed, disk_changed, live_sigs, disk_sigs = self._collect_signatures(save_paths)
            if seq_changed or need_v2_upgrade or live_changed or disk_changed:
                self._last_live_file_sigs = live_sigs
                self._last_save_sigs = disk_sigs
                scanned = self.scan_all_saves(save_paths=save_paths)
                cur, ch_scan = self._apply_save_scan_to_progress(cur, scanned)
                changed = changed or ch_scan
        else:
            live_changed = False
            disk_changed = False

        found_items: set[str] = set()
        found_pois: set[str] = set()
        found_bosses: set[str] = set()
        found_missions: set[str] = set()
        found_provs: set[str] = set()

        player = frame.get("player")
        if mode == "live" and player:
            found_items.update(("wp_p416", "wp_p45t"))
            pu = float(player.get("u", 0.5))
            pv = float(player.get("v", 0.5))
            near_prov = self._nearest_province(pu, pv)
            if near_prov:
                found_provs.add(near_prov)

            if (wseq > 0 and seq_changed) or disk_changed:
                for poi in self._pois:
                    d_m = math.hypot(float(poi["u"]) - pu, float(poi["v"]) - pv) * 16384.0
                    if d_m <= 65.0:
                        pid = str(poi["id"])
                        found_pois.add(pid)
                        if poi.get("item_id"):
                            found_items.add(str(poi["item_id"]))
                        if poi.get("cat") == "boss_hq" and poi.get("province"):
                            found_bosses.add(str(poi["province"]))
                for pr in self._provinces:
                    for m in pr.get("missions") or []:
                        d_m = math.hypot(float(m["u"]) - pu, float(m["v"]) - pv) * 16384.0
                        if d_m <= 75.0:
                            found_missions.add(str(m["id"]))
                            if m.get("is_boss"):
                                found_bosses.add(str(pr["id"]))

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

        return cur, changed

    def get_save_probe(self) -> dict[str, Any]:
        self._ensure_loaded()
        live_files = []
        if self.live_saves_dir.is_dir():
            for p in sorted(self.live_saves_dir.glob("slot_*.bin")):
                live_files.append({"name": p.name, "size": p.stat().st_size, "mtime": int(p.stat().st_mtime)})
        scanned = self.scan_all_saves()
        return {
            "live_saves_dir": str(self.live_saves_dir),
            "live_files": live_files,
            "disk_saves": [p.name for p in find_save_files()],
            "table1_missions_loaded": len(self._t1_missions),
            "table2_items_loaded": len(self._t2_items),
            "forge_ids_loaded": len(self._forge_ids.get("weapons") or {}),
            "detected_items": sorted(scanned["items"]),
            "detected_bosses": sorted(scanned["bosses"]),
            "detected_provinces": sorted(scanned["provinces"]),
            "detected_missions_count": len(scanned["missions"]),
            "sources": scanned["sources"],
        }
