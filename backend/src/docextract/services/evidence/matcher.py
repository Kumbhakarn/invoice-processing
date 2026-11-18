"""Normalize invoice values and locate justified candidates in page text boxes."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from docextract.core.config import Settings
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import (
    EvidenceReason,
    FieldEvidence,
    FieldSource,
    NormalizedBox,
    RawFieldText,
    SourceCandidate,
)
from docextract.services.evidence.types import TextBox

_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "invoice_number": ("invoice no", "invoice number", "inv no"),
    "invoice_date": ("invoice date", "date"),
    "buyer_name": ("buyer", "buyer name", "bill to"),
    "buyer_address": ("buyer address", "bill to"),
    "exporter_name": ("exporter", "seller", "shipper"),
    "exporter_address": ("exporter address", "seller address", "shipper address"),
    "consignee_name": ("consignee", "consignee name"),
    "consignee_address": ("consignee address", "delivery address"),
    "notify_party_name": ("notify party", "notify party name"),
    "notify_party_address": ("notify address", "notify party address"),
    "country_of_origin": ("country of origin", "origin"),
    "country_of_final_destination": ("final destination country", "country of destination"),
    "port_of_loading": ("port of loading", "loading port"),
    "port_of_discharge": ("port of discharge", "discharge port"),
    "final_destination": ("final destination", "destination"),
    "shipping_marks": ("shipping marks", "marks and numbers"),
    "currency": ("currency", "currency code"),
    "terms_of_delivery_and_payment": ("terms of delivery and payment",),
    "payment_terms": ("payment terms", "terms of payment"),
    "incoterms": ("incoterms", "terms of delivery"),
    "amount_in_words": ("amount in words", "say total"),
    "net_weight": ("net weight", "n.w."),
    "gross_weight": ("gross weight", "g.w."),
    "weight_unit": ("weight unit",),
    "sr_no": ("sr no", "s.no", "item no", "no."),
    "marks_and_numbers": ("marks and numbers", "marks"),
    "number_of_packages": ("packages", "no of packages", "cartons"),
    "description_of_goods": ("description", "description of goods", "goods"),
    "quantity": ("quantity", "qty"),
    "hsn_code": ("hsn", "hs code", "tariff code"),
    "unit_of_measurement": ("unit", "uom", "unit of measurement"),
    "rate": ("unit price", "rate", "price"),
    "amount": ("amount", "line total", "value"),
}
_NUMERIC_FIELDS = {
    "number_of_packages",
    "quantity",
    "rate",
    "amount",
    "net_weight",
    "gross_weight",
}
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d %Y",
    "%B %d %Y",
    "%B %d, %Y",
    "%d-%b-%Y",
)


@dataclass(frozen=True, slots=True)
class _Line:
    page: int
    boxes: tuple[TextBox, ...]
    text: str
    y_center: float


@dataclass(slots=True)
class _Candidate:
    page: int
    boxes: tuple[tuple[float, float, float, float], ...]
    score: float
    evidence_text: str
    estimated: bool = False
    context_score: float = 0.0

    @property
    def ranked_score(self) -> float:
        return self.score + self.context_score

    def public(self) -> SourceCandidate:
        return SourceCandidate(
            page=self.page,
            boxes=list(self.boxes),
            match_score=self.score,
            evidence_text=self.evidence_text,
            estimated=self.estimated,
        )


def match_invoice_fields(
    data: InvoiceExtractionData,
    text_boxes: list[TextBox],
    settings: Settings,
    *,
    ocr_failed: bool = False,
) -> list[FieldEvidence]:
    """Find field evidence without altering extracted values or inventing sources."""
    lines = _group_lines(text_boxes)
    values = _field_values(data)
    matches: dict[str, list[_Candidate]] = {}
    paths: dict[str, str] = {}
    for path, value in values.items():
        if value is None or not str(value).strip():
            continue
        field_name = path.rsplit(".", maxsplit=1)[-1]
        paths[path] = field_name
        matches[path] = _find_candidates(
            value,
            field_name,
            lines,
            settings.evidence_match_threshold,
        )

    for path, candidates in matches.items():
        field_name = paths[path]
        for candidate in candidates:
            candidate.context_score += _label_bonus(field_name, candidate, lines)

    anchors = _unique_line_item_anchors(
        matches,
        ambiguity_margin=settings.evidence_match_ambiguity_margin,
    )
    for path, candidates in matches.items():
        if not path.startswith("line_items[") or path.endswith(".description_of_goods"):
            continue
        item_index = _line_item_index(path)
        if item_index is None:
            continue
        anchor = anchors.get(item_index)
        if anchor is None:
            continue
        for candidate in candidates:
            if _same_row(candidate, anchor):
                candidate.context_score += 0.15

    evidence: list[FieldEvidence] = []
    for path in paths:
        candidates = matches[path]
        field_evidence = FieldEvidence(field=path)
        field_evidence.source = _select_source(
            candidates,
            threshold=settings.evidence_match_threshold,
            ambiguity_margin=settings.evidence_match_ambiguity_margin,
            ocr_failed=ocr_failed,
        )
        evidence.append(field_evidence)
    return evidence


def ground_raw_fields(
    data: InvoiceExtractionData,
    raw_fields: tuple[RawFieldText, ...],
    text_boxes: list[TextBox],
) -> dict[str, str]:
    """Keep provider raw strings only when a high-quality document match exists."""
    lines = _group_lines(text_boxes)
    values = _field_values(data)
    document_text = _source_text(" ".join(line.text for line in lines))
    grounded: dict[str, str] = {}
    for raw_field in raw_fields:
        value = values.get(raw_field.field)
        raw = raw_field.raw.strip()
        if value is None or not raw or str(value).strip() == raw:
            continue
        if raw_field.field in grounded:
            continue
        if _source_text(raw) in document_text:
            grounded[raw_field.field] = raw
    return grounded


def _source_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _field_values(data: InvoiceExtractionData) -> dict[str, object]:
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


def _group_lines(boxes: list[TextBox]) -> list[_Line]:
    ordered = sorted(boxes, key=lambda box: (box.page, _center_y(box), box.bbox[0]))
    groups: list[list[TextBox]] = []
    for box in ordered:
        center = _center_y(box)
        if (
            groups
            and groups[-1][0].page == box.page
            and abs(_center_y(groups[-1][0]) - center) <= max(0.006, box.bbox[3] - box.bbox[1])
        ):
            groups[-1].append(box)
        else:
            groups.append([box])
    result: list[_Line] = []
    for group in groups:
        sorted_group = tuple(sorted(group, key=lambda box: box.bbox[0]))
        result.append(
            _Line(
                page=sorted_group[0].page,
                boxes=sorted_group,
                text=" ".join(box.text for box in sorted_group),
                y_center=sum(_center_y(box) for box in sorted_group) / len(sorted_group),
            )
        )
    return result


def _find_candidates(
    value: object,
    field_name: str,
    lines: list[_Line],
    threshold: float,
) -> list[_Candidate]:
    target = str(value)
    target_norm = _normalize(target, field_name)
    if not target_norm:
        return []
    target_tokens = target.split()
    min_words = max(1, len(target_tokens) - 1)
    max_words = (
        max(3, len(target_tokens) + 1) if field_name == "invoice_date" else len(target_tokens) + 1
    )
    candidates: list[_Candidate] = []
    for start in range(len(lines)):
        segment: list[_Line] = []
        for end in range(start, min(len(lines), start + 5)):
            line = lines[end]
            if segment and (
                line.page != segment[-1].page or line.y_center - segment[-1].y_center > 0.055
            ):
                break
            segment.append(line)
            if len(segment) == 1 and len(line.boxes) == 1 and line.boxes[0].source == "ocr":
                candidates.extend(
                    _match_inside_ocr_line(
                        target,
                        field_name,
                        line.boxes[0],
                        threshold,
                    )
                )
            elif len(segment) > 1 and all(
                len(segment_line.boxes) == 1 and segment_line.boxes[0].source == "ocr"
                for segment_line in segment
            ):
                actual_text = " ".join(segment_line.text for segment_line in segment)
                score = _similarity(target, actual_text, field_name)
                if score >= 0.45:
                    segment_boxes = tuple(segment_line.boxes[0] for segment_line in segment)
                    candidates.append(
                        _Candidate(
                            page=line.page,
                            boxes=tuple(box.bbox for box in segment_boxes),
                            score=score,
                            evidence_text=actual_text,
                        )
                    )
            for window in _word_windows(segment, min_words, max_words):
                actual_text = " ".join(box.text for box in window)
                score = _similarity(target, actual_text, field_name)
                if score >= 0.45:
                    candidates.append(
                        _Candidate(
                            page=window[0].page,
                            boxes=tuple(box.bbox for box in window),
                            score=score,
                            evidence_text=actual_text,
                        )
                    )
    return _prune_overlapping(_deduplicate(candidates))


def _word_windows(lines: list[_Line], minimum: int, maximum: int) -> list[tuple[TextBox, ...]]:
    words = [box for line in lines for box in line.boxes]
    return [
        tuple(words[start : start + width])
        for width in range(minimum, maximum + 1)
        for start in range(0, len(words) - width + 1)
    ]


def _match_inside_ocr_line(
    target: str,
    field_name: str,
    box: TextBox,
    threshold: float,
) -> list[_Candidate]:
    if field_name in _NUMERIC_FIELDS:
        return _match_numeric_ocr_line(target, field_name, box)
    text_norm, offsets = _compact_with_offsets(box.text)
    target_compact = "".join(char for char in _normalize(target, field_name) if char.isalnum())
    target_len = len(target_compact)
    if not target_len or target_len > len(text_norm):
        return []
    candidates: list[_Candidate] = []
    lengths = {target_len}
    if target_len > 1:
        lengths.update({max(1, target_len - 1), target_len + 1})
    for length in lengths:
        for start in range(0, len(text_norm) - length + 1):
            end = start + length
            char_start = offsets[start]
            char_end = offsets[end - 1] + 1
            actual_text = box.text[char_start:char_end]
            score = _similarity(target, actual_text, field_name)
            if score < 0.45:
                continue
            x0, y0, x1, y1 = box.bbox
            line_width = x1 - x0
            estimated_box = (
                x0 + line_width * char_start / max(1, len(box.text)),
                y0,
                x0 + line_width * char_end / max(1, len(box.text)),
                y1,
            )
            candidates.append(
                _Candidate(
                    page=box.page,
                    boxes=(estimated_box,),
                    score=score,
                    evidence_text=box.text,
                    estimated=char_start > 0 or char_end < len(box.text),
                )
            )
    return candidates


def _match_numeric_ocr_line(target: str, field_name: str, box: TextBox) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    pattern = re.compile(r"(?<![\w])[0-9oоil|.,]+(?![\w])", re.IGNORECASE)
    for match in pattern.finditer(box.text):
        actual_text = match.group(0)
        score = _similarity(target, actual_text, field_name)
        if score < 0.45:
            continue
        x0, y0, x1, y1 = box.bbox
        line_width = x1 - x0
        start = match.start()
        end = match.end()
        estimated_box = (
            x0 + line_width * start / max(1, len(box.text)),
            y0,
            x0 + line_width * end / max(1, len(box.text)),
            y1,
        )
        candidates.append(
            _Candidate(
                page=box.page,
                boxes=(estimated_box,),
                score=score,
                evidence_text=box.text,
                estimated=start > 0 or end < len(box.text),
            )
        )
    return candidates


def _similarity(target: str, candidate: str, field_name: str) -> float:
    target_dates = _date_keys(target) if field_name == "invoice_date" else set()
    candidate_dates = _date_keys(candidate) if field_name == "invoice_date" else set()
    if target_dates and candidate_dates:
        return 1.0 if target_dates.intersection(candidate_dates) else 0.0
    if field_name in _NUMERIC_FIELDS:
        target_decimal = _decimal_key(target)
        candidate_decimal = _decimal_key(candidate)
        if target_decimal is not None and candidate_decimal is not None:
            return 1.0 if target_decimal == candidate_decimal else 0.0
    return _normalized_similarity(
        _normalize(target, field_name),
        _normalize(candidate, field_name),
    )


def _normalize(value: str, field_name: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    if field_name == "invoice_date":
        date_key = _date_key(value)
        if date_key:
            return date_key
    if field_name in _NUMERIC_FIELDS:
        decimal_key = _decimal_key(value)
        if decimal_key is not None:
            return decimal_key
    value = _fold_ocr_confusions(value)
    return "".join(char for char in value if char.isalnum())


def _fold_ocr_confusions(value: str) -> str:
    chars = list(value)
    for index, char in enumerate(chars):
        before = chars[index - 1].isdigit() if index else False
        after = chars[index + 1].isdigit() if index + 1 < len(chars) else False
        if char in {"o", "о"} and (before or after):
            chars[index] = "0"
        elif char in {"l", "i", "|"} and (before or after):
            chars[index] = "1"
    return "".join(chars)


def _compact_with_offsets(value: str) -> tuple[str, list[int]]:
    normalized = _fold_ocr_confusions(unicodedata.normalize("NFKC", value).casefold())
    output: list[str] = []
    offsets: list[int] = []
    for index, char in enumerate(normalized):
        if char.isalnum():
            output.append(char)
            offsets.append(index)
    return "".join(output), offsets


def _decimal_key(value: str) -> str | None:
    compact = value.replace("\u00a0", "").replace(" ", "").strip()
    if "," in compact and "." in compact:
        if compact.rfind(",") > compact.rfind("."):
            compact = compact.replace(".", "").replace(",", ".")
        else:
            compact = compact.replace(",", "")
    elif "," in compact:
        if re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+", compact):
            compact = compact.replace(",", "")
        else:
            compact = compact.replace(",", ".")
    compact = _fold_ocr_confusions(compact)
    try:
        number = Decimal(compact)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    return format(number.normalize(), "f")


def _date_key(value: str) -> str | None:
    keys = _date_keys(value)
    return sorted(keys)[0] if keys else None


def _date_keys(value: str) -> set[str]:
    stripped = re.sub(r"\s+", " ", value.strip())
    keys: set[str] = set()
    for date_format in _DATE_FORMATS:
        try:
            keys.add(datetime.strptime(stripped.title(), date_format).date().isoformat())
        except ValueError:
            continue
    return keys


def _normalized_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    if max(len(left), len(right)) <= 2:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _label_bonus(field_name: str, candidate: _Candidate, lines: list[_Line]) -> float:
    labels = _FIELD_LABELS.get(field_name, ())
    if not labels:
        return 0.0
    candidate_x = sum((box[0] + box[2]) / 2 for box in candidate.boxes) / len(candidate.boxes)
    candidate_y = sum((box[1] + box[3]) / 2 for box in candidate.boxes) / len(candidate.boxes)
    best = 0.0
    for line in lines:
        if line.page != candidate.page:
            continue
        line_norm = _normalize(line.text, "")
        if not any(_normalize(label, "") in line_norm for label in labels):
            continue
        label_x = sum(_center_x(box) for box in line.boxes) / len(line.boxes)
        distance = abs(label_x - candidate_x) + abs(line.y_center - candidate_y) * 1.8
        if distance <= 0.25:
            best = max(best, 0.12 * (1 - distance / 0.25))
    return best


def _unique_line_item_anchors(
    matches: dict[str, list[_Candidate]],
    *,
    ambiguity_margin: float,
) -> dict[int, _Candidate]:
    anchors: dict[int, _Candidate] = {}
    for path, candidates in matches.items():
        if not (path.endswith(".description_of_goods") or path.endswith(".sr_no")):
            continue
        index = _line_item_index(path)
        if index is None or not candidates:
            continue
        ranked = sorted(candidates, key=lambda item: item.ranked_score, reverse=True)
        if len(ranked) == 1 or ranked[0].ranked_score - ranked[1].ranked_score >= ambiguity_margin:
            anchors[index] = ranked[0]
    return anchors


def _same_row(candidate: _Candidate, anchor: _Candidate) -> bool:
    if candidate.page != anchor.page:
        return False
    candidate_y = sum((box[1] + box[3]) / 2 for box in candidate.boxes) / len(candidate.boxes)
    anchor_y = sum((box[1] + box[3]) / 2 for box in anchor.boxes) / len(anchor.boxes)
    return abs(candidate_y - anchor_y) <= 0.035


def _select_source(
    candidates: list[_Candidate],
    *,
    threshold: float,
    ambiguity_margin: float,
    ocr_failed: bool,
) -> FieldSource:
    if not candidates:
        reason: EvidenceReason = "ocr_failed" if ocr_failed else "not_found"
        return FieldSource(status="unavailable", reason=reason)
    ranked = sorted(candidates, key=lambda item: item.ranked_score, reverse=True)
    eligible = [candidate for candidate in ranked if candidate.score >= threshold]
    if not eligible:
        return FieldSource(status="unavailable", reason="low_quality", match_count=len(ranked))
    top = eligible[0]
    if len(eligible) > 1 and top.ranked_score - eligible[1].ranked_score < ambiguity_margin:
        return FieldSource(
            status="ambiguous",
            reason="ambiguous",
            match_count=len(eligible),
            candidates=[candidate.public() for candidate in eligible],
        )
    return FieldSource(
        page=top.page,
        boxes=list(top.boxes),
        status="located",
        reason=None,
        match_count=len(eligible),
        candidates=[candidate.public() for candidate in eligible],
        evidence_text=top.evidence_text,
        estimated=top.estimated,
    )


def _deduplicate(candidates: list[_Candidate]) -> list[_Candidate]:
    unique: dict[tuple[int, tuple[NormalizedBox, ...]], _Candidate] = {}
    for candidate in candidates:
        rounded_boxes: tuple[NormalizedBox, ...] = tuple(
            (round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5))
            for box in candidate.boxes
        )
        key = (candidate.page, rounded_boxes)
        current = unique.get(key)
        if current is None or candidate.score > current.score:
            unique[key] = candidate
    return list(unique.values())


def _prune_overlapping(candidates: list[_Candidate]) -> list[_Candidate]:
    """Collapse fuzzy windows that contain a stronger match at the same location."""
    kept: list[_Candidate] = []
    for candidate in sorted(candidates, key=lambda item: item.score, reverse=True):
        if any(
            candidate.page == stronger.page
            and candidate.score - stronger.score < 0.05
            and _candidate_regions_overlap(candidate, stronger)
            for stronger in kept
        ):
            continue
        kept.append(candidate)
    return kept


def _candidate_regions_overlap(left: _Candidate, right: _Candidate) -> bool:
    if not left.boxes or not right.boxes:
        return False
    left_bounds = (
        min(box[0] for box in left.boxes),
        min(box[1] for box in left.boxes),
        max(box[2] for box in left.boxes),
        max(box[3] for box in left.boxes),
    )
    right_bounds = (
        min(box[0] for box in right.boxes),
        min(box[1] for box in right.boxes),
        max(box[2] for box in right.boxes),
        max(box[3] for box in right.boxes),
    )
    intersection_width = max(
        0.0,
        min(left_bounds[2], right_bounds[2]) - max(left_bounds[0], right_bounds[0]),
    )
    intersection_height = max(
        0.0,
        min(left_bounds[3], right_bounds[3]) - max(left_bounds[1], right_bounds[1]),
    )
    smaller_area = min(
        (left_bounds[2] - left_bounds[0]) * (left_bounds[3] - left_bounds[1]),
        (right_bounds[2] - right_bounds[0]) * (right_bounds[3] - right_bounds[1]),
    )
    return smaller_area > 0 and intersection_width * intersection_height / smaller_area >= 0.8


def _line_item_index(path: str) -> int | None:
    match = re.match(r"line_items\[(\d+)\]", path)
    return int(match.group(1)) if match else None


def _center_x(box: TextBox) -> float:
    return (box.bbox[0] + box.bbox[2]) / 2


def _center_y(box: TextBox) -> float:
    return (box.bbox[1] + box.bbox[3]) / 2
