"""Extrator local de máscaras, ícones oficiais BC7, IDs Anvil e bancos de dados para cache/ do Ghost Tactical Pad."""
from __future__ import annotations

import json
import struct
import threading
import time
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw

from anvil_formats import ForgeArchive, decode_anvil_texture_map
from config import (
    CACHE_VERSION,
    CARTEL_PATH,
    CATALOG_PATH,
    FORGE_IDS_PATH,
    ICONS_CACHE_DIR,
    MAP_DATA_PATH,
    MASKS_CACHE_DIR,
    META_PATH,
    ensure_dirs,
)
from grw_catalog_db import (
    ATTACHMENTS_DB,
    MAP_CATEGORIES,
    PROVINCES,
    WEAPONS_DB,
    build_static_databases,
)

_BUILD_LOCK = threading.Lock()

# TODOS os 12 ícones oficiais de categorias do mapa no DataPC.forge (BC7 32x32)
FORGE_ICON_MAP: dict[str, str] = {
    "weapon_case": "UI_HUD_Hint_Marker_WeaponLoot_Map",
    "attachment_case": "UI_HUD_Hint_Marker_WeaponAttachmentLoot_Map",
    "bonus_medal": "UI_HUD_Hint_Icon_Medal_Map",
    "sb_base": "UI_HUD_Hint_SB_Icon_Map",
    "unidad_base": "UI_HUD_Hint_UnidadGauge_Icon_Map",
    "sam_site": "UI_HUD_Hint_SAMLauncher_Icon_Map",
    "jammer": "UI_HUD_Hint_DroneJamer_Icon_Map",
    "rebel_op": "UI_HUD_Hint_RebelOps_Icon_Map",
    "rally_point": "UI_HUD_Hint_RallyPoint_Map",
    "skill_point": "UI_HUD_Hint_Icon_SkillPoint_Map",
    "kingslayer": "UI_HUD_Hint_Intel_Story_Icon_Map",
    "boss_hq": "UI_HUD_Hint_Icon_HVT_Map",
}

# Ícones oficiais de classe de armas no DataPC.forge
FORGE_CLASS_ICON_MAP: dict[str, str] = {
    "class_ar": "UI_COM_Icon_Assault_Rifles_Map",
    "class_sniper": "UI_COM_Icon_Sniper_Rifles_Map",
    "class_smg": "UI_COM_Icon_SmallMachineGuns_Map",
    "class_lmg": "UI_COM_Icon_LightMachineGuns_Map",
    "class_pistol": "UI_COM_Icon_HandGuns_Map",
}


def _hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha
    return 255, 255, 255, alpha


def _render_fallback_icon(cat_id: str, color_hex: str, out_path: Path) -> None:
    """Desenha um ícone tático nítido 36x36 em PNG caso DataPC.forge não esteja acessível."""
    sz = 36
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    col = _hex_to_rgba(color_hex, 255)
    bg = (10, 16, 24, 225)
    c = sz // 2

    if cat_id in ("sb_base", "unidad_base", "boss_hq"):
        pts = [(c, 3), (sz - 4, c), (c, sz - 3), (4, c)]
        draw.polygon(pts, fill=bg, outline=col)
        if cat_id == "boss_hq":
            draw.ellipse([c - 6, c - 6, c + 6, c + 6], fill=col)
        else:
            draw.rectangle([c - 4, c - 4, c + 4, c + 4], fill=col)
    elif cat_id in ("sam_site", "jammer"):
        pts = [(c, 4), (sz - 4, sz - 5), (4, sz - 5)]
        draw.polygon(pts, fill=bg, outline=col)
        draw.ellipse([c - 3, c + 1, c + 3, c + 7], fill=col)
    elif cat_id in ("weapon_case", "attachment_case"):
        draw.rounded_rectangle([4, 7, sz - 4, sz - 7], radius=5, fill=bg, outline=col, width=2)
        if cat_id == "weapon_case":
            draw.rectangle([9, c - 2, sz - 9, c + 2], fill=col)
            draw.rectangle([12, c + 2, 16, c + 6], fill=col)
        else:
            draw.ellipse([c - 5, c - 5, c + 5, c + 5], outline=col, width=2)
            draw.ellipse([c - 2, c - 2, c + 2, c + 2], fill=col)
    else:
        draw.ellipse([4, 4, sz - 4, sz - 4], fill=bg, outline=col, width=2)
        draw.ellipse([c - 4, c - 4, c + 4, c + 4], fill=col)

    im.save(out_path, format="PNG")


