"""Compila o proxy x64 winmm.dll (com telemetria read-only para GRW.exe TU25) e empacota mod_release/."""
from __future__ import annotations

import argparse
import importlib
import os
import shutil
import struct
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = Path(__file__).resolve().parent / "build"
RELEASE_DIR = ROOT_DIR / "mod_release"
RELEASE_ZIP = ROOT_DIR / "GhostPad_GRW_v1.1.0.zip"
SYSTEM_WINMM = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "winmm.dll"
VCVARS64 = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat")

EMBED_PYTHON_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
KEEP_RUNTIME_BINARIES = frozenset({
    "python312.dll",
    "python3.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "libffi-8.dll",
    "_ctypes.pyd",
    "_socket.pyd",
    "select.pyd",
    "_queue.pyd",
    "unicodedata.pyd",
    "_uuid.pyd",
    "_wmi.pyd",
    "pyexpat.pyd",
})
PY_SOURCE_FILES = (
    "config.py",
    "anvil_formats.py",
    "grw_catalog_db.py",
    "grw_asset_builder.py",
    "grw_memory.py",
    "grw_save_sync.py",
    "tactical_engine.py",
    "server.py",
    "launcher.py",
)

# Hooks read-only verificados em GRW.exe 2026-09-15 Title Update 25 (TS=0x6A99768A, SizeOfImage=0x185BA000)
# Cada entrada é (nome, thunk_rva, impl_rva) onde o thunk tem E9 rel32 + padding CC até 14+ bytes.
TU25_THUNKS = (
    ("proj2", 0x01376DF0, 0x0D67B110),
    ("selector", 0x013796D0, 0x0D67FFA0),
    ("SkeletonPostUpdate", 0x01899110, 0x0F6D9800),
    ("cPlayerComponent_OnInit", 0x02752340, 0x139AE870),
    ("weapon_update", 0x029FB1C0, 0x1483DE80),
    ("GR_cNPC_vt2", 0x026BC090, 0x137732D0),
    ("GR_cNPC_vt8", 0x026C7E00, 0x137BDCE0),
    ("GR_cNPC_vt5_OnEvent", 0x02611EB0, 0x13148FE0),
)


def parse_pe_exports(dll_path: Path) -> list[tuple[int, str | None]]:
    """Extrai todos os exports (ordinal, nome_ou_None) da tabela de exportação PE32+."""
    data = dll_path.read_bytes()
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    n_sec = struct.unpack_from("<H", data, pe_off + 6)[0]
    opt_sz = struct.unpack_from("<H", data, pe_off + 20)[0]
    exp_rva, _exp_sz = struct.unpack_from("<II", data, pe_off + 24 + 112)
    sec_off = pe_off + 24 + opt_sz

    secs: list[tuple[int, int, int]] = []
    for i in range(n_sec):
        vsz, vrva, rsz, rptr = struct.unpack_from("<IIII", data, sec_off + i * 40 + 8)
        secs.append((vrva, max(vsz, rsz), rptr))

    def rva2off(rva: int) -> int | None:
        for vrva, sz, rptr in secs:
            if vrva <= rva < vrva + sz:
                return rptr + (rva - vrva)
        return None

    eo = rva2off(exp_rva)
    assert eo is not None
    ord_base, n_funcs, n_names, funcs_rva, names_rva, ords_rva = struct.unpack_from("<6I", data, eo + 16)
    fo = rva2off(funcs_rva)
    no = rva2off(names_rva)
    oo = rva2off(ords_rva)
    assert fo is not None and no is not None and oo is not None

    name_by_idx: dict[int, str] = {}
    name_rvas = struct.unpack_from(f"<{n_names}I", data, no)
    name_ords = struct.unpack_from(f"<{n_names}H", data, oo)
    for nr, idx in zip(name_rvas, name_ords):
        off = rva2off(nr)
        if off is not None:
            nul = data.index(b"\0", off)
            name_by_idx[idx] = data[off:nul].decode("ascii", "strict")

    func_rvas = struct.unpack_from(f"<{n_funcs}I", data, fo)
    exports: list[tuple[int, str | None]] = []
    for idx, frva in enumerate(func_rvas):
        if frva == 0:
            continue
        exports.append((ord_base + idx, name_by_idx.get(idx)))
    return exports


def parse_pe_imports(pe_path: Path) -> list[str]:
    """Extrai a lista de DLLs importadas da tabela PE32+."""
    data = pe_path.read_bytes()
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    n_sec = struct.unpack_from("<H", data, pe_off + 6)[0]
    opt_sz = struct.unpack_from("<H", data, pe_off + 20)[0]
    imp_rva, _imp_sz = struct.unpack_from("<II", data, pe_off + 24 + 120)
    sec_off = pe_off + 24 + opt_sz

    secs: list[tuple[int, int, int]] = []
    for i in range(n_sec):
        vsz, vrva, rsz, rptr = struct.unpack_from("<IIII", data, sec_off + i * 40 + 8)
        secs.append((vrva, max(vsz, rsz), rptr))

    def rva2off(rva: int) -> int | None:
        for vrva, sz, rptr in secs:
            if vrva <= rva < vrva + sz:
                return rptr + (rva - vrva)
        return None

    off = rva2off(imp_rva)
    if off is None:
        return []
    dlls: list[str] = []
    idx = 0
    while off + idx * 20 + 20 <= len(data):
        _il, _ts, _fc, name_rva, _ft = struct.unpack_from("<5I", data, off + idx * 20)
        if name_rva == 0:
            break
        noff = rva2off(name_rva)
        if noff is not None:
            nul = data.index(b"\0", noff)
            dlls.append(data[noff:nul].decode("ascii", "replace"))
        idx += 1
    return dlls


