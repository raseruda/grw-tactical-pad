"""Leitores e decodificadores AnvilNext 2.0 (.forge, .wmap, LZO1X, TextureMap) para Ghost Recon Wildlands."""
from __future__ import annotations

import ctypes
import io
import math
import os
import struct
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

import texture2ddecoder
from PIL import Image

WMAP_LOD_TILE_OFFSETS = (0, 16384, 20480, 21504, 21760, 21824, 21840)
WMAP_LOD_GRID_256 = (128, 64, 32, 16, 8, 4, 2)
ANVIL_BLOCKSET_MAGIC = 0x1004FA9957FBAA33

_NATIVE_LZO_FN: Any = None
_NATIVE_LZO_CHECKED = False


def _get_native_lzo():
    """Tenta resolver grw_lzo1x_decompress na winmm.dll quando embutido em GRW.exe."""
    global _NATIVE_LZO_FN, _NATIVE_LZO_CHECKED
    if _NATIVE_LZO_CHECKED:
        return _NATIVE_LZO_FN
    _NATIVE_LZO_CHECKED = True
    try:
        # Procura winmm carregada no processo atual (evita carregar outra DLL)
        k32 = ctypes.windll.kernel32
        k32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        k32.GetModuleHandleW.restype = ctypes.c_void_p
        k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        k32.GetProcAddress.restype = ctypes.c_void_p
        hmod = k32.GetModuleHandleW("winmm.dll")
        if hmod:
            addr = k32.GetProcAddress(hmod, b"grw_lzo1x_decompress")
            if addr:
                fn = ctypes.CFUNCTYPE(
                    ctypes.c_int,
                    ctypes.c_void_p,
                    ctypes.c_uint32,
                    ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_uint32),
                )(addr)
                _NATIVE_LZO_FN = fn
    except Exception:
        _NATIVE_LZO_FN = None
    return _NATIVE_LZO_FN


def lzo1x_decompress(src: bytes, expected_len: int = 0) -> bytes:
    """Descompacta stream LZO1X (usa rotina C nativa se disponível, senão Python puro)."""
    if not src:
        return b""
    native = _get_native_lzo()
    if native is not None and expected_len > 0:
        in_buf = (ctypes.c_ubyte * len(src)).from_buffer_copy(src)
        out_buf = (ctypes.c_ubyte * expected_len)()
        out_sz = ctypes.c_uint32(expected_len)
        rc = native(in_buf, len(src), out_buf, ctypes.byref(out_sz))
        if rc == 0 and out_sz.value == expected_len:
            return bytes(out_buf)

    out = bytearray()
    ip = 0
    n = len(src)
    t = src[ip]
    if t > 17:
        t -= 17
        ip += 1
        if t < 4:
            out.extend(src[ip : ip + t])
            ip += t
            t = src[ip]
            ip += 1
            state = "match"
        else:
            out.extend(src[ip : ip + t])
            ip += t
            state = "first_literal_run"
    else:
        state = "loop"

    while ip < n:
        if state == "loop":
            t = src[ip]
            ip += 1
            if t >= 16:
                state = "match"
                continue
            if t == 0:
                while src[ip] == 0:
                    t += 255
                    ip += 1
                t += 15 + src[ip]
                ip += 1
            out.extend(src[ip : ip + t + 3])
            ip += t + 3
            state = "first_literal_run"

        if state == "first_literal_run":
            t = src[ip]
            ip += 1
            if t >= 16:
                state = "match"
                continue
            m_pos = len(out) - 0x801 - (t >> 2) - (src[ip] << 2)
            ip += 1
            out.append(out[m_pos])
            out.append(out[m_pos + 1])
            out.append(out[m_pos + 2])
            state = "match_done"

        if state == "match":
            if t >= 64:
                m_pos = len(out) - 1 - ((t >> 2) & 7) - (src[ip] << 3)
                ip += 1
                t = (t >> 5) - 1
                for _ in range(t + 2):
                    out.append(out[m_pos])
                    m_pos += 1
            elif t >= 32:
                t &= 31
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 31 + src[ip]
                    ip += 1
                m_pos = len(out) - 1 - (src[ip] >> 2) - (src[ip + 1] << 6)
                ip += 2
                for _ in range(t + 2):
                    out.append(out[m_pos])
                    m_pos += 1
            elif t >= 16:
                m_pos = len(out) - ((t & 8) << 11)
                t &= 7
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 7 + src[ip]
                    ip += 1
                m_pos -= (src[ip] >> 2) + (src[ip + 1] << 6)
                ip += 2
                if m_pos == len(out):
                    break
                m_pos -= 0x4000
                for _ in range(t + 2):
                    out.append(out[m_pos])
                    m_pos += 1
            else:
                m_pos = len(out) - 1 - (t >> 2) - (src[ip] << 2)
                ip += 1
                out.append(out[m_pos])
                out.append(out[m_pos + 1])
            state = "match_done"

        if state == "match_done":
            t = src[ip - 2] & 3
            if t == 0:
                state = "loop"
                continue
            out.extend(src[ip : ip + t])
            ip += t
            t = src[ip]
            ip += 1
            state = "match"

    return bytes(out)


