from pathlib import Path


def test_leaving_configure_uses_configure_page_index_for_unsaved_prompt():
    source = Path("src/gui/modern_window.py").read_text(encoding="utf-8")

    assert "if current_index == 1 and index != 1:" in source
    assert 'resolve_unsaved_changes("open another tab")' in source
