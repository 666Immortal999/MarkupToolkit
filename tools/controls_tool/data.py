from __future__ import annotations

import json
from pathlib import Path


def _file() -> Path:
    toolkit_root = Path(__file__).resolve().parents[2]
    return toolkit_root / "Presets" / "UI_Points" / "ui_points.json"


def load_controls_presets() -> dict[str, dict[str, list[object]]]:
    path = _file()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    interfaces = raw.get("interfaces", {})
    out: dict[str, dict[str, list[object]]] = {}
    if not isinstance(interfaces, dict):
        return out
    for iname, idata in interfaces.items():
        interface_name = str(iname).strip()
        if not interface_name:
            continue
        if not isinstance(idata, dict):
            continue
        presets = idata.get("presets", {}) if isinstance(idata, dict) else {}
        if not isinstance(presets, dict):
            continue
        sub: dict[str, list[object]] = {}
        for pname, pdata in presets.items():
            preset_name = str(pname).strip()
            if not preset_name or preset_name in sub:
                continue
            points = pdata.get("points", {}) if isinstance(pdata, dict) else {}
            if not isinstance(points, dict):
                points = pdata.get("boxes", {}) if isinstance(pdata, dict) else {}
            items = []
            for n, p in points.items():
                c = type("Point", (), {})()
                c.name = str(n)
                c.x = float(p.get("x", p.get("nx", p.get("nx1", 0.5))))
                c.y = float(p.get("y", p.get("ny", p.get("ny1", 0.5))))
                c.w = 0.02
                c.h = 0.02
                c.point_type = str(p.get("point_type", "click"))
                items.append(c)
            sub[preset_name] = items
        if interface_name in out:
            out[interface_name].update(sub)
        else:
            out[interface_name] = sub
    return out


def save_controls_points(interface_name: str, preset_name: str, points: list[object]) -> None:
    path = _file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    interfaces = raw.setdefault("interfaces", {})
    iface = interfaces.setdefault(interface_name, {})
    presets = iface.setdefault("presets", {})
    preset = presets.setdefault(preset_name, {})
    point_map = {}
    for p in points:
        point_map[str(getattr(p, "name", ""))] = {
            "nx1": float(getattr(p, "x", 0.5)),
            "ny1": float(getattr(p, "y", 0.5)),
            "nx2": float(getattr(p, "x", 0.5)),
            "ny2": float(getattr(p, "y", 0.5)),
            "point_type": str(getattr(p, "point_type", "click")),
        }
    preset["points"] = point_map
    preset["boxes"] = point_map
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
