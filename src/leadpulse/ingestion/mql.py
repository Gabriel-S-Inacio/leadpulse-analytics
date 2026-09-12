"""CLI and compatibility helpers for the MQL raw snapshot."""

from __future__ import annotations

from pathlib import Path

from leadpulse.ingestion.config import PostgresConfig
from leadpulse.ingestion.contracts import MQL_CONTRACT
from leadpulse.ingestion.snapshot import (
    LoadResult,
    SnapshotSourceError,
    load_snapshot,
    run_snapshot_cli,
    validate_source_header,
)

DEFAULT_SOURCE = MQL_CONTRACT.default_source
EXPECTED_COLUMNS = MQL_CONTRACT.source_columns
TARGET_TABLE = MQL_CONTRACT.target_table
MqlSourceError = SnapshotSourceError


def validate_mql_header(path: Path) -> None:
    validate_source_header(path, MQL_CONTRACT)


def load_mql_snapshot(path: Path, config: PostgresConfig) -> LoadResult:
    return load_snapshot(path, MQL_CONTRACT, config)


def main() -> int:
    return run_snapshot_cli(MQL_CONTRACT)


if __name__ == "__main__":
    raise SystemExit(main())
