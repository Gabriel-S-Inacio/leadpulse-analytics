from __future__ import annotations

import hashlib
import inspect
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))

from leadpulse.ingestion.config import ConfigurationError, PostgresConfig
from leadpulse.ingestion.contracts import (
    CLOSED_DEALS_CONTRACT,
    ORDER_ITEMS_CONTRACT,
    ORDERS_CONTRACT,
    SELLERS_CONTRACT,
    SOURCE_CONTRACTS,
    SYNTHETIC_MARKETING_SPEND_CONTRACT,
    RawSnapshotContract,
)
from leadpulse.ingestion.metadata import build_source_metadata
from leadpulse.ingestion.mql import MqlSourceError, validate_mql_header
from leadpulse.ingestion.snapshot import SnapshotSourceError, validate_source_header
from leadpulse.synthetic import marketing_spend
from leadpulse.synthetic.marketing_spend import (
    DAILY_BASELINE_BY_ORIGIN,
    DATA_CLASSIFICATION,
    SyntheticSpendError,
    generate_marketing_spend,
)


class PostgresConfigTest(unittest.TestCase):
    def test_reads_complete_environment(self) -> None:
        config = PostgresConfig.from_env(
            {
                "POSTGRES_DB": "leadpulse",
                "POSTGRES_USER": "leadpulse",
                "POSTGRES_PASSWORD": "local-only",
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5432",
            }
        )

        self.assertEqual(config.dbname, "leadpulse")
        self.assertEqual(config.port, 5432)
        self.assertNotIn("password", repr(config))

    def test_rejects_missing_password(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "POSTGRES_PASSWORD is required"):
            PostgresConfig.from_env(
                {
                    "POSTGRES_DB": "leadpulse",
                    "POSTGRES_USER": "leadpulse",
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": "5432",
                }
            )

    def test_rejects_invalid_port(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "must be an integer"):
            PostgresConfig.from_env(
                {
                    "POSTGRES_DB": "leadpulse",
                    "POSTGRES_USER": "leadpulse",
                    "POSTGRES_PASSWORD": "local-only",
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": "postgres",
                }
            )


class SourceMetadataTest(unittest.TestCase):
    def test_records_basename_checksum_and_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.csv"
            content = b"id\nexample\n"
            source.write_bytes(content)
            loaded_at = datetime(2026, 9, 12, tzinfo=UTC)

            metadata = build_source_metadata(source, loaded_at=loaded_at)

            self.assertEqual(metadata.source_file, "source.csv")
            self.assertEqual(metadata.source_sha256, hashlib.sha256(content).hexdigest())
            self.assertEqual(metadata.loaded_at, loaded_at)


