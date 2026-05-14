from __future__ import annotations


class UIBoxesRuntime:
    """Runtime state/ops for UI Boxes mode.

    Kept outside core canvas to avoid mode-specific logic in base widgets.
    """

    def __init__(self, capture_view) -> None:
        self.capture = capture_view

    def set_components(self, components) -> None:
        self.capture.set_markup_components(components)

    def get_components(self):
        return self.capture.get_markup_components()

    def add_component(self, name: str) -> None:
        self.capture.add_component(name)

    def rename_component(self, row: int, name: str) -> None:
        self.capture.rename_component(row, name)

    def remove_component(self, row: int) -> None:
        self.capture.remove_component(row)

    def undo(self) -> bool:
        return self.capture.undo()

    def redo(self) -> bool:
        return self.capture.redo()

