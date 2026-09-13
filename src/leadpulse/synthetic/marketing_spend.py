"""Generate non-causal synthetic paid-media spend from an MQL date domain."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from leadpulse.ingestion.metadata import sha256_file

DEFAULT_MQL_SOURCE = Path(
    "data/raw/olist_marketing_funnel/olist_marketing_qualified_leads_dataset.csv"
)
DEFAULT_OUTPUT = Path("data/generated/synthetic_marketing_spend.csv")

SCENARIO_ID = "baseline_v1"
METHODOLOGY_VERSION = "paid_media_daily_v1"
GENERATION_SEED = 20260913
CURRENCY = "BRL"
DATA_CLASSIFICATION = "SYNTHETIC"

# A-priori illustrative BRL daily baselines. They are not estimated from outcomes.
DAILY_BASELINE_BY_ORIGIN = {
    "paid_search": Decimal("450.00"),
    "display": Decimal("180.00"),
    "social": Decimal("300.00"),
    "other_publicities": Decimal("120.00"),
}

# Integer basis-point effects keep output stable across platforms and Python versions.
MONTH_EFFECT_BPS = (
    9400,
    9600,
    9900,
    10100,
    10300,
    10000,
    9800,
    10000,
    10200,
    10500,
    11000,
    10800,
)
WEEKDAY_EFFECT_BPS = (10000, 10300, 10500, 10200, 9700, 7800, 7200)
OUTPUT_COLUMNS = (
    "spend_date",
    "source_origin",
    "scenario_id",
    "methodology_version",
    "generation_seed",
    "currency",
    "spend_amount",
    "data_classification",
)


class SyntheticSpendError(ValueError):
    """Raised when the permitted MQL domain cannot be derived safely."""


@dataclass(frozen=True)
class GenerationResult:
    output_path: Path
    row_count: int
    source_sha256: str
    origin_bounds: tuple[tuple[str, date, date], ...]


def _origin_date_bounds(mql_source: Path) -> dict[str, tuple[date, date]]:
    bounds: dict[str, tuple[date, date]] = {}
    with mql_source.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"first_contact_date", "origin"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise SyntheticSpendError(
                "MQL input must contain first_contact_date and origin"
            )

        for line_number, row in enumerate(reader, start=2):
            origin = (row.get("origin") or "").strip()
            if origin not in DAILY_BASELINE_BY_ORIGIN:
                continue
            raw_date = (row.get("first_contact_date") or "").strip()
            try:
                contact_date = date.fromisoformat(raw_date)
            except ValueError as error:
                raise SyntheticSpendError(
                    f"invalid first_contact_date at line {line_number}"
                ) from error

            current = bounds.get(origin)
            if current is None:
                bounds[origin] = (contact_date, contact_date)
            else:
                bounds[origin] = (
                    min(current[0], contact_date),
                    max(current[1], contact_date),
                )

    missing = set(DAILY_BASELINE_BY_ORIGIN) - set(bounds)
    if missing:
        raise SyntheticSpendError(
            f"MQL input has no date coverage for eligible origins: {sorted(missing)}"
        )
    return bounds


def _bounded_noise_bps(origin: str, spend_date: date) -> int:
    identity = (
        f"{GENERATION_SEED}|{SCENARIO_ID}|{METHODOLOGY_VERSION}|"
        f"{origin}|{spend_date.isoformat()}"
    )
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return 9000 + int.from_bytes(digest[:8], "big") % 2001


def _daily_spend(origin: str, spend_date: date) -> Decimal:
    amount = DAILY_BASELINE_BY_ORIGIN[origin]
    amount *= Decimal(MONTH_EFFECT_BPS[spend_date.month - 1]) / Decimal(10000)
    amount *= Decimal(WEEKDAY_EFFECT_BPS[spend_date.weekday()]) / Decimal(10000)
    amount *= Decimal(_bounded_noise_bps(origin, spend_date)) / Decimal(10000)
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_marketing_spend(
    mql_source: Path = DEFAULT_MQL_SOURCE,
    output_path: Path = DEFAULT_OUTPUT,
) -> GenerationResult:
    """Write a deterministic spend snapshot using only MQL origin/date coverage."""

    bounds = _origin_date_bounds(mql_source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    row_count = 0

    with temporary_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=OUTPUT_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        for origin in DAILY_BASELINE_BY_ORIGIN:
            first_date, last_date = bounds[origin]
            current_date = first_date
            while current_date <= last_date:
                writer.writerow(
                    {
                        "spend_date": current_date.isoformat(),
                        "source_origin": origin,
                        "scenario_id": SCENARIO_ID,
                        "methodology_version": METHODOLOGY_VERSION,
                        "generation_seed": GENERATION_SEED,
                        "currency": CURRENCY,
                        "spend_amount": _daily_spend(origin, current_date),
                        "data_classification": DATA_CLASSIFICATION,
                    }
                )
                row_count += 1
                current_date += timedelta(days=1)

    temporary_path.replace(output_path)
    ordered_bounds = tuple(
        (origin, *bounds[origin]) for origin in DAILY_BASELINE_BY_ORIGIN
    )
    return GenerationResult(
        output_path=output_path,
        row_count=row_count,
        source_sha256=sha256_file(output_path),
        origin_bounds=ordered_bounds,
    )
