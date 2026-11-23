"""Inicializador do Ghost Tactical Pad no Monitor 2 via Edge/Chrome App Mode."""
from __future__ import annotations

import ctypes
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from ctypes import wintypes
from pathlib import Path
from typing import Any

import anvil_formats
from config import CACHE_DIR, DATA_DIR, DEFAULT_PORT, ensure_dirs, get_game_dir, load_settings
from server import create_server

MONITORINFOF_PRIMARY = 0x00000001
SW_RESTORE = 9
SW_MAXIMIZE = 3
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)
_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

_user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), _MONITORENUMPROC, wintypes.LPARAM]
_user32.EnumDisplayMonitors.restype = wintypes.BOOL
_user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
_user32.GetMonitorInfoW.restype = wintypes.BOOL
_user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
_user32.EnumWindows.restype = wintypes.BOOL
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.IsWindowVisible.restype = wintypes.BOOL
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.ShowWindow.restype = wintypes.BOOL
_user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
_user32.SetWindowPos.restype = wintypes.BOOL
_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
_user32.MessageBoxW.restype = ctypes.c_int

_STDOUT_IS_LOG = False


def _setup_logging(force_redirect: bool = False) -> None:
    global _STDOUT_IS_LOG
    ensure_dirs()
    log_path = DATA_DIR / "ghost_pad.log"
    try:
        fh = open(log_path, "a", encoding="utf-8", buffering=1)
        if force_redirect or sys.stdout is None:
            sys.stdout = fh
            _STDOUT_IS_LOG = True
        if force_redirect or sys.stderr is None:
            sys.stderr = fh
    except OSError:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    if _STDOUT_IS_LOG:
        return
    try:
        ensure_dirs()
        with open(DATA_DIR / "ghost_pad.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def list_monitors() -> list[dict[str, Any]]:
    monitors: list[dict[str, Any]] = []

    @_MONITORENUMPROC
    def cb(hmon: int, _hdc: int, _rect: Any, _lparam: int) -> bool:
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if _user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcWork
            monitors.append({
                "device": info.szDevice,
                "primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
                "x": int(r.left),
                "y": int(r.top),
                "width": int(r.right - r.left),
                "height": int(r.bottom - r.top),
            })
        return True

    _user32.EnumDisplayMonitors(None, None, cb, 0)
    return monitors


def pick_secondary_monitor() -> dict[str, Any]:
    mons = list_monitors()
    for m in mons:
        if not m["primary"]:
            return m
    return mons[0] if mons else {"device": "DEFAULT", "primary": True, "x": 0, "y": 0, "width": 1280, "height": 720}


def find_browser_executable() -> Path | None:
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(pf) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
        Path(pf86) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
    ]
    if local:
        candidates.extend([
            Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(local) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(local) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
            Path(local) / "Vivaldi" / "Application" / "vivaldi.exe",
        ])
    try:
        import winreg
        for exe_name in ("msedge.exe", "chrome.exe", "brave.exe", "vivaldi.exe"):
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}") as k:
                        val, _ = winreg.QueryValueEx(k, None)
                        if val:
                            candidates.append(Path(str(val).strip('"')))
                except OSError:
                    continue
    except Exception:
        pass
    for c in candidates:
        if c.is_file():
            return c
    return None


def pick_free_port(preferred: int = DEFAULT_PORT) -> int:
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return 0


def _find_app_window(pid: int | None) -> int | None:
    found: list[int] = []

    @_WNDENUMPROC
    def cb(hwnd: int, _lparam: int) -> bool:
        if not _user32.IsWindowVisible(hwnd):
            return True
        ln = _user32.GetWindowTextLengthW(hwnd)
        if ln <= 0:
            return True
        buf = ctypes.create_unicode_buffer(ln + 1)
        _user32.GetWindowTextW(hwnd, buf, ln + 1)
        if "Ghost Tactical Pad" in buf.value:
            found.append(hwnd)
            return False
        if pid:
            wpid = wintypes.DWORD(0)
            _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value == pid:
                found.append(hwnd)
                return False
        return True

    _user32.EnumWindows(cb, 0)
    return found[0] if found else None


def move_window_to_monitor(pid: int | None, mon: dict[str, Any], timeout_s: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        hwnd = _find_app_window(pid)
        if hwnd:
            _user32.ShowWindow(hwnd, SW_RESTORE)
            _user32.SetWindowPos(hwnd, None, mon["x"], mon["y"], mon["width"], mon["height"], SWP_NOZORDER | SWP_SHOWWINDOW)
            _user32.ShowWindow(hwnd, SW_MAXIMIZE)
            return True
        time.sleep(0.15)
    return False


def _launch_browser_window(url: str, mon: dict[str, Any], browser: Path | None) -> tuple[subprocess.Popen[Any] | None, int | None]:
    if browser is not None:
        profile_dir = CACHE_DIR / "edge_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(browser),
            f"--app={url}",
            f"--user-data-dir={profile_dir}",
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
            f"--window-position={mon['x']},{mon['y']}",
            f"--window-size={mon['width']},{mon['height']}",
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        move_window_to_monitor(proc.pid, mon, timeout_s=8.0)
        return proc, _find_app_window(proc.pid)
    _log("No Chromium browser found; using default browser.")
    webbrowser.open(url)
    return None, None


def _write_hwnd_slot(hwnd_slot_addr: int, hwnd: int | None) -> None:
    if hwnd_slot_addr:
        ctypes.c_void_p.from_address(hwnd_slot_addr).value = int(hwnd) if hwnd else 0


def _bind_native_lzo(lzo_fn_addr: int) -> None:
    if lzo_fn_addr and lzo_fn_addr > 0x10000:
        try:
            fn = ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
            )(lzo_fn_addr)
            anvil_formats._NATIVE_LZO_FN = fn
            anvil_formats._NATIVE_LZO_CHECKED = True
        except Exception:
            pass


