"""Leitor de telemetria ao vivo da memória de GRW.exe (in-process via winmm.dll) e classificador de entidades."""
from __future__ import annotations

import ctypes
import math
import os
import threading
import time
from ctypes import wintypes
from typing import Any

MAX_CHARS = 512
MAX_WEAPONS = 64
TELEMETRY_MAGIC = 0x47525754

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class GRWCharSlot(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("skel_ptr", ctypes.c_uint64),
        ("entity_ptr", ctypes.c_uint64),
        ("rig_ptr", ctypes.c_uint64),
        ("pose_ptr", ctypes.c_uint64),
        ("entity_vtable", ctypes.c_uint64),
        ("last_seen_ms", ctypes.c_uint64),
        ("bone_count", ctypes.c_uint32),
        ("rig_map_count", ctypes.c_uint32),
        ("head_idx", ctypes.c_int32),
        ("rhand_idx", ctypes.c_int32),
        ("lhand_idx", ctypes.c_int32),
        ("hips_idx", ctypes.c_int32),
        ("pose_flags", ctypes.c_uint32),
        ("valid_flags", ctypes.c_uint32),
        ("root_pos", ctypes.c_float * 4),
        ("root_quat", ctypes.c_float * 4),
        ("head_pos", ctypes.c_float * 4),
        ("head_quat", ctypes.c_float * 4),
        ("rhand_pos", ctypes.c_float * 4),
        ("lhand_pos", ctypes.c_float * 4),
        ("hips_pos", ctypes.c_float * 4),
        ("ent_u32", ctypes.c_uint32 * 32),
    ]


class GRWWeaponSlot(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("weapon_ptr", ctypes.c_uint64),
        ("essence_ptr", ctypes.c_uint64),
        ("gun_root_owner", ctypes.c_uint64),
        ("muzzle_owner", ctypes.c_uint64),
        ("attachment_holder", ctypes.c_uint64),
        ("last_seen_ms", ctypes.c_uint64),
        ("weapon_category", ctypes.c_uint32),
        ("shoot_mode", ctypes.c_uint32),
        ("gun_root_idx", ctypes.c_int32),
        ("muzzle_idx", ctypes.c_int32),
        ("max_range", ctypes.c_float),
        ("muzzle_velocity", ctypes.c_float),
        ("extra_u32", ctypes.c_uint32 * 16),
    ]


