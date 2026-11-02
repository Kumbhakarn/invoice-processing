"""Compare extraction JSON with verified references and write evaluation reports.

Run from ``backend`` with ``uv run python -m docextract.evaluation --help``.
Actual results are supplied as ``<document-id>.json`` files; no provider calls are
made by this module.
"""

from __future__ import annotations

import argparse
import json
import math
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

_NUMERIC_FIELDS = {
    "net_weight", "gross_weight", "number_of_packages", "quantity", "rate", "amount",
}
_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%d %b %Y", "%Y年%m月%d日",
    "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S",
)
_ITEM_IDENTITY_FIELDS = (
    "description_of_goods", "amount", "quantity", "hsn_code", "rate",
    "unit_of_measurement", "number_of_packages", "marks_and_numbers", "sr_no",
)


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _normalized_date(value: str) -> date | None:
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), date_format).date()
        except ValueError:
            continue
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _compare_value(
    expected: Any,
    actual: Any,
    field: str,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> dict[str, Any]:
    exact = type(expected) is type(actual) and expected == actual
    matched_by = "exact" if exact else None
    if not exact and isinstance(expected, str) and isinstance(actual, str):
        if field == "invoice_date":
            expected_date = _normalized_date(expected)
            actual_date = _normalized_date(actual)
            if expected_date is not None and expected_date == actual_date:
                matched_by = "normalized_date"
        elif _normalized_text(expected) == _normalized_text(actual):
            matched_by = "normalized_text"
    numeric_field = field in _NUMERIC_FIELDS or isinstance(expected, (int, float))
    if not exact and matched_by is None and numeric_field:
        expected_number = _number(expected)
        actual_number = _number(actual)
        if expected_number is not None and actual_number is not None:
            tolerance = max(absolute_tolerance, relative_tolerance * abs(expected_number))
            if abs(expected_number - actual_number) <= tolerance:
                matched_by = "numeric_tolerance"
    return {
        "expected": expected,
        "actual": actual,
        "exact_match": exact,
        "correct": matched_by is not None,
        "matched_by": matched_by,
        "missing": actual is None and expected is not None,
        "unexpected": expected is None and actual is not None,
    }


def _item_pair_score(expected: dict[str, Any], actual: dict[str, Any]) -> int:
    score = 0
    for field in _ITEM_IDENTITY_FIELDS:
        left, right = expected.get(field), actual.get(field)
        if left is None or right is None:
            continue
        if field in _NUMERIC_FIELDS:
            left_number, right_number = _number(left), _number(right)
            if left_number is not None and right_number is not None and math.isclose(
                left_number, right_number, rel_tol=1e-9, abs_tol=1e-9
            ):
                score += 2
        elif _normalized_text(str(left)) == _normalized_text(str(right)):
            score += 2
    return score


def _match_items(
    expected: list[dict[str, Any]], actual: list[dict[str, Any]]
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    candidates = sorted(
        (
            (_item_pair_score(expected[left], actual[right]), left, right)
            for left in range(len(expected))
            for right in range(len(actual))
        ),
        key=lambda candidate: (-candidate[0], candidate[1], candidate[2]),
    )
    matched_expected: set[int] = set()
    matched_actual: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for score, left, right in candidates:
        if score == 0:
            continue
        if left not in matched_expected and right not in matched_actual:
            pairs.append((left, right))
            matched_expected.add(left)
            matched_actual.add(right)
    return (
        pairs,
        [index for index in range(len(expected)) if index not in matched_expected],
        [index for index in range(len(actual)) if index not in matched_actual],
    )


def _field_result(
    field: str,
    expected: Any,
    actual: Any,
    absolute_tolerance: float,
    relative_tolerance: float,
    expected_present: bool = True,
    actual_present: bool = True,
) -> dict[str, Any]:
    if not actual_present or not expected_present:
        return {
            "field": field,
            "expected": expected,
            "actual": actual,
            "exact_match": False,
            "correct": False,
            "matched_by": None,
            "missing": not actual_present,
            "unexpected": expected is None and actual_present and actual is not None,
        }
    result = _compare_value(expected, actual, field, absolute_tolerance, relative_tolerance)
    result["field"] = field
    return result


def _evaluate_document(
    document_id: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
    absolute_tolerance: float,
    relative_tolerance: float,
) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    all_fields = sorted(
        (set(expected) | {key for key, value in actual.items() if value is not None})
        - {"line_items"}
    )
    for field in all_fields:
        fields.append(
            _field_result(
                field, expected.get(field), actual.get(field),
                absolute_tolerance, relative_tolerance,
                expected_present=field in expected, actual_present=field in actual,
            )
        )

    expected_items = expected.get("line_items")
    actual_items = actual.get("line_items")
    item_count_correct = True
    item_matches = 0
    item_expected = 0
    if "line_items" in expected or "line_items" in actual:
        if expected_items is None or actual_items is None:
            fields.append(
                _field_result(
                    "line_items", expected_items, actual_items,
                    absolute_tolerance, relative_tolerance,
                    expected_present="line_items" in expected,
                    actual_present="line_items" in actual,
                )
            )
            item_count_correct = expected_items is None and actual_items is None
            item_expected = len(expected_items) if isinstance(expected_items, list) else 0
            if isinstance(expected_items, list):
                for index, item in enumerate(expected_items):
                    fields.append({
                        "field": f"line_items[{index}]", "expected": item, "actual": None,
                        "exact_match": False, "correct": False, "matched_by": None,
                        "missing": True, "unexpected": False,
                    })
            if isinstance(actual_items, list):
                for index, item in enumerate(actual_items):
                    non_null = {key: value for key, value in item.items() if value is not None}
                    fields.append({
                        "field": f"line_items[extra:{index}]", "expected": None, "actual": non_null,
                        "exact_match": False, "correct": False, "matched_by": None,
                        "missing": False, "unexpected": bool(non_null),
                    })
        elif isinstance(expected_items, list) and isinstance(actual_items, list):
            pairs, missing_items, extra_items = _match_items(expected_items, actual_items)
            item_count_correct = len(expected_items) == len(actual_items)
            item_matches = len(pairs)
            item_expected = len(expected_items)
            for expected_index, actual_index in pairs:
                expected_item = expected_items[expected_index]
                actual_item = actual_items[actual_index]
                keys = sorted(set(expected_item) | set(actual_item))
                for key in keys:
                    fields.append(
                        _field_result(
                            f"line_items[{expected_index}].{key}", expected_item.get(key),
                            actual_item.get(key), absolute_tolerance, relative_tolerance,
                            expected_present=key in expected_item,
                            actual_present=key in actual_item,
                        )
                    )
            for index in missing_items:
                fields.append({
                    "field": f"line_items[{index}]",
                    "expected": expected_items[index], "actual": None,
                    "exact_match": False, "correct": False, "matched_by": None,
                    "missing": True, "unexpected": False,
                })
            for index in extra_items:
                extra_item = actual_items[index]
                non_null = {key: value for key, value in extra_item.items() if value is not None}
                fields.append({
                    "field": f"line_items[extra:{index}]", "expected": None, "actual": non_null,
                    "exact_match": False, "correct": False, "matched_by": None,
                    "missing": False, "unexpected": bool(non_null),
                })
        else:
            fields.append({
                "field": "line_items", "expected": expected_items, "actual": actual_items,
                "exact_match": False, "correct": False, "matched_by": None,
                "missing": actual_items is None, "unexpected": False,
            })
            item_count_correct = False

    totals = _summarize_fields(fields)
    return {
        "document_id": document_id,
        "fields": fields,
        "total_fields": totals["total_fields"],
        "correct_fields": totals["correct_fields"],
        "incorrect_fields": totals["incorrect_fields"],
        "missing_fields": totals["missing_fields"],
        "exact_matches": totals["exact_matches"],
        "normalized_text_matches": totals["normalized_text_matches"],
        "normalized_date_matches": totals["normalized_date_matches"],
        "numeric_tolerance_matches": totals["numeric_tolerance_matches"],
        "field_completeness": _ratio(
            totals["total_fields"] - totals["missing_fields"], totals["total_fields"]
        ),
        "unexpected_values": totals["unexpected_values"],
        "field_accuracy": _ratio(totals["correct_fields"], totals["total_fields"]),
        "line_items": {
            "expected_count": item_expected,
            "actual_count": len(actual_items) if isinstance(actual_items, list) else None,
            "matched_count": item_matches,
            "count_correct": item_count_correct,
        },
    }


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _summarize_fields(fields: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_fields": len(fields),
        "correct_fields": sum(field["correct"] for field in fields),
        "incorrect_fields": sum(not field["correct"] for field in fields),
        "missing_fields": sum(field["missing"] for field in fields),
        "unexpected_values": sum(field["unexpected"] for field in fields),
        "exact_matches": sum(field["exact_match"] for field in fields),
        "normalized_text_matches": sum(
            field["matched_by"] == "normalized_text" for field in fields
        ),
        "normalized_date_matches": sum(
            field["matched_by"] == "normalized_date" for field in fields
        ),
        "numeric_tolerance_matches": sum(
            field["matched_by"] == "numeric_tolerance" for field in fields
        ),
    }


def evaluate_dataset(
    expected_dir: Path,
    actual_dir: Path,
    absolute_tolerance: float = 0.01,
    relative_tolerance: float = 0.0,
) -> dict[str, Any]:
    """Evaluate same-ID JSON files; an absent actual file is a failed document."""
    expected_paths = {path.stem: path for path in expected_dir.glob("*.json")}
    actual_paths = {path.stem: path for path in actual_dir.glob("*.json")}
    if not expected_paths:
        raise ValueError(f"No expected JSON files found in {expected_dir}")
    documents = []
    for document_id, expected_path in sorted(expected_paths.items()):
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        if not isinstance(expected, dict):
            raise ValueError(f"Expected JSON must be an object: {expected_path}")
        actual_path = actual_paths.get(document_id)
        if actual_path is None:
            actual: dict[str, Any] = {}
        else:
            loaded_actual = json.loads(actual_path.read_text(encoding="utf-8"))
            if not isinstance(loaded_actual, dict):
                raise ValueError(f"Actual JSON must be an object: {actual_path}")
            actual = loaded_actual
        documents.append(
            _evaluate_document(
                document_id, expected, actual, absolute_tolerance, relative_tolerance
            )
        )
    totals = _summarize_fields([field for doc in documents for field in doc["fields"]])
    unexpected_documents = sorted(set(actual_paths) - set(expected_paths))
    line_documents = [
        doc for doc in documents
        if doc["line_items"]["expected_count"] > 0
        or (doc["line_items"]["actual_count"] or 0) > 0
    ]
    return {
        "total_documents": len(documents),
        "unexpected_documents": unexpected_documents,
        "total_fields": totals["total_fields"],
        "correct_fields": totals["correct_fields"],
        "incorrect_fields": totals["incorrect_fields"],
        "missing_fields": totals["missing_fields"],
        "field_completeness": _ratio(
            totals["total_fields"] - totals["missing_fields"], totals["total_fields"]
        ),
        "unexpected_values": totals["unexpected_values"],
        "exact_matches": totals["exact_matches"],
        "normalized_text_matches": totals["normalized_text_matches"],
        "normalized_date_matches": totals["normalized_date_matches"],
        "numeric_tolerance_matches": totals["numeric_tolerance_matches"],
        "field_accuracy": _ratio(totals["correct_fields"], totals["total_fields"]),
        "line_item_documents": len(line_documents),
        "line_item_count_correct": sum(
            doc["line_items"]["count_correct"] for doc in line_documents
        ),
        "line_item_field_accuracy": _ratio(
            sum(
                field["correct"]
                for doc in documents
                for field in doc["fields"]
                if field["field"] == "line_items" or field["field"].startswith("line_items[")
            ),
            sum(
                field["field"] == "line_items" or field["field"].startswith("line_items[")
                for doc in documents
                for field in doc["fields"]
            ),
        ),
        "tolerances": {"absolute": absolute_tolerance, "relative": relative_tolerance},
        "documents": documents,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    """Render a concise human-readable report, retaining field-level details."""
    lines = [
        "# Invoice extraction evaluation report", "",
        f"- Documents evaluated: {report['total_documents']}",
        f"- Fields evaluated: {report['total_fields']}",
        f"- Correct fields: {report['correct_fields']}",
        f"- Incorrect fields: {report['incorrect_fields']}",
        f"- Missing extracted values: {report['missing_fields']}",
        f"- Field completeness: {report['field_completeness']:.1%}",
        f"- Unexpected non-null values: {report['unexpected_values']}",
        f"- Actual files without expected references: {len(report['unexpected_documents'])}",
        f"- Exact field matches: {report['exact_matches']}",
        f"- Normalized text matches: {report['normalized_text_matches']}",
        f"- Normalized date matches: {report['normalized_date_matches']}",
        f"- Numeric tolerance matches: {report['numeric_tolerance_matches']}",
        f"- Field accuracy: {report['field_accuracy']:.1%}",
        f"- Line-item count correct: "
        f"{report['line_item_count_correct']}/{report['line_item_documents']}",
        f"- Line-item field accuracy: {report['line_item_field_accuracy']:.1%}", "",
        "## Per document", "",
        "| Document | Correct / fields | Accuracy | Line items (matched / expected; actual) |",
        "|---|---:|---:|---:|",
    ]
    for document in report["documents"]:
        items = document["line_items"]
        actual_count = "missing" if items["actual_count"] is None else str(items["actual_count"])
        lines.append(
            f"| {document['document_id']} | "
            f"{document['correct_fields']} / {document['total_fields']} "
            f"| {document['field_accuracy']:.1%} | {items['matched_count']} / "
            f"{items['expected_count']}; {actual_count} |"
        )
    lines.extend(["", "## Incorrect fields", ""])
    if report["unexpected_documents"]:
        lines.append("Unexpected actual document IDs: " + ", ".join(report["unexpected_documents"]))
        lines.append("")
    for document in report["documents"]:
        incorrect = [field for field in document["fields"] if not field["correct"]]
        if incorrect:
            lines.append(f"### {document['document_id']}")
            for field in incorrect:
                lines.append(
                    f"- `{field['field']}`: expected `{field['expected']!r}`, "
                    f"actual `{field['actual']!r}`"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(report: dict[str, Any], markdown_path: Path, json_path: Path) -> None:
    """Write both report formats, creating output directories as needed."""
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare actual extraction JSON to evaluation references."
    )
    parser.add_argument("--expected", type=Path, default=Path("../evaluation/expected"))
    parser.add_argument(
        "--actual", type=Path, required=True, help="Directory of <invoice-id>.json results"
    )
    parser.add_argument("--markdown", type=Path, default=Path("evaluation-report.md"))
    parser.add_argument(
        "--json", dest="json_report", type=Path, default=Path("evaluation-report.json")
    )
    parser.add_argument("--absolute-tolerance", type=float, default=0.01)
    parser.add_argument("--relative-tolerance", type=float, default=0.0)
    args = parser.parse_args()
    if args.absolute_tolerance < 0 or args.relative_tolerance < 0:
        parser.error("numeric tolerances must be non-negative")
    report = evaluate_dataset(
        args.expected, args.actual, args.absolute_tolerance, args.relative_tolerance
    )
    write_reports(report, args.markdown, args.json_report)
    print(render_markdown_report(report))


if __name__ == "__main__":
    main()
