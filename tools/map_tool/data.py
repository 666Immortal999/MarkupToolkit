from __future__ import annotations

import json
from pathlib import Path


def _maps_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "Presets" / "Maps"


def _parse_name(stem: str) -> tuple[str, str] | None:
    prefix = "map_navmesh_calibration_"
    if not stem.startswith(prefix):
        return None
    tail = stem[len(prefix):]
    if not tail:
        return None
    if "__" in tail:
        preset, sub = tail.split("__", 1)
        return preset.strip(), (sub.strip() or "default")
    return tail.strip(), "default"


def load_map_presets() -> dict[str, dict[str, list[object]]]:
    out: dict[str, dict[str, list[object]]] = {}
    base = _maps_dir()
    if not base.exists():
        return out
    for path in sorted(base.glob("map_navmesh_calibration_*.json")):
        parsed = _parse_name(path.stem)
        if not parsed:
            continue
        preset, subpreset = parsed
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        zones = (raw.get("zones") or {}).get("zones", []) if isinstance(raw, dict) else []
        ref_size = raw.get("reference_size", [1024, 1024]) if isinstance(raw, dict) else [1024, 1024]
        try:
            ref_w = max(1.0, float(ref_size[0]))
            ref_h = max(1.0, float(ref_size[1]))
        except Exception:
            ref_w, ref_h = 1024.0, 1024.0
        comps: list[object] = []
        for i, zone in enumerate(zones):
            if not isinstance(zone, dict):
                continue
            pts = zone.get("points", [])
            if not isinstance(pts, list) or not pts:
                continue
            xy = []
            for pt in pts:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    try:
                        xy.append((float(pt[0]), float(pt[1])))
                    except Exception:
                        pass
            if not xy:
                continue
            min_x = min(p[0] for p in xy)
            min_y = min(p[1] for p in xy)
            max_x = max(p[0] for p in xy)
            max_y = max(p[1] for p in xy)
            c = type("MapZone", (), {})()
            raw_label = str(zone.get("label", "")).strip()
            if not raw_label:
                aliases = zone.get("callout_names", zone.get("aliases", []))
                if isinstance(aliases, list) and aliases:
                    raw_label = str(aliases[0]).strip()
            c.name = raw_label or f"Zone {i+1}"
            c.x = max(0.0, min(1.0, min_x / ref_w))
            c.y = max(0.0, min(1.0, min_y / ref_h))
            c.w = max(0.01, min(1.0, (max_x - min_x) / ref_w))
            c.h = max(0.01, min(1.0, (max_y - min_y) / ref_h))
            c.zone_type = str(zone.get("mode", "blocked"))
            c.shape_type = str(zone.get("shape", "polygon"))
            c.polygon_closed = bool(zone.get("closed", zone.get("_closed", True)))
            c.polygon_points = [
                [max(0.0, min(1.0, float(px) / ref_w)), max(0.0, min(1.0, float(py) / ref_h))]
                for px, py in xy
            ]
            c.point_type = "" if c.shape_type != "circle" else "click"
            comps.append(c)
        zone_order = {"blocked": 0, "walkable": 1, "plant": 2, "zone callouts": 3, "jump spot": 4, "boost zone": 5}
        comps.sort(key=lambda z: (zone_order.get(str(getattr(z, "zone_type", "blocked")).lower(), 99), str(getattr(z, "name", "")).lower()))
        out.setdefault(preset, {})[subpreset] = comps
    return out


def save_map_preset(preset_name: str, subpreset_name: str, components: list[object], reference_size: tuple[int, int] = (1024, 1024)) -> bool:
    preset = str(preset_name or "").strip()
    sub = str(subpreset_name or "").strip() or "default"
    if not preset:
        return False
    base = _maps_dir()
    base.mkdir(parents=True, exist_ok=True)
    stem = f"map_navmesh_calibration_{preset}"
    if sub and sub != "default":
        stem = f"{stem}__{sub}"
    path = base / f"{stem}.json"

    ref_w = max(1.0, float(reference_size[0] if isinstance(reference_size, tuple) else 1024))
    ref_h = max(1.0, float(reference_size[1] if isinstance(reference_size, tuple) else 1024))
    zones: list[dict] = []
    for i, c in enumerate(components or []):
        poly = getattr(c, "polygon_points", None)
        if not isinstance(poly, list) or len(poly) < 2:
            continue
        points: list[list[float]] = []
        for p in poly:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                try:
                    nx = max(0.0, min(1.0, float(p[0])))
                    ny = max(0.0, min(1.0, float(p[1])))
                    points.append([round(nx * ref_w, 3), round(ny * ref_h, 3)])
                except Exception:
                    continue
        if len(points) < 2:
            continue
        zones.append(
            {
                "label": str(getattr(c, "name", f"Zone {i + 1}")).strip() or f"Zone {i + 1}",
                "mode": str(getattr(c, "zone_type", "blocked") or "blocked"),
                "shape": str(getattr(c, "shape_type", "polygon") or "polygon"),
                "closed": bool(getattr(c, "polygon_closed", True)),
                "points": points,
            }
        )

    payload = {
        "reference_size": [int(round(ref_w)), int(round(ref_h))],
        "zones": {"zones": zones},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
