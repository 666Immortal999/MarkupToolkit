from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsManager:
    """Simple JSON-backed settings storage for UI state."""

    def __init__(self, path: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        self._path = path or (root / "settings.json")

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

