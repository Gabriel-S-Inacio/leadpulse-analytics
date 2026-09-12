"""Source contracts for the small set of raw snapshots supported by the MVP."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class RawSnapshotContract:
    """Describe one CSV snapshot and its raw PostgreSQL target."""

    name: str
    default_source: Path
    schema: str
    table: str
    source_columns: tuple[str, ...]
    required_columns: tuple[str, ...]
    primary_key: tuple[str, ...]

    def __post_init__(self) -> None:
        identifiers = (self.schema, self.table, *self.source_columns)
        invalid = [value for value in identifiers if not _IDENTIFIER.fullmatch(value)]
        if invalid:
            raise ValueError(f"Invalid PostgreSQL identifier(s): {invalid}")
        if not self.source_columns:
            raise ValueError("A source contract must declare at least one column")
        if len(set(self.source_columns)) != len(self.source_columns):
            raise ValueError("Source contract columns must be unique")

        source_set = set(self.source_columns)
        for label, columns in (
            ("required", self.required_columns),
            ("primary key", self.primary_key),
        ):
            missing = set(columns) - source_set
            if missing:
                raise ValueError(f"Unknown {label} column(s): {sorted(missing)}")
        if not self.primary_key:
            raise ValueError("A source contract must declare a primary key")

    @property
    def target_table(self) -> str:
        return f"{self.schema}.{self.table}"


MQL_CONTRACT = RawSnapshotContract(
    name="marketing qualified leads",
    default_source=Path(
        "data/raw/olist_marketing_funnel/"
        "olist_marketing_qualified_leads_dataset.csv"
    ),
    schema="raw",
    table="olist_marketing_qualified_leads",
    source_columns=("mql_id", "first_contact_date", "landing_page_id", "origin"),
    required_columns=("mql_id", "first_contact_date", "landing_page_id"),
    primary_key=("mql_id",),
)


CLOSED_DEALS_CONTRACT = RawSnapshotContract(
    name="closed deals",
    default_source=Path(
        "data/raw/olist_marketing_funnel/olist_closed_deals_dataset.csv"
    ),
    schema="raw",
    table="olist_closed_deals",
    source_columns=(
        "mql_id",
        "seller_id",
        "sdr_id",
        "sr_id",
        "won_date",
        "business_segment",
        "lead_type",
        "lead_behaviour_profile",
        "has_company",
        "has_gtin",
        "average_stock",
        "business_type",
        "declared_product_catalog_size",
        "declared_monthly_revenue",
    ),
    required_columns=("mql_id", "seller_id", "won_date"),
    primary_key=("mql_id",),
)
