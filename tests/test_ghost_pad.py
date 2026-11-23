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
from grw_asset_builder import ensure_cache_built
from grw_catalog_db import ATTACHMENTS_DB, BONUS_MEDALS, PROVINCES, WEAPON_ACOUSTICS, WEAPONS_DB, build_static_databases
from grw_memory import GRWLiveReader
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


class TestServerAndPersistence(unittest.TestCase):
    def test_http_server_routes_and_settings_roundtrip(self) -> None:
        import time
        import threading
        import urllib.request
        from server import create_server

        srv, runtime = create_server(game_dir=WILDLANDS_DIR, port=0, lan=False)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        base = f"http://127.0.0.1:{runtime.port}"
        try:
            # Aguarda cache pronto
            for _ in range(40):
                st = json.loads(urllib.request.urlopen(f"{base}/api/status", timeout=5).read().decode())
                if st["build"]["state"] == "ready":
                    break
                time.sleep(0.15)
            self.assertEqual(st["build"]["state"], "ready")

            # Testa persistência completa das opções customizadas
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
            }
            req = urllib.request.Request(
                f"{base}/api/settings",
                data=json.dumps({"ui_prefs": custom}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            post_res = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            self.assertTrue(post_res["ok"])
            got = json.loads(urllib.request.urlopen(f"{base}/api/settings", timeout=5).read().decode())
            for k, v in custom.items():
                self.assertEqual(got["ui_prefs"][k], v)

            # Testa HTML, estáticos e tiles satélite + heatmap
            html = urllib.request.urlopen(f"{base}/", timeout=5).read().decode()
            self.assertIn("GHOST TACTICAL PAD", html)
            cat = json.loads(urllib.request.urlopen(f"{base}/api/static/catalog", timeout=5).read().decode())
            self.assertGreaterEqual(len(cat["weapons"]), 55)
            if WILDLANDS_DIR.is_dir():
                t_sat = urllib.request.urlopen(f"{base}/api/tile/satellite/6/0/0.png", timeout=5).read()
                t_heat = urllib.request.urlopen(f"{base}/api/tile/heatmap/6/0/0.png", timeout=5).read()
                self.assertTrue(t_sat.startswith(b"\x89PNG"))
                self.assertTrue(t_heat.startswith(b"\x89PNG"))
        finally:
            runtime.close()
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
