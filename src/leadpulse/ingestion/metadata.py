"""Small, deterministic source-file lineage helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class SourceMetadata:
    loaded_at: datetime
    source_file: str
    source_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_source_metadata(path: Path, *, loaded_at: datetime | None = None) -> SourceMetadata:
    resolved = path.resolve(strict=True)
    timestamp = loaded_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("loaded_at must be timezone-aware")
    return SourceMetadata(
        loaded_at=timestamp,
        source_file=resolved.name,
        source_sha256=sha256_file(resolved),
    )
