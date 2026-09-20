"""Tests for the project-wide local configuration contract."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from leadpulse.config import ConfigurationError, PostgresConfig


class ProjectConfigTest(unittest.TestCase):
    def test_versioned_example_is_a_complete_local_contract(self) -> None:
        example = Path(__file__).resolve().parents[1] / ".env.example"
        with patch.dict(os.environ, {}, clear=True):
            config = PostgresConfig.from_env(dotenv_path=example)

        self.assertEqual(config.dbname, "leadpulse")
        self.assertEqual(config.user, "leadpulse")
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 55433)

    def test_loads_dotenv_and_applies_local_network_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dotenv_path = Path(temporary) / ".env"
            dotenv_path.write_text(
                "POSTGRES_DB=leadpulse\n"
                "POSTGRES_USER=leadpulse\n"
                "POSTGRES_PASSWORD=local-test-only\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = PostgresConfig.from_env(dotenv_path=dotenv_path)

        self.assertEqual(config.dbname, "leadpulse")
        self.assertEqual(config.user, "leadpulse")
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 55433)
        self.assertNotIn("local-test-only", repr(config))

    def test_explicit_environment_is_not_replaced_by_dotenv(self) -> None:
        config = PostgresConfig.from_env(
            {
                "POSTGRES_DB": "explicit-db",
                "POSTGRES_USER": "explicit-user",
                "POSTGRES_PASSWORD": "explicit-password",
                "POSTGRES_HOST": "database.internal",
                "POSTGRES_PORT": "6432",
            }
        )

        self.assertEqual(config.dbname, "explicit-db")
        self.assertEqual(config.host, "database.internal")
        self.assertEqual(config.port, 6432)

    def test_reports_every_missing_required_variable(self) -> None:
        with self.assertRaises(ConfigurationError) as captured:
            PostgresConfig.from_env({})

        self.assertEqual(
            captured.exception.missing_variables,
            ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"),
        )

    def test_rejects_out_of_range_port(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "between 1 and 65535"):
            PostgresConfig.from_env(
                {
                    "POSTGRES_DB": "leadpulse",
                    "POSTGRES_USER": "leadpulse",
                    "POSTGRES_PASSWORD": "local-test-only",
                    "POSTGRES_PORT": "70000",
                }
            )


if __name__ == "__main__":
    unittest.main()
