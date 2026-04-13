from PyQt6.QtCore import Qt

from src.gui.config_tab import _set_stop_rule_control_state


class _Control:
    def __init__(self):
        self.enabled = None
        self.style = None
        self.cursor = None

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setStyleSheet(self, style):
        self.style = style

    def setCursor(self, cursor):
        self.cursor = cursor


def test_stop_rule_state_is_visibly_muted_when_disabled():
    label = _Control()
    combo = _Control()

    _set_stop_rule_control_state(label, combo, False)

    assert label.enabled is True
    assert combo.enabled is False
    assert label.style == ""
    assert "rgba" in combo.style
    assert label.cursor == Qt.CursorShape.ArrowCursor
    assert combo.cursor == Qt.CursorShape.ForbiddenCursor


def test_stop_rule_state_clears_inline_styles_when_enabled():
    label = _Control()
    combo = _Control()

    _set_stop_rule_control_state(label, combo, True)

    assert label.enabled is True
    assert combo.enabled is True
    assert label.style == ""
    assert combo.style == ""
    assert label.cursor == Qt.CursorShape.ArrowCursor
    assert combo.cursor == Qt.CursorShape.ArrowCursor