def _build_province_masks(sectors_bytes: bytes) -> None:
    """Gera overlays PNG de borda da Bolívia e divisões regionais a partir de UI_Tacmap_ProvinceMap_Map (1024x1024)."""
    if len(sectors_bytes) != 1024 * 1024:
        return
    (MASKS_CACHE_DIR / "sectors.bin").write_bytes(sectors_bytes)

    w = h = 1024
    border_buf = bytearray(w * h * 4)
    prov_buf = bytearray(w * h * 4)
    data = sectors_bytes

    for y in range(h):
        row_off = y * w
        for x in range(w):
            idx = row_off + x
            v = data[idx]
            p4 = idx * 4
            if v == 255:
                border_buf[p4 : p4 + 4] = b"\x06\x0b\x12\xaa"
                continue
            is_outer = False
            is_sector = False
            if x > 0:
                nv = data[idx - 1]
                if nv == 255:
                    is_outer = True
                elif nv != v:
                    is_sector = True
            if x + 1 < w:
                nv = data[idx + 1]
                if nv == 255:
                    is_outer = True
                elif nv != v:
                    is_sector = True
            if y > 0:
                nv = data[idx - w]
                if nv == 255:
                    is_outer = True
                elif nv != v:
                    is_sector = True
            if y + 1 < h:
                nv = data[idx + w]
                if nv == 255:
                    is_outer = True
                elif nv != v:
                    is_sector = True

            if is_outer:
                border_buf[p4 : p4 + 4] = b"\x38\xbd\xf8\xd0"
                prov_buf[p4 : p4 + 4] = b"\x38\xbd\xf8\xd0"
            elif is_sector:
                prov_buf[p4 : p4 + 4] = b"\x7d\xd3\xfc\x48"

    Image.frombytes("RGBA", (w, h), bytes(border_buf)).save(MASKS_CACHE_DIR / "bolivia_border.png", "PNG")
    Image.frombytes("RGBA", (w, h), bytes(prov_buf)).save(MASKS_CACHE_DIR / "provinces_overlay.png", "PNG")


def _extract_gbs_tables(game_dir: Path | None, fallback_forge: ForgeArchive | None = None) -> tuple[dict[str, str], dict[str, str]]:
    """Extrai tabelas Anvil (Table 1 missões/províncias `0x830B78C0` e Table 2 armas/acessórios `0x36C9CB38`) do Game Bootstrap Settings."""
    gbs_blob: bytes | None = None
    candidates: list[ForgeArchive] = []
    if game_dir is not None:
        patch_path = game_dir / "DataPC_patch_01.forge"
        if patch_path.is_file():
            try:
                candidates.append(ForgeArchive(patch_path))
            except Exception:
                pass
    if fallback_forge is not None:
        candidates.append(fallback_forge)

    for arch in candidates:
        try:
            entries = arch.find_by_name("Game Bootstrap Settings")
            if entries:
                sets = arch.read_payload_sets(entries[0])
                if sets:
                    gbs_blob = b"".join(sets)
                    break
        except Exception:
            continue

    if not gbs_blob:
        return {}, {}

    t1: dict[str, str] = {}
    pos = 0
    blob_len = len(gbs_blob)
    while True:
        i = gbs_blob.find(b"\xc0\x78\x0b\x83", pos)
        if i == -1:
            break
        if i + 8 <= blob_len:
            slen = struct.unpack_from("<I", gbs_blob, i + 4)[0]
            if 1 <= slen <= 160 and i + 17 + slen <= blob_len and gbs_blob[i + 8 + slen] == 0:
                name = gbs_blob[i + 8 : i + 8 + slen].decode("ascii", errors="replace")
                vid = struct.unpack_from("<Q", gbs_blob, i + 9 + slen)[0]
                if vid > 0x10000 and name:
                    t1[str(vid)] = name
                pos = i + 17 + slen
                continue
        pos = i + 4

    t2: dict[str, str] = {}
    pos = 10
    while True:
        i = gbs_blob.find(b"\x38\xcb\xc9\x36", pos)
        if i == -1 or i + 16 > blob_len:
            break
        slen = struct.unpack_from("<I", gbs_blob, i + 8)[0]
        if 2 <= slen <= 160 and i + 12 + slen < blob_len and gbs_blob[i + 12 + slen] == 0:
            name = gbs_blob[i + 12 : i + 12 + slen].decode("ascii", errors="replace")
            vid = struct.unpack_from("<Q", gbs_blob, i - 10)[0]
            if vid > 0x10000 and name:
                t2[str(vid)] = name
            pos = i + 13 + slen
            continue
        pos = i + 4

    return t1, t2


