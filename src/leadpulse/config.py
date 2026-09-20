"""Project configuration loaded from the local environment contract."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POSTGRES_HOST = "127.0.0.1"
DEFAULT_POSTGRES_PORT = 55433
REQUIRED_POSTGRES_VARIABLES = (
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)


class ConfigurationError(ValueError):
    """Raised when required database configuration is missing or invalid."""

    def __init__(self, message: str, *, missing_variables: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.missing_variables = missing_variables


def load_local_environment(dotenv_path: str | Path | None = None) -> bool:
    """Load the repository-local .env without overriding explicit shell values."""

    path = Path(dotenv_path) if dotenv_path is not None else PROJECT_ROOT / ".env"
    return load_dotenv(dotenv_path=path, override=False)


@dataclass(frozen=True)
class PostgresConfig:
    """Validated PostgreSQL settings shared by ingestion and consumption."""

    dbname: str
    user: str
    password: str = field(repr=False)
    host: str = DEFAULT_POSTGRES_HOST
    port: int = DEFAULT_POSTGRES_PORT

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        dotenv_path: str | Path | None = None,
    ) -> PostgresConfig:
        if environ is None:
            load_local_environment(dotenv_path)
            values: Mapping[str, str] = os.environ
        else:
            values = environ

        missing = tuple(
            name for name in REQUIRED_POSTGRES_VARIABLES if not values.get(name, "").strip()
        )
        if missing:
            joined = ", ".join(missing)
            raise ConfigurationError(
                f"Missing required database variables: {joined}",
                missing_variables=missing,
            )

        raw_port = values.get("POSTGRES_PORT", str(DEFAULT_POSTGRES_PORT)).strip()
        try:
            port = int(raw_port)
        except ValueError as error:
            raise ConfigurationError("POSTGRES_PORT must be an integer") from error
        if not 1 <= port <= 65535:
            raise ConfigurationError("POSTGRES_PORT must be between 1 and 65535")

        return cls(
            dbname=values["POSTGRES_DB"].strip(),
            user=values["POSTGRES_USER"].strip(),
            password=values["POSTGRES_PASSWORD"].strip(),
            host=values.get("POSTGRES_HOST", DEFAULT_POSTGRES_HOST).strip()
            or DEFAULT_POSTGRES_HOST,
            port=port,
        )