class MqlSourceContractTest(unittest.TestCase):
    def test_accepts_expected_header(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "mql.csv"
            source.write_text(
                "mql_id,first_contact_date,landing_page_id,origin\n",
                encoding="utf-8",
            )
            validate_mql_header(source)

    def test_rejects_unexpected_header(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "mql.csv"
            source.write_text("mql_id,origin\n", encoding="utf-8")
            with self.assertRaisesRegex(
                MqlSourceError, "unexpected marketing qualified leads columns"
            ):
                validate_mql_header(source)


class RawSnapshotContractTest(unittest.TestCase):
    def test_closed_deals_contract_preserves_all_source_columns(self) -> None:
        self.assertEqual(len(CLOSED_DEALS_CONTRACT.source_columns), 14)
        self.assertEqual(CLOSED_DEALS_CONTRACT.target_table, "raw.olist_closed_deals")
        self.assertEqual(CLOSED_DEALS_CONTRACT.primary_key, ("mql_id",))

    def test_validates_closed_deals_header_with_shared_logic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "closed_deals.csv"
            source.write_text(
                ",".join(CLOSED_DEALS_CONTRACT.source_columns) + "\n",
                encoding="utf-8",
            )
            validate_source_header(source, CLOSED_DEALS_CONTRACT)

    def test_validates_commerce_source_headers_with_shared_logic(self) -> None:
        contracts = (SELLERS_CONTRACT, ORDERS_CONTRACT, ORDER_ITEMS_CONTRACT)
        with tempfile.TemporaryDirectory() as temporary:
            for contract in contracts:
                with self.subTest(source=contract.name):
                    source = Path(temporary) / f"{contract.table}.csv"
                    source.write_text(
                        ",".join(contract.source_columns) + "\n",
                        encoding="utf-8",
                    )
                    validate_source_header(source, contract)

    def test_unified_source_registry_targets_distinct_raw_tables(self) -> None:
        targets = [contract.target_table for contract in SOURCE_CONTRACTS.values()]
        self.assertEqual(len(targets), len(set(targets)))
        self.assertEqual(
            set(SOURCE_CONTRACTS),
            {
                "mql",
                "closed-deals",
                "sellers",
                "orders",
                "order-items",
                "synthetic-spend",
            },
        )

    def test_synthetic_spend_contract_uses_governed_grain(self) -> None:
        self.assertEqual(
            SYNTHETIC_MARKETING_SPEND_CONTRACT.target_table,
            "raw.synthetic_marketing_spend",
        )
        self.assertEqual(
            SYNTHETIC_MARKETING_SPEND_CONTRACT.primary_key,
            ("spend_date", "source_origin", "scenario_id"),
        )

    def test_rejects_unknown_required_column(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown required column"):
            RawSnapshotContract(
                name="invalid",
                default_source=Path("source.csv"),
                schema="raw",
                table="source",
                source_columns=("id",),
                required_columns=("missing",),
                primary_key=("id",),
            )

    def test_rejects_unexpected_closed_deals_header(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "closed_deals.csv"
            source.write_text("mql_id,seller_id\n", encoding="utf-8")
            with self.assertRaisesRegex(
                SnapshotSourceError, "unexpected closed deals columns"
            ):
                validate_source_header(source, CLOSED_DEALS_CONTRACT)


class SyntheticMarketingSpendTest(unittest.TestCase):
    @staticmethod
    def _write_mql_fixture(path: Path) -> None:
        rows = [
            "mql_id,first_contact_date,landing_page_id,origin",
            "mql-1,2026-01-01,page-1,paid_search",
            "mql-2,2026-01-03,page-2,paid_search",
            "mql-3,2026-01-02,page-3,display",
            "mql-4,2026-01-02,page-4,social",
            "mql-5,2026-01-02,page-5,other_publicities",
            "mql-6,2026-01-02,page-6,organic_search",
        ]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    def test_generation_is_byte_stable_and_governed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "mql.csv"
            first_output = root / "first.csv"
            second_output = root / "second.csv"
            self._write_mql_fixture(source)

            first = generate_marketing_spend(source, first_output)
            second = generate_marketing_spend(source, second_output)

            self.assertEqual(first.row_count, 6)
            self.assertEqual(first.source_sha256, second.source_sha256)
            self.assertEqual(first_output.read_bytes(), second_output.read_bytes())
            self.assertEqual(len(first.origin_bounds), len(DAILY_BASELINE_BY_ORIGIN))
            self.assertIn(DATA_CLASSIFICATION, first_output.read_text(encoding="utf-8"))

    def test_generation_requires_coverage_for_every_eligible_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "mql.csv"
            source.write_text(
                "mql_id,first_contact_date,landing_page_id,origin\n"
                "mql-1,2026-01-01,page-1,paid_search\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SyntheticSpendError, "no date coverage"):
                generate_marketing_spend(source, Path(temporary) / "spend.csv")

    def test_generator_has_no_downstream_or_database_dependency(self) -> None:
        source = inspect.getsource(marketing_spend).lower()
        forbidden = (
            "psycopg",
            "fct_closed_deal",
            "fct_seller_lifecycle",
            "fct_order_item",
            "olist_orders",
            "order_purchase_timestamp",
            "eligible_gmv",
            "gmv",
            "conversion",
        )

        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)
