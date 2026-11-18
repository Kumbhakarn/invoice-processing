"""Confidence tests ensure optional signals renormalize without inventing certainty."""

import json

import pytest

from docextract.core.config import Settings
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import FieldEvidence, FieldSource, SourceCandidate
from docextract.services.evidence.confidence import score_field_confidence
from docextract.services.evidence.types import TextBox


def test_confidence_uses_grounding_match_ocr_logprob_and_validation_components() -> None:
    data = InvoiceExtractionData(invoice_number="INV-1")
    box = (0.1, 0.1, 0.3, 0.12)
    source = FieldSource(
        page=1,
        boxes=[box],
        status="located",
        reason=None,
        match_count=1,
        candidates=[SourceCandidate(page=1, boxes=[box], match_score=0.9, evidence_text="INV-1")],
        evidence_text="INV-1",
    )
    result = score_field_confidence(
        data,
        [FieldEvidence(field="invoice_number", source=source)],
        [TextBox(page=1, text="INV-1", bbox=box, source="ocr", ocr_confidence=0.8)],
        {"invoice_number": 0.5},
        Settings(),
    )

    assert result[0].confidence == pytest.approx(0.895)


def test_confidence_is_zero_when_source_is_ambiguous_or_unavailable() -> None:
    data = InvoiceExtractionData(invoice_number="INV-1")
    result = score_field_confidence(
        data,
        [
            FieldEvidence(field="invoice_number", source=FieldSource()),
            FieldEvidence(
                field="invoice_number",
                source=FieldSource(
                    status="ambiguous",
                    reason="ambiguous",
                    match_count=2,
                    candidates=[
                        SourceCandidate(page=1, boxes=[(0.1, 0.1, 0.2, 0.12)], match_score=1),
                        SourceCandidate(page=2, boxes=[(0.1, 0.1, 0.2, 0.12)], match_score=1),
                    ],
                ),
            ),
        ],
        [],
        {},
        Settings(),
    )

    assert [field.confidence for field in result] == [0, 0]


def test_confidence_weights_are_configurable_and_invalid_weights_rejected() -> None:
    data = InvoiceExtractionData(invoice_number="INV-1")
    source = FieldSource(
        page=1,
        boxes=[(0.1, 0.1, 0.2, 0.12)],
        status="located",
        reason=None,
        match_count=1,
    )
    settings = Settings(
        evidence_confidence_weights_json=json.dumps(
            {
                "grounding": 1,
                "match_quality": 0,
                "ocr_confidence": 0,
                "provider_logprob": 0,
                "validation": 0,
            }
        )
    )
    result = score_field_confidence(
        data,
        [FieldEvidence(field="invoice_number", source=source)],
        [],
        {},
        settings,
    )

    assert result[0].confidence == 1
    with pytest.raises(ValueError, match="documented components"):
        score_field_confidence(
            data,
            [FieldEvidence(field="invoice_number", source=source)],
            [],
            {},
            Settings(evidence_confidence_weights_json="{}"),
        )