class WmapReader:
    """Leitor sob demanda para os mapas multi-LOD gr.wmap (satélite) e gr_h.wmap (Skell heatmap)."""

    def __init__(self, path: Path, cache_limit: int = 512) -> None:
        self.path = path
        self.valid = False
        self.full_size = 32768
        self.tile_px = 256
        self.grid_lod0 = 128
        self.num_lods = 7
        self._lock = threading.Lock()
        self._fh = None
        self._lru: OrderedDict[tuple[int, int, int], bytes] = OrderedDict()
        self._cache_limit = max(32, cache_limit)
        if path.is_file():
            try:
                fh = path.open("rb")
                hdr = fh.read(16)
                if len(hdr) == 16:
                    fs, tp, g0, nl = struct.unpack("<4I", hdr)
                    if fs == 32768 and tp == 256 and g0 == 128 and nl == 7:
                        self.full_size, self.tile_px, self.grid_lod0, self.num_lods = fs, tp, g0, nl
                        self._fh = fh
                        self.valid = True
                        return
                fh.close()
            except OSError:
                pass

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.close()
                except OSError:
                    pass
                self._fh = None
            self.valid = False

    def decode_tile_image(self, lod: int, col: int, row: int) -> Image.Image | None:
        """Decodifica um tile 256x256 (composto por 2x2 sub-tiles 128x128 BC1)."""
        if not self.valid or not (0 <= lod < self.num_lods):
            return None
        grid = WMAP_LOD_GRID_256[lod]
        if not (0 <= col < grid and 0 <= row < grid):
            return None

        w_sub = grid * 2
        base_sub_idx = WMAP_LOD_TILE_OFFSETS[lod] * 4
        chunks: list[tuple[int, int, bytes]] = []
        with self._lock:
            if self._fh is None:
                return None
            for dy in (0, 1):
                sy = row * 2 + dy
                for dx in (0, 1):
                    sx = col * 2 + dx
                    sub_idx = sy * w_sub + sx
                    off = 16 + (base_sub_idx + sub_idx) * 8192
                    self._fh.seek(off)
                    raw = self._fh.read(8192)
                    if len(raw) != 8192:
                        return None
                    chunks.append((dx * 128, dy * 128, raw))

        out = Image.new("RGBA", (256, 256))
        for px, py, raw in chunks:
            rgba = texture2ddecoder.decode_bc1(raw, 128, 128)
            sub = Image.frombytes("RGBA", (128, 128), rgba, "raw", "BGRA")
            out.paste(sub, (px, py))
        return out

    def get_tile_png(self, lod: int, col: int, row: int) -> bytes | None:
        """Retorna bytes PNG de um tile 256x256 usando cache LRU em memória."""
        key = (lod, col, row)
        with self._lock:
            cached = self._lru.get(key)
            if cached is not None:
                self._lru.move_to_end(key)
                return cached
        im = self.decode_tile_image(lod, col, row)
        if im is None:
            return None
        buf = io.BytesIO()
        im.save(buf, format="PNG", compress_level=3)
        data = buf.getvalue()
        with self._lock:
            self._lru[key] = data
            self._lru.move_to_end(key)
            while len(self._lru) > self._cache_limit:
                self._lru.popitem(last=False)
        return data


