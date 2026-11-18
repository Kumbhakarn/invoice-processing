"""Uncalibrated, field-level confidence heuristics for evidence results."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping

from docextract.core.config import Settings
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import FieldEvidence, SourceCandidate
from docextract.services.evidence.types import TextBox
from docextract.services.invoice_validator import validate_invoice

_DEFAULT_WEIGHTS = {
    "grounding": 0.35,
    "match_quality": 0.25,
    "ocr_confidence": 0.15,
    "provider_logprob": 0.10,
    "validation": 0.15,
}


def score_field_confidence(
    data: InvoiceExtractionData,
    evidence: list[FieldEvidence],
    text_boxes: list[TextBox],
    field_logprobs: Mapping[str, float],
    settings: Settings,
) -> list[FieldEvidence]:
    """Score only located fields; omit unavailable components and reweight the rest.

    Formula: normalized weighted mean of document grounding, matcher score, OCR confidence,
    field-aligned OpenAI token probability, and the existing business validator result.
    Defaults live in EVIDENCE_CONFIDENCE_WEIGHTS_JSON; this is an uncalibrated heuristic,
    not a probability. Missing OCR/logprob components are left out and weights renormalized.
    """
    weights = _confidence_weights(settings.evidence_confidence_weights_json)
    issues_by_field: dict[str, list[str]] = {}
    for issue in validate_invoice(data).issues:
        issues_by_field.setdefault(issue.field, []).append(issue.severity)

    scored: list[FieldEvidence] = []
    for record in evidence:
        source = record.source
        if source.status != "located":
            scored.append(record.model_copy(update={"confidence": 0.0}))
            continue

        components: dict[str, float] = {"grounding": 1.0}
        selected_candidate = _selected_candidate(record)
        if selected_candidate is not None:
            components["match_quality"] = selected_candidate.match_score

        ocr_scores = _source_ocr_scores(source.page, source.boxes, text_boxes)
        if ocr_scores:
            components["ocr_confidence"] = sum(ocr_scores) / len(ocr_scores)

        logprob = field_logprobs.get(record.field)
        if logprob is not None and math.isfinite(logprob) and 0 <= logprob <= 1:
            components["provider_logprob"] = logprob

        field_issues = issues_by_field.get(record.field, [])
        if "error" in field_issues:
            components["validation"] = 0.0
        elif field_issues:
            components["validation"] = 0.5
        else:
            components["validation"] = 1.0

        available_weight = sum(weights[key] for key in components)
        confidence = (
            sum(weights[key] * value for key, value in components.items()) / available_weight
            if available_weight > 0
            else 0.0
        )
        scored.append(record.model_copy(update={"confidence": round(confidence, 4)}))
    return scored


def _confidence_weights(raw: str) -> dict[str, float]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("EVIDENCE_CONFIDENCE_WEIGHTS_JSON must be valid JSON") from exc
    if not isinstance(value, dict) or set(value) != set(_DEFAULT_WEIGHTS):
        raise ValueError("Confidence weights must define the five documented components")
    weights: dict[str, float] = {}
    for key, weight in value.items():
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("Confidence weights must be numeric")
        numeric = float(weight)
        if not math.isfinite(numeric) or numeric < 0:
            raise ValueError("Confidence weights must be finite and non-negative")
        weights[key] = numeric
    if sum(weights.values()) <= 0:
        raise ValueError("At least one confidence weight must be positive")
    return weights


def _selected_candidate(record: FieldEvidence) -> SourceCandidate | None:
    for candidate in record.source.candidates:
        if candidate.page == record.source.page and candidate.boxes == record.source.boxes:
            return candidate
    return record.source.candidates[0] if record.source.candidates else None


def _source_ocr_scores(
    page: int | None,
    boxes: list[tuple[float, float, float, float]],
    text_boxes: list[TextBox],
) -> list[float]:
    if page is None:
        return []
    scores: list[float] = []
    for text_box in text_boxes:
        if text_box.page != page or text_box.source != "ocr" or text_box.ocr_confidence is None:
            continue
        if any(_overlap_fraction(text_box.bbox, source_box) >= 0.2 for source_box in boxes):
            scores.append(text_box.ocr_confidence)
    return scores


def _overlap_fraction(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    intersection = width * height
    smaller = min(
        (left[2] - left[0]) * (left[3] - left[1]),
        (right[2] - right[0]) * (right[3] - right[1]),
    )
    return intersection / smaller if smaller > 0 else 0.0
