"""Unified command-line entry point for supported raw snapshot loads."""

from __future__ import annotations

import argparse
from pathlib import Path

from leadpulse.ingestion.config import ConfigurationError, PostgresConfig
from leadpulse.ingestion.contracts import SOURCE_CONTRACTS
from leadpulse.ingestion.snapshot import SnapshotSourceError, load_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=SOURCE_CONTRACTS)
    parser.add_argument(
        "--source-file",
        type=Path,
        help="Override the source contract's default CSV path",
    )
    arguments = parser.parse_args()
    contract = SOURCE_CONTRACTS[arguments.source]
    source_path = arguments.source_file or contract.default_source

    try:
        result = load_snapshot(source_path, contract, PostgresConfig.from_env())
    except (ConfigurationError, FileNotFoundError, SnapshotSourceError) as error:
        parser.error(str(error))

    print(f"table={result.table}")
    print(f"rows={result.row_count}")
    print(f"source_file={result.metadata.source_file}")
    print(f"source_sha256={result.metadata.source_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