class GRWTelemetryState(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("pe_timestamp", ctypes.c_uint32),
        ("pe_size_of_image", ctypes.c_uint32),
        ("module_base", ctypes.c_uint64),
        ("hooks_mask", ctypes.c_uint32),
        ("build_matched", ctypes.c_uint32),
        ("frame_tick", ctypes.c_uint64),
        ("hook_calls", ctypes.c_uint64 * 8),
        ("local_player_comp", ctypes.c_uint64),
        ("local_player_entity", ctypes.c_uint64),
        ("local_player_skel", ctypes.c_uint64),
        ("cam_ptr", ctypes.c_uint64),
        ("cam_mode", ctypes.c_uint32),
        ("cam_valid", ctypes.c_uint32),
        ("cam_vfov", ctypes.c_float),
        ("cam_fov_proj", ctypes.c_float),
        ("cam_pos", ctypes.c_float * 3),
        ("cam_right", ctypes.c_float * 3),
        ("cam_up", ctypes.c_float * 3),
        ("cam_fwd", ctypes.c_float * 3),
        ("cam_last_ms", ctypes.c_uint64),
        ("chars", GRWCharSlot * MAX_CHARS),
        ("weapons", GRWWeaponSlot * MAX_WEAPONS),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.GetTickCount64.restype = ctypes.c_uint64
_kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_kernel32.Process32FirstW.restype = wintypes.BOOL
_kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_kernel32.Process32NextW.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL


def find_grw_pid() -> int | None:
    """Retorna o PID de GRW.exe se estiver em execução."""
    if os.path.basename(os.sys.executable).lower() == "grw.exe":
        return os.getpid()
    snap = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return None
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not _kernel32.Process32FirstW(snap, ctypes.byref(pe)):
            return None
        while True:
            if pe.szExeFile.lower() == "grw.exe":
                return int(pe.th32ProcessID)
            if not _kernel32.Process32NextW(snap, ctypes.byref(pe)):
                break
        return None
    finally:
        _kernel32.CloseHandle(snap)


def _quat_rotate(q: tuple[float, float, float, float], v: tuple[float, float, float]) -> tuple[float, float, float]:
    qx, qy, qz, qw = q
    n2 = qx * qx + qy * qy + qz * qz + qw * qw
    if n2 < 1e-12:
        return v
    inv = 1.0 / math.sqrt(n2)
    qx *= inv
    qy *= inv
    qz *= inv
    qw *= inv
    tx = 2.0 * (qy * v[2] - qz * v[1])
    ty = 2.0 * (qz * v[0] - qx * v[2])
    tz = 2.0 * (qx * v[1] - qy * v[0])
    return (
        v[0] + qw * tx + (qy * tz - qz * ty),
        v[1] + qw * ty + (qz * tx - qx * tz),
        v[2] + qw * tz + (qx * ty - qy * tx),
    )


def _norm3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if l < 1e-9 or not math.isfinite(l):
        return (0.0, 1.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)


def _vec_to_yaw_deg(v: tuple[float, float, float]) -> float:
    """Converte vetor direção (x=Leste, y=Norte no Anvil Z-up) em azimute graus (0=Norte, 90=Leste)."""
    return math.degrees(math.atan2(v[0], v[1])) % 360.0


# Mapeamento provisório de m_eWeaponCategory (+0x17C) para classe acústica (calibrado em Step 4)
WEAPON_CATEGORY_MAP: dict[int, str] = {
    0: "ar",
    1: "ar",
    2: "smg",
    3: "lmg",
    4: "sniper",
    5: "shotgun",
    6: "pistol",
}


class GRWLiveReader:
    """Lê a estrutura compartilhada GRWTelemetryState sem bloqueio e classifica Player/Aliados/Inimigos."""

    def __init__(self, telemetry_ptr: int | None = None, world_bounds: dict[str, Any] | None = None) -> None:
        self.telemetry_ptr = telemetry_ptr
        self._state: GRWTelemetryState | None = None
        if telemetry_ptr and telemetry_ptr > 0x10000:
            self._state = GRWTelemetryState.from_address(telemetry_ptr)
        self._lock = threading.RLock()
        self.world_bounds = dict(world_bounds or {
            "min_x": -10500.0,
            "max_x": 10500.0,
            "min_y": -10500.0,
            "max_y": 10500.0,
            "invert_y": True,
        })
        self.head_local_axis: tuple[float, float, float] = (0.0, 1.0, 0.0)
        self._trail: list[dict[str, Any]] = []
        self._last_trail_xy: tuple[float, float] | None = None
        self._override_snapshot: dict[str, Any] | None = None

    def set_world_bounds(self, bounds: dict[str, Any]) -> None:
        with self._lock:
            self.world_bounds.update(bounds)

    def world_to_uv(self, wx: float, wy: float) -> tuple[float, float]:
        b = self.world_bounds
        dx = max(1.0, float(b["max_x"]) - float(b["min_x"]))
        dy = max(1.0, float(b["max_y"]) - float(b["min_y"]))
        u = (wx - float(b["min_x"])) / dx
        v = (wy - float(b["min_y"])) / dy
        if b.get("invert_y", True):
            v = 1.0 - v
        return max(0.0, min(1.0, u)), max(0.0, min(1.0, v))

    def set_simulated_frame(self, frame: dict[str, Any] | None) -> None:
        """Permite injetar cena sintética em testes unitários sem modificar a lógica do leitor."""
        with self._lock:
            self._override_snapshot = frame

    def get_debug_probe(self) -> dict[str, Any]:
        """Retorna dump diagnóstico bruto de câmera, player, esqueletos e armas para calibração."""
        st = self._state
        if st is None or st.magic != TELEMETRY_MAGIC:
            return {"status": "no_telemetry_ptr", "pid": find_grw_pid()}
        now_ms = int(_kernel32.GetTickCount64())
        chars = []
        for i in range(MAX_CHARS):
            c = st.chars[i]
            if c.skel_ptr == 0 or (now_ms - c.last_seen_ms) > 2500:
                continue
            chars.append({
                "slot": i,
                "skel": hex(c.skel_ptr),
                "entity": hex(c.entity_ptr),
                "rig": hex(c.rig_ptr),
                "vtable": hex(c.entity_vtable),
                "bones": int(c.bone_count),
                "map_cnt": int(c.rig_map_count),
                "age_ms": now_ms - int(c.last_seen_ms),
                "root": [round(float(x), 3) for x in c.root_pos[:3]],
                "head": [round(float(x), 3) for x in c.head_pos[:3]],
                "head_q": [round(float(x), 4) for x in c.head_quat[:4]],
                "rhand": [round(float(x), 3) for x in c.rhand_pos[:3]],
                "ent_u32_hex": [f"{int(x):08x}" for x in c.ent_u32[:16]],
            })
        weapons = []
        for i in range(MAX_WEAPONS):
            w = st.weapons[i]
            if w.weapon_ptr == 0 or (now_ms - w.last_seen_ms) > 2500:
                continue
            weapons.append({
                "slot": i,
                "weapon": hex(w.weapon_ptr),
                "essence": hex(w.essence_ptr),
                "gun_root_owner": hex(w.gun_root_owner),
                "muzzle_owner": hex(w.muzzle_owner),
                "att_holder": hex(w.attachment_holder),
                "category": int(w.weapon_category),
                "shoot_mode": int(w.shoot_mode),
                "max_range": round(float(w.max_range), 2),
                "muzzle_vel": round(float(w.muzzle_velocity), 2),
                "extra_u32_hex": [f"{int(x):08x}" for x in w.extra_u32[:12]],
            })
        return {
            "status": "ok",
            "build_matched": bool(st.build_matched),
            "pe_timestamp": hex(st.pe_timestamp),
            "pe_size_of_image": hex(st.pe_size_of_image),
            "module_base": hex(st.module_base),
            "hooks_mask": hex(st.hooks_mask),
            "frame_tick": int(st.frame_tick),
            "hook_calls": [int(x) for x in st.hook_calls[:5]],
            "local_player_entity": hex(st.local_player_entity),
            "local_player_skel": hex(st.local_player_skel),
            "cam": {
                "valid": bool(st.cam_valid),
                "mode": int(st.cam_mode),
                "vfov": round(float(st.cam_vfov), 4),
                "fov_proj": round(float(st.cam_fov_proj), 4),
                "pos": [round(float(x), 3) for x in st.cam_pos[:3]],
                "fwd": [round(float(x), 4) for x in st.cam_fwd[:3]],
            },
            "chars_active": len(chars),
            "chars": chars[:64],
            "weapons_active": len(weapons),
            "weapons": weapons[:32],
        }

    def _classify_character(
        self,
        c: GRWCharSlot,
        local_ent: int,
        local_skel: int,
        weapon_by_owner: dict[int, GRWWeaponSlot],
        player_vtable: int,
        player_rig: int,
    ) -> str:
        """Classifica entidade capturada em SkeletonPostUpdate para Player / Co-op / AI Ally / Inimigo."""
        if (local_ent and c.entity_ptr == local_ent) or (local_skel and c.skel_ptr == local_skel):
            return "player"
        has_weapon = (c.entity_ptr in weapon_by_owner) or (c.skel_ptr in weapon_by_owner)
        # Rig de jogador (Ghost ~312 bones) que não é o jogador local: aliado Co-op ou Squadmate IA
        is_ghost_rig = (player_rig and c.rig_ptr == player_rig) or c.bone_count >= 280
        if is_ghost_rig:
            if player_vtable and c.entity_vtable == player_vtable:
                return "ally_coop"
            return "ally_ai"
        if not has_weapon and c.bone_count < 140:
            return "civilian"
        return "enemy_sb"

    def read_live_frame(self) -> dict[str, Any]:
        """Lê o estado tático atual do jogo (ou status offline se GRW.exe não estiver rodando)."""
        with self._lock:
            if self._override_snapshot is not None:
                return dict(self._override_snapshot)

        st = self._state
        if st is None or st.magic != TELEMETRY_MAGIC:
            pid = find_grw_pid()
            return {
                "mode": "external" if pid else "offline",
                "status": "waiting_plugin" if pid else "offline",
                "pid": pid,
                "hooks_mask": 0,
                "player": None,
                "drone": None,
                "allies": [],
                "enemies": [],
                "trail": list(self._trail),
            }

        now_ms = int(_kernel32.GetTickCount64())
        hooks_mask = int(st.hooks_mask)
        cam_fresh = bool(st.cam_valid) and (now_ms - int(st.cam_last_ms)) < 2000

        if not hooks_mask or not cam_fresh:
            return {
                "mode": "title" if st.build_matched else "mismatch",
                "status": "title" if st.build_matched else "build_mismatch",
                "hooks_mask": hooks_mask,
                "build_matched": bool(st.build_matched),
                "player": None,
                "drone": None,
                "allies": [],
                "enemies": [],
                "trail": list(self._trail),
            }

        # Indexa armas ativas por dono (entity_ptr / skel_ptr)
        weapon_by_owner: dict[int, GRWWeaponSlot] = {}
        for i in range(MAX_WEAPONS):
            w = st.weapons[i]
            if w.weapon_ptr == 0 or (now_ms - int(w.last_seen_ms)) > 1500:
                continue
            if w.gun_root_owner:
                weapon_by_owner[int(w.gun_root_owner)] = w
            if w.muzzle_owner:
                weapon_by_owner[int(w.muzzle_owner)] = w

        local_ent = int(st.local_player_entity)
        local_skel = int(st.local_player_skel)

        # Na tela inicial / Ghost Room, local_player_entity==0 e não há armas ativas em mundo aberto
        if local_ent == 0 and local_skel == 0 and not weapon_by_owner:
            return {
                "mode": "title",
                "status": "ghost_room_or_menu",
                "hooks_mask": hooks_mask,
                "build_matched": bool(st.build_matched),
                "player": None,
                "drone": None,
                "allies": [],
                "enemies": [],
                "trail": list(self._trail),
            }

        # Identifica vtable e rig do jogador local primeiro
        player_slot: GRWCharSlot | None = None
        player_vtable = 0
        player_rig = 0
        active_slots: list[GRWCharSlot] = []
        for i in range(MAX_CHARS):
            c = st.chars[i]
            if c.skel_ptr == 0 or (now_ms - int(c.last_seen_ms)) > 1000:
                continue
            if not (c.valid_flags & 1):
                continue
            active_slots.append(c)
            if (local_ent and c.entity_ptr == local_ent) or (local_skel and c.skel_ptr == local_skel):
                player_slot = c
                player_vtable = int(c.entity_vtable)
                player_rig = int(c.rig_ptr)

        cam_pos = (float(st.cam_pos[0]), float(st.cam_pos[1]), float(st.cam_pos[2]))
        cam_fwd = _norm3((float(st.cam_fwd[0]), float(st.cam_fwd[1]), float(st.cam_fwd[2])))
        # Em matrizes de câmera OpenGL/Anvil, cam_fwd pode apontar -Z da câmera (ou +Z); normalizamos com sinal positivo para frente
        cam_fov = float(st.cam_fov_proj or st.cam_vfov or 0.85)
        is_ads = 0.05 < cam_fov < 0.72

        if player_slot is not None:
            px, py, pz = float(player_slot.root_pos[0]), float(player_slot.root_pos[1]), float(player_slot.root_pos[2])
            hx, hy, hz = (
                (float(player_slot.head_pos[0]), float(player_slot.head_pos[1]), float(player_slot.head_pos[2]))
                if (player_slot.valid_flags & 2)
                else (px, py, pz + 1.6)
            )
            pw = weapon_by_owner.get(int(player_slot.entity_ptr)) or weapon_by_owner.get(int(player_slot.skel_ptr))
        else:
            px, py, pz = cam_pos
            hx, hy, hz = cam_pos
            pw = None

        w_class = WEAPON_CATEGORY_MAP.get(int(pw.weapon_category), "ar") if pw else "ar"
        # Detecta silenciador via attachment_holder / extra flags (calibrado em Step 4; padrão True se categoria desconhecida)
        w_suppressed = bool(int(pw.extra_u32[2]) & 1) if (pw and int(pw.extra_u32[2]) != 0) else True

        pu, pv = self.world_to_uv(px, py)
        player_yaw = _vec_to_yaw_deg(cam_fwd)

        # Trilha da sessão
        with self._lock:
            if self._last_trail_xy is None or math.hypot(px - self._last_trail_xy[0], py - self._last_trail_xy[1]) >= 8.0:
                self._last_trail_xy = (px, py)
                self._trail.append({"u": round(pu, 5), "v": round(pv, 5), "x": round(px, 1), "y": round(py, 1), "z": round(pz, 1)})
                if len(self._trail) > 1500:
                    self._trail.pop(0)

        cam_dist = math.sqrt((cam_pos[0] - hx) ** 2 + (cam_pos[1] - hy) ** 2 + (cam_pos[2] - hz) ** 2)
        drone_obj = None
        if cam_dist > 5.0 and cam_dist < 450.0:
            du, dv = self.world_to_uv(cam_pos[0], cam_pos[1])
            drone_obj = {
                "x": round(cam_pos[0], 2),
                "y": round(cam_pos[1], 2),
                "z": round(cam_pos[2], 2),
                "u": round(du, 5),
                "v": round(dv, 5),
                "yaw": round(player_yaw, 1),
                "dist_m": round(cam_dist, 1),
            }

        player_obj = {
            "x": round(px, 2),
            "y": round(py, 2),
            "z": round(pz, 2),
            "u": round(pu, 5),
            "v": round(pv, 5),
            "head": [round(hx, 2), round(hy, 2), round(hz, 2)],
            "aim_origin": [round(cam_pos[0], 2), round(cam_pos[1], 2), round(cam_pos[2], 2)],
            "aim_dir": [round(cam_fwd[0], 4), round(cam_fwd[1], 4), round(cam_fwd[2], 4)],
            "yaw": round(player_yaw, 1),
            "vfov": round(cam_fov, 4),
            "is_aiming": bool(is_ads and drone_obj is None),
            "weapon_class": w_class,
            "suppressed": w_suppressed,
            "stance": "prone" if (hz - pz) < 0.65 else ("crouch" if (hz - pz) < 1.28 else "stand"),
        }

        allies: list[dict[str, Any]] = []
        enemies: list[dict[str, Any]] = []
        ai_idx = 0
        coop_idx = 0

        for c in active_slots:
            kind = self._classify_character(c, local_ent, local_skel, weapon_by_owner, player_vtable, player_rig)
            if kind in ("player", "civilian"):
                continue

            rx, ry, rz = float(c.root_pos[0]), float(c.root_pos[1]), float(c.root_pos[2])
            if not (c.valid_flags & 2):
                continue
            ehx, ehy, ehz = float(c.head_pos[0]), float(c.head_pos[1]), float(c.head_pos[2])
            # Filtra corpos caídos / bonecos no chão (< 0.35m altura cabeça-raiz sem arma ativa)
            w = weapon_by_owner.get(int(c.entity_ptr)) or weapon_by_owner.get(int(c.skel_ptr))
            if (ehz - rz) < 0.30 and w is None:
                continue

            hq = (float(c.head_quat[0]), float(c.head_quat[1]), float(c.head_quat[2]), float(c.head_quat[3]))
            look_dir = _norm3(_quat_rotate(hq, self.head_local_axis))
            yaw_deg = _vec_to_yaw_deg(look_dir)
            eu, ev = self.world_to_uv(rx, ry)

            # Vetor de mira pela mão direita / cabeça quando armado
            aim_dir = look_dir
            is_aiming = False
            if (c.valid_flags & 4) and (ehz - rz) > 0.7:
                rhx, rhy, rhz = float(c.rhand_pos[0]), float(c.rhand_pos[1]), float(c.rhand_pos[2])
                # Quando a mão direita sobe próxima à altura do ombro/queixo, o personagem está mirando
                if (ehz - rhz) < 0.42:
                    is_aiming = True
                    if (c.valid_flags & 8):
                        lhx, lhy, lhz = float(c.lhand_pos[0]), float(c.lhand_pos[1]), float(c.lhand_pos[2])
                        hand_vec = (lhx - rhx, lhy - rhy, lhz - rhz)
                        if math.sqrt(hand_vec[0] ** 2 + hand_vec[1] ** 2 + hand_vec[2] ** 2) > 0.12:
                            aim_dir = _norm3(hand_vec)

            if kind in ("ally_ai", "ally_coop"):
                if kind == "ally_coop":
                    coop_idx += 1
                    label = f"Co-op Ghost {coop_idx}"
                else:
                    ai_idx += 1
                    names = ("Holt", "Midas", "Weaver")
                    label = names[(ai_idx - 1) % len(names)]
                aw_cls = WEAPON_CATEGORY_MAP.get(int(w.weapon_category), "ar") if w else "ar"
                allies.append({
                    "id": f"{kind}_{int(c.skel_ptr):x}",
                    "type": "coop" if kind == "ally_coop" else "ai",
                    "name": label,
                    "x": round(rx, 2),
                    "y": round(ry, 2),
                    "z": round(rz, 2),
                    "u": round(eu, 5),
                    "v": round(ev, 5),
                    "head": [round(ehx, 2), round(ehy, 2), round(ehz, 2)],
                    "look_dir": [round(look_dir[0], 4), round(look_dir[1], 4), round(look_dir[2], 4)],
                    "aim_dir": [round(aim_dir[0], 4), round(aim_dir[1], 4), round(aim_dir[2], 4)],
                    "yaw": round(yaw_deg, 1),
                    "is_aiming": is_aiming,
                    "weapon_class": aw_cls,
                    "suppressed": None,
                })
            elif kind in ("enemy_sb", "enemy_unidad"):
                enemies.append({
                    "id": f"en_{int(c.skel_ptr):x}",
                    "faction": "unidad" if kind == "enemy_unidad" else "santa_blanca",
                    "x": round(rx, 2),
                    "y": round(ry, 2),
                    "z": round(rz, 2),
                    "u": round(eu, 5),
                    "v": round(ev, 5),
                    "head": [round(ehx, 2), round(ehy, 2), round(ehz, 2)],
                    "look_dir": [round(look_dir[0], 4), round(look_dir[1], 4), round(look_dir[2], 4)],
                    "yaw": round(yaw_deg, 1),
                    "alert": "unaware",
                    "alive": True,
                })

        return {
            "mode": "live",
            "status": "live",
            "hooks_mask": hooks_mask,
            "frame_tick": int(st.frame_tick),
            "player": player_obj,
            "drone": drone_obj,
            "allies": allies,
            "enemies": enemies,
            "trail": list(self._trail),
        }
