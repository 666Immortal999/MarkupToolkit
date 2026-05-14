from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UIBoxComponent:
    name: str
    x: float
    y: float
    w: float
    h: float


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _boxes_file() -> Path:
    toolkit_root = Path(__file__).resolve().parents[2]
    return toolkit_root / "Presets" / "UI_Boxes" / "ui_boxes.json"


def load_ui_boxes_presets() -> dict[str, dict[str, list[UIBoxComponent]]]:
    path = _boxes_file()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

    interfaces = raw.get("interfaces", {})
    if not isinstance(interfaces, dict):
        return {}

    result: dict[str, dict[str, list[UIBoxComponent]]] = {}
    for interface_name, iface_data in interfaces.items():
        interface_name = str(interface_name).strip()
        if not interface_name:
            continue
        if not isinstance(iface_data, dict):
            continue
        presets = iface_data.get("presets", {})
        if not isinstance(presets, dict):
            continue

        sub_map: dict[str, list[UIBoxComponent]] = {}
        for preset_name, preset_data in presets.items():
            preset_name = str(preset_name).strip()
            if not preset_name or preset_name in sub_map:
                continue
            if not isinstance(preset_data, dict):
                continue
            boxes = preset_data.get("boxes", {})
            if not isinstance(boxes, dict):
                boxes = {}
            comps: list[UIBoxComponent] = []
            for box_name, box in boxes.items():
                if not isinstance(box, dict):
                    continue
                try:
                    nx1 = _clamp01(box.get("nx1", 0.0))
                    ny1 = _clamp01(box.get("ny1", 0.0))
                    nx2 = _clamp01(box.get("nx2", 0.0))
                    ny2 = _clamp01(box.get("ny2", 0.0))
                except Exception:
                    continue
                x1, x2 = (nx1, nx2) if nx1 <= nx2 else (nx2, nx1)
                y1, y2 = (ny1, ny2) if ny1 <= ny2 else (ny2, ny1)
                comps.append(
                    UIBoxComponent(
                        name=str(box_name),
                        x=x1,
                        y=y1,
                        w=max(0.0, x2 - x1),
                        h=max(0.0, y2 - y1),
                    )
                )
                comps[-1].lock_move = bool(box.get("lock_move", False))
                comps[-1].lock_size = bool(box.get("lock_size", False))
                comps[-1].lock_aspect = bool(box.get("lock_aspect", False))
                comps[-1].ocr_filter = str(box.get("ocr_filter", "none"))
                comps[-1].ocr_max_value = box.get("ocr_max_value", None)
                comps[-1].ocr_letters_lang = str(box.get("ocr_letters_lang", "ru+en"))
                comps[-1].ocr_postprocess = bool(box.get("ocr_postprocess", False))
            sub_map[preset_name] = comps
        if interface_name in result:
            result[interface_name].update(sub_map)
        else:
            result[interface_name] = sub_map
    return result


