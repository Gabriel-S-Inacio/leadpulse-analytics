from __future__ import annotations

import hashlib
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
    RawSnapshotContract,
)
from leadpulse.ingestion.metadata import build_source_metadata
from leadpulse.ingestion.mql import MqlSourceError, validate_mql_header
from leadpulse.ingestion.snapshot import SnapshotSourceError, validate_source_header


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
            {"mql", "closed-deals", "sellers", "orders", "order-items"},
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
