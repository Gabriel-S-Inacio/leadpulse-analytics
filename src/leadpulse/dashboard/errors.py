"""Safe, actionable error classification for dashboard users."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import psycopg

from leadpulse.config import ConfigurationError
from leadpulse.dashboard.data import DataContractError


class DashboardErrorKind(StrEnum):
    CONFIGURATION = "configuration"
    DATABASE = "database"
    MARTS = "marts"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True)
class PublicDashboardError:
    kind: DashboardErrorKind
    message: str
    action: str


def classify_dashboard_error(error: Exception) -> PublicDashboardError:
    """Translate internal failures into messages that never include connection secrets."""

    if isinstance(error, ConfigurationError):
        missing = (
            f" Variáveis ausentes: {', '.join(error.missing_variables)}."
            if error.missing_variables
            else ""
        )
        return PublicDashboardError(
            kind=DashboardErrorKind.CONFIGURATION,
            message="A configuração local do banco de dados está incompleta.",
            action=(
                "Copie .env.example para .env e inicie o PostgreSQL com "
                f"docker compose up -d.{missing}"
            ),
        )
    if isinstance(error, psycopg.OperationalError):
        return PublicDashboardError(
            kind=DashboardErrorKind.DATABASE,
            message="O PostgreSQL não está disponível.",
            action="Execute docker compose up -d e aguarde o banco ficar saudável.",
        )
    if isinstance(
        error,
        (DataContractError, psycopg.errors.UndefinedTable, psycopg.errors.UndefinedColumn),
    ):
        return PublicDashboardError(
            kind=DashboardErrorKind.MARTS,
            message="Os modelos analíticos não estão disponíveis.",
            action=(
                "Execute python -m dotenv run -- dbt run "
                "--project-dir transform --profiles-dir transform."
            ),
        )
    return PublicDashboardError(
        kind=DashboardErrorKind.UNEXPECTED,
        message="Não foi possível carregar os dados do dashboard.",
        action="Verifique a configuração local e os logs da aplicação e tente novamente.",
    )
