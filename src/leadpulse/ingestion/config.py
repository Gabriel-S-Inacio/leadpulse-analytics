"""Environment-backed PostgreSQL configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


class ConfigurationError(ValueError):
    """Raised when required database configuration is invalid."""


@dataclass(frozen=True)
class PostgresConfig:
    dbname: str
    user: str
    password: str = field(repr=False)
    host: str
    port: int

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> PostgresConfig:
        values = os.environ if environ is None else environ

        def required(name: str) -> str:
            value = values.get(name, "").strip()
            if not value:
                raise ConfigurationError(f"{name} is required")
            return value

        raw_port = required("POSTGRES_PORT")
        try:
            port = int(raw_port)
        except ValueError as error:
            raise ConfigurationError("POSTGRES_PORT must be an integer") from error
        if not 1 <= port <= 65535:
            raise ConfigurationError("POSTGRES_PORT must be between 1 and 65535")

        return cls(
            dbname=required("POSTGRES_DB"),
            user=required("POSTGRES_USER"),
            password=required("POSTGRES_PASSWORD"),
            host=required("POSTGRES_HOST"),
            port=port,
        )
