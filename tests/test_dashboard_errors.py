"""Tests for safe dashboard error classification."""

from __future__ import annotations

import unittest

import psycopg

from leadpulse.config import ConfigurationError
from leadpulse.dashboard.data import DataContractError
from leadpulse.dashboard.errors import DashboardErrorKind, classify_dashboard_error


class DashboardErrorTest(unittest.TestCase):
    def test_classifies_missing_configuration_with_actionable_guidance(self) -> None:
        error = ConfigurationError(
            "internal detail",
            missing_variables=("POSTGRES_DB", "POSTGRES_PASSWORD"),
        )

        result = classify_dashboard_error(error)

        self.assertEqual(result.kind, DashboardErrorKind.CONFIGURATION)
        self.assertIn("Copie .env.example para .env", result.action)
        self.assertIn("POSTGRES_DB", result.action)
        self.assertIn("POSTGRES_PASSWORD", result.action)

    def test_distinguishes_database_and_mart_failures(self) -> None:
        database = classify_dashboard_error(
            psycopg.OperationalError("password=must-never-be-rendered")
        )
        missing_table = classify_dashboard_error(
            psycopg.errors.UndefinedTable("analytics mart missing")
        )
        changed_contract = classify_dashboard_error(DataContractError("columns changed"))

        self.assertEqual(database.kind, DashboardErrorKind.DATABASE)
        self.assertIn("docker compose up -d", database.action)
        self.assertEqual(missing_table.kind, DashboardErrorKind.MARTS)
        self.assertEqual(changed_contract.kind, DashboardErrorKind.MARTS)
        self.assertIn("dbt run", missing_table.action)

    def test_public_messages_never_echo_internal_errors_or_passwords(self) -> None:
        secret = "must-never-be-rendered"
        errors = (
            psycopg.OperationalError(f"password={secret}"),
            DataContractError(f"unsafe internal detail {secret}"),
            RuntimeError(f"unexpected internal detail {secret}"),
        )

        for error in errors:
            with self.subTest(error=type(error).__name__):
                result = classify_dashboard_error(error)
                rendered = f"{result.message} {result.action}"
                self.assertNotIn(secret, rendered)
                self.assertNotIn("password=", rendered)


if __name__ == "__main__":
    unittest.main()
