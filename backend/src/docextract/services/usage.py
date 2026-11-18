"""Provider usage metadata and configurable USD cost calculations."""

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ProviderUsage:
    """Token counts reported by a provider; absent counts remain unknown."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    source: str = "provider_reported"


@dataclass(frozen=True)
class CostEstimate:
    """Estimated USD cost from configured per-million-token prices."""

    amount_usd: Decimal | None
    pricing_version: str
    source: str = "estimated"


def reported_usage(response: Any, provider: str) -> ProviderUsage:
    """Read usage from an OpenAI Responses or Gemini GenerateContent response."""
    if provider == "OpenAI":
        usage = getattr(response, "usage", None)
        return ProviderUsage(
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            reasoning_tokens=getattr(
                getattr(usage, "output_tokens_details", None), "reasoning_tokens", None
            ),
        )
    usage = getattr(response, "usage_metadata", None)
    return ProviderUsage(
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
        reasoning_tokens=getattr(usage, "thoughts_token_count", None),
    )


def calculate_cost(
    provider: str,
    model: str,
    usage: ProviderUsage,
    pricing_json: str,
    pricing_version: str,
) -> CostEstimate:
    """Calculate an estimate from configured USD prices per million tokens."""
    try:
        config = json.loads(pricing_json)
        prices = config.get(provider, {}).get(model)
        if prices is None or usage.input_tokens is None or usage.output_tokens is None:
            return CostEstimate(None, pricing_version)
        amount = (
            Decimal(usage.input_tokens) * Decimal(str(prices["input_per_million_usd"]))
            + Decimal(usage.output_tokens) * Decimal(str(prices["output_per_million_usd"]))
        ) / Decimal(1_000_000)
        return CostEstimate(amount, pricing_version)
    except (ValueError, TypeError, KeyError, ArithmeticError):
        return CostEstimate(None, pricing_version)
