"""Structural checks for the manually curated invoice evaluation fixtures."""

import json
from pathlib import Path

import pytest

_DATASET_ROOT = Path(__file__).resolve().parents[2] / "evaluation"
_INVOICES = _DATASET_ROOT / "invoices"
_EXPECTED = _DATASET_ROOT / "expected"


def test_every_invoice_has_one_expected_json() -> None:
    invoice_ids = {path.stem for path in _INVOICES.glob("*.txt")}
    expected_ids = {path.stem for path in _EXPECTED.glob("*.json")}

    assert invoice_ids, "evaluation dataset contains no invoice sources"
    assert invoice_ids == expected_ids


@pytest.mark.parametrize("expected_path", sorted(_EXPECTED.glob("*.json")))
def test_expected_json_is_valid_object_with_source(expected_path: Path) -> None:
    assert (_INVOICES / f"{expected_path.stem}.txt").is_file()
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert isinstance(expected, dict)