def generate_sources(exports: list[tuple[int, str | None]]) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    n = len(exports)
    nh = len(TU25_THUNKS)

    # 1. winmm_proxy.def
    def_lines = ["LIBRARY winmm", "EXPORTS"]
    for idx, (ordinal, name) in enumerate(exports):
        if name:
            def_lines.append(f"  {name}=ghost_stub_{idx} @{ordinal}")
        else:
            def_lines.append(f"  ord_{ordinal}=ghost_stub_{idx} @{ordinal} NONAME")
    (BUILD_DIR / "winmm_proxy.def").write_text("\n".join(def_lines) + "\n", encoding="ascii")

    # 2. winmm_stubs.asm (MASM x64: 181 forwarders + ABI-safe probe observers)
    asm_lines = [
        "EXTERN g_winmm_procs:QWORD",
        "EXTERN grw_probe_originals:QWORD",
        "EXTERN grw_probe_record:PROC",
        ".code",
    ]
    for idx in range(n):
        asm_lines.append(f"ghost_stub_{idx} PROC")
        asm_lines.append(f"    jmp qword ptr [g_winmm_procs + {idx * 8}]")
        asm_lines.append(f"ghost_stub_{idx} ENDP")

    # Stub comum com preservação ABI x64 (sub rsp, 0B8h -> 8 mod 16 -> 0 mod 16 antes do call)
    asm_lines.extend([
        "grw_probe_common PROC PRIVATE",
        "    sub rsp, 0B8h",
        "    mov [rsp+40h], rcx",
        "    mov [rsp+48h], rdx",
        "    mov [rsp+50h], r8",
        "    mov [rsp+58h], r9",
        "    movups [rsp+60h], xmm0",
        "    movups [rsp+70h], xmm1",
        "    movups [rsp+80h], xmm2",
        "    movups [rsp+90h], xmm3",
        "    mov [rsp+0A0h], r10",
        "    mov rcx, r10",
        "    lea rdx, [rsp+40h]",
        "    mov r8, [rsp+0B8h]",
        "    lea r9, [rsp+0C0h]",
        "    call grw_probe_record",
        "    mov r10, [rsp+0A0h]",
        "    movups xmm3, [rsp+90h]",
        "    movups xmm2, [rsp+80h]",
        "    movups xmm1, [rsp+70h]",
        "    movups xmm0, [rsp+60h]",
        "    mov r9, [rsp+58h]",
        "    mov r8, [rsp+50h]",
        "    mov rdx, [rsp+48h]",
        "    mov rcx, [rsp+40h]",
        "    lea r11, grw_probe_originals",
        "    mov r11, [r11 + r10*8]",
        "    add rsp, 0B8h",
        "    jmp r11",
        "grw_probe_common ENDP",
    ])
    for idx in range(nh):
        asm_lines.extend([
            f"grw_probe_entry_{idx} PROC",
            f"    mov r10d, {idx}",
            "    jmp grw_probe_common",
            f"grw_probe_entry_{idx} ENDP",
        ])
    asm_lines.append("END")
    (BUILD_DIR / "winmm_stubs.asm").write_text("\n".join(asm_lines) + "\n", encoding="ascii")

    # 3. winmm_proxy.c
    c_names = [f'"{name}"' if name else "NULL" for _, name in exports]
    c_ords = [str(ordinal) for ordinal, _ in exports]

    thunk_entries = []
    thunk_decls = []
    for idx, (tname, trva, irva) in enumerate(TU25_THUNKS):
        thunk_decls.append(f"extern void grw_probe_entry_{idx}(void);")
        thunk_entries.append(f'    {{ "{tname}", 0x{trva:08X}u, 0x{irva:08X}u, (void*)&grw_probe_entry_{idx} }}')

    c_src = f'''#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

#define NUM_EXPORTS {n}
#define NUM_PROBES {nh}
#define MAX_CHARS 512
#define MAX_WEAPONS 64
#define MAX_RIG_CACHE 64
#define MAX_NPC_LINKS 1024
#define MAX_SAVE_TRACKS 16
#define MAX_LIVE_SAVE_BYTES (4u * 1024u * 1024u)

#ifndef LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR
#define LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR 0x00000100
#endif
#ifndef LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
#define LOAD_LIBRARY_SEARCH_DEFAULT_DIRS 0x00001000
#endif

FARPROC g_winmm_procs[NUM_EXPORTS] = {{0}};
uint64_t grw_probe_originals[NUM_PROBES] = {{0}};

static HMODULE g_real_winmm = NULL;
static HANDLE g_mutex = NULL;
static volatile HWND g_app_hwnd = NULL;
static volatile LONG g_shutting_down = 0;

static const char *const g_export_names[NUM_EXPORTS] = {{
    {", ".join(c_names)}
}};
static const WORD g_export_ordinals[NUM_EXPORTS] = {{
    {", ".join(c_ords)}
}};

{chr(10).join(thunk_decls)}

typedef struct SavedArgs {{
    uint64_t rcx, rdx, r8, r9;
    float xmm0[4], xmm1[4], xmm2[4], xmm3[4];
}} SavedArgs;

#pragma pack(push, 8)
typedef struct GRWCharSlot {{
    uint64_t skel_ptr;
    uint64_t entity_ptr;
    uint64_t rig_ptr;
    uint64_t pose_ptr;
    uint64_t entity_vtable;
    uint64_t last_seen_ms;
    uint64_t npc_ptr;
    uint64_t npc_vtable;
    uint32_t bone_count;
    uint32_t rig_map_count;
    int32_t head_idx;
    int32_t rhand_idx;
    int32_t lhand_idx;
    int32_t hips_idx;
    uint32_t pose_flags;
    uint32_t valid_flags;
    int32_t faction_raw;
    int32_t alert_raw;
    int32_t faction_1e8;
    int32_t alert_328;
    uint32_t is_player_comp;
    uint32_t _pad_npc;
    float root_pos[4];
    float root_quat[4];
    float head_pos[4];
    float head_quat[4];
    float rhand_pos[4];
    float lhand_pos[4];
    float hips_pos[4];
    uint32_t ent_u32[32];
}} GRWCharSlot;

typedef struct GRWWeaponSlot {{
    uint64_t weapon_ptr;
    uint64_t essence_ptr;
    uint64_t gun_root_owner;
    uint64_t muzzle_owner;
    uint64_t attachment_holder;
    uint64_t muzzle_stuff;
    uint64_t last_seen_ms;
    uint32_t weapon_category;
    uint32_t shoot_mode;
    int32_t gun_root_idx;
    int32_t muzzle_idx;
    float max_range;
    float muzzle_velocity;
    uint32_t extra_u32[16];
}} GRWWeaponSlot;

typedef struct GRWTelemetryState {{
    uint32_t magic;
    uint32_t version;
    uint32_t pe_timestamp;
    uint32_t pe_size_of_image;
    uint64_t module_base;
    uint32_t hooks_mask;
    uint32_t build_matched;
    uint64_t frame_tick;
    uint64_t hook_calls[16];
    uint64_t local_player_comp;
    uint64_t local_player_entity;
    uint64_t local_player_skel;
    uint64_t player_entities[8];
    uint32_t player_entity_count;
    uint32_t save_read_seq;
    uint32_t save_write_seq;
    uint32_t last_save_slot;
    uint64_t cam_ptr;
    uint32_t cam_mode;
    uint32_t cam_valid;
    float cam_vfov;
    float cam_fov_proj;
    float cam_pos[3];
    float cam_right[3];
    float cam_up[3];
    float cam_fwd[3];
    uint64_t cam_last_ms;
    GRWCharSlot chars[MAX_CHARS];
    GRWWeaponSlot weapons[MAX_WEAPONS];
}} GRWTelemetryState;
#pragma pack(pop)

static GRWTelemetryState g_telemetry = {{ 0x47525754u, 2u }};

typedef struct RigBoneCache {{
    uint64_t rig_ptr;
    uint16_t bone_count;
    uint16_t map_count;
    int32_t head_idx;
    int32_t rhand_idx;
    int32_t lhand_idx;
    int32_t hips_idx;
}} RigBoneCache;

static RigBoneCache g_rig_cache[MAX_RIG_CACHE] = {{0}};

typedef struct NpcLink {{
    uint64_t entity_ptr;
    uint64_t npc_ptr;
    uint64_t npc_vtable;
    uint64_t last_seen_ms;
}} NpcLink;

static NpcLink g_npc_links[MAX_NPC_LINKS] = {{0}};

typedef struct ThunkSpec {{
    const char *name;
    uint32_t thunk_rva;
    uint32_t impl_rva;
    void *replacement;
}} ThunkSpec;

static const ThunkSpec g_thunk_specs[NUM_PROBES] = {{
{",\n".join(thunk_entries)}
}};

static uint8_t g_saved_thunks[NUM_PROBES][16];
static uint8_t *g_patched_addrs[NUM_PROBES] = {{0}};
static int g_patched_ok[NUM_PROBES] = {{0}};
static wchar_t g_mod_dir[MAX_PATH * 2] = {{0}};

typedef int (__cdecl *PFN_UPLAY_SAVE_Open)(uint32_t slot_id, uint32_t mode, uint32_t *out_handle, void *overlapped);
typedef int (__cdecl *PFN_UPLAY_SAVE_Close)(uint32_t handle);
typedef int (__cdecl *PFN_UPLAY_SAVE_Read)(uint32_t handle, uint32_t bytes_to_read, uint32_t offset, void **buf_ptr, uint32_t *out_bytes_read, void *overlapped);
typedef int (__cdecl *PFN_UPLAY_SAVE_Write)(uint32_t handle, uint32_t bytes_to_write, void **buf_ptr, void *overlapped);

static PFN_UPLAY_SAVE_Open  g_orig_save_open  = NULL;
static PFN_UPLAY_SAVE_Close g_orig_save_close = NULL;
static PFN_UPLAY_SAVE_Read  g_orig_save_read  = NULL;
static PFN_UPLAY_SAVE_Write g_orig_save_write = NULL;
static uint64_t *g_iat_save_open  = NULL;
static uint64_t *g_iat_save_close = NULL;
static uint64_t *g_iat_save_read  = NULL;
static uint64_t *g_iat_save_write = NULL;

typedef struct SaveTrack {{
    int in_use;
    uint32_t handle;
    uint32_t slot_id;
    uint32_t mode;
    uint8_t *pending_buf;
    uint32_t pending_off;
    uint32_t pending_req;
    uint32_t *pending_out_len;
    uint32_t max_len;
    uint8_t *buf;
    uint32_t cap;
}} SaveTrack;

static CRITICAL_SECTION g_save_cs;
static int g_save_cs_init = 0;
static SaveTrack g_save_tracks[MAX_SAVE_TRACKS] = {{0}};

static void init_real_winmm(void) {{
    if (g_real_winmm) return;
    wchar_t sys_dir[MAX_PATH];
    wchar_t dll_path[MAX_PATH + 32];
    UINT len = GetSystemDirectoryW(sys_dir, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) return;
    lstrcpynW(dll_path, sys_dir, MAX_PATH);
    lstrcatW(dll_path, L"\\\\winmm.dll");
    g_real_winmm = LoadLibraryW(dll_path);
    if (!g_real_winmm) return;
    for (int i = 0; i < NUM_EXPORTS; ++i) {{
        LPCSTR proc_id = g_export_names[i] ? g_export_names[i] : (LPCSTR)(ULONG_PTR)g_export_ordinals[i];
        g_winmm_procs[i] = GetProcAddress(g_real_winmm, proc_id);
    }}
}}

static int ends_with_ci(const wchar_t *str, const wchar_t *suffix) {{
    int sl = lstrlenW(str);
    int xl = lstrlenW(suffix);
    if (sl < xl) return 0;
    return CompareStringOrdinal(str + (sl - xl), xl, suffix, xl, TRUE) == CSTR_EQUAL;
}}

static int file_exists(const wchar_t *path) {{
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}}

static void log_loader_msg(const wchar_t *pad_dir, const char *msg) {{
    if (!pad_dir || !pad_dir[0]) return;
    wchar_t data_dir[MAX_PATH * 2];
    wchar_t log_path[MAX_PATH * 2];
    swprintf_s(data_dir, MAX_PATH * 2, L"%ls\\\\data", pad_dir);
    CreateDirectoryW(data_dir, NULL);
    swprintf_s(log_path, MAX_PATH * 2, L"%ls\\\\ghost_pad_loader.log", data_dir);
    HANDLE hf = CreateFileW(log_path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf != INVALID_HANDLE_VALUE) {{
        DWORD written = 0;
        WriteFile(hf, msg, (DWORD)lstrlenA(msg), &written, NULL);
        WriteFile(hf, "\\r\\n", 2, &written, NULL);
        CloseHandle(hf);
    }}
}}

/* Descompressor rápido LZO1X exportável via ponteiro para anvil_formats.py */
int __cdecl grw_lzo1x_decompress(const uint8_t *src, uint32_t src_len, uint8_t *dst, uint32_t *dst_len) {{
    const uint8_t *ip = src;
    const uint8_t *ip_end = src + src_len;
    uint8_t *op = dst;
    uint8_t *op_end = dst + (*dst_len);
    uint32_t t = 0;
    int state = 0; /* 0=loop, 1=flr, 2=match, 3=md */
    if (!src || !dst || !dst_len || src_len == 0) return -1;

    if (*ip > 17) {{
        t = *ip++ - 17;
        if (t < 4) {{
            if (ip + t >= ip_end || op + t > op_end) return -2;
            while (t--) *op++ = *ip++;
            t = *ip++;
            state = 2;
        }} else {{
            if (ip + t > ip_end || op + t > op_end) return -2;
            while (t--) *op++ = *ip++;
            state = 1;
        }}
    }}

    while (ip < ip_end) {{
        if (state == 0) {{
            t = *ip++;
            if (t >= 16) {{ state = 2; continue; }}
            if (t == 0) {{
                while (ip < ip_end && *ip == 0) {{ t += 255; ip++; }}
                if (ip >= ip_end) return -3;
                t += 15 + *ip++;
            }}
            t += 3;
            if (ip + t > ip_end || op + t > op_end) return -2;
            while (t--) *op++ = *ip++;
            state = 1;
        }}
        if (state == 1) {{
            if (ip >= ip_end) break;
            t = *ip++;
            if (t >= 16) {{ state = 2; continue; }}
            if (ip >= ip_end) return -3;
            uint8_t *m = op - 0x801 - (t >> 2) - (((uint32_t)*ip++) << 2);
            if (m < dst || op + 3 > op_end) return -4;
            *op++ = *m++; *op++ = *m++; *op++ = *m++;
            state = 3;
        }}
        if (state == 2) {{
            if (t >= 64) {{
                if (ip >= ip_end) return -3;
                uint8_t *m = op - 1 - ((t >> 2) & 7) - (((uint32_t)*ip++) << 3);
                uint32_t len = (t >> 5) - 1 + 2;
                if (m < dst || op + len > op_end) return -4;
                while (len--) *op++ = *m++;
            }} else if (t >= 32) {{
                t &= 31;
                if (t == 0) {{
                    while (ip < ip_end && *ip == 0) {{ t += 255; ip++; }}
                    if (ip >= ip_end) return -3;
                    t += 31 + *ip++;
                }}
                if (ip + 2 > ip_end) return -3;
                uint8_t *m = op - 1 - (ip[0] >> 2) - (((uint32_t)ip[1]) << 6);
                ip += 2;
                uint32_t len = t + 2;
                if (m < dst || op + len > op_end) return -4;
                while (len--) *op++ = *m++;
            }} else if (t >= 16) {{
                uint8_t *m = op - ((t & 8) << 11);
                t &= 7;
                if (t == 0) {{
                    while (ip < ip_end && *ip == 0) {{ t += 255; ip++; }}
                    if (ip >= ip_end) return -3;
                    t += 7 + *ip++;
                }}
                if (ip + 2 > ip_end) return -3;
                m -= (ip[0] >> 2) + (((uint32_t)ip[1]) << 6);
                ip += 2;
                if (m == op) break;
                m -= 0x4000;
                uint32_t len = t + 2;
                if (m < dst || op + len > op_end) return -4;
                while (len--) *op++ = *m++;
            }} else {{
                if (ip >= ip_end) return -3;
                uint8_t *m = op - 1 - (t >> 2) - (((uint32_t)*ip++) << 2);
                if (m < dst || op + 2 > op_end) return -4;
                *op++ = *m++; *op++ = *m++;
            }}
            state = 3;
        }}
        if (state == 3) {{
            t = ip[-2] & 3;
            if (t == 0) {{ state = 0; continue; }}
            if (ip + t >= ip_end || op + t > op_end) return -2;
            while (t--) *op++ = *ip++;
            t = *ip++;
            state = 2;
        }}
    }}
    *dst_len = (uint32_t)(op - dst);
    return 0;
}}

static int ptr_ok(uint64_t p) {{
    return p >= 0x10000ULL && p < 0x00007FFFFFFFFFFFULL && ((p & 3ULL) == 0ULL);
}}

static int rig_find_bone_raw(uint64_t rig, uint32_t hash, uint16_t bones) {{
    uint16_t cnt = *(const uint16_t *)(rig + 0x5A);
    uint64_t map = *(const uint64_t *)(rig + 0x50);
    if (cnt == 0 || cnt >= 2048 || !ptr_ok(map)) return -1;
    int a = 0, b = (int)cnt - 1;
    while (a <= b) {{
        int mid = (a + b) / 2;
        uint32_t h = *(const uint32_t *)(map + (uint64_t)mid * 8ULL);
        if (h == hash) {{
            uint16_t idx = *(const uint16_t *)(map + (uint64_t)mid * 8ULL + 4ULL);
            if (bones && idx >= bones) return -1;
            return (int)idx;
        }}
        if (h < hash) a = mid + 1; else b = mid - 1;
    }}
    return -1;
}}

static void get_rig_indices(uint64_t rig, RigBoneCache *out) {{
    uint32_t slot = (uint32_t)((rig >> 6) & (MAX_RIG_CACHE - 1));
    if (g_rig_cache[slot].rig_ptr == rig) {{
        *out = g_rig_cache[slot];
        return;
    }}
    RigBoneCache tmp;
    memset(&tmp, 0, sizeof(tmp));
    tmp.rig_ptr = rig;
    tmp.map_count = *(const uint16_t *)(rig + 0x5A);
    tmp.bone_count = *(const uint16_t *)(rig + 0x8A);
    tmp.head_idx = rig_find_bone_raw(rig, 0x07C159A2u, tmp.bone_count);   /* Head */
    tmp.rhand_idx = rig_find_bone_raw(rig, 0x75F94D30u, tmp.bone_count);  /* RightHand */
    tmp.lhand_idx = rig_find_bone_raw(rig, 0xB675F36Cu, tmp.bone_count);  /* LeftHand */
    tmp.hips_idx = rig_find_bone_raw(rig, 0xDED10611u, tmp.bone_count);   /* Hips */
    g_rig_cache[slot] = tmp;
    *out = tmp;
}}

static void quat_norm(const float q[4], float out[4]) {{
    float len2 = q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3];
    if (len2 < 1e-12f || !isfinite(len2)) {{
        out[0] = 0.0f; out[1] = 0.0f; out[2] = 0.0f; out[3] = 1.0f;
        return;
    }}
    float inv = 1.0f / sqrtf(len2);
    out[0] = q[0]*inv; out[1] = q[1]*inv; out[2] = q[2]*inv; out[3] = q[3]*inv;
}}

static void quat_rot_vec(const float q[4], const float v[3], float out[3]) {{
    float tx = 2.0f * (q[1]*v[2] - q[2]*v[1]);
    float ty = 2.0f * (q[2]*v[0] - q[0]*v[2]);
    float tz = 2.0f * (q[0]*v[1] - q[1]*v[0]);
    out[0] = v[0] + q[3]*tx + (q[1]*tz - q[2]*ty);
    out[1] = v[1] + q[3]*ty + (q[2]*tx - q[0]*tz);
    out[2] = v[2] + q[3]*tz + (q[0]*ty - q[1]*tx);
}}

static void quat_mul(const float a[4], const float b[4], float out[4]) {{
    out[0] = a[3]*b[0] + a[0]*b[3] + a[1]*b[2] - a[2]*b[1];
    out[1] = a[3]*b[1] - a[0]*b[2] + a[1]*b[3] + a[2]*b[0];
    out[2] = a[3]*b[2] + a[0]*b[1] - a[1]*b[0] + a[2]*b[3];
    out[3] = a[3]*b[3] - a[0]*b[0] - a[1]*b[1] - a[2]*b[2];
}}

static void read_bone_world(uint64_t buf, int idx, int is_world, const float rootT[4], const float rootQ[4], float outPos[4], float outQuat[4]) {{
    const float *rec = (const float *)(buf + (uint64_t)idx * 0x20ULL);
    if (is_world) {{
        outPos[0] = rec[0]; outPos[1] = rec[1]; outPos[2] = rec[2]; outPos[3] = 1.0f;
        if (outQuat) {{
            outQuat[0] = rec[4]; outQuat[1] = rec[5]; outQuat[2] = rec[6]; outQuat[3] = rec[7];
        }}
    }} else {{
        float rot[3];
        quat_rot_vec(rootQ, rec, rot);
        outPos[0] = rootT[0] + rot[0];
        outPos[1] = rootT[1] + rot[1];
        outPos[2] = rootT[2] + rot[2];
        outPos[3] = 1.0f;
        if (outQuat) {{
            float bq[4] = {{ rec[4], rec[5], rec[6], rec[7] }};
            quat_mul(rootQ, bq, outQuat);
        }}
    }}
}}

static void link_npc_entity(uint64_t ent, uint64_t npc, uint64_t vt, uint64_t now_ms) {{
    if (!ptr_ok(ent) || !ptr_ok(npc)) return;
    uint32_t idx = (uint32_t)((ent >> 5) & (MAX_NPC_LINKS - 1));
    for (int p = 0; p < 16; ++p) {{
        uint32_t s = (idx + p) & (MAX_NPC_LINKS - 1);
        if (g_npc_links[s].entity_ptr == ent || g_npc_links[s].entity_ptr == 0 ||
            (now_ms - g_npc_links[s].last_seen_ms) > 4000ULL) {{
            g_npc_links[s].entity_ptr = ent;
            g_npc_links[s].npc_ptr = npc;
            g_npc_links[s].npc_vtable = vt;
            g_npc_links[s].last_seen_ms = now_ms;
            break;
        }}
    }}
}}

static int find_npc_link(uint64_t ent, uint64_t *out_npc, uint64_t *out_vt) {{
    if (!ptr_ok(ent)) return 0;
    uint32_t idx = (uint32_t)((ent >> 5) & (MAX_NPC_LINKS - 1));
    for (int p = 0; p < 16; ++p) {{
        uint32_t s = (idx + p) & (MAX_NPC_LINKS - 1);
        if (g_npc_links[s].entity_ptr == ent) {{
            *out_npc = g_npc_links[s].npc_ptr;
            *out_vt = g_npc_links[s].npc_vtable;
            return 1;
        }}
        if (g_npc_links[s].entity_ptr == 0) break;
    }}
    return 0;
}}

static void read_npc_faction_alert(uint64_t npc, GRWCharSlot *slot) {{
    slot->faction_raw = -1;
    slot->alert_raw = -1;
    slot->faction_1e8 = -1;
    slot->alert_328 = -1;
    if (!ptr_ok(npc)) return;
    __try {{
        uint64_t fsub = *(const uint64_t *)(npc + 0x258);
        if (ptr_ok(fsub)) {{
            slot->faction_raw = *(const int32_t *)(fsub + 0x10C);
        }}
        uint64_t sub1e8 = *(const uint64_t *)(npc + 0x1E8);
        if (ptr_ok(sub1e8)) {{
            slot->faction_1e8 = *(const int32_t *)(sub1e8 + 0x120);
        }}
        uint64_t asub1 = *(const uint64_t *)(npc + 0x320);
        if (ptr_ok(asub1)) {{
            slot->alert_raw = *(const int32_t *)(asub1 + 0x0F0);
        }}
        uint64_t asub2 = *(const uint64_t *)(npc + 0x328);
        if (ptr_ok(asub2)) {{
            slot->alert_328 = *(const int32_t *)(asub2 + 0x0C4);
        }}
    }} __except (EXCEPTION_EXECUTE_HANDLER) {{
    }}
}}

static void record_npc(uint64_t npc) {{
    if (!ptr_ok(npc)) return;
    __try {{
        uint64_t ent = *(const uint64_t *)(npc + 0x10);
        if (!ptr_ok(ent)) return;
        uint64_t vt = *(const uint64_t *)npc;
        uint64_t now_ms = GetTickCount64();
        link_npc_entity(ent, npc, vt, now_ms);
    }} __except (EXCEPTION_EXECUTE_HANDLER) {{
    }}
}}

static void write_live_save_file(uint32_t slot_id, const uint8_t *buf, uint32_t len, int is_write) {{
    if (!g_mod_dir[0] || !buf || len == 0 || len > MAX_LIVE_SAVE_BYTES) return;
    wchar_t data_dir[MAX_PATH * 2];
    wchar_t saves_dir[MAX_PATH * 2];
    wchar_t tmp_path[MAX_PATH * 2];
    wchar_t dst_path[MAX_PATH * 2];
    swprintf_s(data_dir, MAX_PATH * 2, L"%ls\\\\data", g_mod_dir);
    CreateDirectoryW(data_dir, NULL);
    swprintf_s(saves_dir, MAX_PATH * 2, L"%ls\\\\live_saves", data_dir);
    CreateDirectoryW(saves_dir, NULL);
    swprintf_s(tmp_path, MAX_PATH * 2, L"%ls\\\\slot_%u.tmp", saves_dir, slot_id);
    swprintf_s(dst_path, MAX_PATH * 2, L"%ls\\\\slot_%u.bin", saves_dir, slot_id);
    HANDLE hf = CreateFileW(tmp_path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf != INVALID_HANDLE_VALUE) {{
        DWORD written = 0;
        BOOL ok = WriteFile(hf, buf, (DWORD)len, &written, NULL);
        CloseHandle(hf);
        if (ok && written == (DWORD)len) {{
            MoveFileExW(tmp_path, dst_path, MOVEFILE_REPLACE_EXISTING);
            g_telemetry.last_save_slot = slot_id;
            if (is_write) g_telemetry.save_write_seq++;
            else g_telemetry.save_read_seq++;
        }} else {{
            DeleteFileW(tmp_path);
        }}
    }}
}}

static void save_track_flush_pending(SaveTrack *t) {{
    if (!t || !t->in_use || !t->pending_buf) return;
    uint32_t got = 0;
    __try {{
        if (t->pending_out_len && ptr_ok((uint64_t)t->pending_out_len)) {{
            got = *(t->pending_out_len);
        }} else {{
            got = t->pending_req;
        }}
        if (got > t->pending_req) got = t->pending_req;
        if (got > 0 && got <= MAX_LIVE_SAVE_BYTES && ptr_ok((uint64_t)t->pending_buf)) {{
            uint32_t end_off = t->pending_off + got;
            if (end_off <= MAX_LIVE_SAVE_BYTES) {{
                if (end_off > t->cap) {{
                    uint32_t new_cap = (end_off + 0xFFFFu) & ~0xFFFFu;
                    uint8_t *nb = (uint8_t *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, new_cap);
                    if (nb) {{
                        if (t->buf && t->max_len > 0) memcpy(nb, t->buf, t->max_len);
                        if (t->buf) HeapFree(GetProcessHeap(), 0, t->buf);
                        t->buf = nb;
                        t->cap = new_cap;
                    }}
                }}
                if (t->buf && end_off <= t->cap) {{
                    memcpy(t->buf + t->pending_off, t->pending_buf, got);
                    if (end_off > t->max_len) t->max_len = end_off;
                }}
            }}
        }}
    }} __except (EXCEPTION_EXECUTE_HANDLER) {{
    }}
    t->pending_buf = NULL;
    t->pending_off = 0;
    t->pending_req = 0;
    t->pending_out_len = NULL;
}}

static int __cdecl hook_uplay_save_open(uint32_t slot_id, uint32_t mode, uint32_t *out_handle, void *overlapped) {{
    int rc = g_orig_save_open ? g_orig_save_open(slot_id, mode, out_handle, overlapped) : 0;
    if (g_save_cs_init && out_handle) {{
        __try {{
            uint32_t h = *out_handle;
            EnterCriticalSection(&g_save_cs);
            for (int i = 0; i < MAX_SAVE_TRACKS; ++i) {{
                if (!g_save_tracks[i].in_use || g_save_tracks[i].handle == h) {{
                    if (g_save_tracks[i].buf) HeapFree(GetProcessHeap(), 0, g_save_tracks[i].buf);
                    memset(&g_save_tracks[i], 0, sizeof(SaveTrack));
                    g_save_tracks[i].in_use = 1;
                    g_save_tracks[i].handle = h;
                    g_save_tracks[i].slot_id = slot_id;
                    g_save_tracks[i].mode = mode;
                    break;
                }}
            }}
            LeaveCriticalSection(&g_save_cs);
        }} __except (EXCEPTION_EXECUTE_HANDLER) {{
        }}
    }}
    return rc;
}}

static int __cdecl hook_uplay_save_read(uint32_t handle, uint32_t bytes_to_read, uint32_t offset, void **buf_ptr, uint32_t *out_bytes_read, void *overlapped) {{
    if (g_save_cs_init) {{
        EnterCriticalSection(&g_save_cs);
        for (int i = 0; i < MAX_SAVE_TRACKS; ++i) {{
            if (g_save_tracks[i].in_use && g_save_tracks[i].handle == handle) {{
                save_track_flush_pending(&g_save_tracks[i]);
                break;
            }}
        }}
        LeaveCriticalSection(&g_save_cs);
    }}
    int rc = g_orig_save_read ? g_orig_save_read(handle, bytes_to_read, offset, buf_ptr, out_bytes_read, overlapped) : 0;
    if (g_save_cs_init && buf_ptr) {{
        __try {{
            uint8_t *raw_ptr = (uint8_t *)(*buf_ptr);
            if (ptr_ok((uint64_t)raw_ptr) && bytes_to_read > 0 && bytes_to_read <= MAX_LIVE_SAVE_BYTES) {{
                EnterCriticalSection(&g_save_cs);
                for (int i = 0; i < MAX_SAVE_TRACKS; ++i) {{
                    if (g_save_tracks[i].in_use && g_save_tracks[i].handle == handle) {{
                        g_save_tracks[i].pending_buf = raw_ptr;
                        g_save_tracks[i].pending_off = offset;
                        g_save_tracks[i].pending_req = bytes_to_read;
                        g_save_tracks[i].pending_out_len = out_bytes_read;
                        break;
                    }}
                }}
                LeaveCriticalSection(&g_save_cs);
            }}
        }} __except (EXCEPTION_EXECUTE_HANDLER) {{
        }}
    }}
    return rc;
}}

static int __cdecl hook_uplay_save_write(uint32_t handle, uint32_t bytes_to_write, void **buf_ptr, void *overlapped) {{
    if (g_save_cs_init && buf_ptr && bytes_to_write > 0 && bytes_to_write <= MAX_LIVE_SAVE_BYTES) {{
        uint32_t slot_id = 0xFFFFFFFFu;
        EnterCriticalSection(&g_save_cs);
        for (int i = 0; i < MAX_SAVE_TRACKS; ++i) {{
            if (g_save_tracks[i].in_use && g_save_tracks[i].handle == handle) {{
                slot_id = g_save_tracks[i].slot_id;
                break;
            }}
        }}
        LeaveCriticalSection(&g_save_cs);
        if (slot_id != 0xFFFFFFFFu) {{
            uint8_t *copy = (uint8_t *)HeapAlloc(GetProcessHeap(), 0, bytes_to_write);
            if (copy) {{
                int ok = 0;
                __try {{
                    const void *src = *buf_ptr;
                    if (ptr_ok((uint64_t)src)) {{
                        memcpy(copy, src, bytes_to_write);
                        ok = 1;
                    }}
                }} __except (EXCEPTION_EXECUTE_HANDLER) {{
                    ok = 0;
                }}
                if (ok) write_live_save_file(slot_id, copy, bytes_to_write, 1);
                HeapFree(GetProcessHeap(), 0, copy);
            }}
        }}
    }}
    return g_orig_save_write ? g_orig_save_write(handle, bytes_to_write, buf_ptr, overlapped) : 0;
}}

static int __cdecl hook_uplay_save_close(uint32_t handle) {{
    if (g_save_cs_init) {{
        uint32_t slot_id = 0xFFFFFFFFu;
        uint8_t *snap = NULL;
        uint32_t snap_len = 0;
        EnterCriticalSection(&g_save_cs);
        for (int i = 0; i < MAX_SAVE_TRACKS; ++i) {{
            if (g_save_tracks[i].in_use && g_save_tracks[i].handle == handle) {{
                save_track_flush_pending(&g_save_tracks[i]);
                if (g_save_tracks[i].mode == 0 && g_save_tracks[i].buf && g_save_tracks[i].max_len > 0) {{
                    slot_id = g_save_tracks[i].slot_id;
                    snap = g_save_tracks[i].buf;
                    snap_len = g_save_tracks[i].max_len;
                    g_save_tracks[i].buf = NULL;
                }} else if (g_save_tracks[i].buf) {{
                    HeapFree(GetProcessHeap(), 0, g_save_tracks[i].buf);
                    g_save_tracks[i].buf = NULL;
                }}
                g_save_tracks[i].in_use = 0;
                break;
            }}
        }}
        LeaveCriticalSection(&g_save_cs);
        if (snap && snap_len > 0) {{
            write_live_save_file(slot_id, snap, snap_len, 0);
            HeapFree(GetProcessHeap(), 0, snap);
        }}
    }}
    return g_orig_save_close ? g_orig_save_close(handle) : 0;
}}

static void install_uplay_save_hooks(const wchar_t *pad_dir) {{
    HMODULE hExe = GetModuleHandleW(NULL);
    HMODULE hUplay = GetModuleHandleW(L"uplay_r1_loader64.dll");
    if (!hExe || !hUplay) return;
    if (!g_save_cs_init) {{
        InitializeCriticalSection(&g_save_cs);
        g_save_cs_init = 1;
    }}
    const uint8_t *base = (const uint8_t *)hExe;
    struct {{ uint32_t rva; const char *name; void *hook; uint64_t **slot_out; void **orig_out; }} items[4] = {{
        {{ 0x0389D508u, "UPLAY_SAVE_Open",  (void *)&hook_uplay_save_open,  &g_iat_save_open,  (void **)&g_orig_save_open }},
        {{ 0x0389D518u, "UPLAY_SAVE_Close", (void *)&hook_uplay_save_close, &g_iat_save_close, (void **)&g_orig_save_close }},
        {{ 0x0389D520u, "UPLAY_SAVE_Read",  (void *)&hook_uplay_save_read,  &g_iat_save_read,  (void **)&g_orig_save_read }},
        {{ 0x0389D528u, "UPLAY_SAVE_Write", (void *)&hook_uplay_save_write, &g_iat_save_write, (void **)&g_orig_save_write }},
    }};
    int hooked = 0;
    for (int i = 0; i < 4; ++i) {{
        FARPROC real_fn = GetProcAddress(hUplay, items[i].name);
        uint64_t *iat_slot = (uint64_t *)(base + items[i].rva);
        if (!real_fn) continue;
        __try {{
            if (*iat_slot == (uint64_t)real_fn) {{
                DWORD old = 0;
                if (VirtualProtect(iat_slot, sizeof(uint64_t), PAGE_READWRITE, &old)) {{
                    *(items[i].orig_out) = (void *)real_fn;
                    *(items[i].slot_out) = iat_slot;
                    *iat_slot = (uint64_t)items[i].hook;
                    VirtualProtect(iat_slot, sizeof(uint64_t), old, &old);
                    hooked++;
                }}
            }}
        }} __except (EXCEPTION_EXECUTE_HANDLER) {{
        }}
    }}
    if (hooked > 0) {{
        char msg[128];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "UPLAY_SAVE IAT observer installed (%d/4)", hooked);
        log_loader_msg(pad_dir, msg);
    }}
}}

static void remove_uplay_save_hooks(void) {{
    struct {{ uint64_t *slot; void *orig; }} items[4] = {{
        {{ g_iat_save_open,  (void *)g_orig_save_open }},
        {{ g_iat_save_close, (void *)g_orig_save_close }},
        {{ g_iat_save_read,  (void *)g_orig_save_read }},
        {{ g_iat_save_write, (void *)g_orig_save_write }},
    }};
    for (int i = 0; i < 4; ++i) {{
        if (items[i].slot && items[i].orig) {{
            __try {{
                DWORD old = 0;
                if (VirtualProtect(items[i].slot, sizeof(uint64_t), PAGE_READWRITE, &old)) {{
                    *items[i].slot = (uint64_t)items[i].orig;
                    VirtualProtect(items[i].slot, sizeof(uint64_t), old, &old);
                }}
            }} __except (EXCEPTION_EXECUTE_HANDLER) {{}}
        }}
    }}
}}

static void record_skeleton(uint64_t skel) {{
    if (!ptr_ok(skel)) return;
    __try {{
        uint64_t ent = *(const uint64_t *)(skel + 0x10);
        uint64_t rig = *(const uint64_t *)(skel + 0x220);
        uint64_t pose = *(const uint64_t *)(skel + 0x238);
        if (!ptr_ok(rig) || !ptr_ok(pose)) return;
        uint64_t buf = *(const uint64_t *)(pose + 0x178);
        if (!ptr_ok(buf)) return;

        RigBoneCache rc;
        get_rig_indices(rig, &rc);
        if (rc.head_idx < 0 && rc.hips_idx < 0) return;

        uint32_t pflags = *(const uint32_t *)(pose + 0x8C);
        int is_world = (pflags & 0x04000000u) != 0;
        const float *rT = (const float *)(pose + 0x00);
        const float *rQraw = (const float *)(pose + 0x10);
        float rootT[4] = {{ rT[0], rT[1], rT[2], rT[3] }};
        float rootQ[4];
        quat_norm(rQraw, rootQ);
        if (!isfinite(rootT[0]) || !isfinite(rootT[1]) || !isfinite(rootT[2])) return;

        uint64_t now_ms = GetTickCount64();
        uint32_t idx = (uint32_t)((skel >> 5) & (MAX_CHARS - 1));
        GRWCharSlot *slot = NULL;
        for (int p = 0; p < 16; ++p) {{
            uint32_t s = (idx + p) & (MAX_CHARS - 1);
            if (g_telemetry.chars[s].skel_ptr == skel || g_telemetry.chars[s].skel_ptr == 0 ||
                (now_ms - g_telemetry.chars[s].last_seen_ms) > 3000ULL) {{
                slot = &g_telemetry.chars[s];
                break;
            }}
        }}
        if (!slot) return;

        int first_or_periodic = (slot->skel_ptr != skel) || ((g_telemetry.hook_calls[2] & 15ULL) == 0ULL);
        slot->skel_ptr = skel;
        slot->entity_ptr = ent;
        slot->rig_ptr = rig;
        slot->pose_ptr = pose;
        slot->bone_count = rc.bone_count;
        slot->rig_map_count = rc.map_count;
        slot->head_idx = rc.head_idx;
        slot->rhand_idx = rc.rhand_idx;
        slot->lhand_idx = rc.lhand_idx;
        slot->hips_idx = rc.hips_idx;
        slot->pose_flags = pflags;

        uint32_t vflags = 1u;
        slot->root_pos[0] = rootT[0]; slot->root_pos[1] = rootT[1]; slot->root_pos[2] = rootT[2]; slot->root_pos[3] = rootT[3];
        slot->root_quat[0] = rootQ[0]; slot->root_quat[1] = rootQ[1]; slot->root_quat[2] = rootQ[2]; slot->root_quat[3] = rootQ[3];

        if (rc.head_idx >= 0) {{
            read_bone_world(buf, rc.head_idx, is_world, rootT, rootQ, slot->head_pos, slot->head_quat);
            vflags |= 2u;
        }}
        if (rc.rhand_idx >= 0) {{
            read_bone_world(buf, rc.rhand_idx, is_world, rootT, rootQ, slot->rhand_pos, NULL);
            vflags |= 4u;
        }}
        if (rc.lhand_idx >= 0) {{
            read_bone_world(buf, rc.lhand_idx, is_world, rootT, rootQ, slot->lhand_pos, NULL);
            vflags |= 8u;
        }}
        if (rc.hips_idx >= 0) {{
            read_bone_world(buf, rc.hips_idx, is_world, rootT, rootQ, slot->hips_pos, NULL);
            vflags |= 16u;
        }}
        slot->valid_flags = vflags;

        if (ent && ent == g_telemetry.local_player_entity) {{
            g_telemetry.local_player_skel = skel;
        }}
        uint32_t is_p = 0;
        for (uint32_t pi = 0; pi < g_telemetry.player_entity_count && pi < 8u; ++pi) {{
            if (g_telemetry.player_entities[pi] == ent && ent != 0) {{
                is_p = 1;
                break;
            }}
        }}
        slot->is_player_comp = is_p;
        uint64_t l_npc = 0, l_vt = 0;
        if (find_npc_link(ent, &l_npc, &l_vt)) {{
            slot->npc_ptr = l_npc;
            slot->npc_vtable = l_vt;
            read_npc_faction_alert(l_npc, slot);
        }} else {{
            slot->npc_ptr = 0;
            slot->npc_vtable = 0;
            slot->faction_raw = -1;
            slot->alert_raw = -1;
            slot->faction_1e8 = -1;
            slot->alert_328 = -1;
        }}
        if (first_or_periodic && ptr_ok(ent)) {{
            slot->entity_vtable = *(const uint64_t *)ent;
            const uint32_t *eu = (const uint32_t *)ent;
            for (int k = 0; k < 32; ++k) slot->ent_u32[k] = eu[k];
        }}
        slot->last_seen_ms = now_ms;
    }} __except (EXCEPTION_EXECUTE_HANDLER) {{
    }}
}}

static void record_weapon(uint64_t wcomp) {{
    if (!ptr_ok(wcomp)) return;
    __try {{
        uint64_t now_ms = GetTickCount64();
        uint32_t idx = (uint32_t)((wcomp >> 5) & (MAX_WEAPONS - 1));
        GRWWeaponSlot *slot = NULL;
        for (int p = 0; p < 16; ++p) {{
            uint32_t s = (idx + p) & (MAX_WEAPONS - 1);
            if (g_telemetry.weapons[s].weapon_ptr == wcomp || g_telemetry.weapons[s].weapon_ptr == 0 ||
                (now_ms - g_telemetry.weapons[s].last_seen_ms) > 3000ULL) {{
                slot = &g_telemetry.weapons[s];
                break;
            }}
        }}
        if (!slot) return;
        slot->weapon_ptr = wcomp;
        slot->essence_ptr = *(const uint64_t *)(wcomp + 0xA8);
        slot->gun_root_owner = *(const uint64_t *)(wcomp + 0xB0);
        slot->gun_root_idx = *(const int32_t *)(wcomp + 0xB8);
        slot->muzzle_owner = *(const uint64_t *)(wcomp + 0xC0);
        slot->muzzle_idx = *(const int32_t *)(wcomp + 0xC8);
        uint64_t holder = *(const uint64_t *)(wcomp + 0xE0);
        slot->attachment_holder = holder;
        uint64_t mstuff = 0;
        if (ptr_ok(holder)) {{
            uint64_t mslot = *(const uint64_t *)(holder + 0xA8);
            if (ptr_ok(mslot)) {{
                mstuff = *(const uint64_t *)(mslot + 0x40);
            }}
        }}
        slot->muzzle_stuff = mstuff;
        slot->weapon_category = *(const uint32_t *)(wcomp + 0x17C);
        slot->muzzle_velocity = *(const float *)(wcomp + 0x1A0);
        slot->max_range = *(const float *)(wcomp + 0x1A4);
        slot->shoot_mode = *(const uint32_t *)(wcomp + 0x1BC);
        const uint32_t *eu = (const uint32_t *)(wcomp + 0xE0);
        for (int k = 0; k < 16; ++k) slot->extra_u32[k] = eu[k];
        slot->last_seen_ms = now_ms;
    }} __except (EXCEPTION_EXECUTE_HANDLER) {{
    }}
}}

void __cdecl grw_probe_record(uint64_t index, const void *saved_raw, void *return_address, uint64_t *stack_args) {{
    (void)return_address;
    if (g_shutting_down || index >= NUM_PROBES) return;
    const SavedArgs *a = (const SavedArgs *)saved_raw;
    g_telemetry.hook_calls[index]++;

    if (index == 0) {{ /* proj2 */
        __try {{
            float fovy = 0.0f;
            memcpy(&fovy, &stack_args[4], sizeof(fovy));
            if (isfinite(fovy) && fovy > 0.01f && fovy < 3.1f) {{
                if (fabsf(fovy - 1.5707964f) > 1e-3f) {{
                    g_telemetry.cam_fov_proj = fovy;
                }}
            }}
        }} __except (EXCEPTION_EXECUTE_HANDLER) {{}}
    }} else if (index == 1) {{ /* selector */
        if (!ptr_ok(a->rcx)) return;
        __try {{
            uint32_t mode = *(const uint32_t *)(a->rcx + 0x290);
            if (mode == 0) {{
                const float *m = (const float *)(a->rcx + 0x000);
                if (isfinite(m[12]) && isfinite(m[13]) && isfinite(m[14])) {{
                    g_telemetry.cam_ptr = a->rcx;
                    g_telemetry.cam_mode = mode;
                    g_telemetry.cam_vfov = *(const float *)(a->rcx + 0x2B0);
                    g_telemetry.cam_right[0] = m[0]; g_telemetry.cam_right[1] = m[1]; g_telemetry.cam_right[2] = m[2];
                    g_telemetry.cam_fwd[0] = m[4]; g_telemetry.cam_fwd[1] = m[5]; g_telemetry.cam_fwd[2] = m[6];
                    g_telemetry.cam_up[0] = m[8]; g_telemetry.cam_up[1] = m[9]; g_telemetry.cam_up[2] = m[10];
                    g_telemetry.cam_pos[0] = m[12]; g_telemetry.cam_pos[1] = m[13]; g_telemetry.cam_pos[2] = m[14];
                    g_telemetry.cam_last_ms = GetTickCount64();
                    g_telemetry.cam_valid = 1;
                    g_telemetry.frame_tick++;
                }}
            }}
        }} __except (EXCEPTION_EXECUTE_HANDLER) {{}}
    }} else if (index == 2) {{ /* SkeletonPostUpdate */
        record_skeleton(a->rcx);
    }} else if (index == 3) {{ /* cPlayerComponent::OnInit callee */
        if (!ptr_ok(a->rcx)) return;
        __try {{
            uint64_t ent = *(const uint64_t *)(a->rcx + 0x10);
            g_telemetry.local_player_comp = a->rcx;
            g_telemetry.local_player_entity = ent;
            if (ptr_ok(ent)) {{
                int seen = 0;
                uint32_t cnt = g_telemetry.player_entity_count;
                if (cnt > 8u) cnt = 8u;
                for (uint32_t pi = 0; pi < cnt; ++pi) {{
                    if (g_telemetry.player_entities[pi] == ent) {{ seen = 1; break; }}
                }}
                if (!seen && cnt < 8u) {{
                    g_telemetry.player_entities[cnt] = ent;
                    g_telemetry.player_entity_count = cnt + 1u;
                }}
            }}
        }} __except (EXCEPTION_EXECUTE_HANDLER) {{}}
    }} else if (index == 4) {{ /* weapon_update */
        record_weapon(a->rcx);
    }} else if (index >= 5 && index <= 7) {{ /* GR_cNPCComponent hooks */
        record_npc(a->rcx);
    }}
}}

static void install_tu25_hooks(const wchar_t *pad_dir) {{
    HMODULE hExe = GetModuleHandleW(NULL);
    if (!hExe) return;
    const uint8_t *base = (const uint8_t *)hExe;
    const IMAGE_DOS_HEADER *dos = (const IMAGE_DOS_HEADER *)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return;
    const IMAGE_NT_HEADERS64 *nt = (const IMAGE_NT_HEADERS64 *)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return;

    uint32_t ts = nt->FileHeader.TimeDateStamp;
    uint32_t soi = nt->OptionalHeader.SizeOfImage;
    g_telemetry.pe_timestamp = ts;
    g_telemetry.pe_size_of_image = soi;
    g_telemetry.module_base = (uint64_t)base;

    if (ts != 0x6A99768Au || soi != 0x185BA000u) {{
        char msg[256];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE,
            "Build mismatch (TS=%08X SOI=%08X, expected 6A99768A/185BA000). Live hooks disabled (map/DB mode active).",
            ts, soi);
        log_loader_msg(pad_dir, msg);
        g_telemetry.build_matched = 0;
        return;
    }}
    g_telemetry.build_matched = 1;

    uint32_t mask = 0;
    for (int i = 0; i < NUM_PROBES; ++i) {{
        uint8_t *thunk = (uint8_t *)(base + g_thunk_specs[i].thunk_rva);
        uint8_t *expect = (uint8_t *)(base + g_thunk_specs[i].impl_rva);
        if (thunk[0] != 0xE9) continue;
        int pad_ok = 1;
        for (int j = 5; j < 14; ++j) {{
            if (thunk[j] != 0xCC) {{ pad_ok = 0; break; }}
        }}
        if (!pad_ok) continue;
        int32_t rel = 0;
        memcpy(&rel, thunk + 1, sizeof(rel));
        if (thunk + 5 + rel != expect) continue;

        memcpy(g_saved_thunks[i], thunk, 16);
        grw_probe_originals[i] = (uint64_t)expect;

        uint8_t patch[14] = {{ 0xFF, 0x25, 0x00, 0x00, 0x00, 0x00 }};
        uint64_t dest = (uint64_t)g_thunk_specs[i].replacement;
        memcpy(patch + 6, &dest, sizeof(dest));

        DWORD old = 0;
        if (VirtualProtect(thunk, 14, PAGE_EXECUTE_READWRITE, &old)) {{
            memcpy(thunk, patch, 14);
            VirtualProtect(thunk, 14, old, &old);
            FlushInstructionCache(GetCurrentProcess(), thunk, 14);
            g_patched_addrs[i] = thunk;
            g_patched_ok[i] = 1;
            mask |= (1u << i);
        }}
    }}
    g_telemetry.hooks_mask = mask;
    char msg[192];
    _snprintf_s(msg, sizeof(msg), _TRUNCATE, "kTU25 hooks installed: mask=0x%02X (base=0x%llX)", mask, (unsigned long long)base);
    log_loader_msg(pad_dir, msg);
}}

static void remove_tu25_hooks(void) {{
    g_shutting_down = 1;
    remove_uplay_save_hooks();
    for (int i = 0; i < NUM_PROBES; ++i) {{
        if (g_patched_ok[i] && g_patched_addrs[i]) {{
            DWORD old = 0;
            if (VirtualProtect(g_patched_addrs[i], 14, PAGE_EXECUTE_READWRITE, &old)) {{
                memcpy(g_patched_addrs[i], g_saved_thunks[i], 14);
                VirtualProtect(g_patched_addrs[i], 14, old, &old);
                FlushInstructionCache(GetCurrentProcess(), g_patched_addrs[i], 14);
            }}
            g_patched_ok[i] = 0;
        }}
    }}
}}

static DWORD WINAPI hook_watcher_thread(LPVOID param) {{
    (void)param;
    if (!g_shutting_down) {{
        Sleep(1500);
        if (!g_shutting_down) {{
            install_tu25_hooks(g_mod_dir);
            if (g_telemetry.build_matched) {{
                install_uplay_save_hooks(g_mod_dir);
            }}
        }}
    }}
    return 0;
}}

static DWORD WINAPI launch_ghost_pad_thread(LPVOID param) {{
    HMODULE hSelf = (HMODULE)param;
    // Aguarda d3d11.dll para garantir que esta é a instância real do jogo (e não o bootstrap da Steam/Ubisoft Connect!)
    for (int i = 0; i < 300 && !g_shutting_down; ++i) {{
        if (GetModuleHandleW(L"d3d11.dll") != NULL) break;
        Sleep(200);
    }}
    if (g_shutting_down || GetModuleHandleW(L"d3d11.dll") == NULL) {{
        return 0;
    }}

    g_mutex = CreateMutexW(NULL, FALSE, L"Local\\\\GRW_GhostTacticalPad_Proxy_Mutex");
    if (!g_mutex || GetLastError() == ERROR_ALREADY_EXISTS) {{
        if (g_mutex) {{
            CloseHandle(g_mutex);
            g_mutex = NULL;
        }}
        return 0;
    }}

    wchar_t mod_path[MAX_PATH * 2];
    wchar_t game_dir[MAX_PATH * 2];
    wchar_t pad_dir[MAX_PATH * 2];
    wchar_t py_dir[MAX_PATH * 2];
    wchar_t dll_path[MAX_PATH * 2];

    DWORD n = GetModuleFileNameW(hSelf, mod_path, MAX_PATH * 2);
    if (n == 0 || n >= MAX_PATH * 2) return 0;

    lstrcpynW(game_dir, mod_path, MAX_PATH * 2);
    int last_sep = -1;
    for (int i = 0; game_dir[i]; ++i) {{
        if (game_dir[i] == L'\\\\' || game_dir[i] == L'/') last_sep = i;
    }}
    if (last_sep <= 0) return 0;
    game_dir[last_sep] = L'\\0';

    swprintf_s(pad_dir, MAX_PATH * 2, L"%ls\\\\GhostPad", game_dir);
    lstrcpynW(g_mod_dir, pad_dir, MAX_PATH * 2);
    swprintf_s(py_dir, MAX_PATH * 2, L"%ls\\\\python", pad_dir);

    HANDLE hWatch = CreateThread(NULL, 0, hook_watcher_thread, NULL, 0, NULL);
    if (hWatch) CloseHandle(hWatch);

    static const wchar_t *const preload_dlls[] = {{
        L"vcruntime140.dll",
        L"vcruntime140_1.dll",
        L"libffi-8.dll",
        L"python3.dll"
    }};
    for (int i = 0; i < 4; ++i) {{
        swprintf_s(dll_path, MAX_PATH * 2, L"%ls\\\\%ls", py_dir, preload_dlls[i]);
        if (file_exists(dll_path)) {{
            LoadLibraryExW(dll_path, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        }}
    }}

    swprintf_s(dll_path, MAX_PATH * 2, L"%ls\\\\python312.dll", py_dir);
    if (!file_exists(dll_path)) {{
        log_loader_msg(pad_dir, "Missing GhostPad\\\\python\\\\python312.dll");
        return 0;
    }}

    HMODULE hPy = LoadLibraryExW(dll_path, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!hPy) {{
        log_loader_msg(pad_dir, "LoadLibraryExW failed on GhostPad\\\\python\\\\python312.dll");
        return 0;
    }}

    typedef void (__cdecl *PFN_Py_InitializeEx)(int);
    typedef int  (__cdecl *PFN_Py_IsInitialized)(void);
    typedef int  (__cdecl *PFN_PyRun_SimpleString)(const char *);

    PFN_Py_InitializeEx pInitEx = (PFN_Py_InitializeEx)GetProcAddress(hPy, "Py_InitializeEx");
    PFN_Py_IsInitialized pIsInit = (PFN_Py_IsInitialized)GetProcAddress(hPy, "Py_IsInitialized");
    PFN_PyRun_SimpleString pRunSimple = (PFN_PyRun_SimpleString)GetProcAddress(hPy, "PyRun_SimpleString");

    if (!pInitEx || !pIsInit || !pRunSimple) {{
        log_loader_msg(pad_dir, "Failed to resolve CPython entry points in python312.dll");
        return 0;
    }}
    if (!pIsInit()) pInitEx(0);

    char utf8_gdir[MAX_PATH * 6];
    int ulen = WideCharToMultiByte(CP_UTF8, 0, game_dir, -1, utf8_gdir, (int)sizeof(utf8_gdir), NULL, NULL);
    if (ulen <= 1) {{
        log_loader_msg(pad_dir, "WideCharToMultiByte failed for game_dir");
        return 0;
    }}
    int raw_bytes = ulen - 1;
    char hex_gdir[MAX_PATH * 12 + 1];
    static const char hex_digits[] = "0123456789abcdef";
    for (int i = 0; i < raw_bytes; ++i) {{
        unsigned char b = (unsigned char)utf8_gdir[i];
        hex_gdir[i * 2] = hex_digits[(b >> 4) & 0xF];
        hex_gdir[i * 2 + 1] = hex_digits[b & 0xF];
    }}
    hex_gdir[raw_bytes * 2] = '\\0';

    char py_code[MAX_PATH * 16];
    int nfmt = _snprintf_s(
        py_code,
        sizeof(py_code),
        _TRUNCATE,
        "import sys, os\\n"
        "_gd = bytes.fromhex('%s').decode('utf-8')\\n"
        "_gp = os.path.join(_gd, 'GhostPad')\\n"
        "if _gp not in sys.path:\\n"
        "    sys.path.insert(0, _gp)\\n"
        "import launcher\\n"
        "launcher.run_embedded(_gd, %llu, %llu, %llu)\\n",
        hex_gdir,
        (unsigned long long)(ULONG_PTR)&g_app_hwnd,
        (unsigned long long)(ULONG_PTR)&g_telemetry,
        (unsigned long long)(ULONG_PTR)&grw_lzo1x_decompress
    );
    if (nfmt < 0) {{
        log_loader_msg(pad_dir, "Python bootstrap script truncated");
        return 0;
    }}
    if (pRunSimple(py_code) != 0) {{
        log_loader_msg(pad_dir, "PyRun_SimpleString returned non-zero");
    }}
    return 0;
}}

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {{
    if (fdwReason == DLL_PROCESS_ATTACH) {{
        DisableThreadLibraryCalls(hinstDLL);
        init_real_winmm();

        wchar_t exe_path[MAX_PATH * 2];
        DWORD len = GetModuleFileNameW(NULL, exe_path, MAX_PATH * 2);
        if (len > 0 && len < MAX_PATH * 2 && ends_with_ci(exe_path, L"\\\\grw.exe")) {{
            HANDLE th = CreateThread(NULL, 0, launch_ghost_pad_thread, hinstDLL, 0, NULL);
            if (th) CloseHandle(th);
        }}
    }} else if (fdwReason == DLL_PROCESS_DETACH) {{
        remove_tu25_hooks();
        HWND app_hwnd = g_app_hwnd;
        if (app_hwnd != NULL) {{
            HMODULE hUser32 = GetModuleHandleW(L"user32.dll");
            if (hUser32) {{
                typedef BOOL (WINAPI *PFN_PostMessageW)(HWND, UINT, WPARAM, LPARAM);
                PFN_PostMessageW pPostMessageW = (PFN_PostMessageW)GetProcAddress(hUser32, "PostMessageW");
                if (pPostMessageW) pPostMessageW(app_hwnd, 0x0010, 0, 0);
            }}
        }}
        if (lpvReserved == NULL && g_mutex) {{
            CloseHandle(g_mutex);
            g_mutex = NULL;
        }}
    }}
    return TRUE;
}}
'''
    (BUILD_DIR / "winmm_proxy.c").write_text(c_src, encoding="utf-8")