def _build_forge_ids_index(forge: ForgeArchive, game_dir: Path | None = None) -> dict[str, Any]:
    """Indexa IDs Anvil do DataPC.forge e tabelas do Game Bootstrap Settings para sincronização de saves."""
    weapons_fids: dict[str, list[dict[str, Any]]] = {}
    atts_fids: dict[str, list[dict[str, Any]]] = {}
    provinces_fids: dict[str, list[dict[str, Any]]] = {}
    collectibles_fids: dict[str, list[int]] = {}

    entry_by_exact: dict[str, list[dict[str, Any]]] = {}
    for e in forge.entries:
        entry_by_exact.setdefault(e["name"], []).append(e)

    def _collect_for_patterns(patterns: list[str]) -> list[dict[str, Any]]:
        matched: list[dict[str, Any]] = []
        seen_fids: set[int] = set()
        for pat in patterns:
            # Prefere correspondência exata e variantes base sem texturas _Map/_Mip
            for e in entry_by_exact.get(pat, ()):
                fid = int(e["fid"])
                if fid not in seen_fids:
                    seen_fids.add(fid)
                    matched.append({"name": e["name"], "fid": fid, "res_id": int(e["res_id"])})
            if not matched:
                for e in forge.entries:
                    nm = e["name"]
                    if nm.startswith(pat) and "Map" not in nm and "_LOD" not in nm:
                        fid = int(e["fid"])
                        if fid not in seen_fids:
                            seen_fids.add(fid)
                            matched.append({"name": nm, "fid": fid, "res_id": int(e["res_id"])})
                        if len(matched) >= 6:
                            break
        return matched

    for w in WEAPONS_DB:
        pats = w.get("forge_patterns") or []
        if pats:
            hits = _collect_for_patterns(pats)
            if hits:
                weapons_fids[w["id"]] = hits

    for a in ATTACHMENTS_DB:
        pats = a.get("forge_patterns") or []
        if pats:
            hits = _collect_for_patterns(pats)
            if hits:
                atts_fids[a["id"]] = hits

    for p in PROVINCES:
        fn = p.get("forge_completed_name")
        if fn:
            hits = _collect_for_patterns([fn])
            if hits:
                provinces_fids[p["id"]] = hits

    for e in forge.entries:
        nm = e["name"]
        if nm.startswith("Collectible_"):
            parts = nm.split("_")
            if len(parts) >= 2:
                collectibles_fids.setdefault(parts[1], []).append(int(e["fid"]))

    t1_missions, t2_items = _extract_gbs_tables(game_dir, fallback_forge=forge)

    return {
        "version": 2,
        "weapons": weapons_fids,
        "attachments": atts_fids,
        "provinces": provinces_fids,
        "collectible_fids": collectibles_fids,
        "table1_missions": t1_missions,
        "table2_items": t2_items,
    }


def is_cache_valid(lang: str, game_dir: Path) -> bool:
    if not (META_PATH.is_file() and MAP_DATA_PATH.is_file() and CATALOG_PATH.is_file() and CARTEL_PATH.is_file()):
        return False
    try:
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        return (
            meta.get("version") == CACHE_VERSION
            and meta.get("lang") == lang
            and meta.get("game_dir") == str(game_dir)
        )
    except (OSError, json.JSONDecodeError):
        return False


