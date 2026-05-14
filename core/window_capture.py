from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


@dataclass
class WindowInfo:
    hwnd: int
    title: str


def _is_window_visible(hwnd: int) -> bool:
    return bool(ctypes.windll.user32.IsWindowVisible(hwnd))


def _get_window_text(hwnd: int) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def list_task_windows() -> list[WindowInfo]:
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
    sorted_items = sorted(dedup.values(), key=lambda x: x.title.lower())
    return sorted_items


def is_window_minimized(hwnd: int) -> bool:
    try:
        return bool(ctypes.windll.user32.IsIconic(int(hwnd)))
    except Exception:
        return False
