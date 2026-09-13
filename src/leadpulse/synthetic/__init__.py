"""Deterministic synthetic datasets owned by LeadPulse."""

from leadpulse.synthetic.marketing_spend import (
    DEFAULT_OUTPUT,
    GenerationResult,
    SyntheticSpendError,
    generate_marketing_spend,
)

__all__ = [
    "DEFAULT_OUTPUT",
    "GenerationResult",
    "SyntheticSpendError",
    "generate_marketing_spend",
]
