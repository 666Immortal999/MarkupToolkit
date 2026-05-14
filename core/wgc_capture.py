from __future__ import annotations

import threading
import time

try:
    from windows_capture import WindowsCapture
except Exception:
    WindowsCapture = None

from qt import QImage


class WgcHwndCapture:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.active = False
        self._capture = None
        self._thread = None
        self._lock = threading.Lock()
        self._latest: tuple[bytes, int, int] | None = None
        self._busy = False
        self._session = 0
        self.last_error = ""
        self.last_frame_ts = 0.0

    def start(self, hwnd: int, window_name: str | None = None) -> None:
        self._session += 1
        session = self._session
        self.stop()
        self.hwnd = int(hwnd)
        self.active = True
        self.last_error = ""
        self._busy = True

        if WindowsCapture is None:
            self.last_error = "windows-capture not installed"
            self._busy = False
            return

        try:
            cap = WindowsCapture(cursor_capture=False, draw_border=None, window_hwnd=self.hwnd)
        except Exception as e:
            self.last_error = f"hwnd failed: {e}"
            if window_name:
                cap = WindowsCapture(cursor_capture=False, draw_border=None, window_name=window_name)
            else:
                self.active = False
                self._busy = False
                return

        @cap.event
        def on_frame_arrived(frame, control):
            if not self.active or session != self._session:
                try:
                    control.stop()
                except Exception:
                    pass
                return
            arr = frame.frame_buffer
            if arr is None:
                return
            h, w = int(frame.height), int(frame.width)
            with self._lock:
                self._latest = (arr.tobytes(), w, h)
            self.last_frame_ts = time.monotonic()

        @cap.event
        def on_closed():
            if session == self._session:
                self.active = False

        self._capture = cap
        self._thread = threading.Thread(target=self._run_capture_safe, daemon=True)
        self._thread.start()

    def _run_capture_safe(self) -> None:
        cap = self._capture
        if cap is None:
            self._busy = False
            return
        try:
            if hasattr(cap, "start_free_threaded"):
                cap.start_free_threaded()
            else:
                cap.start()
        except Exception as e:
            self.active = False
            self.last_error = str(e)
        finally:
            self._busy = False

    def stop(self) -> None:
        self.active = False
        self.hwnd = None
        self._capture = None
        self._thread = None
        self.last_frame_ts = 0.0
        with self._lock:
            self._latest = None

    def get_latest_qimage(self):
        with self._lock:
            frame = self._latest
        if not frame:
            return None
        data, w, h = frame
        fmt = getattr(QImage, "Format_BGRA8888", None)
        if fmt is None and hasattr(QImage, "Format"):
            fmt = getattr(QImage.Format, "Format_BGRA8888", None)
        if fmt is None and hasattr(QImage, "Format"):
            fmt = getattr(QImage.Format, "Format_ARGB32", None)
        if fmt is None:
            fmt = QImage.Format_ARGB32
        return QImage(data, w, h, w * 4, fmt).copy()
