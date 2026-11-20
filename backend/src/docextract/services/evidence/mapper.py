"""Pure mapping from extraction data and evidence sidecars to per-field output."""

from collections.abc import Sequence

from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import FieldEvidence, FieldSource, MappedField


def _extracted_values(data: InvoiceExtractionData) -> dict[str, object]:
    """Flatten scalar invoice and line-item values to stable field paths."""
    values: dict[str, object] = {}
    for field_name in InvoiceExtractionData.model_fields:
        value = getattr(data, field_name)
        if field_name == "line_items":
            for index, item in enumerate(value or []):
                for item_field in item.__class__.model_fields:
                    values[f"line_items[{index}].{item_field}"] = getattr(item, item_field)
        else:
            values[field_name] = value
    return values


def map_extraction_fields(
    data: InvoiceExtractionData,
    evidence: Sequence[FieldEvidence],
) -> dict[str, MappedField]:
    """Map every scalar field while preserving values from the original extraction."""
    values = _extracted_values(data)
    evidence_by_field: dict[str, FieldEvidence] = {}
    for record in evidence:
        if record.field not in values:
            raise ValueError(f"Evidence references unknown field: {record.field}")
        if record.field in evidence_by_field:
            raise ValueError(f"Duplicate evidence for field: {record.field}")
        evidence_by_field[record.field] = record

    mapped: dict[str, MappedField] = {}
    for field_name, value in values.items():
        field_evidence = evidence_by_field.get(field_name)
        mapped[field_name] = MappedField(
            value=value,
            raw=field_evidence.raw if field_evidence else None,
            confidence=field_evidence.confidence if field_evidence else None,
            source=field_evidence.source if field_evidence else FieldSource(),
            edited=field_evidence.edited if field_evidence else False,
        )
    return mapped