def ensure_cache_built(
    game_dir: Path,
    lang: str = "pt-BR",
    force: bool = False,
    progress_cb: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    """Constrói o cache local de dados, ícones oficiais BC7, IDs .forge e máscaras a partir da cópia do jogador."""
    with _BUILD_LOCK:
        ensure_dirs()
        if not force and is_cache_valid(lang, game_dir):
            return json.loads(META_PATH.read_text(encoding="utf-8"))

        t0 = time.perf_counter()
        if progress_cb:
            progress_cb(10, "Indexing Wildlands .forge archives...")

        forge_path = game_dir / "DataPC.forge"
        forge: ForgeArchive | None = None
        if forge_path.is_file():
            try:
                forge = ForgeArchive(forge_path)
            except Exception:
                forge = None

        if progress_cb:
            progress_cb(35, "Extracting province borders & masks...")

        if forge is not None:
            prov_entries = forge.find_by_name("UI_Tacmap_ProvinceMap_Map")
            if prov_entries:
                try:
                    sets = forge.read_payload_sets(prov_entries[0])
                    if sets and len(sets[-1]) >= 1024 * 1024:
                        _build_province_masks(sets[-1][-1048576:])
                except Exception:
                    pass

        if progress_cb:
            progress_cb(55, "Decoding official tactical & weapon icons...")

        for cat in MAP_CATEGORIES:
            cid = cat["id"]
            out_icon = ICONS_CACHE_DIR / f"{cid}.png"
            extracted = False
            if forge is not None and cid in FORGE_ICON_MAP:
                entries = forge.find_by_name(FORGE_ICON_MAP[cid])
                if entries:
                    try:
                        sets = forge.read_payload_sets(entries[0])
                        im = decode_anvil_texture_map(sets)
                        if im is not None:
                            im.save(out_icon, "PNG")
                            extracted = True
                    except Exception:
                        extracted = False
            if not extracted:
                _render_fallback_icon(cid, cat["color"], out_icon)

        if forge is not None:
            for key, tex_name in FORGE_CLASS_ICON_MAP.items():
                out_cls = ICONS_CACHE_DIR / f"{key}.png"
                entries = forge.find_by_name(tex_name)
                if entries:
                    try:
                        im = decode_anvil_texture_map(forge.read_payload_sets(entries[0]))
                        if im is not None:
                            im.save(out_cls, "PNG")
                    except Exception:
                        pass

            if progress_cb:
                progress_cb(72, "Indexing Anvil unlock & province IDs...")
            try:
                forge_ids = _build_forge_ids_index(forge, game_dir=game_dir)
                FORGE_IDS_PATH.write_text(json.dumps(forge_ids, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

        if progress_cb:
            progress_cb(85, "Building tactical catalog, compatibility & cartel DB...")

        map_data, catalog_data, cartel_data = build_static_databases(lang)
        MAP_DATA_PATH.write_text(json.dumps(map_data, ensure_ascii=False), encoding="utf-8")
        CATALOG_PATH.write_text(json.dumps(catalog_data, ensure_ascii=False), encoding="utf-8")
        CARTEL_PATH.write_text(json.dumps(cartel_data, ensure_ascii=False), encoding="utf-8")

        meta = {
            "version": CACHE_VERSION,
            "lang": lang,
            "game_dir": str(game_dir),
            "built_at": int(time.time()),
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "counts": {
                "provinces": len(map_data["provinces"]),
                "pois": len(map_data["pois"]),
                "weapons": len(catalog_data["weapons"]),
                "attachments": len(catalog_data["attachments"]),
                "medals": len(catalog_data["medals"]),
            },
            "has_wmap": (game_dir / "gr.wmap").is_file(),
            "has_heatmap": (game_dir / "gr_h.wmap").is_file(),
            "has_masks": (MASKS_CACHE_DIR / "bolivia_border.png").is_file(),
        }
        META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        if progress_cb:
            progress_cb(100, "Ready")
        return meta
