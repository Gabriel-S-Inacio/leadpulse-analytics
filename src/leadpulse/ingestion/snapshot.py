"""Transactional loader shared by the supported static CSV snapshots."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql

from leadpulse.config import ConfigurationError, PostgresConfig
from leadpulse.ingestion.contracts import RawSnapshotContract
from leadpulse.ingestion.metadata import SourceMetadata, build_source_metadata


class SnapshotSourceError(ValueError):
    """Raised when a CSV does not satisfy its declared source contract."""


@dataclass(frozen=True)
class LoadResult:
    table: str
    row_count: int
    metadata: SourceMetadata


def validate_source_header(path: Path, contract: RawSnapshotContract) -> None:
    """Require an exact header so no source column is silently lost."""

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        actual = tuple(next(csv.reader(source), ()))
    if actual != contract.source_columns:
        raise SnapshotSourceError(
            f"unexpected {contract.name} columns: "
            f"expected {contract.source_columns!r}, got {actual!r}"
        )


def _create_table_statement(contract: RawSnapshotContract) -> sql.Composed:
    required = set(contract.required_columns)
    source_definitions = [
        sql.SQL("{} TEXT{}").format(
            sql.Identifier(column),
            sql.SQL(" NOT NULL") if column in required else sql.SQL(""),
        )
        for column in contract.source_columns
    ]
    technical_definitions = [
        sql.SQL("{} TIMESTAMPTZ NOT NULL").format(sql.Identifier("_loaded_at")),
        sql.SQL("{} TEXT NOT NULL").format(sql.Identifier("_source_file")),
        sql.SQL("{} CHAR(64) NOT NULL").format(sql.Identifier("_source_sha256")),
    ]
    primary_key = sql.SQL("PRIMARY KEY ({})").format(
        sql.SQL(", ").join(map(sql.Identifier, contract.primary_key))
    )
    definitions = (*source_definitions, *technical_definitions, primary_key)
    return sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
        sql.Identifier(contract.schema),
        sql.Identifier(contract.table),
        sql.SQL(", ").join(definitions),
    )


def load_snapshot(
    path: Path,
    contract: RawSnapshotContract,
    config: PostgresConfig,
) -> LoadResult:
    """Replace a raw snapshot atomically with validated CSV contents."""

    validate_source_header(path, contract)
    metadata = build_source_metadata(path)
    all_columns = (
        *contract.source_columns,
        "_loaded_at",
        "_source_file",
        "_source_sha256",
    )
    target = sql.SQL("{}.{}").format(
        sql.Identifier(contract.schema), sql.Identifier(contract.table)
    )

    with (
        psycopg.connect(
            dbname=config.dbname,
            user=config.user,
            password=config.password,
            host=config.host,
            port=config.port,
            connect_timeout=10,
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                sql.Identifier(contract.schema)
            )
        )
        cursor.execute(_create_table_statement(contract))
        cursor.execute(sql.SQL("LOCK TABLE {} IN ACCESS EXCLUSIVE MODE").format(target))
        cursor.execute(sql.SQL("TRUNCATE TABLE {}").format(target))

        copy_statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
            target,
            sql.SQL(", ").join(map(sql.Identifier, all_columns)),
        )
        loaded_rows = 0
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            with cursor.copy(copy_statement) as copy:
                for line_number, row in enumerate(reader, start=2):
                    if None in row:
                        raise SnapshotSourceError(
                            f"extra CSV value at line {line_number}"
                        )
                    missing = [
                        column
                        for column in contract.required_columns
                        if not (row.get(column) or "").strip()
                    ]
                    if missing:
                        raise SnapshotSourceError(
                            f"blank required {contract.name} value(s) {missing} "
                            f"at line {line_number}"
                        )
                    source_values = [
                        row[column] or None for column in contract.source_columns
                    ]
                    copy.write_row(
                        (
                            *source_values,
                            metadata.loaded_at,
                            metadata.source_file,
                            metadata.source_sha256,
                        )
                    )
                    loaded_rows += 1

        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(target))
        count_row = cursor.fetchone()
        if count_row is None:
            raise RuntimeError("raw row-count query returned no result")
        if count_row[0] != loaded_rows:
            raise RuntimeError(
                f"raw row-count mismatch: loaded {loaded_rows}, stored {count_row[0]}"
            )

    return LoadResult(
        table=contract.target_table,
        row_count=loaded_rows,
        metadata=metadata,
    )


def run_snapshot_cli(contract: RawSnapshotContract) -> int:
    parser = argparse.ArgumentParser(description=f"Load the Olist {contract.name} snapshot")
    parser.add_argument("--source", type=Path, default=contract.default_source)
    arguments = parser.parse_args()
    try:
        result = load_snapshot(
            arguments.source,
            contract,
            PostgresConfig.from_env(),
        )
    except (ConfigurationError, FileNotFoundError, SnapshotSourceError) as error:
        parser.error(str(error))

    print(f"table={result.table}")
    print(f"rows={result.row_count}")
    print(f"source_file={result.metadata.source_file}")
    print(f"source_sha256={result.metadata.source_sha256}")
    return 0