def run_embedded(game_dir: str, hwnd_slot_addr: int = 0, telemetry_addr: int = 0, lzo_fn_addr: int = 0) -> None:
    """Ponto de entrada chamado por winmm.dll diretamente dentro do processo GRW.exe."""
    py_dir = Path(__file__).resolve().parent / "python"
    if py_dir.is_dir() and hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(py_dir))
        except OSError:
            pass

    _setup_logging(force_redirect=True)
    _bind_native_lzo(lzo_fn_addr)

    mutex: int | None = None
    srv: Any = None
    runtime: Any = None
    try:
        mutex = _kernel32.CreateMutexW(None, False, "Local\\GRW_GhostTacticalPad_Launcher_Mutex")
        if ctypes.get_last_error() == 183:
            hwnd = _find_app_window(None)
            if hwnd:
                _user32.ShowWindow(hwnd, SW_MAXIMIZE)
                _user32.SetForegroundWindow(hwnd)
                _write_hwnd_slot(hwnd_slot_addr, hwnd)
            return

        mon = pick_secondary_monitor()
        browser = find_browser_executable()
        env_gdir = os.environ.get("GRW_GAME_DIR")
        gdir = Path(env_gdir) if env_gdir else (Path(game_dir) if game_dir else get_game_dir())
        settings = load_settings()
        preferred_port = int(settings.get("port", DEFAULT_PORT))
        port = pick_free_port(preferred_port)
        srv, runtime = create_server(game_dir=gdir, port=port, lan=False, telemetry_ptr=telemetry_addr or None)
        threading.Thread(target=srv.serve_forever, daemon=True, name="HTTPServer").start()

        url = f"http://127.0.0.1:{runtime.port}"
        _log(f"Embedded Ghost Tactical Pad started: game_dir={gdir}, url={url}, telemetry={hex(telemetry_addr)}, monitor={mon['device']}")

        if os.environ.get("GHOST_PAD_NO_BROWSER") != "1":
            _proc, hwnd = _launch_browser_window(url, mon, browser)
            if hwnd:
                _write_hwnd_slot(hwnd_slot_addr, hwnd)

        while not runtime.stop_event.is_set():
            time.sleep(1.0)
            if hwnd_slot_addr:
                _write_hwnd_slot(hwnd_slot_addr, _find_app_window(None))
    except Exception:
        _log(f"EMBEDDED FATAL ERROR:\n{traceback.format_exc()}")
    finally:
        if runtime is not None:
            runtime.close()
        if srv is not None:
            try:
                srv.shutdown()
                srv.server_close()
            except Exception:
                pass
        if mutex:
            _kernel32.CloseHandle(mutex)


def main() -> None:
    multiprocessing.freeze_support()
    import argparse

    _setup_logging()
    ap = argparse.ArgumentParser(description="Inicia o Ghost Tactical Pad maximizado no Monitor 2.")
    ap.add_argument("--lan", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--game-dir", default=None)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()

    mon = pick_secondary_monitor()
    browser = find_browser_executable()
    gdir = get_game_dir(args.game_dir)
    if args.dry_run:
        print("Game dir:", gdir)
        print("Monitors:", list_monitors())
        print("Target Monitor:", mon)
        print("Browser:", browser)
        return

    mutex = _kernel32.CreateMutexW(None, False, "Local\\GRW_GhostTacticalPad_Launcher_Mutex")
    if ctypes.get_last_error() == 183:
        hwnd = _find_app_window(None)
        if hwnd:
            _user32.ShowWindow(hwnd, SW_MAXIMIZE)
            _user32.SetForegroundWindow(hwnd)
        if mutex:
            _kernel32.CloseHandle(mutex)
        return

    settings = load_settings()
    preferred_port = args.port if args.port > 0 else int(settings.get("port", DEFAULT_PORT))
    port = preferred_port if args.port > 0 else pick_free_port(preferred_port)
    srv, runtime = create_server(game_dir=gdir, port=port, lan=args.lan)
    threading.Thread(target=srv.serve_forever, daemon=True, name="HTTPServer").start()

    url = f"http://127.0.0.1:{runtime.port}"
    _log(f"Standalone Ghost Tactical Pad listening at {url}")

    proc: subprocess.Popen[Any] | None = None
    saw_hwnd: int | None = None
    if not args.no_browser:
        proc, saw_hwnd = _launch_browser_window(url, mon, browser)

    start_ts = time.monotonic()
    saw_window = saw_hwnd is not None
    try:
        while not runtime.stop_event.is_set():
            time.sleep(0.5)
            if args.no_browser:
                continue
            elapsed = time.monotonic() - start_ts
            hwnd = _find_app_window(proc.pid if proc else None)
            if hwnd:
                saw_window = True
            if proc is None:
                if saw_window and not hwnd and elapsed > 10.0:
                    break
                continue
            if proc.poll() is not None and elapsed >= 10.0 and not hwnd:
                break
    except KeyboardInterrupt:
        pass
    finally:
        runtime.close()
        srv.shutdown()
        srv.server_close()
        if mutex:
            _kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