def compile_proxy() -> Path:
    if not VCVARS64.is_file():
        raise FileNotFoundError(f"vcvars64.bat não encontrado: {VCVARS64}")

    bat_path = BUILD_DIR / "build.bat"
    bat_path.write_text(
        "@echo off\n"
        f'call "{VCVARS64}" >nul\n'
        f'cd /d "{BUILD_DIR}"\n'
        "ml64 /nologo /c /Fo winmm_stubs.obj winmm_stubs.asm || exit /b 1\n"
        "cl /nologo /O2 /W3 /LD /MT winmm_proxy.c winmm_stubs.obj "
        "/link /DEF:winmm_proxy.def /OUT:winmm.dll kernel32.lib || exit /b 1\n",
        encoding="ascii",
    )
    res = subprocess.run(["cmd.exe", "/c", str(bat_path)], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        raise RuntimeError(f"Compilação falhou com código {res.returncode}")
    out_dll = BUILD_DIR / "winmm.dll"
    if not out_dll.is_file():
        raise FileNotFoundError("winmm.dll não foi gerada")
    return out_dll


def _download_embed_python() -> Path:
    dl_dir = BUILD_DIR / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dl_dir / "python-3.12.10-embed-amd64.zip"
    if zip_path.is_file() and zipfile.is_zipfile(zip_path):
        return zip_path
    print(f"Baixando Python 3.12.10 oficial embutido: {EMBED_PYTHON_URL}")
    req = urllib.request.Request(EMBED_PYTHON_URL, headers={"User-Agent": "Mozilla/5.0"})
    tmp_path = zip_path.with_suffix(".tmp")
    with urllib.request.urlopen(req, timeout=60) as resp, tmp_path.open("wb") as out:
        shutil.copyfileobj(resp, out)
    if not zipfile.is_zipfile(tmp_path):
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError("Arquivo baixado do Python embeddable não é um ZIP válido")
    tmp_path.replace(zip_path)
    return zip_path


def _copy_pkg_files(pkg_name: str, dst_root: Path, allowed_bins: set[str], allowed_py: set[str] | None = None) -> None:
    mod = importlib.import_module(pkg_name)
    src_dir = Path(mod.__file__).resolve().parent
    dst_dir = dst_root / pkg_name
    dst_dir.mkdir(parents=True, exist_ok=True)

    for src in src_dir.rglob("*"):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        rel = src.relative_to(src_dir)
        name = src.name
        if name in allowed_bins:
            pass
        elif src.suffix == ".py" or name == "py.typed":
            if allowed_py is not None and name not in allowed_py:
                continue
        else:
            continue
        dst = dst_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def build_embedded_python() -> Path:
    """Monta o runtime oficial assinado do Python 3.12 sem .exe e sem arquivos .zip aninhados."""
    emb_zip = _download_embed_python()
    emb_dir = BUILD_DIR / "embedded_python"
    if emb_dir.exists():
        shutil.rmtree(emb_dir)
    emb_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(emb_zip) as zf:
        zf.extractall(emb_dir)

    stdlib_zip = emb_dir / "python312.zip"
    if not stdlib_zip.is_file():
        raise FileNotFoundError(f"python312.zip não encontrado em {emb_dir}")
    lib_dir = emb_dir / "Lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(stdlib_zip) as zf:
        zf.extractall(lib_dir)
    stdlib_zip.unlink()

    for item in list(emb_dir.iterdir()):
        if not item.is_file():
            continue
        suf = item.suffix.lower()
        if suf in (".exe", ".zip", ".cat") or item.name.endswith("._pth"):
            item.unlink()
        elif suf in (".dll", ".pyd") and item.name not in KEEP_RUNTIME_BINARIES:
            item.unlink()

    (emb_dir / "python312._pth").write_text("Lib\n.\nsite-packages\n..\n", encoding="utf-8")

    sp_dir = emb_dir / "site-packages"
    sp_dir.mkdir(parents=True, exist_ok=True)
    _copy_pkg_files("PIL", sp_dir, allowed_bins={"_imaging.cp312-win_amd64.pyd"})
    _copy_pkg_files(
        "texture2ddecoder",
        sp_dir,
        allowed_bins={"_texture2ddecoder.pyd"},
        allowed_py={"__init__.py", "py.typed"},
    )

    for cache_dir in emb_dir.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)

    if not (emb_dir / "python312.dll").is_file():
        raise FileNotFoundError(f"python312.dll ausente em {emb_dir}")
    return emb_dir


