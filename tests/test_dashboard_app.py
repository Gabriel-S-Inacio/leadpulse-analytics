"""Opt-in Streamlit runtime smoke test for every dashboard section."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

RUN_APP_TESTS = os.environ.get("LEADPULSE_RUN_APP_TESTS") == "1"
APP_PATH = Path(__file__).resolve().parents[1] / "app" / "app.py"


@unittest.skipUnless(RUN_APP_TESTS, "set LEADPULSE_RUN_APP_TESTS=1 for Streamlit tests")
class DashboardRuntimeTest(unittest.TestCase):
    def test_every_section_loads_without_runtime_exception(self) -> None:
        app = AppTest.from_file(str(APP_PATH), default_timeout=45).run()
        self.assertFalse(app.exception)
        self.assertGreaterEqual(len(app.metric), 12)
        self.assertTrue(all(metric.help for metric in app.metric))
        self.assertGreaterEqual(len(app.get("plotly_chart")), 4)
        self.assertEqual(app.title[0].value, "Visão geral executiva")
        initial_markdown = [element.value for element in app.markdown]
        self.assertTrue(any("Resumo do negócio" in value for value in initial_markdown))
        self.assertTrue(
            any(
                "Resumo do funil de aquisição, ativação, vendas e eficiência de marketing."
                in value
                for value in initial_markdown
            )
        )
        self.assertEqual(len(app.sidebar.selectbox), 0)

        expected_pages = {
            "Aquisição": (
                "Funil de aquisição",
                "Aquisição de vendedores",
                "Como os leads avançam pelo funil até se tornarem vendedores.",
                4,
            ),
            "Ativação": (
                "Primeiros 90 dias",
                "Ativação dos vendedores",
                "Quanto tempo os vendedores levam para começar a vender após a aquisição.",
                4,
            ),
            "Eficiência de marketing": (
                "Cenário simulado",
                "Eficiência de marketing",
                "Comparação entre investimento simulado, aquisição e GMV gerado.",
                4,
            ),
            "Desempenho após aquisição": (
                "Resultado comercial",
                "Desempenho após aquisição",
                "Pedidos e GMV gerados pelos vendedores adquiridos pelo funil.",
                3,
            ),
        }
        for section, (
            expected_eyebrow,
            expected_title,
            expected_description,
            minimum_charts,
        ) in expected_pages.items():
            app.sidebar.radio[0].set_value(section)
            app.run()
            self.assertFalse(app.exception, section)
            self.assertEqual(app.title[0].value, expected_title, section)
            markdown_values = [element.value for element in app.markdown]
            self.assertTrue(
                any(expected_eyebrow in value for value in markdown_values),
                section,
            )
            self.assertTrue(
                any(expected_description in value for value in markdown_values),
                section,
            )
            self.assertGreater(len(app.metric), 0, section)
            self.assertTrue(all(metric.help for metric in app.metric), section)
            self.assertEqual(len(app.sidebar.selectbox), 0, section)
            self.assertGreaterEqual(
                len(app.get("plotly_chart")),
                minimum_charts,
                section,
            )

        self.assertEqual(
            app.sidebar.radio[0].options,
            [
                "Visão geral",
                "Aquisição",
                "Ativação",
                "Eficiência de marketing",
                "Desempenho após aquisição",
            ],
        )


if __name__ == "__main__":
    unittest.main()