def save_ui_boxes_components(interface_name: str, preset_name: str, components: list) -> None:
    path = _boxes_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    interfaces = raw.setdefault("interfaces", {})
    if not isinstance(interfaces, dict):
        interfaces = {}
        raw["interfaces"] = interfaces
    iface = interfaces.setdefault(interface_name, {})
    if not isinstance(iface, dict):
        iface = {}
        interfaces[interface_name] = iface
    presets = iface.setdefault("presets", {})
    if not isinstance(presets, dict):
        presets = {}
        iface["presets"] = presets
    preset = presets.setdefault(preset_name, {})
    if not isinstance(preset, dict):
        preset = {}
        presets[preset_name] = preset

    boxes: dict[str, dict] = {}
    for comp in components:
        name = str(getattr(comp, "name", "")).strip()
        if not name:
            continue
        x = _clamp01(getattr(comp, "x", 0.0))
        y = _clamp01(getattr(comp, "y", 0.0))
        w = max(0.0, min(1.0 - x, float(getattr(comp, "w", 0.0))))
        h = max(0.0, min(1.0 - y, float(getattr(comp, "h", 0.0))))
        boxes[name] = {
            "nx1": round(x, 6),
            "ny1": round(y, 6),
            "nx2": round(x + w, 6),
            "ny2": round(y + h, 6),
            "lock_move": bool(getattr(comp, "lock_move", False)),
            "lock_size": bool(getattr(comp, "lock_size", False)),
            "lock_aspect": bool(getattr(comp, "lock_aspect", False)),
            "ocr_filter": str(getattr(comp, "ocr_filter", "none")),
            "ocr_max_value": getattr(comp, "ocr_max_value", None),
            "ocr_letters_lang": str(getattr(comp, "ocr_letters_lang", "ru+en")),
            "ocr_postprocess": bool(getattr(comp, "ocr_postprocess", False)),
        }

    preset["boxes"] = boxes
    iface["active_preset"] = preset_name
    raw["active_interface"] = interface_name
    raw["active_preset"] = preset_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_interface(interface_name: str) -> None:
    save_ui_boxes_components(interface_name, "default", [])


def rename_interface(old_name: str, new_name: str) -> bool:
    path = _boxes_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except Exception:
        return False
    interfaces = raw.get("interfaces", {})
    if not isinstance(interfaces, dict) or old_name not in interfaces or new_name in interfaces:
        return False
    interfaces[new_name] = interfaces.pop(old_name)
    if raw.get("active_interface") == old_name:
        raw["active_interface"] = new_name
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def create_subpreset(interface_name: str, subpreset_name: str, source_components: list | None = None) -> None:
    save_ui_boxes_components(interface_name, subpreset_name, source_components or [])


def rename_subpreset(interface_name: str, old_name: str, new_name: str) -> bool:
    path = _boxes_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except Exception:
        return False
    interfaces = raw.get("interfaces", {})
    if not isinstance(interfaces, dict):
        return False
    iface = interfaces.get(interface_name, {})
    if not isinstance(iface, dict):
        return False
    presets = iface.get("presets", {})
    if not isinstance(presets, dict) or old_name not in presets or new_name in presets:
        return False
    presets[new_name] = presets.pop(old_name)
    if iface.get("active_preset") == old_name:
        iface["active_preset"] = new_name
    if raw.get("active_interface") == interface_name and raw.get("active_preset") == old_name:
        raw["active_preset"] = new_name
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def delete_interface(interface_name: str) -> bool:
    path = _boxes_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except Exception:
        return False
    interfaces = raw.get("interfaces", {})
    if not isinstance(interfaces, dict) or interface_name not in interfaces:
        return False
    del interfaces[interface_name]
    if not interfaces:
        raw["interfaces"] = {}
        raw["active_interface"] = ""
        raw["active_preset"] = ""
    else:
        first_iface = next(iter(interfaces.keys()))
        if raw.get("active_interface") == interface_name:
            raw["active_interface"] = first_iface
            iface = interfaces.get(first_iface, {})
            presets = iface.get("presets", {}) if isinstance(iface, dict) else {}
            raw["active_preset"] = next(iter(presets.keys()), "")
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def delete_subpreset(interface_name: str, subpreset_name: str) -> bool:
    path = _boxes_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except Exception:
        return False
    interfaces = raw.get("interfaces", {})
    if not isinstance(interfaces, dict):
        return False
    iface = interfaces.get(interface_name, {})
    if not isinstance(iface, dict):
        return False
    presets = iface.get("presets", {})
    if not isinstance(presets, dict) or subpreset_name not in presets:
        return False
    del presets[subpreset_name]
    if not presets:
        presets["default"] = {"boxes": {}}
    if iface.get("active_preset") == subpreset_name:
        iface["active_preset"] = next(iter(presets.keys()), "default")
    if raw.get("active_interface") == interface_name and raw.get("active_preset") == subpreset_name:
        raw["active_preset"] = iface.get("active_preset", "default")
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
