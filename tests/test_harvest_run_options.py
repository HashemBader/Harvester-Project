from src.gui.harvest_support import HarvestWorker
from src.gui.harvest_tab import HarvestTab


class _Check:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _Log:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class _HarvestStartState:
    def __init__(self, config):
        self.input_file = "isbns.tsv"
        self._config = config
        self._started_config = None
        self._started_targets = None
        self.chk_marc_only = _Check(True)
        self.chk_db_only = _Check(False)
        self.log_output = _Log()

    def _config_getter(self):
        return dict(self._config)

    def _check_recent_not_found_isbns(self, retry_days):
        return set()

    def _targets_getter(self):
        return [{"name": "Library of Congress", "selected": True}]

    def _start_worker(self, config, targets, bypass_retry_isbns=None):
        self._started_config = config
        self._started_targets = targets
        self._bypass_retry_isbns = bypass_retry_isbns


def test_marc_only_harvest_uses_configured_both_stop_rule():
    tab = _HarvestStartState(
        {
            "retry_days": 0,
            "call_number_mode": "both",
            "stop_rule": "continue_both",
        }
    )

    HarvestTab._on_start_clicked(tab)

    assert tab._started_config["call_number_mode"] == "both"
    assert tab._started_config["stop_rule"] == "continue_both"
    assert tab._started_config["both_stop_policy"] == "both"
    assert tab._started_config["db_only"] is True
    assert "MARC-only" in tab.log_output.text


class _WorkerState:
    def __init__(self, mode):
        self.config = {"call_number_mode": mode}


def test_successful_result_file_includes_nlm_classification_for_nlm_mode():
    worker = _WorkerState("nlmcn")

    assert HarvestWorker._successful_headers(worker) == [
        "ISBN",
        "NLM",
        "NLM Source",
        "NLM Classification",
        "Date",
    ]

    row = HarvestWorker._build_success_row(
        worker,
        "9780000000001",
        nlmcn="WR 140 D435172 2001",
        nlmcn_source="OCLC",
    )

    assert row[:4] == ["9780000000001", "WR 140 D435172 2001", "OCLC", "WR"]


def test_successful_result_file_includes_nlm_classification_for_both_mode():
    worker = _WorkerState("both")

    assert HarvestWorker._successful_headers(worker) == [
        "ISBN",
        "LCCN",
        "LCCN Source",
        "Classification",
        "NLM",
        "NLM Source",
        "NLM Classification",
        "Date",
    ]

    row = HarvestWorker._build_success_row(
        worker,
        "9780000000001",
        lccn="QA76.73.P98",
        lccn_source="LoC",
        nlmcn="WK 810 H438 2021",
        nlmcn_source="OCLC",
    )

    assert row[:7] == ["9780000000001", "QA76.73.P98", "LoC", "QA", "WK 810 H438 2021", "OCLC", "WK"]
