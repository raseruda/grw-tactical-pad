"""Motor de análise tática furtiva: acústica de armas, campo de visão inimigo e testemunhas para Player e Aliados."""
from __future__ import annotations

import math
from typing import Any

from anvil_formats import HeightmapSampler
from grw_catalog_db import WEAPON_ACOUSTICS


def _dist3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _norm3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if l < 1e-9:
        return (0.0, 1.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)


def _dot3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _clamp_deg_from_cos(c: float) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def _pos3(obj: dict[str, Any], use_head: bool = True) -> tuple[float, float, float]:
    if use_head and obj.get("head") and len(obj["head"]) == 3:
        h = obj["head"]
        return float(h[0]), float(h[1]), float(h[2])
    return float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), float(obj.get("z", 0.0)) + (1.6 if use_head else 0.0)


def resolve_gunshot_radius(
    weapon_class: str | None,
    suppressed: bool | None,
    override_class: str = "auto",
    override_sup: str = "auto",
    fallback_suppressed: bool = True,
) -> tuple[float, str, bool]:
    """Calcula alcance real de detecção sonora do disparo em metros segundo a classe e silenciador."""
    cls = override_class if override_class in WEAPON_ACOUSTICS else (weapon_class if weapon_class in WEAPON_ACOUSTICS else "ar")
    if override_sup == "suppressed":
        sup = True
    elif override_sup == "unsuppressed":
        sup = False
    elif suppressed is not None:
        sup = bool(suppressed)
    else:
        sup = bool(fallback_suppressed)
    ac = WEAPON_ACOUSTICS[cls]
    return (ac["suppressed_m"] if sup else ac["unsuppressed_m"]), cls, sup


