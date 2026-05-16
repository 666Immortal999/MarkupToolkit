from __future__ import annotations

import subprocess
import threading
import time

from qt import QImage


class WaylandCapture:
    def __init__(self):
        self.active = False
        self._latest = None
        self._lock = threading.Lock()
        self.last_error = ""
        self.last_frame_ts = 0.0

    def start(self):
        self.active = True
        thread = threading.Thread(target=self._capture_loop, daemon=True)
        thread.start()

    def _capture_loop(self):
        try:
            while self.active:
                proc = subprocess.run(
                    ["grim", "-t", "ppm", "-l", "0", "-"],
                    capture_output=True,
                    check=False,
                )
                if proc.returncode != 0:
                    self.last_error = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
                    time.sleep(1 / 10)
                    continue
                img = QImage.fromData(proc.stdout, "PPM")
                if not img.isNull():
                    with self._lock:
                        self._latest = img
                    self.last_frame_ts = time.monotonic()
                time.sleep(1 / 30)
        except Exception as e:
            self.last_error = str(e)
            self.active = False

    def stop(self):
        self.active = False
        with self._lock:
            self._latest = None

    def get_latest_qimage(self):
        with self._lock:
            frame = self._latest
        if not frame:
            return None
        return frame.copy()
