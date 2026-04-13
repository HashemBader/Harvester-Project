from src.gui.harvest_tab import HarvestTab, UIState


class _Timer:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class _Label:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text

    def setProperty(self, *_args):
        pass

    def style(self):
        return self

    def unpolish(self, *_args):
        pass

    def polish(self, *_args):
        pass


class _ProgressBar:
    def __init__(self):
        self.value = None

    def setValue(self, value):
        self.value = value


class _Signal:
    def __init__(self):
        self.emitted = False

    def emit(self):
        self.emitted = True


class _TabState:
    def __init__(self, input_file):
        self.current_state = UIState.READY
        self.input_file = str(input_file)
        self.run_timer = _Timer()
        self.lbl_run_elapsed = _Label()
        self.timer_is_paused = True
        self.processed_count = 9
        self.total_count = 10
        self.lbl_progress_text = _Label()
        self.progress_bar = _ProgressBar()
        self.log_output = _Label()
        self.harvest_reset = _Signal()
        self.refresh_called = False
        self.check_called = False
        self.clear_called = False

    def _refresh_active_profile_label(self):
        self.refresh_called = True

    def _check_start_conditions(self):
        self.check_called = True

    def _clear_input(self, emit_reset=True):
        self.clear_called = True


def test_profile_switch_preserves_existing_harvest_input_file(tmp_path):
    input_file = tmp_path / "isbns.tsv"
    input_file.write_text("9780131103627\n", encoding="utf-8")
    tab = _TabState(input_file)

    HarvestTab.reset_for_profile_switch(tab)

    assert tab.input_file == str(input_file)
    assert tab.refresh_called
    assert tab.check_called
    assert not tab.clear_called
    assert tab.harvest_reset.emitted
