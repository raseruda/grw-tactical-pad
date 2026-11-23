"""Testes automatizados para leitores AnvilNext, banco de itens, motor tático e servidor."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from anvil_formats import ForgeArchive, HeightmapSampler, WmapReader, decode_anvil_texture_map
from grw_asset_builder import FORGE_ICON_MAP, ensure_cache_built
from grw_catalog_db import (
    ATTACHMENTS_DB,
    BONUS_MEDALS,
    PROVINCES,
    WEAPON_ACOUSTICS,
    WEAPONS_DB,
    build_static_databases,
)
from grw_memory import EALERT_MAP, EFACTION_MAP, GRWLiveReader, GRWTelemetryState, TELEMETRY_VERSION
from grw_save_sync import AutoProgressSync
from tactical_engine import analyze_tactical_state, evaluate_aim_shot, evaluate_safe_fire

WILDLANDS_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Wildlands")


class TestCatalogAndAssets(unittest.TestCase):
    def test_provinces_and_catalog_completeness(self) -> None:
        self.assertEqual(len(PROVINCES), 21)
        prov_ids = {p["id"] for p in PROVINCES}
        self.assertGreaterEqual(len(WEAPONS_DB), 55)
        self.assertGreaterEqual(len(ATTACHMENTS_DB), 55)
        self.assertGreaterEqual(len(BONUS_MEDALS), 10)
        for w in WEAPONS_DB:
            self.assertIn(w["province"], prov_ids)
            self.assertIn(w["weapon_class"], WEAPON_ACOUSTICS)
            self.assertTrue(0.0 <= w["u"] <= 1.0 and 0.0 <= w["v"] <= 1.0)
        for a in ATTACHMENTS_DB:
            self.assertIn(a["province"], prov_ids)
            self.assertTrue(0.0 <= a["u"] <= 1.0 and 0.0 <= a["v"] <= 1.0)

        m_pt, c_pt, ct_pt = build_static_databases("pt-BR")
        self.assertEqual(len(m_pt["provinces"]), 21)
        self.assertEqual(len(ct_pt["wings"]), 4)
        self.assertGreater(len(m_pt["pois"]), 180)
        self.assertEqual(len(c_pt["weapons"]), len(WEAPONS_DB))

    @unittest.skipUnless((WILDLANDS_DIR / "gr.wmap").is_file(), "Wildlands não instalado")
    def test_wmap_and_heatmap_decode(self) -> None:
        for fname in ("gr.wmap", "gr_h.wmap"):
            rd = WmapReader(WILDLANDS_DIR / fname)
            try:
                self.assertTrue(rd.valid)
                for lod in (6, 4, 2, 0):
                    png = rd.get_tile_png(lod, 0, 0)
                    self.assertIsNotNone(png)
                    self.assertTrue(png.startswith(b"\x89PNG"))
            finally:
                rd.close()

    @unittest.skipUnless((WILDLANDS_DIR / "DataPC.forge").is_file(), "DataPC.forge ausente")
    def test_forge_and_cache_build(self) -> None:
        fa = ForgeArchive(WILDLANDS_DIR / "DataPC.forge")
        self.assertEqual(len(fa.entries), 29640)
        prov = fa.find_by_name("UI_Tacmap_ProvinceMap_Map")
        self.assertTrue(len(prov) >= 1)
        sets = fa.read_payload_sets(prov[0])
        self.assertTrue(len(sets[-1]) >= 1048576)

        sam = fa.find_by_name("UI_HUD_Hint_SAMLauncher_Icon_Map")
        self.assertTrue(len(sam) >= 1)
        im = decode_anvil_texture_map(fa.read_payload_sets(sam[0]))
        self.assertIsNotNone(im)
        self.assertEqual(im.size, (32, 32))

        meta = ensure_cache_built(WILDLANDS_DIR, lang="pt-BR", force=True)
        self.assertTrue(meta["has_wmap"])
        self.assertTrue(meta["has_heatmap"])
        self.assertTrue((config.MASKS_CACHE_DIR / "bolivia_border.png").is_file())

    @unittest.skipUnless((WILDLANDS_DIR / "DataPC.forge").is_file(), "DataPC.forge ausente")
    def test_all_12_bc7_poi_icons_decoded(self) -> None:
        from PIL import Image
        ensure_cache_built(WILDLANDS_DIR, lang="pt-BR", force=False)
        self.assertEqual(len(FORGE_ICON_MAP), 12)
        for cat_id in FORGE_ICON_MAP:
            icon_path = config.ICONS_CACHE_DIR / f"{cat_id}.png"
            self.assertTrue(icon_path.is_file(), f"Ícone ausente: {cat_id}")
            im = Image.open(icon_path).convert("RGBA")
            self.assertEqual(im.size, (32, 32))
            # Verifica que o canal alpha tem pixels visíveis decodificados em BC7 (não imagem vazia/corrompida)
            alpha_extrema = im.getchannel("A").getextrema()
            self.assertGreater(alpha_extrema[1], 16, f"Ícone {cat_id} veio transparente!")

    def test_bidirectional_compatibility_and_province_tasks(self) -> None:
        _, cat_pt, ct_pt = build_static_databases("pt-BR")
        weapons_by_id = {w["id"]: w for w in cat_pt["weapons"]}
        atts_by_id = {a["id"]: a for a in cat_pt["attachments"]}

        m4 = weapons_by_id["wp_m4a1"]
        self.assertTrue(m4["customizable"])
        self.assertTrue(len(m4["compatible_attachments"]) >= 4)
        slots = [grp["slot"] for grp in m4["compatible_attachments"]]
        self.assertIn("scope", slots)
        self.assertIn("muzzle", slots)
        self.assertIn("underbarrel", slots)

        m203 = atts_by_id["att_m203"]
        self.assertTrue(len(m203["compatible_weapons"]) >= 1)
        m203_classes = [grp["weapon_class"] for grp in m203["compatible_weapons"]]
        self.assertIn("ar", m203_classes)
        ar_grp = next(g for g in m203["compatible_weapons"] if g["weapon_class"] == "ar")
        self.assertTrue(any(w["id"] == "wp_m4a1" for w in ar_grp["items"]))

        itacua = next(p for p in ct_pt["provinces"] if p["id"] == "itacua")
        self.assertGreaterEqual(len(itacua["missions"]), 5)
        self.assertIn("tasks", itacua)
        for key in ("missions", "weapons", "attachments", "medals", "skill_points", "kingslayer", "rebel_ops", "rally_points", "bases"):
            self.assertIn(key, itacua["tasks"])


class TestTacticalStealthEngine(unittest.TestCase):
    def _mk_player(self, wclass: str = "ar", suppressed: bool = True, is_aiming: bool = True, aim_dir=(0.0, 1.0, 0.0)):
        return {
            "id": "player",
            "type": "player",
            "name": "Nomad",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "u": 0.5,
            "v": 0.5,
            "head": [0.0, 0.0, 1.6],
            "aim_origin": [0.0, 0.0, 1.6],
            "aim_dir": list(aim_dir),
            "is_aiming": is_aiming,
            "weapon_class": wclass,
            "suppressed": suppressed,
        }

    def _mk_enemy(self, eid: str, x: float, y: float, z: float = 0.0, look=(0.0, 1.0, 0.0), alert: str = "unaware"):
        return {
            "id": eid,
            "faction": "santa_blanca",
            "x": x,
            "y": y,
            "z": z,
            "u": 0.5 + x * 0.0001,
            "v": 0.5 - y * 0.0001,
            "head": [x, y, z + 1.6],
            "look_dir": list(look),
            "alert": alert,
            "alive": True,
        }

    def test_safe_fire_all_weapon_classes(self) -> None:
        # Inimigo a 25m: seguro com pistola silenciada (18m), ouvido com fuzil AR silenciado (34m) e com pistola sem silenciador (49m)
        enemies = [self._mk_enemy("e1", 0.0, 25.0)]
        self.assertTrue(evaluate_safe_fire(self._mk_player("pistol", True), enemies)["safe"])
        self.assertFalse(evaluate_safe_fire(self._mk_player("pistol", False), enemies)["safe"])
        self.assertFalse(evaluate_safe_fire(self._mk_player("ar", True), enemies)["safe"])

        # Inimigo a 120m: ouvido apenas por sniper sem silenciador (130m), seguro com LMG/Shotgun sem silenciador (109m)
        far_enemies = [self._mk_enemy("e2", 0.0, 120.0)]
        self.assertTrue(evaluate_safe_fire(self._mk_player("lmg", False), far_enemies)["safe"])
        self.assertFalse(evaluate_safe_fire(self._mk_player("sniper", False), far_enemies)["safe"])

    def test_aim_sound_and_visual_witnesses(self) -> None:
        player = self._mk_player("ar", True, is_aiming=True, aim_dir=(0.0, 1.0, 0.0))
        target = self._mk_enemy("tgt", 0.0, 60.0, look=(0.0, -1.0, 0.0))

        # Testemunha 1: olhando diretamente para o alvo a 30m de distância (deve detectar testemunha visual!)
        w_seeing = self._mk_enemy("w_see", 30.0, 60.0, look=(-1.0, 0.0, 0.0))
        res_vis = evaluate_aim_shot(player, [target, w_seeing], prefs={"enemyVisionRangeM": 55, "enemyFovDeg": 110})
        self.assertIsNotNone(res_vis)
        self.assertEqual(res_vis["target_id"], "tgt")
        self.assertEqual(res_vis["verdict"], "visual_risk")
        self.assertEqual(res_vis["visual_witness_count"], 1)
        self.assertEqual(res_vis["sound_witness_count"], 0)

        # Testemunha 2: de costas para o alvo a 30m (fora do FOV), mas um terceiro inimigo a 8m do alvo (ouve o impacto!)
        w_back = self._mk_enemy("w_back", 30.0, 60.0, look=(1.0, 0.0, 0.0))
        w_impact = self._mk_enemy("w_imp", 8.0, 60.0, look=(1.0, 0.0, 0.0))
        res_snd = evaluate_aim_shot(player, [target, w_back, w_impact], prefs={"bulletImpactNoiseM": 12})
        self.assertIsNotNone(res_snd)
        self.assertEqual(res_snd["verdict"], "sound_risk")
        self.assertEqual(res_snd["visual_witness_count"], 0)
        self.assertEqual(res_snd["sound_witness_count"], 1)
        self.assertEqual(res_snd["sound_witnesses"][0]["reason"], "impact")

    def test_terrain_los_blocks_visual_witness(self) -> None:
        # Terreno com crista alta no meio (entre x=10..20)
        grid = [[0.0] * 11 for _ in range(11)]
        for r in range(11):
            grid[r][5] = 25.0  # colina de 25m no centro x=0
        hm = HeightmapSampler(grid, min_x=-50.0, max_x=50.0, min_y=-50.0, max_y=50.0)

        player = self._mk_player("sniper", True, is_aiming=True, aim_dir=(-1.0, 0.0, 0.0))
        player["x"], player["y"], player["aim_origin"] = -20.0, 0.0, [-20.0, 0.0, 1.6]
        target = self._mk_enemy("t_left", -30.0, 0.0)
        observer = self._mk_enemy("obs_right", 30.0, 0.0, look=(-1.0, 0.0, 0.0))

        # Sem terrain LOS -> vê
        res_no_los = evaluate_aim_shot(player, [target, observer], heightmap=hm, prefs={"useTerrainLos": False, "enemyVisionRangeM": 80})
        self.assertEqual(res_no_los["visual_witness_count"], 1)
        # Com terrain LOS -> colina bloqueia
        res_los = evaluate_aim_shot(player, [target, observer], heightmap=hm, prefs={"useTerrainLos": True, "enemyVisionRangeM": 80})
        self.assertEqual(res_los["visual_witness_count"], 0)

    def test_solo_ai_and_coop_ally_aim_alerts(self) -> None:
        player = self._mk_player("ar", True, is_aiming=False)
        target = self._mk_enemy("t1", 0.0, 80.0)
        watcher = self._mk_enemy("w1", 25.0, 80.0, look=(-1.0, 0.0, 0.0))

        ally_ai = {
            "id": "ai_holt",
            "type": "ai",
            "name": "Holt",
            "x": -20.0,
            "y": 40.0,
            "z": 0.0,
            "u": 0.49,
            "v": 0.50,
            "head": [-20.0, 40.0, 1.6],
            "aim_dir": [20.0 / 44.721, 40.0 / 44.721, 0.0],
            "is_aiming": True,
            "weapon_class": "ar",
            "suppressed": True,
        }
        ally_coop = {
            "id": "coop_1",
            "type": "coop",
            "name": "Co-op Ghost 1",
            "x": 0.0,
            "y": 50.0,
            "z": 0.0,
            "u": 0.50,
            "v": 0.495,
            "head": [0.0, 50.0, 1.6],
            "aim_dir": [0.0, 1.0, 0.0],
            "is_aiming": True,
            "weapon_class": "sniper",
            "suppressed": False,
        }
        frame = {"player": player, "allies": [ally_ai, ally_coop], "enemies": [target, watcher]}

        res_both = analyze_tactical_state(frame, prefs={"showAlliesSolo": True, "showAlliesCoop": True, "showAllyAimWarning": True})
        self.assertEqual(len(res_both["ally_aims"]), 2)
        self.assertEqual(res_both["ally_aims"][0]["verdict"], "visual_risk")
        self.assertEqual(res_both["ally_aims"][1]["verdict"], "critical")  # Co-op sniper sem silenciador -> som E visão!

        # Customização: desabilitar aliados Solo AI mantém apenas Co-op!
        res_coop_only = analyze_tactical_state(frame, prefs={"showAlliesSolo": False, "showAlliesCoop": True, "showAllyAimWarning": True})
        self.assertEqual(len(res_coop_only["visible_allies"]), 1)
        self.assertEqual(len(res_coop_only["ally_aims"]), 1)
        self.assertEqual(res_coop_only["ally_aims"][0]["shooter_type"], "coop")

    def test_faction_filtered_sound_and_vision(self) -> None:
        player = self._mk_player("ar", True, is_aiming=True, aim_dir=(0.0, 1.0, 0.0))
        target = self._mk_enemy("tgt", 0.0, 60.0, look=(0.0, -1.0, 0.0))
        rebel = {
            **self._mk_enemy("reb_1", 10.0, 10.0, look=(-1.0, -1.0, 0.0)),
            "faction": "rebel",
        }
        civilian = {
            **self._mk_enemy("civ_1", 20.0, 60.0, look=(-1.0, 0.0, 0.0)),
            "faction": "civilian",
        }
        npcs = [target, rebel, civilian]

        # Padrão: apenas santa_blanca e unidad são considerados ouvintes / testemunhas
        res_default = analyze_tactical_state({"player": player, "npcs": npcs}, prefs={})
        self.assertTrue(res_default["safe_fire"]["safe"])
        self.assertEqual(res_default["player_aim"]["verdict"], "safe")

        # Ao ativar rebeldes para som e civis para visão, ambos passam a gerar alertas!
        res_custom = analyze_tactical_state(
            {"player": player, "npcs": npcs},
            prefs={
                "soundFactions": ["santa_blanca", "unidad", "rebel"],
                "visionFactions": ["santa_blanca", "unidad", "civilian"],
                "enemyVisionRangeM": 55,
            },
        )
        self.assertFalse(res_custom["safe_fire"]["safe"])
        self.assertEqual(res_custom["player_aim"]["visual_witness_count"], 1)


class TestTelemetryLanguageAndAutoSync(unittest.TestCase):
    def test_launcher_game_language_byte_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            docs = Path(td)
            cfg_dir = docs / "My Games" / "Ghost Recon Wildlands"
            cfg_dir.mkdir(parents=True)
            lang_file = cfg_dir / "LAUNCHER_GAME_LANGUAGE"

            for byte_val, expected in ((8, "pt-BR"), (1, "en-US"), (7, "es-LA"), (9, "ja-JP")):
                lang_file.write_bytes(bytes([byte_val]))
                self.assertEqual(config.read_grw_launcher_language(docs), expected)

            lang_file.write_bytes(b"\x00")
            self.assertIsNone(config.read_grw_launcher_language(docs))

    def test_telemetry_v2_struct_and_faction_maps(self) -> None:
        import ctypes
        self.assertEqual(TELEMETRY_VERSION, 2)
        self.assertEqual(ctypes.sizeof(GRWTelemetryState), 193888)
        self.assertEqual(EFACTION_MAP[0], "civilian")
        self.assertEqual(EFACTION_MAP[1], "civilian")
        self.assertEqual(EFACTION_MAP[2], "ghost")
        self.assertEqual(EFACTION_MAP[3], "santa_blanca")
        self.assertEqual(EFACTION_MAP[4], "santa_blanca")
        self.assertEqual(EFACTION_MAP[5], "unidad")
        self.assertEqual(EFACTION_MAP[6], "rebel")
        self.assertEqual(EFACTION_MAP[7], "rebel")
        self.assertEqual(EFACTION_MAP[8], "santa_blanca")
        self.assertEqual(EALERT_MAP[3], "suspected")
        self.assertEqual(EALERT_MAP[6], "hostile")

    def test_auto_progress_sync_save_fid_and_proximity(self) -> None:
        import struct
        import zlib
        with tempfile.TemporaryDirectory() as td:
            saves_dir = Path(td)
            sync = AutoProgressSync(live_saves_dir=saves_dir)
            fake_fid = 0x1122334455667788
            sync._forge_ids = {
                "weapons": {"wp_m4a1": [{"fid": fake_fid, "name": "W_ASR_M4A1"}]},
                "attachments": {},
                "provinces": {"libertad": [{"fid": 0x9988776655443322, "name": "UI_Libertad_Completed"}]},
            }
            _, _, ct = build_static_databases("pt-BR")
            sync._provinces = ct["provinces"]
            sync._pois = [
                {
                    "id": "poi_att_panoramic",
                    "item_id": "att_panoramic",
                    "cat": "attachment_case",
                    "u": 0.525,
                    "v": 0.620,
                }
            ]
            sync._catalog_loaded = True

            payload = b"HEADER" + struct.pack("<Q", fake_fid) + b"UI_Libertad_Completed"
            (saves_dir / "slot_0.bin").write_bytes(zlib.compress(payload))

            frame = {
                "mode": "live",
                "save_read_seq": 1,
                "save_write_seq": 1,
                "player": {"u": 0.525, "v": 0.620},
            }
            updated, changed = sync.process_live_tick(frame, {}, save_paths=[])
            self.assertTrue(changed)
            self.assertIn("wp_m4a1", updated["collected_items"])
            self.assertIn("att_panoramic", updated["collected_items"])
            self.assertIn("poi_att_panoramic", updated["completed_pois"])
            self.assertIn("libertad", updated["defeated_bosses"])
            self.assertTrue(len(updated["completed_missions"]) >= 1)

            # Não re-adiciona item se usuário desmarcou manualmente depois do auto-sync!
            updated["collected_items"].remove("wp_m4a1")
            updated2, changed2 = sync.process_live_tick(
                {"mode": "live", "save_read_seq": 2, "save_write_seq": 2, "player": {"u": 0.525, "v": 0.620}},
                updated,
                save_paths=[],
            )
            self.assertFalse(changed2)
            self.assertNotIn("wp_m4a1", updated2["collected_items"])


class TestServerAndPersistence(unittest.TestCase):
    def test_http_server_routes_and_settings_roundtrip(self) -> None:
        import time
        import threading
        import urllib.error
        import urllib.request
        from server import create_server

        orig_settings = config.SETTINGS_PATH.read_bytes() if config.SETTINGS_PATH.is_file() else None
        orig_progress = config.PROGRESS_PATH.read_bytes() if config.PROGRESS_PATH.is_file() else None
        srv, runtime = create_server(game_dir=WILDLANDS_DIR, port=0, lan=False, allow_takeover=True)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        base = f"http://127.0.0.1:{runtime.port}"
        try:
            # Aguarda cache pronto
            st = {}
            for _ in range(40):
                with urllib.request.urlopen(f"{base}/api/status", timeout=5) as r:
                    st = json.loads(r.read().decode())
                if st["build"]["state"] == "ready":
                    break
                time.sleep(0.15)
            self.assertEqual(st["build"]["state"], "ready")

            # Testa persistência completa das opções customizadas + novas opções v1.1.0
            custom = {
                "showEnemyDirection": False,
                "showEnemyVisionCones": True,
                "showAlliesSolo": False,
                "showAlliesCoop": True,
                "enemyVisionRangeM": 75,
                "enemyFovDeg": 130,
                "bulletImpactNoiseM": 16,
                "weaponOverrideClass": "sniper",
                "weaponOverrideSuppressed": "unsuppressed",
                "weaponNoiseRingMode": "aiming",
                "visionFactions": ["santa_blanca", "unidad", "civilian"],
                "soundFactions": ["santa_blanca", "rebel"],
                "showFactionRebel": False,
                "selectedProvince": "itacua",
                "nearbyCats": ["weapon_case", "attachment_case", "kingslayer", "skill_point"],
            }
            req = urllib.request.Request(
                f"{base}/api/settings",
                data=json.dumps({"ui_prefs": custom}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                post_res = json.loads(r.read().decode())
            self.assertTrue(post_res["ok"])

            # Atualização parcial de idioma NÃO pode apagar ui_prefs já salvos!
            req_lang = urllib.request.Request(
                f"{base}/api/settings",
                data=json.dumps({"lang": "en-US"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req_lang, timeout=5) as r:
                r.read()

            with urllib.request.urlopen(f"{base}/api/settings", timeout=5) as r:
                got = json.loads(r.read().decode())
            self.assertEqual(got["lang"], "en-US")
            for k, v in custom.items():
                self.assertEqual(got["ui_prefs"][k], v)

            # Testa HTML, estáticos, compatibilidade, ícones oficiais e tiles satélite + heatmap
            with urllib.request.urlopen(f"{base}/", timeout=5) as r:
                html = r.read().decode()
            self.assertIn("GHOST TACTICAL PAD", html)
            with urllib.request.urlopen(f"{base}/api/static/catalog", timeout=5) as r:
                cat = json.loads(r.read().decode())
            self.assertGreaterEqual(len(cat["weapons"]), 55)
            if WILDLANDS_DIR.is_dir():
                with urllib.request.urlopen(f"{base}/api/tile/satellite/6/0/0.png", timeout=5) as r:
                    t_sat = r.read()
                with urllib.request.urlopen(f"{base}/api/tile/heatmap/6/0/0.png", timeout=5) as r:
                    t_heat = r.read()
                self.assertTrue(t_sat.startswith(b"\x89PNG"))
                self.assertTrue(t_heat.startswith(b"\x89PNG"))
                with urllib.request.urlopen(f"{base}/api/icon/weapon_case.png", timeout=5) as r:
                    t_icon = r.read()
                self.assertTrue(t_icon.startswith(b"\x89PNG"))

            # Testa takeover via POST /api/shutdown (200 quando allow_takeover=True)
            req_sd = urllib.request.Request(f"{base}/api/shutdown", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req_sd, timeout=5) as r:
                sd_res = json.loads(r.read().decode())
            self.assertTrue(sd_res["ok"])
            self.assertTrue(runtime.stop_event.wait(timeout=1.5))
        finally:
            runtime.close()
            srv.shutdown()
            srv.server_close()
            if orig_settings is not None:
                config.SETTINGS_PATH.write_bytes(orig_settings)
            elif config.SETTINGS_PATH.is_file():
                config.SETTINGS_PATH.unlink()
            if orig_progress is not None:
                config.PROGRESS_PATH.write_bytes(orig_progress)
            elif config.PROGRESS_PATH.is_file():
                config.PROGRESS_PATH.unlink()

    def test_shutdown_rejected_when_embedded(self) -> None:
        import threading
        import urllib.error
        import urllib.request
        from server import create_server

        srv, runtime = create_server(game_dir=WILDLANDS_DIR, port=0, lan=False, allow_takeover=False)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        base = f"http://127.0.0.1:{runtime.port}"
        try:
            req = urllib.request.Request(f"{base}/api/shutdown", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                with urllib.request.urlopen(req, timeout=5) as r:
                    r.read()
            self.assertEqual(ctx.exception.code, 403)
        finally:
            runtime.close()
            srv.shutdown()
            srv.server_close()


USER_SAVE_DIR = (
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    / "Ubisoft"
    / "Ubisoft Game Launcher"
    / "savegames"
    / "1d0734dc-4bc2-4c19-990a-a7d16dda7b0e"
    / "3559"
)
USER_SAVE_4 = USER_SAVE_DIR / "4.save"


class TestBugfixesV120(unittest.TestCase):
    def test_texture_map_vertical_orientation(self) -> None:
        import struct
        name = b"TestIcon"
        hdr = bytearray(12)
        struct.pack_into("<I", hdr, 8, len(name))
        prefix = bytes(hdr) + name + b"\x00" + b"\x00" * 12
        meta = bytearray(112)
        struct.pack_into("<4I", meta, 1, 4, 4, 1, 0)  # width=4, height=4, depth=1, fmt=0 (BGRA)
        # Bottom-up rows stored in Anvil TextureMap: top buffer rows = red BGRA, bottom buffer rows = blue BGRA
        red_bgra = bytes([0, 0, 255, 255])
        blue_bgra = bytes([255, 0, 0, 255])
        pixels = (red_bgra * 8) + (blue_bgra * 8)
        im = decode_anvil_texture_map([prefix + bytes(meta) + pixels])
        self.assertIsNotNone(im)
        self.assertEqual(im.size, (4, 4))
        # Após espelhamento vertical, y=0 fica azul e y=3 fica vermelho
        self.assertEqual(im.getpixel((0, 0)), (0, 0, 255, 255))
        self.assertEqual(im.getpixel((0, 3)), (255, 0, 0, 255))

    def test_world_bounds_calibration_and_v3_migration(self) -> None:
        wb = config.DEFAULT_SETTINGS["world_bounds"]
        self.assertEqual(wb["min_x"], -8192.0)
        self.assertEqual(wb["max_x"], 8192.0)
        self.assertEqual(wb["min_y"], -8192.0)
        self.assertEqual(wb["max_y"], 8192.0)
        self.assertFalse(config.DEFAULT_UI_PREFS["showTrail"])

        reader = GRWLiveReader()
        u, v = reader.world_to_uv(5570.0, 5719.0)
        self.assertTrue(0.83 < u < 0.85, f"Esperado NE Espíritu Santo, veio u={u}")
        self.assertTrue(0.14 < v < 0.16, f"Esperado v~0.151, veio v={v}")

        # Simula settings.json antigo (-10500..10500 e showTrail=True sem prefs_migrated_v3)
        old_cfg = {
            "lang": "pt-BR",
            "world_bounds": {"min_x": -10500.0, "max_x": 10500.0, "min_y": -10500.0, "max_y": 10500.0, "invert_y": True},
            "ui_prefs": {"showTrail": True, "followPlayer": False},
        }
        migrated = config._merge_settings_defaults(old_cfg)
        self.assertEqual(migrated["world_bounds"]["min_x"], -8192.0)
        self.assertEqual(migrated["world_bounds"]["max_x"], 8192.0)
        self.assertTrue(migrated.get("prefs_migrated_v3"))
        self.assertFalse(migrated["ui_prefs"]["showTrail"])
        self.assertFalse(migrated["ui_prefs"]["followPlayer"])

    def test_no_fake_coop_ghosts_and_ally_cap(self) -> None:
        import ctypes
        from grw_memory import TELEMETRY_MAGIC

        now_ms = int(ctypes.windll.kernel32.GetTickCount64())
        st = GRWTelemetryState()
        st.magic = TELEMETRY_MAGIC
        st.version = TELEMETRY_VERSION
        st.hooks_mask = 1
        st.build_matched = 1
        st.cam_valid = 1
        st.cam_last_ms = now_ms
        st.cam_fwd[1] = 1.0
        st.local_player_entity = 0x1000
        st.local_player_skel = 0x2000

        shared_vtable = 0x7FF000010000
        # Slot 0: Player
        p = st.chars[0]
        p.entity_ptr = 0x1000
        p.skel_ptr = 0x2000
        p.entity_vtable = shared_vtable
        p.rig_ptr = 0xAAAA
        p.valid_flags = 3
        p.last_seen_ms = now_ms
        p.faction_raw = 2  # ghost
        p.alert_raw = 1
        p.root_pos[0], p.root_pos[1], p.root_pos[2] = 0.0, 0.0, 100.0
        p.head_pos[0], p.head_pos[1], p.head_pos[2] = 0.0, 0.0, 101.6

        # Slots 1..40: 40 NPCs compartilhando o MESMO entity_vtable do player + Santa Blanca / civis + distantes
        for idx in range(1, 41):
            c = st.chars[idx]
            c.entity_ptr = 0x3000 + idx
            c.skel_ptr = 0x4000 + idx
            c.entity_vtable = shared_vtable
            c.rig_ptr = 0xAAAA if idx <= 6 else 0xBBBB
            c.valid_flags = 3
            c.last_seen_ms = now_ms
            c.bone_count = 300
            c.alert_raw = 1
            c.root_pos[0], c.root_pos[1], c.root_pos[2] = float(idx * 5), 10.0, 100.0
            c.head_pos[0], c.head_pos[1], c.head_pos[2] = float(idx * 5), 10.0, 101.6
            if idx <= 5:
                c.faction_raw = 2  # 5 ghosts candidatos -> deve limitar em no máximo 3!
            elif idx <= 25:
                c.faction_raw = 3  # Santa Blanca
            else:
                c.faction_raw = 0  # Civil / neutro

        reader = GRWLiveReader(telemetry_ptr=ctypes.addressof(st))
        frame = reader.read_live_frame()
        self.assertEqual(frame["mode"], "live")
        self.assertLessEqual(len(frame["allies"]), 3)
        self.assertGreaterEqual(len(frame["enemies"]), 20)
        self.assertEqual(len([a for a in frame["allies"] if a["type"] == "coop"]), 0)

    def test_rebel_entity_d0_faction_and_offscreen_retention(self) -> None:
        import ctypes
        from grw_memory import TELEMETRY_MAGIC

        now_ms = int(ctypes.windll.kernel32.GetTickCount64())
        st = GRWTelemetryState()
        st.magic = TELEMETRY_MAGIC
        st.version = TELEMETRY_VERSION
        st.hooks_mask = 1
        st.build_matched = 1
        st.cam_valid = 1
        st.cam_last_ms = now_ms
        st.cam_fwd[1] = 1.0
        st.local_player_entity = 0x1000
        st.local_player_skel = 0x2000

        p = st.chars[0]
        p.entity_ptr = 0x1000
        p.skel_ptr = 0x2000
        p.valid_flags = 3
        p.last_seen_ms = now_ms

        # Rebelde Kataris 26 com arma equipada e faction_raw=0, Entity+0xD0=0x1d1a (bits 10..13 = 7 -> 7-1 = 6 = Rebel)
        # e visto há 2100ms (fora do frustum da câmera com throttling de LOD)
        reb = st.chars[1]
        reb.entity_ptr = 0x3000
        reb.skel_ptr = 0x4000
        reb.valid_flags = 3
        reb.last_seen_ms = now_ms - 2100
        reb.faction_raw = 0
        reb.faction_1e8 = -1
        reb.alert_raw = 1
        reb.ent_u32[31] = 0x1D1A  # (fbits - 1) == 6 (Kataris 26 Rebel)
        reb.root_pos[0], reb.root_pos[1], reb.root_pos[2] = 25.0, 30.0, 100.0
        reb.head_pos[0], reb.head_pos[1], reb.head_pos[2] = 25.0, 30.0, 101.6

        # Caso regressão v1.3.0: mesmo se subcomponente secundário trouxer 3 (MexCartel), Entity+0xD0=0x21d1a (Rebelde) deve vencer!
        reb2 = st.chars[2]
        reb2.entity_ptr = 0x3001
        reb2.skel_ptr = 0x4001
        reb2.valid_flags = 3
        reb2.last_seen_ms = now_ms
        reb2.faction_raw = 3  # Santa Blanca em campo secundário
        reb2.faction_1e8 = 3
        reb2.alert_raw = 1
        reb2.ent_u32[31] = 0x21D1A  # Entity::GetFaction = 6 (Rebel)
        reb2.root_pos[0], reb2.root_pos[1], reb2.root_pos[2] = 35.0, 40.0, 100.0
        reb2.head_pos[0], reb2.head_pos[1], reb2.head_pos[2] = 35.0, 40.0, 101.6

        w = st.weapons[0]
        w.weapon_ptr = 0x9000
        w.gun_root_owner = 0x3000
        w.last_seen_ms = now_ms

        with tempfile.TemporaryDirectory() as td:
            dump_path = Path(td) / "probe.json"
            reader = GRWLiveReader(telemetry_ptr=ctypes.addressof(st), probe_dump_path=dump_path)
            self.assertEqual(
                reader._classify_character(reb2, 0x1000, 0x2000, {0x3000: w}, 0, 0, set()),
                "rebel",
            )
            frame = reader.read_live_frame()
            self.assertEqual(len(frame["rebels"]), 2)
            self.assertTrue(all(r["faction"] == "rebel" for r in frame["rebels"]))
            self.assertEqual(len(frame["enemies"]), 0)
            self.assertTrue(dump_path.is_file())
            dump_obj = json.loads(dump_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(dump_obj["chars_count"], 3)
            self.assertTrue(any(row["classified_faction"] == "rebel" for row in dump_obj["chars"]))

    def test_trail_arming_and_teleport_break(self) -> None:
        import ctypes
        from grw_memory import TELEMETRY_MAGIC

        now_ms = int(ctypes.windll.kernel32.GetTickCount64())
        st = GRWTelemetryState()
        st.magic = TELEMETRY_MAGIC
        st.version = TELEMETRY_VERSION
        st.hooks_mask = 1
        st.build_matched = 1
        st.cam_valid = 1
        st.cam_last_ms = now_ms
        st.cam_fwd[1] = 1.0
        st.local_player_entity = 0x1000
        st.local_player_skel = 0x2000

        p = st.chars[0]
        p.entity_ptr = 0x1000
        p.skel_ptr = 0x2000
        p.valid_flags = 1
        p.last_seen_ms = now_ms
        p.faction_raw = 3

        reader = GRWLiveReader(telemetry_ptr=ctypes.addressof(st))

        # 1) Posições iniciais de carregamento não armam a trilha
        for x in (100.0, 102.0):
            p.root_pos[0], p.root_pos[1], p.root_pos[2] = x, 100.0, 50.0
            p.head_pos[0], p.head_pos[1], p.head_pos[2] = x, 100.0, 51.6
            fr = reader.read_live_frame()
            self.assertEqual(len(fr["trail"]), 0)

        # 2) Salto grande (>45m) de teleporte/fast travel NÃO grava traço cruzando o mapa
        p.root_pos[0], p.root_pos[1], p.root_pos[2] = 500.0, 500.0, 50.0
        p.head_pos[0], p.head_pos[1], p.head_pos[2] = 500.0, 500.0, 51.6
        fr = reader.read_live_frame()
        self.assertEqual(len(fr["trail"]), 0)

        # 3) Após 3 passos firmes, a trilha arma e passa a gravar novos pontos a cada >= 6m
        for dx in (504.0, 508.0, 512.0, 519.0, 526.0):
            p.root_pos[0], p.root_pos[1], p.root_pos[2] = dx, 500.0, 50.0
            p.head_pos[0], p.head_pos[1], p.head_pos[2] = dx, 500.0, 51.6
            fr = reader.read_live_frame()
        self.assertGreaterEqual(len(fr["trail"]), 2)

        # 4) Novo teleporte grande marca "brk": True quando o jogador voltar a andar
        p.root_pos[0], p.root_pos[1], p.root_pos[2] = -200.0, -200.0, 50.0
        p.head_pos[0], p.head_pos[1], p.head_pos[2] = -200.0, -200.0, 51.6
        reader.read_live_frame()
        for dx in (-196.0, -192.0, -188.0, -181.0):
            p.root_pos[0], p.root_pos[1], p.root_pos[2] = dx, -200.0, 50.0
            p.head_pos[0], p.head_pos[1], p.head_pos[2] = dx, -200.0, 51.6
            fr = reader.read_live_frame()
        self.assertTrue(any(pt.get("brk") for pt in fr["trail"]))

    def test_synthetic_encrypted_save_roundtrip_and_sync(self) -> None:
        import struct
        import grw_save_sync as gs

        vid_prov = 0x79D290B79C
        vid_boss = 0x79D290B7AA
        vid_att_ak = 0x111122223333
        vid_wp_tar = 0x111122224444
        vid_wp_llam = 0x111122225555
        vid_doc_av = 0x79FB146095
        vid_skill_av = 0x118FEB6067A
        vid_medal_av = 648457331000

        # Chunk campanha 0x1FE25FCB
        chunk_camp = (
            struct.pack("<Q", vid_prov)
            + b"\x00\x00\x1d\x00\x0b\x01"
            + struct.pack("<I", 1)
            + b"\x01"
            + b"\x00" * 16
            + struct.pack("<Q", vid_boss)
            + b"\x19\x00\x0b"
            + struct.pack("<I", 2)
            + b"\x00" * 12
        )
        # Chunk inventário 0x8A9136AA
        chunk_inv = (
            b"\x00\x00\x12\x00\x0b"
            + struct.pack("<Q", vid_att_ak)
            + b"\x00" * 12
            + struct.pack("<Q", vid_wp_tar)
            + b"\x00" * 12
            + struct.pack("<Q", vid_wp_llam)
            + b"\x00" * 12
        )
        # Chunk pickups 0x8C28B28A (medalha + ponto de habilidade) e chunk state list 0x42709AEA (documento Kingslayer)
        chunk_pickups = b"\x00" * 12 + b"\x9d\x04\x0b\x01" + struct.pack("<I2Q", 2, vid_skill_av, vid_medal_av)
        chunk_docs = b"\x00" * 12 + b"\x9d\x04\x0b\x01" + struct.pack("<I1Q", 1, vid_doc_av)

        def _wrap_chunk(cid: int, data: bytes) -> bytes:
            return (
                struct.pack("<II", cid, len(data))
                + gs.GRW_CHUNK_MAGIC_BYTES
                + b"\x00" * 7
                + struct.pack("<BIII", 0, len(data), len(data), 0)
                + data
            )

        plaintext = (
            _wrap_chunk(gs.CID_CAMPAIGN_PROGRESS, chunk_camp)
            + _wrap_chunk(gs.CID_INVENTORY_UNLOCKS, chunk_inv)
            + _wrap_chunk(gs.CID_WORLD_PICKUPS, chunk_pickups)
            + _wrap_chunk(gs.CID_WORLD_STATE_LIST, chunk_docs)
        )
        enc = gs.encrypt_grw_payload(plaintext, seed1=54321, seed2=98765, bsz=16)
        # Simula cabeçalho Ubisoft de 552 bytes (.save)
        header = struct.pack("<I", 548) + b"\x00" * 548
        save_bytes = header + enc

        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            sf = tp / "slot_test.save"
            sf.write_bytes(save_bytes)

            sync = gs.AutoProgressSync(live_saves_dir=tp / "empty_live")
            sync._forge_ids = {
                "table1_missions": {str(vid_prov): "AguaVerde-INF_06", str(vid_boss): "INF_06_M060_Boss"},
                "table2_items": {
                    str(vid_att_ak): "BarrelAttachment_LongBarrel_ASR_AK47",
                    str(vid_wp_tar): "ASR_TAR21",
                    str(vid_wp_llam): "LEG_LMG_KRYTAC_LLAMATIVO",
                },
                "table3_docs": {str(vid_doc_av): "DBCollectibleDescriptor_06_000"},
            }
            sync._t1_missions = {vid_prov: "AguaVerde-INF_06", vid_boss: "INF_06_M060_Boss"}
            sync._t1_lo4 = {
                vid_prov & 0xFFFFFFFF: [(vid_prov, "AguaVerde-INF_06")],
                vid_boss & 0xFFFFFFFF: [(vid_boss, "INF_06_M060_Boss")],
            }
            sync._t2_items = {
                vid_att_ak: "BarrelAttachment_LongBarrel_ASR_AK47",
                vid_wp_tar: "ASR_TAR21",
                vid_wp_llam: "LEG_LMG_KRYTAC_LLAMATIVO",
            }
            sync._t3_docs = {vid_doc_av: "DBCollectibleDescriptor_06_000"}
            sync._t2_lo4 = {}
            for k, v in sync._t2_items.items():
                sync._t2_lo4.setdefault(k & 0xFFFFFFFF, []).append((k, v))
            wm_col = {
                "documents": [{"id": "ks_agua_verde_01", "vid": vid_doc_av, "gbs_name": "DBCollectibleDescriptor_06_000", "province": "agua_verde", "u": 0.6785, "v": 0.2442}],
                "skill_points": [{"id": "skill_agua_verde_01", "vid": vid_skill_av, "province": "agua_verde", "tier": "DBLootConfig_Easy_AvatarUpgradePoints", "u": 0.5327, "v": 0.319}],
            }
            m_pt, _, ct = build_static_databases("pt-BR", wm_collectibles=wm_col)
            sync._provinces = ct["provinces"]
            sync.set_context(pois=m_pt["pois"])
            sync._catalog_loaded = True

            prog, changed = sync.sync_disk_saves({}, save_paths=[sf], force=True)
            self.assertTrue(changed)
            self.assertIn("agua_verde", prog["discovered_provinces"])
            self.assertIn("agua_verde", prog["defeated_bosses"])
            self.assertIn("att_ar_long_barrel", prog["collected_items"])
            self.assertIn("wp_tar21", prog["collected_items"])
            self.assertIn("wp_llamativo", prog["collected_items"])
            self.assertIn("med_rebel_icon", prog["collected_items"])
            self.assertIn("poi_med_rebel_icon", prog["completed_pois"])
            self.assertIn("ks_agua_verde_01", prog["completed_pois"])
            self.assertIn("skill_agua_verde_01", prog["completed_pois"])
            self.assertNotIn("wp_ak47", prog["collected_items"])

    @unittest.skipUnless(
        USER_SAVE_4.is_file() and (WILDLANDS_DIR / "DataPC_patch_01.forge").is_file(),
        "Saves locais Ubisoft / Wildlands ausentes",
    )
    def test_real_wildlands_saves_sync(self) -> None:
        import grw_asset_builder as ab
        import grw_save_sync as gs

        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            fa = ForgeArchive(WILDLANDS_DIR / "DataPC.forge")
            fids = ab._build_forge_ids_index(fa, game_dir=WILDLANDS_DIR)
            map_data, catalog_data, cartel_data = build_static_databases("pt-BR", wm_collectibles=fids.get("wm_collectibles"))

            fjson = tp / "forge_ids.json"
            cjson = tp / "cartel.json"
            mjson = tp / "map_data.json"
            kjson = tp / "catalog.json"
            fjson.write_text(json.dumps(fids), encoding="utf-8")
            cjson.write_text(json.dumps(cartel_data), encoding="utf-8")
            mjson.write_text(json.dumps(map_data), encoding="utf-8")
            kjson.write_text(json.dumps(catalog_data), encoding="utf-8")

            old_paths = (gs.FORGE_IDS_PATH, gs.CARTEL_PATH, gs.MAP_DATA_PATH, gs.CATALOG_PATH)
            gs.FORGE_IDS_PATH, gs.CARTEL_PATH, gs.MAP_DATA_PATH, gs.CATALOG_PATH = fjson, cjson, mjson, kjson
            try:
                sync = gs.AutoProgressSync(live_saves_dir=tp / "live", game_dir=WILDLANDS_DIR)
                prog, changed = sync.sync_disk_saves({}, force=True)
                self.assertTrue(changed)
                for b in ("agua_verde", "ocoro", "itacua", "pucara", "malca"):
                    self.assertIn(b, prog["defeated_bosses"])
                self.assertIn("espiritu_santo", prog["discovered_provinces"])
                self.assertNotIn("espiritu_santo", prog["defeated_bosses"])
                for und in ("barvechos", "media_luna"):
                    self.assertNotIn(und, prog["discovered_provinces"])
                for item in ("wp_llamativo", "wp_sr3m", "att_panoramic", "med_rebel_icon", "med_no_pain"):
                    self.assertIn(item, prog["collected_items"])
                # Todos os 11 documentos e 7 pontos de habilidade de Agua Verde devem estar sincronizados
                for idx in range(1, 12):
                    self.assertIn(f"ks_agua_verde_{idx:02d}", prog["completed_pois"])
                for idx in range(1, 8):
                    self.assertIn(f"skill_agua_verde_{idx:02d}", prog["completed_pois"])

                # Itacua deve ter exatamente 34 itens de campanha sincronizados (6/10/3/5/8/2)
                it_p = next(p for p in cartel_data["provinces"] if p["id"] == "itacua")
                it_t = it_p["tasks"]
                self.assertEqual(len(it_t["missions"]), 6)
                self.assertEqual(len(it_t["kingslayer"]), 10)
                self.assertEqual(len(it_t["weapons"]), 3)
                self.assertEqual(len(it_t["attachments"]), 5)
                self.assertEqual(len(it_t["skill_points"]), 8)
                self.assertEqual(len(it_t["medals"]), 2)
                self.assertTrue(all(m["id"] in prog["completed_missions"] for m in it_t["missions"]))
                self.assertTrue(all(k["poi_id"] in prog["completed_pois"] for k in it_t["kingslayer"]))
                self.assertTrue(all(w["item_id"] in prog["collected_items"] for w in it_t["weapons"]))
                self.assertTrue(all(a["item_id"] in prog["collected_items"] for a in it_t["attachments"]))
                self.assertTrue(all(s["poi_id"] in prog["completed_pois"] for s in it_t["skill_points"]))
                self.assertTrue(all(md["item_id"] in prog["collected_items"] for md in it_t["medals"]))

                # Espíritu Santo não deve ter falso-positivo de pontos de habilidade nem da medalha Quiet Running
                es_p = next(p for p in cartel_data["provinces"] if p["id"] == "espiritu_santo")
                es_t = es_p["tasks"]
                self.assertEqual(len(es_t["skill_points"]), 6)
                self.assertTrue(all(s["poi_id"] not in prog["completed_pois"] for s in es_t["skill_points"]))
                self.assertNotIn("med_quiet_run", prog["collected_items"])
            finally:
                gs.FORGE_IDS_PATH, gs.CARTEL_PATH, gs.MAP_DATA_PATH, gs.CATALOG_PATH = old_paths


if __name__ == "__main__":
    unittest.main()
