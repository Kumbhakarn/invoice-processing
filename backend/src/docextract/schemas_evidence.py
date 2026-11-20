"""Public response models for field-level extraction evidence."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from docextract.schemas import InvoiceExtractionData

NormalizedBox = tuple[float, float, float, float]
EvidenceReason = Literal["not_found", "ambiguous", "ocr_failed", "low_quality"]
EvidenceStatus = Literal["located", "unavailable", "ambiguous"]
ConfidenceLevel = Literal["High", "Medium", "Low"]


class SourceCandidate(BaseModel):
    """One possible source location for an extracted field."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    boxes: list[NormalizedBox]
    match_score: float = Field(ge=0, le=1)
    evidence_text: str | None = None
    estimated: bool = False

    @model_validator(mode="after")
    def validate_boxes(self) -> "SourceCandidate":
        if not self.boxes or any(
            not (0 <= x0 <= x1 <= 1 and 0 <= y0 <= y1 <= 1) for x0, y0, x1, y1 in self.boxes
        ):
            raise ValueError("candidate requires normalized, ordered boxes")
        return self


class FieldSource(BaseModel):
    """Selected or unavailable source location, with ambiguity details."""

    model_config = ConfigDict(extra="forbid")

    page: int | None = Field(default=None, ge=1)
    boxes: list[NormalizedBox] = Field(default_factory=list)
    status: EvidenceStatus = "unavailable"
    reason: EvidenceReason | None = "not_found"
    match_count: int = Field(default=0, ge=0)
    candidates: list[SourceCandidate] = Field(default_factory=list)
    evidence_text: str | None = None
    estimated: bool = False

    @model_validator(mode="after")
    def validate_location_state(self) -> "FieldSource":
        if any(not (0 <= x0 <= x1 <= 1 and 0 <= y0 <= y1 <= 1) for x0, y0, x1, y1 in self.boxes):
            raise ValueError("source boxes must be normalized and ordered")
        if self.status == "located" and (
            self.page is None or not self.boxes or self.reason is not None or self.match_count < 1
        ):
            raise ValueError("located source requires a page, boxes, a match, and no reason")
        if self.status == "ambiguous" and (
            self.page is not None
            or self.boxes
            or self.reason != "ambiguous"
            or self.match_count < 2
            or len(self.candidates) != self.match_count
        ):
            raise ValueError("ambiguous source requires all candidate locations and no selection")
        if self.status == "unavailable" and (
            self.page is not None or self.boxes or self.reason is None
        ):
            raise ValueError("unavailable source requires a reason and no location")
        return self


class FieldEvidence(BaseModel):
    """Internal evidence sidecar for a single invoice field path."""

    model_config = ConfigDict(extra="forbid")

    field: str
    raw: str | None = None
    confidence: ConfidenceLevel | None = None
    source: FieldSource = Field(default_factory=FieldSource)
    edited: bool = False


class MappedField(BaseModel):
    """Per-field public mapping that preserves the original extraction value."""

    model_config = ConfigDict(extra="forbid")

    value: Any
    raw: str | None
    confidence: ConfidenceLevel | None = None
    source: FieldSource
    edited: bool


class DocumentPage(BaseModel):
    """One-based document page and dimensions used for highlighting."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ProviderUsageMetadata(BaseModel):
    """Token usage returned by one provider attempt."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)


class EvidenceMetadata(BaseModel):
    """Processing timings and provider usage for an evidence extraction."""

    model_config = ConfigDict(extra="forbid")

    timings_ms: dict[str, float] = Field(default_factory=dict)
    provider_usage: list[ProviderUsageMetadata] = Field(default_factory=list)


class EvidenceExtractionResponse(BaseModel):
    """Interim evidence endpoint response, separate from `/api/extract`."""

    model_config = ConfigDict(extra="forbid")

    data: InvoiceExtractionData
    fields: dict[str, MappedField]
    pages: list[DocumentPage]
    meta: EvidenceMetadata


class RawFieldText(BaseModel):
    """Provider-returned printed text for one extracted field, before grounding."""

    model_config = ConfigDict(extra="forbid")

    field: str
    raw: str


class FieldConfidenceAssessment(BaseModel):
    """Model self-assessment for one scalar invoice field path."""

    model_config = ConfigDict(extra="forbid")

    field: str
    confidence: ConfidenceLevel | None


class EvidenceProviderResponse(BaseModel):
    """Private structured result used only by the evidence extraction pipeline."""

    model_config = ConfigDict(extra="forbid")

    data: InvoiceExtractionData
    raw_fields: list[RawFieldText]
    field_confidences: list[FieldConfidenceAssessment]
