from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from dataclasses import dataclass

if sys.platform == "win32":
    from ctypes import wintypes


@dataclass
class WindowInfo:
    hwnd: int
    title: str


def _is_window_visible(hwnd: int) -> bool:
    if sys.platform != "win32":
        return False
    return bool(ctypes.windll.user32.IsWindowVisible(hwnd))


def _get_window_text(hwnd: int) -> str:
    if sys.platform != "win32":
        return ""
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def _list_windows_win32() -> list[WindowInfo]:
    results: list[WindowInfo] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, lparam):
        if not _is_window_visible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if not title:
            return True
        exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        if exstyle & 0x80:  # WS_EX_TOOLWINDOW
            return True
        results.append(WindowInfo(hwnd=int(hwnd), title=title))
        return True

    ctypes.windll.user32.EnumWindows(enum_proc, 0)
    dedup: dict[str, WindowInfo] = {}
    for item in results:
        dedup[f"{item.hwnd}:{item.title}"] = item
    return sorted(dedup.values(), key=lambda x: x.title.lower())


def _list_windows_linux_x11() -> list[WindowInfo]:
    # Requires X11 + wmctrl (Wayland sessions usually cannot be captured this way).
    if shutil.which("wmctrl") is None:
        return []

    try:
        proc = subprocess.run(
            ["wmctrl", "-lp"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except Exception:
        return []

    if proc.returncode != 0:
        return []

    items: list[WindowInfo] = []
    for line in proc.stdout.splitlines():
        # Format: 0x03c00007  0  1234 host Window Title
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        wid_hex = parts[0]
        title = parts[4].strip()
        if not title:
            continue
        try:
            wid = int(wid_hex, 16)
        except ValueError:
            continue
        items.append(WindowInfo(hwnd=wid, title=title))

    dedup: dict[str, WindowInfo] = {}
    for item in items:
        dedup[f"{item.hwnd}:{item.title}"] = item
    return sorted(dedup.values(), key=lambda x: x.title.lower())


def list_task_windows() -> list[WindowInfo]:
    if sys.platform == "win32":
        return _list_windows_win32()
    if sys.platform.startswith("linux"):
        return _list_windows_linux_x11()
    return []


def is_window_minimized(hwnd: int) -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.user32.IsIconic(int(hwnd)))
    except Exception:
        return False