def evaluate_safe_fire(
    player: dict[str, Any] | None,
    enemies: list[dict[str, Any]],
    prefs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Avalia se disparar a arma equipada agora pode ser ouvido por algum inimigo próximo."""
    p = prefs or {}
    if not player:
        return {"safe": True, "hear_radius_m": 0.0, "weapon_class": "ar", "suppressed": True, "listener_count": 0, "listeners": []}

    radius_m, wclass, sup = resolve_gunshot_radius(
        player.get("weapon_class"),
        player.get("suppressed"),
        str(p.get("weaponOverrideClass") or "auto"),
        str(p.get("weaponOverrideSuppressed") or "auto"),
        fallback_suppressed=True,
    )
    ppos = _pos3(player, use_head=False)
    listeners: list[dict[str, Any]] = []
    for en in enemies:
        if not en.get("alive", True):
            continue
        epos = _pos3(en, use_head=False)
        d = _dist3(ppos, epos)
        # Inimigos já em alerta ("suspected"/"hunted") ganham ~5m extras de percepção auditiva no GRW
        alert_bonus = 5.0 if en.get("alert") in ("suspected", "hunted", "engaged") else 0.0
        if d <= radius_m + alert_bonus:
            listeners.append({
                "id": en["id"],
                "dist_m": round(d, 1),
                "faction": en.get("faction", "santa_blanca"),
                "alert": en.get("alert", "unaware"),
                "u": en.get("u"),
                "v": en.get("v"),
            })
    listeners.sort(key=lambda x: x["dist_m"])
    return {
        "safe": len(listeners) == 0,
        "hear_radius_m": radius_m,
        "weapon_class": wclass,
        "suppressed": sup,
        "listener_count": len(listeners),
        "listeners": listeners[:24],
    }


def _find_aimed_enemy(
    aim_origin: tuple[float, float, float],
    aim_dir: tuple[float, float, float],
    enemies: list[dict[str, Any]],
    cone_deg: float,
    max_range_m: float = 350.0,
    heightmap: HeightmapSampler | None = None,
    use_terrain_los: bool = True,
) -> dict[str, Any] | None:
    """Seleciona o inimigo mais alinhado dentro do cone angular da mira do atirador."""
    adir = _norm3(aim_dir)
    best: tuple[float, float, dict[str, Any]] | None = None
    for en in enemies:
        if not en.get("alive", True):
            continue
        for target_pt in (_pos3(en, use_head=True), _pos3(en, use_head=False)):
            vec = (target_pt[0] - aim_origin[0], target_pt[1] - aim_origin[1], target_pt[2] - aim_origin[2])
            dist = math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)
            if dist < 1.2 or dist > max_range_m:
                continue
            udir = (vec[0] / dist, vec[1] / dist, vec[2] / dist)
            ang = _clamp_deg_from_cos(_dot3(adir, udir))
            # Margem ligeiramente maior a curtíssima distância (<12m) por largura do tronco/cabeça
            effective_cone = cone_deg + (1.5 if dist < 12.0 else 0.0)
            if ang <= effective_cone:
                if use_terrain_los and heightmap and heightmap.has_data():
                    if not heightmap.has_terrain_los(aim_origin, target_pt):
                        continue
                score = ang + dist * 0.002
                if best is None or score < best[0]:
                    best = (score, dist, en)
    return best[2] if best else None


def _check_visual_witness(
    observer: dict[str, Any],
    target: dict[str, Any],
    vision_range_m: float,
    half_fov_deg: float,
    heightmap: HeightmapSampler | None,
    use_terrain_los: bool,
) -> dict[str, Any] | None:
    """Verifica se um inimigo observador vê outro inimigo sendo abatido."""
    obs_head = _pos3(observer, use_head=True)
    tgt_body = _pos3(target, use_head=True)
    vec = (tgt_body[0] - obs_head[0], tgt_body[1] - obs_head[1], tgt_body[2] - obs_head[2])
    dist = math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)
    if dist < 0.5 or dist > vision_range_m:
        return None

    obs_look = observer.get("look_dir")
    if not obs_look or len(obs_look) != 3:
        yaw_rad = math.radians(float(observer.get("yaw", 0.0)))
        obs_look = (math.sin(yaw_rad), math.cos(yaw_rad), 0.0)
    look_n = _norm3((float(obs_look[0]), float(obs_look[1]), float(obs_look[2])))
    dir_to_tgt = (vec[0] / dist, vec[1] / dist, vec[2] / dist)
    ang = _clamp_deg_from_cos(_dot3(look_n, dir_to_tgt))

    # Visão periférica próxima (< 14m) amplia levemente o cone lateral
    allowed_half = max(half_fov_deg, 75.0) if dist <= 14.0 else half_fov_deg
    if ang > allowed_half:
        return None

    # Oclusão por elevação/terreno 3D
    if use_terrain_los:
        if heightmap and heightmap.has_data():
            if not heightmap.has_terrain_los(obs_head, tgt_body):
                return None
        # Diferença vertical extrema com linha de visão muito inclinada (> 60°) costuma estar separada por laje/telhado/penhasco
        if abs(vec[2]) > 7.5 and abs(vec[2]) / max(1.0, math.hypot(vec[0], vec[1])) > 1.6:
            return None

    return {
        "id": observer["id"],
        "dist_m": round(dist, 1),
        "angle_deg": round(ang, 1),
        "faction": observer.get("faction", "santa_blanca"),
        "u": observer.get("u"),
        "v": observer.get("v"),
    }


def evaluate_aim_shot(
    shooter: dict[str, Any],
    enemies: list[dict[str, Any]],
    heightmap: HeightmapSampler | None = None,
    prefs: dict[str, Any] | None = None,
    is_ally: bool = False,
) -> dict[str, Any] | None:
    """Analisa se o inimigo na mira de `shooter` causará detecção por som ou testemunha visual."""
    p = prefs or {}
    if not shooter.get("is_aiming", False):
        return None
    aim_dir_raw = shooter.get("aim_dir")
    if not aim_dir_raw or len(aim_dir_raw) != 3:
        return None

    origin_raw = shooter.get("aim_origin")
    if origin_raw and len(origin_raw) == 3:
        aim_origin = (float(origin_raw[0]), float(origin_raw[1]), float(origin_raw[2]))
    else:
        aim_origin = _pos3(shooter, use_head=True)
    aim_dir = (float(aim_dir_raw[0]), float(aim_dir_raw[1]), float(aim_dir_raw[2]))

    use_terrain = bool(p.get("useTerrainLos", True))
    cone_deg = float(p.get("allyAimConeDeg", 3.5) if is_ally else p.get("aimConeDeg", 2.8))
    target = _find_aimed_enemy(
        aim_origin,
        aim_dir,
        enemies,
        cone_deg=cone_deg,
        max_range_m=350.0,
        heightmap=heightmap,
        use_terrain_los=use_terrain,
    )
    if target is None:
        return None

    if is_ally:
        hear_radius_m, wclass, sup = resolve_gunshot_radius(
            shooter.get("weapon_class"),
            shooter.get("suppressed"),
            fallback_suppressed=bool(p.get("allyAssumedSuppressed", True)),
        )
    else:
        hear_radius_m, wclass, sup = resolve_gunshot_radius(
            shooter.get("weapon_class"),
            shooter.get("suppressed"),
            str(p.get("weaponOverrideClass") or "auto"),
            str(p.get("weaponOverrideSuppressed") or "auto"),
            fallback_suppressed=True,
        )

    impact_noise_m = max(0.0, float(p.get("bulletImpactNoiseM", 12.0)))
    vision_range_m = max(10.0, float(p.get("enemyVisionRangeM", 55.0)))
    half_fov_deg = max(15.0, min(85.0, float(p.get("enemyFovDeg", 110.0)) * 0.5))

    s_pos = _pos3(shooter, use_head=False)
    t_pos = _pos3(target, use_head=False)
    shot_dist = _dist3(s_pos, t_pos)

    sound_witnesses: list[dict[str, Any]] = []
    visual_witnesses: list[dict[str, Any]] = []

    for en in enemies:
        if not en.get("alive", True) or en.get("id") == target.get("id"):
            continue
        e_pos = _pos3(en, use_head=False)
        alert_bonus = 5.0 if en.get("alert") in ("suspected", "hunted", "engaged") else 0.0

        d_gun = _dist3(s_pos, e_pos)
        d_imp = _dist3(t_pos, e_pos)
        heard_gun = d_gun <= (hear_radius_m + alert_bonus)
        heard_imp = impact_noise_m > 0.0 and d_imp <= (impact_noise_m + alert_bonus * 0.5)
        if heard_gun or heard_imp:
            sound_witnesses.append({
                "id": en["id"],
                "dist_m": round(d_gun if heard_gun else d_imp, 1),
                "reason": "gunshot" if heard_gun else "impact",
                "faction": en.get("faction", "santa_blanca"),
                "u": en.get("u"),
                "v": en.get("v"),
            })

        vis = _check_visual_witness(en, target, vision_range_m, half_fov_deg, heightmap, use_terrain)
        if vis is not None:
            visual_witnesses.append(vis)

    sound_witnesses.sort(key=lambda x: x["dist_m"])
    visual_witnesses.sort(key=lambda x: x["dist_m"])

    has_sound = len(sound_witnesses) > 0
    has_vis = len(visual_witnesses) > 0
    if has_sound and has_vis:
        verdict = "critical"
    elif has_vis:
        verdict = "visual_risk"
    elif has_sound:
        verdict = "sound_risk"
    else:
        verdict = "safe"

    return {
        "shooter_id": shooter.get("id", "player"),
        "shooter_name": shooter.get("name", "Ghost"),
        "shooter_type": shooter.get("type", "player"),
        "shooter_u": shooter.get("u"),
        "shooter_v": shooter.get("v"),
        "target_id": target["id"],
        "target_faction": target.get("faction", "santa_blanca"),
        "target_u": target.get("u"),
        "target_v": target.get("v"),
        "shot_dist_m": round(shot_dist, 1),
        "weapon_class": wclass,
        "suppressed": sup,
        "hear_radius_m": hear_radius_m,
        "impact_noise_m": impact_noise_m,
        "verdict": verdict,
        "sound_witness_count": len(sound_witnesses),
        "visual_witness_count": len(visual_witnesses),
        "sound_witnesses": sound_witnesses[:16],
        "visual_witnesses": visual_witnesses[:16],
    }


def analyze_tactical_state(
    live_frame: dict[str, Any],
    heightmap: HeightmapSampler | None = None,
    prefs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Executa toda a análise tática (arma equipada, mira do jogador e mira dos aliados Solo/Co-op)."""
    p = prefs or {}
    player = live_frame.get("player")
    enemies = live_frame.get("enemies") or []
    allies = live_frame.get("allies") or []

    safe_fire = evaluate_safe_fire(player, enemies, p)

    player_aim = None
    if player and p.get("showPlayerAimWarning", True):
        player_aim = evaluate_aim_shot(player, enemies, heightmap=heightmap, prefs=p, is_ally=False)

    show_solo = bool(p.get("showAlliesSolo", True))
    show_coop = bool(p.get("showAlliesCoop", True))
    filtered_allies: list[dict[str, Any]] = []
    ally_aims: list[dict[str, Any]] = []

    for ally in allies:
        atype = ally.get("type", "ai")
        if atype == "ai" and not show_solo:
            continue
        if atype == "coop" and not show_coop:
            continue
        filtered_allies.append(ally)
        if p.get("showAllyAimWarning", True):
            res = evaluate_aim_shot(ally, enemies, heightmap=heightmap, prefs=p, is_ally=True)
            if res is not None:
                ally_aims.append(res)

    return {
        "safe_fire": safe_fire,
        "player_aim": player_aim,
        "ally_aims": ally_aims,
        "visible_allies": filtered_allies,
    }
