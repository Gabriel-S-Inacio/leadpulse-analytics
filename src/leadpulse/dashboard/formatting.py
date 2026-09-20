"""Locale-stable display formatting for the executive dashboard."""

from __future__ import annotations

import math
from decimal import Decimal

Numeric = float | Decimal


def _finite_number(value: Numeric | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _pt_br_number(value: float, decimals: int) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "#").replace(".", ",").replace("#", ".")


def format_integer(value: Numeric | None) -> str:
    numeric = _finite_number(value)
    return "N/A" if numeric is None else _pt_br_number(numeric, 0)


def format_decimal(value: Numeric | None, decimals: int = 2) -> str:
    numeric = _finite_number(value)
    return "N/A" if numeric is None else _pt_br_number(numeric, decimals)


def format_brl(value: Numeric | None) -> str:
    numeric = _finite_number(value)
    return "N/A" if numeric is None else f"R$ {_pt_br_number(numeric, 2)}"


def format_percent(value: Numeric | None, decimals: int = 2) -> str:
    numeric = _finite_number(value)
    return "N/A" if numeric is None else f"{_pt_br_number(numeric * 100, decimals)}%"


def format_roas(value: Numeric | None) -> str:
    numeric = _finite_number(value)
    return "N/A" if numeric is None else f"{_pt_br_number(numeric, 2)}x"


def format_days(value: Numeric | None) -> str:
    numeric = _finite_number(value)
    return "N/A" if numeric is None else f"{_pt_br_number(numeric, 2)} dias"
