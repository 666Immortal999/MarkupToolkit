from __future__ import annotations

import json
from pathlib import Path


PATTERN_KEYS = ("pattern", "pattern_raw", "pattern_spray")


def _file() -> Path:
    toolkit_root = Path(__file__).resolve().parents[2]
    return toolkit_root / "Presets" / "Patterns" / "spray_patterns.json"


def _load_raw() -> dict:
    path = _file()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def load_spray_presets() -> dict[str, dict[str, list[object]]]:
    raw = _load_raw()
    weapons = raw.get("weapons", {})
    if not isinstance(weapons, dict):
        return {}
    out: dict[str, dict[str, list[object]]] = {}
    for weapon_id, weapon_data in weapons.items():
        weapon_key = str(weapon_id).strip()
        if not weapon_key or not isinstance(weapon_data, dict):
            continue
        sub: dict[str, list[object]] = {}
        for pattern_key in PATTERN_KEYS:
            points = weapon_data.get(pattern_key, [])
            if not isinstance(points, list):
                continue
            items: list[object] = []
            for i, xy in enumerate(points):
                if not isinstance(xy, (list, tuple)) or len(xy) < 2:
                    continue
                try:
                    x = float(xy[0])
                    y = float(xy[1])
                except Exception:
                    continue
                c = type("SprayPoint", (), {})()
                c.name = f"{pattern_key}_{i + 1:02d}"
                c.x = x
                c.y = y
                c.w = 0.02
                c.h = 0.02
                c.point_type = "spray"
                items.append(c)
            sub[pattern_key] = items
        out[weapon_key] = sub
    return out


def save_spray_pattern(weapon_id: str, pattern_key: str, points: list[object]) -> bool:
    if pattern_key not in PATTERN_KEYS:
        return False
    path = _file()
    raw = _load_raw()
    weapons = raw.setdefault("weapons", {})
    if not isinstance(weapons, dict):
        weapons = {}
        raw["weapons"] = weapons
    weapon = weapons.get(weapon_id, {})
    if not isinstance(weapon, dict):
        weapon = {}
    weapon[pattern_key] = [[float(getattr(p, "x", 0.0)), float(getattr(p, "y", 0.0))] for p in points]
    weapons[weapon_id] = weapon
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
