"""Deterministic tests for invoice extraction evaluation and reporting."""

import json
from pathlib import Path

from docextract.evaluation import evaluate_dataset, render_markdown_report


def test_exact_normalized_numeric_date_and_null_scoring(tmp_path: Path) -> None:
    expected_dir = tmp_path / "expected"
    actual_dir = tmp_path / "actual"
    expected_dir.mkdir()
    actual_dir.mkdir()
    (expected_dir / "doc.json").write_text(
        json.dumps(
            {
                "invoice_number": "INV 8", "buyer_name": "Acme Ltd", "invoice_date": "2025-03-14",
                "gross_weight": 100.0, "payment_terms": None,
            }
        ),
        encoding="utf-8",
    )
    (actual_dir / "doc.json").write_text(
        json.dumps(
            {
                "invoice_number": "INV 8", "buyer_name": "  ACME   Ltd ",
                "invoice_date": "14 March 2025", "gross_weight": 100.005, "payment_terms": None,
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_dataset(expected_dir, actual_dir)

    assert report["correct_fields"] == 5
    assert report["exact_matches"] == 2
    methods = {field["field"]: field["matched_by"] for field in report["documents"][0]["fields"]}
    assert methods["buyer_name"] == "normalized_text"
    assert methods["invoice_date"] == "normalized_date"
    assert methods["gross_weight"] == "numeric_tolerance"
    assert methods["payment_terms"] == "exact"


def test_absent_extracted_null_and_unexpected_values_are_not_hidden(tmp_path: Path) -> None:
    expected_dir = tmp_path / "expected"
    actual_dir = tmp_path / "actual"
    expected_dir.mkdir()
    actual_dir.mkdir()
    (expected_dir / "doc.json").write_text(
        json.dumps({"buyer_name": None, "invoice_number": "A-1"}), encoding="utf-8"
    )
    (actual_dir / "doc.json").write_text(
        json.dumps({"buyer_name": "Invented buyer"}), encoding="utf-8"
    )

    report = evaluate_dataset(expected_dir, actual_dir)

    assert report["correct_fields"] == 0
    assert report["incorrect_fields"] == 2
    assert report["missing_fields"] == 1
    assert report["unexpected_values"] == 1


def test_line_items_are_matched_by_content_not_list_position(tmp_path: Path) -> None:
    expected_dir = tmp_path / "expected"
    actual_dir = tmp_path / "actual"
    expected_dir.mkdir()
    actual_dir.mkdir()
    expected_items = [
        {"description_of_goods": "Paper", "quantity": 2, "amount": 10.0},
        {"description_of_goods": "Ink", "quantity": 1, "amount": 7.0},
    ]
    actual_items = [
        {"description_of_goods": "Ink", "quantity": 1, "amount": 7.0},
        {"description_of_goods": "Paper", "quantity": 2, "amount": 10.0},
    ]
    (expected_dir / "doc.json").write_text(
        json.dumps({"line_items": expected_items}), encoding="utf-8"
    )
    (actual_dir / "doc.json").write_text(json.dumps({"line_items": actual_items}), encoding="utf-8")

    report = evaluate_dataset(expected_dir, actual_dir)
    document = report["documents"][0]

    assert report["field_accuracy"] == 1.0
    assert report["line_item_field_accuracy"] == 1.0
    assert document["line_items"]["count_correct"] is True


def test_missing_actual_document_and_report_text(tmp_path: Path) -> None:
    expected_dir = tmp_path / "expected"
    actual_dir = tmp_path / "actual"
    expected_dir.mkdir()
    actual_dir.mkdir()
    (expected_dir / "doc.json").write_text(json.dumps({"invoice_number": "A-1"}), encoding="utf-8")

    report = evaluate_dataset(expected_dir, actual_dir)
    markdown = render_markdown_report(report)

    assert report["total_documents"] == 1
    assert report["missing_fields"] == 1
    assert "Documents evaluated: 1" in markdown
    assert "doc" in markdown