class HeightmapSampler:
    """Amostrador opcional de elevação 3D do terreno para checagem de oclusão de visão (LOS)."""

    def __init__(
        self,
        grid: list[list[float]] | None = None,
        min_x: float = -10500.0,
        max_x: float = 10500.0,
        min_y: float = -10500.0,
        max_y: float = 10500.0,
    ) -> None:
        self.grid = grid
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.rows = len(grid) if grid else 0
        self.cols = len(grid[0]) if (grid and grid[0]) else 0

    def has_data(self) -> bool:
        return self.rows > 1 and self.cols > 1

    def sample(self, x: float, y: float) -> float | None:
        if not self.has_data():
            return None
        dx = self.max_x - self.min_x
        dy = self.max_y - self.min_y
        if dx <= 0 or dy <= 0:
            return None
        u = max(0.0, min(1.0, (x - self.min_x) / dx))
        v = max(0.0, min(1.0, (y - self.min_y) / dy))
        fx = u * (self.cols - 1)
        fy = v * (self.rows - 1)
        x0 = int(fx)
        y0 = int(fy)
        x1 = min(self.cols - 1, x0 + 1)
        y1 = min(self.rows - 1, y0 + 1)
        tx = fx - x0
        ty = fy - y0
        assert self.grid is not None
        h00 = self.grid[y0][x0]
        h10 = self.grid[y0][x1]
        h01 = self.grid[y1][x0]
        h11 = self.grid[y1][x1]
        return (h00 * (1 - tx) + h10 * tx) * (1 - ty) + (h01 * (1 - tx) + h11 * tx) * ty

    def has_terrain_los(
        self,
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        clearance_m: float = 1.2,
        step_m: float = 4.0,
    ) -> bool:
        """Verifica se uma linha 3D entre p1 e p2 cruza alguma crista do terreno."""
        if not self.has_data():
            return True
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 2.0:
            return True
        steps = max(4, min(64, int(dist / max(1.0, step_m))))
        for i in range(1, steps):
            t = i / steps
            px = p1[0] + dx * t
            py = p1[1] + dy * t
            pz = p1[2] + dz * t
            th = self.sample(px, py)
            if th is not None and th > pz + clearance_m:
                return False
        return True