def compile_standalone_exe() -> Path:
    """Compila GhostTacticalPad.exe independente (zero Python do sistema necessário)."""
    if not VCVARS64.is_file():
        raise FileNotFoundError(f"vcvars64.bat não encontrado: {VCVARS64}")

    exe_c = r'''#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>
#include <stdio.h>
#include <string.h>

#ifndef LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR
#define LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR 0x00000100
#endif
#ifndef LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
#define LOAD_LIBRARY_SEARCH_DEFAULT_DIRS 0x00001000
#endif

static int dir_or_file_exists(const wchar_t *p) {
    return GetFileAttributesW(p) != INVALID_FILE_ATTRIBUTES;
}

static int file_exists(const wchar_t *p) {
    DWORD a = GetFileAttributesW(p);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

static void to_hex_utf8(const wchar_t *ws, char *hex_out, size_t hex_cap) {
    char u8[MAX_PATH * 6];
    int n = WideCharToMultiByte(CP_UTF8, 0, ws, -1, u8, (int)sizeof(u8), NULL, NULL);
    if (n <= 1 || (size_t)((n - 1) * 2 + 1) > hex_cap) {
        hex_out[0] = '\0';
        return;
    }
    static const char hx[] = "0123456789abcdef";
    for (int i = 0; i < n - 1; ++i) {
        unsigned char b = (unsigned char)u8[i];
        hex_out[i * 2] = hx[(b >> 4) & 0xF];
        hex_out[i * 2 + 1] = hx[b & 0xF];
    }
    hex_out[(n - 1) * 2] = '\0';
}

int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE hPrev, PWSTR cmdLine, int nCmdShow) {
    (void)hInst; (void)hPrev; (void)cmdLine; (void)nCmdShow;
    wchar_t self_path[MAX_PATH * 2];
    wchar_t exe_dir[MAX_PATH * 2];
    wchar_t pad_dir[MAX_PATH * 2];
    wchar_t py_dir[MAX_PATH * 2];
    wchar_t probe[MAX_PATH * 2];

    DWORD n = GetModuleFileNameW(NULL, self_path, MAX_PATH * 2);
    if (n == 0 || n >= MAX_PATH * 2) return 1;
    lstrcpynW(exe_dir, self_path, MAX_PATH * 2);
    int sep = -1;
    for (int i = 0; exe_dir[i]; ++i) {
        if (exe_dir[i] == L'\\' || exe_dir[i] == L'/') sep = i;
    }
    if (sep <= 0) return 1;
    exe_dir[sep] = L'\0';

    swprintf_s(probe, MAX_PATH * 2, L"%ls\\GhostPad\\launcher.py", exe_dir);
    if (file_exists(probe)) {
        swprintf_s(pad_dir, MAX_PATH * 2, L"%ls\\GhostPad", exe_dir);
    } else {
        lstrcpynW(pad_dir, exe_dir, MAX_PATH * 2);
    }

    swprintf_s(probe, MAX_PATH * 2, L"%ls\\python\\python312.dll", pad_dir);
    if (file_exists(probe)) {
        swprintf_s(py_dir, MAX_PATH * 2, L"%ls\\python", pad_dir);
    } else {
        swprintf_s(py_dir, MAX_PATH * 2, L"%ls\\python", exe_dir);
    }

    int argc = 0;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    int want_console = 0;
    for (int i = 1; i < argc; ++i) {
        if (wcscmp(argv[i], L"--dry-run") == 0 || wcscmp(argv[i], L"--help") == 0 || wcscmp(argv[i], L"-h") == 0) {
            want_console = 1;
        }
    }
    if (want_console && AttachConsole(ATTACH_PARENT_PROCESS)) {
        FILE *fp = NULL;
        freopen_s(&fp, "CONOUT$", "w", stdout);
        freopen_s(&fp, "CONOUT$", "w", stderr);
    }

    swprintf_s(probe, MAX_PATH * 2, L"%ls\\python312.dll", py_dir);
    if (!file_exists(probe)) {
        if (argv) LocalFree(argv);
        MessageBoxW(NULL, L"GhostPad\\python\\python312.dll nao encontrado.", L"Ghost Tactical Pad", MB_OK | MB_ICONERROR);
        return 2;
    }

    static const wchar_t *const preloads[] = { L"vcruntime140.dll", L"vcruntime140_1.dll", L"libffi-8.dll", L"python3.dll" };
    for (int i = 0; i < 4; ++i) {
        wchar_t dep[MAX_PATH * 2];
        swprintf_s(dep, MAX_PATH * 2, L"%ls\\%ls", py_dir, preloads[i]);
        if (file_exists(dep)) {
            LoadLibraryExW(dep, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        }
    }
    HMODULE hPy = LoadLibraryExW(probe, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!hPy) {
        if (argv) LocalFree(argv);
        MessageBoxW(NULL, L"Falha ao carregar python312.dll embutida.", L"Ghost Tactical Pad", MB_OK | MB_ICONERROR);
        return 3;
    }

    typedef void (__cdecl *PFN_Py_InitializeEx)(int);
    typedef int  (__cdecl *PFN_PyRun_SimpleString)(const char *);
    typedef void (__cdecl *PFN_Py_FinalizeEx)(void);

    PFN_Py_InitializeEx pInitEx = (PFN_Py_InitializeEx)GetProcAddress(hPy, "Py_InitializeEx");
    PFN_PyRun_SimpleString pRunSimple = (PFN_PyRun_SimpleString)GetProcAddress(hPy, "PyRun_SimpleString");
    PFN_Py_FinalizeEx pFin = (PFN_Py_FinalizeEx)GetProcAddress(hPy, "Py_FinalizeEx");
    if (!pInitEx || !pRunSimple) {
        if (argv) LocalFree(argv);
        return 4;
    }
    pInitEx(0);

    char hex_pad[MAX_PATH * 12 + 1];
    char hex_py[MAX_PATH * 12 + 1];
    char hex_self[MAX_PATH * 12 + 1];
    to_hex_utf8(pad_dir, hex_pad, sizeof(hex_pad));
    to_hex_utf8(py_dir, hex_py, sizeof(hex_py));
    to_hex_utf8(self_path, hex_self, sizeof(hex_self));

    char args_list[16384];
    size_t pos = 0;
    pos += (size_t)_snprintf_s(args_list + pos, sizeof(args_list) - pos, _TRUNCATE, "[bytes.fromhex('%s').decode('utf-8')", hex_self);
    for (int i = 1; i < argc && pos + 256 < sizeof(args_list); ++i) {
        char ha[MAX_PATH * 4 + 1];
        to_hex_utf8(argv[i], ha, sizeof(ha));
        pos += (size_t)_snprintf_s(args_list + pos, sizeof(args_list) - pos, _TRUNCATE, ",bytes.fromhex('%s').decode('utf-8')", ha);
    }
    _snprintf_s(args_list + pos, sizeof(args_list) - pos, _TRUNCATE, "]");
    if (argv) LocalFree(argv);

    char py_code[24576];
    _snprintf_s(
        py_code,
        sizeof(py_code),
        _TRUNCATE,
        "import sys, os\n"
        "_pad = bytes.fromhex('%s').decode('utf-8')\n"
        "_py = bytes.fromhex('%s').decode('utf-8')\n"
        "if hasattr(os, 'add_dll_directory') and os.path.isdir(_py):\n"
        "    os.add_dll_directory(_py)\n"
        "if _pad not in sys.path:\n"
        "    sys.path.insert(0, _pad)\n"
        "sys.argv = %s\n"
        "import launcher\n"
        "launcher.main()\n",
        hex_pad,
        hex_py,
        args_list
    );
    int rc = pRunSimple(py_code);
    if (pFin) pFin();
    return rc;
}
'''
    (BUILD_DIR / "ghost_pad_exe.c").write_text(exe_c, encoding="utf-8")
    bat_path = BUILD_DIR / "build_exe.bat"
    bat_path.write_text(
        "@echo off\n"
        f'call "{VCVARS64}" >nul\n'
        f'cd /d "{BUILD_DIR}"\n'
        "cl /nologo /O2 /W3 /MT ghost_pad_exe.c "
        "/link /SUBSYSTEM:WINDOWS /OUT:GhostTacticalPad.exe kernel32.lib user32.lib shell32.lib || exit /b 1\n",
        encoding="ascii",
    )
    res = subprocess.run(["cmd.exe", "/c", str(bat_path)], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        raise RuntimeError(f"Compilação de GhostTacticalPad.exe falhou com código {res.returncode}")
    out_exe = BUILD_DIR / "GhostTacticalPad.exe"
    if not out_exe.is_file():
        raise FileNotFoundError("GhostTacticalPad.exe não foi gerado")
    return out_exe


def verify_clean_release(rel_dir: Path) -> None:
    """Garante apenas GhostTacticalPad.exe permitido como .exe, zero zips internos, zero cache/data e imports mínimos."""
    forbidden_ext = {".zip", ".7z", ".rar", ".whl", ".save", ".log", ".forge", ".wmap"}
    forbidden_dirs = {"cache", "data", "__pycache__"}
    for p in rel_dir.rglob("*"):
        if p.is_dir():
            assert p.name not in forbidden_dirs, f"Pasta proibida em mod_release: {p}"
        else:
            suf = p.suffix.lower()
            if suf == ".exe":
                assert p.name == "GhostTacticalPad.exe" and p.parent == rel_dir, f"Executável inesperado em mod_release: {p}"
            else:
                assert suf not in forbidden_ext, f"Arquivo proibido em mod_release: {p}"

    dll_imports = [d.lower() for d in parse_pe_imports(rel_dir / "winmm.dll")]
    assert dll_imports == ["kernel32.dll"], f"Imports inesperados em winmm.dll: {dll_imports}"
    exe_imports = {d.lower() for d in parse_pe_imports(rel_dir / "GhostTacticalPad.exe")}
    assert exe_imports <= {"kernel32.dll", "user32.dll", "shell32.dll"}, f"Imports inesperados em GhostTacticalPad.exe: {exe_imports}"


def _enduser_installer_bat() -> str:
    return (
        "@echo off\n"
        "setlocal\n"
        "title Ghost Tactical Pad — Instalador Wildlands\n"
        "set \"TARGET=\"\n"
        "for %%D in (\n"
        "  \"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Wildlands\"\n"
        "  \"C:\\Program Files (x86)\\Ubisoft\\Ubisoft Game Launcher\\games\\Tom Clancy's Ghost Recon Wildlands\"\n"
        "  \"C:\\Program Files\\Ubisoft\\Ubisoft Game Launcher\\games\\Tom Clancy's Ghost Recon Wildlands\"\n"
        "  \"D:\\SteamLibrary\\steamapps\\common\\Wildlands\"\n"
        "  \"D:\\Games\\Wildlands\"\n"
        ") do (\n"
        "  if exist \"%%~D\\GRW.exe\" if not defined TARGET set \"TARGET=%%~D\"\n"
        ")\n"
        "if not defined TARGET (\n"
        "  set /p \"TARGET=Informe o caminho da pasta de Ghost Recon Wildlands (onde fica GRW.exe): \"\n"
        ")\n"
        "if not exist \"%TARGET%\\GRW.exe\" (\n"
        "  echo ERRO: GRW.exe nao encontrado em \"%TARGET%\".\n"
        "  pause\n"
        "  exit /b 1\n"
        ")\n"
        "echo Instalando Ghost Tactical Pad em \"%TARGET%\"...\n"
        "copy /Y \"%~dp0winmm.dll\" \"%TARGET%\\winmm.dll\" >nul\n"
        "copy /Y \"%~dp0GhostTacticalPad.exe\" \"%TARGET%\\GhostTacticalPad.exe\" >nul\n"
        "xcopy /E /I /Y \"%~dp0GhostPad\" \"%TARGET%\\GhostPad\" >nul\n"
        "echo.\n"
        "echo Pronto! Abra o Ghost Recon Wildlands normalmente (ou execute GhostTacticalPad.exe para modo offline).\n"
        "pause\n"
    )


def package_release(dll_path: Path, exe_path: Path, embedded_py_dir: Path | None, make_zip: bool = True) -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    gp_dir = RELEASE_DIR / "GhostPad"
    gp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll_path, RELEASE_DIR / "winmm.dll")
    shutil.copy2(exe_path, RELEASE_DIR / "GhostTacticalPad.exe")

    for py_name in PY_SOURCE_FILES:
        src = ROOT_DIR / py_name
        if src.is_file():
            shutil.copy2(src, gp_dir / py_name)
    if embedded_py_dir is not None:
        shutil.copytree(embedded_py_dir, gp_dir / "python")

    if (ROOT_DIR / "web").is_dir():
        shutil.copytree(ROOT_DIR / "web", gp_dir / "web")
    if (ROOT_DIR / "Iniciar Ghost Pad.bat").is_file():
        shutil.copy2(ROOT_DIR / "Iniciar Ghost Pad.bat", gp_dir / "Iniciar Ghost Pad.bat")
    (RELEASE_DIR / "Instalar Mod.bat").write_text(_enduser_installer_bat(), encoding="utf-8")
    if (ROOT_DIR / "README.md").is_file():
        shutil.copy2(ROOT_DIR / "README.md", RELEASE_DIR / "README.md")
    if (ROOT_DIR / "LICENSE").is_file():
        shutil.copy2(ROOT_DIR / "LICENSE", RELEASE_DIR / "LICENSE")

    verify_clean_release(RELEASE_DIR)

    if make_zip:
        if RELEASE_ZIP.is_file():
            RELEASE_ZIP.unlink()
        with zipfile.ZipFile(RELEASE_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for item in sorted(RELEASE_DIR.rglob("*")):
                if item.is_file():
                    zf.write(item, item.relative_to(RELEASE_DIR).as_posix())


def main() -> None:
    ap = argparse.ArgumentParser(description="Compila winmm.dll e GhostTacticalPad.exe e gera o pacote standalone.")
    ap.add_argument("--proxy-only", action="store_true", help="Compila apenas winmm.dll/exe sem montar o runtime Python embutido")
    ap.add_argument("--no-zip", action="store_true", help="Não gera o .zip final de distribuição")
    args = ap.parse_args()

    exports = parse_pe_exports(SYSTEM_WINMM)
    print(f"Exports detectados em {SYSTEM_WINMM}: {len(exports)}")
    generate_sources(exports)
    dll_path = compile_proxy()
    exe_path = compile_standalone_exe()
    out_exports = parse_pe_exports(dll_path)
    imports = parse_pe_imports(dll_path)
    exe_imports = parse_pe_imports(exe_path)
    print(f"winmm.dll compilada ({dll_path.stat().st_size} bytes), exports={len(out_exports)}, imports={imports}")
    print(f"GhostTacticalPad.exe compilado ({exe_path.stat().st_size} bytes), imports={exe_imports}")
    assert len(out_exports) == len(exports)

    embedded_py_dir = None if args.proxy_only else build_embedded_python()
    package_release(dll_path, exe_path, embedded_py_dir, make_zip=not args.no_zip)
    print(f"Pacote pronto em {RELEASE_DIR}")


if __name__ == "__main__":
    main()
