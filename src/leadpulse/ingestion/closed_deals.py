"""CLI for the Closed Deals raw snapshot."""

from __future__ import annotations

from pathlib import Path

from leadpulse.ingestion.config import PostgresConfig
from leadpulse.ingestion.contracts import CLOSED_DEALS_CONTRACT
from leadpulse.ingestion.snapshot import LoadResult, load_snapshot, run_snapshot_cli


def load_closed_deals_snapshot(path: Path, config: PostgresConfig) -> LoadResult:
    return load_snapshot(path, CLOSED_DEALS_CONTRACT, config)


def main() -> int:
    return run_snapshot_cli(CLOSED_DEALS_CONTRACT)


if __name__ == "__main__":
    raise SystemExit(main())
