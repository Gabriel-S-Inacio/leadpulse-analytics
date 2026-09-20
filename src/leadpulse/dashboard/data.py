"""Read-only PostgreSQL access restricted to dashboard-ready semantic marts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
import psycopg

from leadpulse.config import PostgresConfig

MartName = Literal[
    "acquisition",
    "activation",
    "marketing",
    "downstream",
]


class DataContractError(RuntimeError):
    """Raised when a semantic mart no longer matches the dashboard contract."""


ACQUISITION_COLUMNS = (
    "cohort_month_key",
    "cohort_month",
    "origin_key",
    "source_origin",
    "normalized_channel",
    "mqls",
    "closed_deals",
    "acquired_sellers",
    "mql_to_acquired_seller_conversion_rate",
)
ACTIVATION_COLUMNS = (
    "cohort_month_key",
    "cohort_month",
    "origin_key",
    "source_origin",
    "normalized_channel",
    "observation_cutoff_timestamp",
    "lifecycle_rule_version",
    "source_snapshot_id",
    "acquired_sellers_mature",
    "activated_sellers_90d",
    "seller_activation_rate",
    "avg_time_to_first_order_days",
    "median_time_to_first_order_days",
    "gmv_90d",
    "orders_90d",
    "gmv_per_activated_seller",
    "orders_per_activated_seller",
)
MARKETING_COLUMNS = (
    "period_key",
    "period",
    "coverage_start_date",
    "coverage_end_date",
    "origin_key",
    "source_origin",
    "normalized_channel",
    "scenario_id",
    "methodology_version",
    "generation_seed",
    "currency",
    "data_classification",
    "observation_cutoff_timestamp",
    "lifecycle_rule_version",
    "lifecycle_source_snapshot_id",
    "synthetic_marketing_spend",
    "mqls",
    "acquired_sellers",
    "eligible_gmv_90d",
    "cpl",
    "seller_acquisition_cost",
    "gmv_roas",
)
DOWNSTREAM_COLUMNS = (
    "purchase_month_key",
    "purchase_month",
    "origin_key",
    "source_origin",
    "normalized_channel",
    "order_id",
    "orders",
    "seller_order_participations",
    "eligible_gmv",
)

MART_COLUMNS: dict[MartName, tuple[str, ...]] = {
    "acquisition": ACQUISITION_COLUMNS,
    "activation": ACTIVATION_COLUMNS,
    "marketing": MARKETING_COLUMNS,
    "downstream": DOWNSTREAM_COLUMNS,
}

MART_QUERIES: dict[MartName, str] = {
    "acquisition": (
        f"SELECT {', '.join(ACQUISITION_COLUMNS)} "
        "FROM analytics.mart_acquisition_performance"
    ),
    "activation": (
        f"SELECT {', '.join(ACTIVATION_COLUMNS)} FROM analytics.mart_seller_activation"
    ),
    "marketing": (
        f"SELECT {', '.join(MARKETING_COLUMNS)} FROM analytics.mart_marketing_efficiency"
    ),
    "downstream": (
        f"SELECT {', '.join(DOWNSTREAM_COLUMNS)} FROM analytics.mart_downstream_performance"
    ),
}

DATE_COLUMNS = {
    "cohort_month",
    "period",
    "coverage_start_date",
    "coverage_end_date",
    "purchase_month",
    "observation_cutoff_timestamp",
}


@dataclass(frozen=True)
class DashboardData:
    acquisition: pd.DataFrame
    activation: pd.DataFrame
    marketing: pd.DataFrame
    downstream: pd.DataFrame


class MartRepository:
    """Fetch the four approved marts through constant, read-only queries."""

    def __init__(self, config: PostgresConfig) -> None:
        self._config = config

    @classmethod
    def from_env(cls) -> MartRepository:
        return cls(PostgresConfig.from_env())

    def fetch(self, name: MartName) -> pd.DataFrame:
        with psycopg.connect(
            dbname=self._config.dbname,
            user=self._config.user,
            password=self._config.password,
            host=self._config.host,
            port=self._config.port,
            options="-c default_transaction_read_only=on",
        ) as connection:
            return self._fetch_with_connection(name, connection)

    def _fetch_with_connection(
        self,
        name: MartName,
        connection: psycopg.Connection[Any],
    ) -> pd.DataFrame:
        query = MART_QUERIES[name]
        expected_columns = MART_COLUMNS[name]
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = tuple(column.name for column in cursor.description or ())

        if columns != expected_columns:
            raise DataContractError(
                f"{name} mart columns changed: expected {expected_columns}, received {columns}"
            )

        frame = pd.DataFrame(rows, columns=list(columns))
        for column in DATE_COLUMNS.intersection(frame.columns):
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
        return frame

    def fetch_all(self) -> DashboardData:
        with psycopg.connect(
            dbname=self._config.dbname,
            user=self._config.user,
            password=self._config.password,
            host=self._config.host,
            port=self._config.port,
            options="-c default_transaction_read_only=on",
        ) as connection:
            return DashboardData(
                acquisition=self._fetch_with_connection("acquisition", connection),
                activation=self._fetch_with_connection("activation", connection),
                marketing=self._fetch_with_connection("marketing", connection),
                downstream=self._fetch_with_connection("downstream", connection),
            )
