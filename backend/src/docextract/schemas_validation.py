"""Public response models for invoice business validation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ValidationIssue(BaseModel):
    """One non-mutating business rule finding."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    field: str
    line_item_index: int | None = None
    severity: Literal["warning", "error"]
    message: str


class InvoiceValidationResult(BaseModel):
    """Validation outcome kept separate from extracted invoice values."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["valid", "needs_review", "invalid"]
    issues: list[ValidationIssue]