class ForgeArchive:
    """Leitor completo multi-seção para arquivos .forge (AnvilNext 2.0 / scimitar v27)."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.entries: list[dict[str, Any]] = []
        self._by_name: dict[str, list[dict[str, Any]]] = {}
        self._by_fid: dict[int, dict[str, Any]] = {}
        if self.path.is_file():
            self._index()

    def _index(self) -> None:
        with self.path.open("rb") as f:
            hdr = f.read(21)
            if len(hdr) < 21 or hdr[:8] != b"scimitar":
                raise ValueError(f"Arquivo .forge inválido: {self.path}")
            _magic, _unk1, ver, dh1_off = struct.unpack("<8sBiQ", hdr)
            if ver != 27:
                raise ValueError(f"Versão .forge inesperada ({ver}): {self.path}")
            f.seek(dh1_off + 36)
            sec_off = struct.unpack("<q", f.read(8))[0]
            while sec_off > 0:
                f.seek(sec_off)
                idx_cnt, _u1, off_idx, next_sec, _is, _ie, off_name, _u2 = struct.unpack("<iiqqiiqq", f.read(48))
                f.seek(off_idx)
                ibuf = f.read(idx_cnt * 20)
                f.seek(off_name)
                nbuf = f.read(idx_cnt * 192)
                for i in range(idx_cnt):
                    off_raw, fid, rsz = struct.unpack_from("<qqi", ibuf, i * 20)
                    rec_off = i * 192
                    res_id = struct.unpack_from("<I", nbuf, rec_off + 16)[0]
                    name = nbuf[rec_off + 44 : rec_off + 172].split(b"\0", 1)[0].decode("latin1", errors="replace")
                    item = {
                        "name": name,
                        "fid": fid,
                        "res_id": res_id,
                        "offset": off_raw,
                        "raw_size": rsz,
                    }
                    self.entries.append(item)
                    self._by_name.setdefault(name, []).append(item)
                    self._by_fid[fid] = item
                sec_off = next_sec

    def find_by_name(self, name: str) -> list[dict[str, Any]]:
        return list(self._by_name.get(name, ()))

    def read_payload_sets(self, entry: dict[str, Any]) -> list[bytes]:
        """Lê e descompacta os block sets de uma entrada .forge."""
        with self.path.open("rb") as f:
            f.seek(entry["offset"])
            raw = f.read(entry["raw_size"])
        pos = 0
        sets: list[bytes] = []
        while pos + 19 <= len(raw):
            magic, _ver, _comp, _m1, _m2, bcnt = struct.unpack_from("<QhBHHi", raw, pos)
            if magic != ANVIL_BLOCKSET_MAGIC:
                break
            pos += 19
            sizes = [struct.unpack_from("<HH", raw, pos + j * 4) for j in range(bcnt)]
            pos += bcnt * 4
            out = bytearray()
            for usz, csz in sizes:
                pos += 4  # pula Adler-32 modificado
                chunk = raw[pos : pos + csz]
                pos += csz
                if csz == usz:
                    out.extend(chunk)
                else:
                    dec = lzo1x_decompress(chunk, usz)
                    out.extend(dec)
            sets.append(bytes(out))
        return sets


def decode_anvil_texture_map(sets: list[bytes]) -> Image.Image | None:
    """Decodifica um recurso TextureMap (0xA2B7E917) descompactado para Image RGBA."""
    if not sets:
        return None
    body = sets[-1]
    if len(body) < 128:
        return None
    nlen = struct.unpack_from("<I", body, 8)[0]
    if nlen <= 0 or nlen > 256:
        return None
    base = 12 + nlen + 1 + 12  # após nome + nul + fid(8) + rid(4)
    if base + 112 > len(body):
        return None
    width, height, _depth, fmt = struct.unpack_from("<4I", body, base + 1)
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        return None
    pixel_off = base + 112
    data = body[pixel_off:]
    if not data:
        return None

    # Formatos observados no GRW AnvilNext 2.0:
    # 11 = R8 (1 byte/px), 9 = BC7 (HUD/Tacmap icons; BC3 fallback), 7/8 = BC1/DXT1, 0/1 = RGBA8/BGRA8
    # TextureMap UI sprites são gravados de baixo para cima no .forge -> espelha verticalmente.
    if fmt == 11 and len(data) >= width * height:
        return Image.frombytes("L", (width, height), data[: width * height]).convert("RGBA")
    if fmt == 9:
        need = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 16
        if len(data) >= need:
            try:
                rgba = texture2ddecoder.decode_bc7(data[:need], width, height)
            except Exception:
                rgba = texture2ddecoder.decode_bc3(data[:need], width, height)
            return Image.frombytes("RGBA", (width, height), rgba, "raw", "BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if fmt in (7, 8):
        need = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 8
        if len(data) >= need:
            rgba = texture2ddecoder.decode_bc1(data[:need], width, height)
            return Image.frombytes("RGBA", (width, height), rgba, "raw", "BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if fmt in (0, 1) and len(data) >= width * height * 4:
        return Image.frombytes("RGBA", (width, height), data[: width * height * 4], "raw", "BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    # Heurística por tamanho exato restante
    if len(data) == width * height:
        return Image.frombytes("L", (width, height), data).convert("RGBA")
    if len(data) == max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 16:
        try:
            rgba = texture2ddecoder.decode_bc7(data, width, height) if fmt == 9 else texture2ddecoder.decode_bc3(data, width, height)
        except Exception:
            rgba = texture2ddecoder.decode_bc3(data, width, height)
        return Image.frombytes("RGBA", (width, height), rgba, "raw", "BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if len(data) == max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 8:
        rgba = texture2ddecoder.decode_bc1(data, width, height)
        return Image.frombytes("RGBA", (width, height), rgba, "raw", "BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return None
