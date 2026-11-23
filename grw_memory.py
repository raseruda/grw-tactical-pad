"""Leitor de telemetria ao vivo da memória de GRW.exe (in-process via winmm.dll) e classificador de facções/estados."""
from __future__ import annotations

import ctypes
import math
import os
import threading
from ctypes import wintypes
from typing import Any

MAX_CHARS = 512
MAX_WEAPONS = 64
TELEMETRY_MAGIC = 0x47525754
TELEMETRY_VERSION = 2

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# Mapeamento exato recuperado de GRW.exe (0x3b88c98..0x3b88cec):
# 0=Neutral, 1=Civilian, 2=Ghost, 3=MexCartel, 4=MexTraitor, 5=Unidad, 6=Penitentes, 7=Rebel
EFACTION_MAP: dict[int, str] = {
    0: "civilian",
    1: "civilian",
    2: "ghost",
    3: "santa_blanca",
    4: "santa_blanca",
    5: "unidad",
    6: "santa_blanca",
    7: "rebel",
}

# Mapeamento exato recuperado de GRW.exe (0x13bea785 jump table 0x27d918c):
# 0=Down, 1=Idle, 2=Stealth, 3=Suspected, 4=Vanish, 5=Vanishing, 6=Fight
EALERT_MAP: dict[int, str] = {
    0: "down",
    1: "unaware",
    2: "unaware",
    3: "suspected",
    4: "suspected",
    5: "suspected",
    6: "hostile",
}

CIVILIAN_NPC_VTABLE_RVAS = frozenset({0x3B81890, 0x3B81D58})


