from src.utils.lccn_validator import is_valid_lccn


def test_lccn_validator_accepts_lc_classification_ranges():
    assert is_valid_lccn("QK710-899")
    assert is_valid_lccn("QC221-246")
    assert is_valid_lccn("TA401-492")


def test_lccn_validator_rejects_descending_or_open_ranges():
    assert not is_valid_lccn("QK899-710")
    assert not is_valid_lccn("QK710-")
    assert not is_valid_lccn("QK-899")
