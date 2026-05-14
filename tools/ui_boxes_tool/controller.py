from __future__ import annotations

from tools.ui_boxes_tool.data import load_ui_boxes_presets, save_ui_boxes_components


def apply_ui_boxes_mode(workspace) -> None:
    """Populate UI for UI Boxes mode and sync canvas components."""
    ui_boxes_presets = load_ui_boxes_presets()
    presets = sorted(ui_boxes_presets.keys())
    workspace.presets.set_items(presets)
    preset_name = workspace.presets.combo.currentText() or (presets[0] if presets else "")
    sub_map = ui_boxes_presets.get(preset_name, {})
    subpresets = sorted(sub_map.keys())
    workspace.subpresets.set_items(subpresets)
    subpreset_name = workspace.subpresets.combo.currentText() or (subpresets[0] if subpresets else "")
    comps = list(sub_map.get(subpreset_name, []))
    workspace.tool_settings.set_items([c.name for c in comps])
    workspace.ui_boxes_runtime.set_components(comps)
    # Load mode-specific extra display settings on mode select.
    mode_state = workspace._mode_states.get("ui_boxes", {})
    if isinstance(mode_state, dict):
        workspace.display.apply_state(mode_state.get("display", {}))
    workspace._apply_display_options()


def save_ui_boxes_mode(workspace) -> bool:
    interface_name = workspace.presets.combo.currentText().strip()
    preset_name = workspace.subpresets.combo.currentText().strip()
    if not interface_name or not preset_name:
        return False
    comps = list(workspace.ui_boxes_runtime.get_components() or [])
    save_ui_boxes_components(interface_name, preset_name, comps)
    return True


def reset_ui_boxes_mode(workspace) -> bool:
    apply_ui_boxes_mode(workspace)
    return True