class GRWCharSlot(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("skel_ptr", ctypes.c_uint64),
        ("entity_ptr", ctypes.c_uint64),
        ("rig_ptr", ctypes.c_uint64),
        ("pose_ptr", ctypes.c_uint64),
        ("entity_vtable", ctypes.c_uint64),
        ("last_seen_ms", ctypes.c_uint64),
        ("npc_ptr", ctypes.c_uint64),
        ("npc_vtable", ctypes.c_uint64),
        ("bone_count", ctypes.c_uint32),
        ("rig_map_count", ctypes.c_uint32),
        ("head_idx", ctypes.c_int32),
        ("rhand_idx", ctypes.c_int32),
        ("lhand_idx", ctypes.c_int32),
        ("hips_idx", ctypes.c_int32),
        ("pose_flags", ctypes.c_uint32),
        ("valid_flags", ctypes.c_uint32),
        ("faction_raw", ctypes.c_int32),
        ("alert_raw", ctypes.c_int32),
        ("faction_1e8", ctypes.c_int32),
        ("alert_328", ctypes.c_int32),
        ("is_player_comp", ctypes.c_uint32),
        ("_pad_npc", ctypes.c_uint32),
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
        ("muzzle_stuff", ctypes.c_uint64),
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
        ("hook_calls", ctypes.c_uint64 * 16),
        ("local_player_comp", ctypes.c_uint64),
        ("local_player_entity", ctypes.c_uint64),
        ("local_player_skel", ctypes.c_uint64),
        ("player_entities", ctypes.c_uint64 * 8),
        ("player_entity_count", ctypes.c_uint32),
        ("save_read_seq", ctypes.c_uint32),
        ("save_write_seq", ctypes.c_uint32),
        ("last_save_slot", ctypes.c_uint32),
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


# Mapeamento de m_eWeaponCategory (+0x17C) para classe acústica
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
    """Lê GRWTelemetryState sem bloqueio e classifica Ghosts/Santa Blanca/Unidad/Rebeldes/Civis + estados."""

    def __init__(self, telemetry_ptr: int | None = None, world_bounds: dict[str, Any] | None = None) -> None:
        self.telemetry_ptr = telemetry_ptr
        self._state: GRWTelemetryState | None = None
        if telemetry_ptr and telemetry_ptr > 0x10000:
            self._state = GRWTelemetryState.from_address(telemetry_ptr)
        self._lock = threading.RLock()
        self.world_bounds = dict(world_bounds or {
            "min_x": -8192.0,
            "max_x": 8192.0,
            "min_y": -8192.0,
            "max_y": 8192.0,
            "invert_y": True,
        })
        self.head_local_axis: tuple[float, float, float] = (0.0, 1.0, 0.0)
        self._trail: list[dict[str, Any]] = []
        self._last_trail_xy: tuple[float, float] | None = None
        self._trail_armed: bool = False
        self._trail_anchor_xy: tuple[float, float] | None = None
        self._trail_prev_xy: tuple[float, float] | None = None
        self._trail_move_steps: int = 0
        self._trail_need_break: bool = True
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
        """Permite injetar cena sintética em testes unitários ou demo UI."""
        with self._lock:
            self._override_snapshot = frame

    def get_debug_probe(self) -> dict[str, Any]:
        """Retorna dump diagnóstico bruto de câmera, player, NPCs, facções, estados e armas."""
        st = self._state
        if st is None or st.magic != TELEMETRY_MAGIC:
            return {"status": "no_telemetry_ptr", "pid": find_grw_pid()}
        now_ms = int(_kernel32.GetTickCount64())
        mod_base = int(st.module_base)
        chars = []
        for i in range(MAX_CHARS):
            c = st.chars[i]
            if c.skel_ptr == 0 or (now_ms - c.last_seen_ms) > 2500:
                continue
            vt_rva = (int(c.npc_vtable) - mod_base) if (c.npc_vtable and mod_base and c.npc_vtable > mod_base) else 0
            chars.append({
                "slot": i,
                "skel": hex(c.skel_ptr),
                "entity": hex(c.entity_ptr),
                "npc": hex(c.npc_ptr),
                "npc_vt_rva": hex(vt_rva),
                "rig": hex(c.rig_ptr),
                "vtable": hex(c.entity_vtable),
                "bones": int(c.bone_count),
                "is_player": int(c.is_player_comp),
                "faction_raw": int(c.faction_raw),
                "faction_1e8": int(c.faction_1e8),
                "alert_raw": int(c.alert_raw),
                "alert_328": int(c.alert_328),
                "age_ms": now_ms - int(c.last_seen_ms),
                "root": [round(float(x), 3) for x in c.root_pos[:3]],
                "head": [round(float(x), 3) for x in c.head_pos[:3]],
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
                "muzzle_stuff": hex(w.muzzle_stuff),
                "category": int(w.weapon_category),
                "shoot_mode": int(w.shoot_mode),
                "max_range": round(float(w.max_range), 2),
                "muzzle_vel": round(float(w.muzzle_velocity), 2),
            })
        return {
            "status": "ok",
            "version": int(st.version),
            "build_matched": bool(st.build_matched),
            "pe_timestamp": hex(st.pe_timestamp),
            "pe_size_of_image": hex(st.pe_size_of_image),
            "module_base": hex(st.module_base),
            "hooks_mask": hex(st.hooks_mask),
            "frame_tick": int(st.frame_tick),
            "hook_calls": [int(x) for x in st.hook_calls[:8]],
            "local_player_entity": hex(st.local_player_entity),
            "local_player_skel": hex(st.local_player_skel),
            "player_entities": [hex(st.player_entities[k]) for k in range(min(8, int(st.player_entity_count)))],
            "save_read_seq": int(st.save_read_seq),
            "save_write_seq": int(st.save_write_seq),
            "last_save_slot": int(st.last_save_slot),
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
        player_rig: int,
        module_base: int,
        coop_entities: set[int],
    ) -> str:
        """Classifica entidade para Player / Ghost Co-op / Ghost IA / Santa Blanca / La Unidad / Rebelde / Civil."""
        if (local_ent and c.entity_ptr == local_ent) or (local_skel and c.skel_ptr == local_skel):
            return "player"

        fac_enum = EFACTION_MAP.get(int(c.faction_raw)) or EFACTION_MAP.get(int(c.faction_1e8))
        # Nunca usa player_vtable para Co-op (todos os personagens Anvil compartilham a mesma vtable de Entity)
        if (int(c.is_player_comp) != 0 or (c.entity_ptr in coop_entities)) and fac_enum in (None, "ghost"):
            return "ally_coop"

        if fac_enum == "ghost":
            return "ally_ai"
        if fac_enum == "civilian":
            return "civilian"
        if fac_enum == "rebel":
            return "rebel"
        if fac_enum == "unidad":
            return "enemy_unidad"
        if fac_enum == "santa_blanca":
            return "enemy_sb"

        vt_rva = (int(c.npc_vtable) - module_base) if (c.npc_vtable and module_base and c.npc_vtable > module_base) else 0
        if vt_rva in CIVILIAN_NPC_VTABLE_RVAS:
            return "civilian"

        if player_rig and c.rig_ptr == player_rig:
            return "ally_ai_candidate"

        has_weapon = (c.entity_ptr in weapon_by_owner) or (c.skel_ptr in weapon_by_owner)
        if not has_weapon and c.bone_count < 140:
            return "civilian"
        return "enemy_sb"

    @staticmethod
    def _resolve_alert(c: GRWCharSlot) -> str:
        for raw in (int(c.alert_raw), int(c.alert_328)):
            if raw in EALERT_MAP:
                return EALERT_MAP[raw]
        return "unaware"

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
                "save_read_seq": 0,
                "save_write_seq": 0,
                "last_save_slot": 0,
                "player": None,
                "drone": None,
                "allies": [],
                "enemies": [],
                "rebels": [],
                "civilians": [],
                "npcs": [],
                "trail": list(self._trail),
            }

        now_ms = int(_kernel32.GetTickCount64())
        hooks_mask = int(st.hooks_mask)
        cam_fresh = bool(st.cam_valid) and (now_ms - int(st.cam_last_ms)) < 2000
        save_rseq = int(st.save_read_seq)
        save_wseq = int(st.save_write_seq)
        save_slot = int(st.last_save_slot)

        if not hooks_mask or not cam_fresh:
            with self._lock:
                self._trail_armed = False
                self._trail_move_steps = 0
                self._trail_need_break = True
                self._trail_anchor_xy = None
                self._trail_prev_xy = None
            return {
                "mode": "title" if st.build_matched else "mismatch",
                "status": "title" if st.build_matched else "build_mismatch",
                "hooks_mask": hooks_mask,
                "build_matched": bool(st.build_matched),
                "save_read_seq": save_rseq,
                "save_write_seq": save_wseq,
                "last_save_slot": save_slot,
                "player": None,
                "drone": None,
                "allies": [],
                "enemies": [],
                "rebels": [],
                "civilians": [],
                "npcs": [],
                "trail": list(self._trail),
            }

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
        mod_base = int(st.module_base)
        coop_entities = {int(st.player_entities[k]) for k in range(min(8, int(st.player_entity_count))) if st.player_entities[k]}
        coop_entities.discard(local_ent)

        if local_ent == 0 and local_skel == 0 and not weapon_by_owner:
            with self._lock:
                self._trail_armed = False
                self._trail_move_steps = 0
                self._trail_need_break = True
                self._trail_anchor_xy = None
                self._trail_prev_xy = None
            return {
                "mode": "title",
                "status": "ghost_room_or_menu",
                "hooks_mask": hooks_mask,
                "build_matched": bool(st.build_matched),
                "save_read_seq": save_rseq,
                "save_write_seq": save_wseq,
                "last_save_slot": save_slot,
                "player": None,
                "drone": None,
                "allies": [],
                "enemies": [],
                "rebels": [],
                "civilians": [],
                "npcs": [],
                "trail": list(self._trail),
            }

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
        if pw and int(pw.attachment_holder) != 0:
            w_suppressed = bool(int(pw.muzzle_stuff) != 0)
        elif pw and int(pw.extra_u32[2]) != 0:
            w_suppressed = bool(int(pw.extra_u32[2]) & 1)
        else:
            w_suppressed = True

        pu, pv = self.world_to_uv(px, py)
        player_yaw = _vec_to_yaw_deg(cam_fwd)

        with self._lock:
            if player_slot is None or local_ent == 0 or (abs(px) < 10.0 and abs(py) < 10.0):
                self._trail_armed = False
                self._trail_move_steps = 0
                self._trail_need_break = True
                self._trail_anchor_xy = None
                self._trail_prev_xy = None
            else:
                step_from_prev = (
                    math.hypot(px - self._trail_prev_xy[0], py - self._trail_prev_xy[1])
                    if self._trail_prev_xy is not None
                    else 9999.0
                )
                if step_from_prev > 45.0:
                    # Salto de carregamento / viagem rápida: desarma e marca quebra na próxima caminhada
                    self._trail_armed = False
                    self._trail_move_steps = 0
                    self._trail_need_break = True
                    self._trail_anchor_xy = (px, py)
                    self._trail_prev_xy = (px, py)
                elif not self._trail_armed:
                    self._trail_prev_xy = (px, py)
                    if self._trail_anchor_xy is None:
                        self._trail_anchor_xy = (px, py)
                    d_anchor = math.hypot(px - self._trail_anchor_xy[0], py - self._trail_anchor_xy[1])
                    if 1.5 <= d_anchor <= 45.0:
                        self._trail_anchor_xy = (px, py)
                        self._trail_move_steps += 1
                        if self._trail_move_steps >= 3:
                            self._trail_armed = True
                            self._last_trail_xy = (px, py)
                            self._trail.append({
                                "u": round(pu, 5),
                                "v": round(pv, 5),
                                "x": round(px, 1),
                                "y": round(py, 1),
                                "z": round(pz, 1),
                                "brk": True,
                            })
                            self._trail_need_break = False
                            if len(self._trail) > 1500:
                                self._trail.pop(0)
                else:
                    self._trail_prev_xy = (px, py)
                    d_last = (
                        math.hypot(px - self._last_trail_xy[0], py - self._last_trail_xy[1])
                        if self._last_trail_xy is not None
                        else 9999.0
                    )
                    if 6.0 <= d_last <= 45.0:
                        self._last_trail_xy = (px, py)
                        self._trail.append({
                            "u": round(pu, 5),
                            "v": round(pv, 5),
                            "x": round(px, 1),
                            "y": round(py, 1),
                            "z": round(pz, 1),
                            "brk": bool(self._trail_need_break),
                        })
                        self._trail_need_break = False
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

        coop_candidates: list[tuple[float, dict[str, Any]]] = []
        ai_candidates: list[tuple[int, float, dict[str, Any], bool]] = []
        enemies: list[dict[str, Any]] = []
        rebels: list[dict[str, Any]] = []
        civilians: list[dict[str, Any]] = []

        for c in active_slots:
            kind = self._classify_character(
                c, local_ent, local_skel, weapon_by_owner, player_rig, mod_base, coop_entities
            )
            if kind == "player":
                continue

            alert_state = self._resolve_alert(c)
            if alert_state == "down":
                continue

            rx, ry, rz = float(c.root_pos[0]), float(c.root_pos[1]), float(c.root_pos[2])
            if not (c.valid_flags & 2):
                continue
            ehx, ehy, ehz = float(c.head_pos[0]), float(c.head_pos[1]), float(c.head_pos[2])
            w = weapon_by_owner.get(int(c.entity_ptr)) or weapon_by_owner.get(int(c.skel_ptr))
            if (ehz - rz) < 0.30 and w is None:
                continue

            hq = (float(c.head_quat[0]), float(c.head_quat[1]), float(c.head_quat[2]), float(c.head_quat[3]))
            look_dir = _norm3(_quat_rotate(hq, self.head_local_axis))
            yaw_deg = _vec_to_yaw_deg(look_dir)
            eu, ev = self.world_to_uv(rx, ry)
            dist_p = math.hypot(rx - px, ry - py)

            aim_dir = look_dir
            is_aiming = False
            if (c.valid_flags & 4) and (ehz - rz) > 0.7:
                rhx, rhy, rhz = float(c.rhand_pos[0]), float(c.rhand_pos[1]), float(c.rhand_pos[2])
                if (ehz - rhz) < 0.42:
                    is_aiming = True
                    if (c.valid_flags & 8):
                        lhx, lhy, lhz = float(c.lhand_pos[0]), float(c.lhand_pos[1]), float(c.lhand_pos[2])
                        hand_vec = (lhx - rhx, lhy - rhy, lhz - rhz)
                        if math.sqrt(hand_vec[0] ** 2 + hand_vec[1] ** 2 + hand_vec[2] ** 2) > 0.12:
                            aim_dir = _norm3(hand_vec)

            base_obj = {
                "skel_ptr": int(c.skel_ptr),
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
                "alert": alert_state,
                "alive": True,
                "has_weapon": w is not None,
                "weapon_class": WEAPON_CATEGORY_MAP.get(int(w.weapon_category), "ar") if w else None,
                "suppressed": (bool(int(w.muzzle_stuff) != 0) if (w and int(w.attachment_holder) != 0) else None),
            }

            if kind == "ally_coop":
                coop_candidates.append((dist_p, base_obj))
            elif kind == "ally_ai":
                ai_candidates.append((0, dist_p, base_obj, True))
            elif kind == "ally_ai_candidate":
                if dist_p <= 120.0:
                    ai_candidates.append((1, dist_p, base_obj, False))
                else:
                    npc_obj = {
                        "id": f"npc_{base_obj['skel_ptr']:x}",
                        "faction": "santa_blanca" if base_obj["has_weapon"] else "civilian",
                        "x": base_obj["x"],
                        "y": base_obj["y"],
                        "z": base_obj["z"],
                        "u": base_obj["u"],
                        "v": base_obj["v"],
                        "head": base_obj["head"],
                        "look_dir": base_obj["look_dir"],
                        "yaw": base_obj["yaw"],
                        "alert": base_obj["alert"],
                        "alive": True,
                        "has_weapon": base_obj["has_weapon"],
                        "weapon_class": base_obj["weapon_class"],
                    }
                    (enemies if npc_obj["faction"] == "santa_blanca" else civilians).append(npc_obj)
            else:
                faction_str = {
                    "enemy_unidad": "unidad",
                    "enemy_sb": "santa_blanca",
                    "rebel": "rebel",
                    "civilian": "civilian",
                }.get(kind, "santa_blanca")
                npc_obj = {
                    "id": f"npc_{base_obj['skel_ptr']:x}",
                    "faction": faction_str,
                    "x": base_obj["x"],
                    "y": base_obj["y"],
                    "z": base_obj["z"],
                    "u": base_obj["u"],
                    "v": base_obj["v"],
                    "head": base_obj["head"],
                    "look_dir": base_obj["look_dir"],
                    "yaw": base_obj["yaw"],
                    "alert": base_obj["alert"],
                    "alive": True,
                    "has_weapon": base_obj["has_weapon"],
                    "weapon_class": base_obj["weapon_class"],
                }
                if faction_str in ("santa_blanca", "unidad"):
                    enemies.append(npc_obj)
                elif faction_str == "rebel":
                    rebels.append(npc_obj)
                else:
                    civilians.append(npc_obj)

        # Limite rígido de esquadrão no GRW: no máximo 3 aliados além do jogador (Co-op primeiro, depois IA Holt/Midas/Weaver)
        allies: list[dict[str, Any]] = []
        coop_candidates.sort(key=lambda t: t[0])
        ai_candidates.sort(key=lambda t: (t[0], t[1]))

        for idx_c, (_dist, bo) in enumerate(coop_candidates, start=1):
            if len(allies) < 3:
                allies.append({
                    "id": f"ally_coop_{bo['skel_ptr']:x}",
                    "type": "coop",
                    "faction": "ghost",
                    "name": f"Co-op Ghost {idx_c}",
                    "x": bo["x"],
                    "y": bo["y"],
                    "z": bo["z"],
                    "u": bo["u"],
                    "v": bo["v"],
                    "head": bo["head"],
                    "look_dir": bo["look_dir"],
                    "aim_dir": bo["aim_dir"],
                    "yaw": bo["yaw"],
                    "is_aiming": bo["is_aiming"],
                    "alert": bo["alert"],
                    "weapon_class": bo["weapon_class"] or "ar",
                    "suppressed": bo["suppressed"],
                    "alive": True,
                })
            else:
                npc_obj = {
                    "id": f"npc_{bo['skel_ptr']:x}",
                    "faction": "santa_blanca" if bo["has_weapon"] else "civilian",
                    "x": bo["x"],
                    "y": bo["y"],
                    "z": bo["z"],
                    "u": bo["u"],
                    "v": bo["v"],
                    "head": bo["head"],
                    "look_dir": bo["look_dir"],
                    "yaw": bo["yaw"],
                    "alert": bo["alert"],
                    "alive": True,
                    "has_weapon": bo["has_weapon"],
                    "weapon_class": bo["weapon_class"],
                }
                (enemies if npc_obj["faction"] == "santa_blanca" else civilians).append(npc_obj)

        ai_names = ("Holt", "Midas", "Weaver")
        ai_count = 0
        for _prio, _dist, bo, _explicit in ai_candidates:
            if len(allies) < 3:
                ai_count += 1
                allies.append({
                    "id": f"ally_ai_{bo['skel_ptr']:x}",
                    "type": "ai",
                    "faction": "ghost",
                    "name": ai_names[(ai_count - 1) % len(ai_names)],
                    "x": bo["x"],
                    "y": bo["y"],
                    "z": bo["z"],
                    "u": bo["u"],
                    "v": bo["v"],
                    "head": bo["head"],
                    "look_dir": bo["look_dir"],
                    "aim_dir": bo["aim_dir"],
                    "yaw": bo["yaw"],
                    "is_aiming": bo["is_aiming"],
                    "alert": bo["alert"],
                    "weapon_class": bo["weapon_class"] or "ar",
                    "suppressed": bo["suppressed"],
                    "alive": True,
                })
            else:
                npc_obj = {
                    "id": f"npc_{bo['skel_ptr']:x}",
                    "faction": "santa_blanca" if bo["has_weapon"] else "civilian",
                    "x": bo["x"],
                    "y": bo["y"],
                    "z": bo["z"],
                    "u": bo["u"],
                    "v": bo["v"],
                    "head": bo["head"],
                    "look_dir": bo["look_dir"],
                    "yaw": bo["yaw"],
                    "alert": bo["alert"],
                    "alive": True,
                    "has_weapon": bo["has_weapon"],
                    "weapon_class": bo["weapon_class"],
                }
                (enemies if npc_obj["faction"] == "santa_blanca" else civilians).append(npc_obj)

        return {
            "mode": "live",
            "status": "live",
            "hooks_mask": hooks_mask,
            "frame_tick": int(st.frame_tick),
            "save_read_seq": save_rseq,
            "save_write_seq": save_wseq,
            "last_save_slot": save_slot,
            "player": player_obj,
            "drone": drone_obj,
            "allies": allies,
            "enemies": enemies,
            "rebels": rebels,
            "civilians": civilians,
            "npcs": enemies + rebels + civilians,
            "trail": list(self._trail),
        }
