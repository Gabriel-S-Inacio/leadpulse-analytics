"""Opt-in live reconciliation for the dashboard semantic contract."""

from __future__ import annotations

import os
import unittest
from typing import ClassVar

from leadpulse.dashboard.data import DashboardData, MartRepository
from leadpulse.dashboard.metrics import (
    acquisition_summary,
    activation_summary,
    downstream_summary,
    marketing_summary,
)

RUN_DB_TESTS = os.environ.get("LEADPULSE_RUN_DB_TESTS") == "1"


@unittest.skipUnless(RUN_DB_TESTS, "set LEADPULSE_RUN_DB_TESTS=1 for live mart tests")
class DashboardReconciliationTest(unittest.TestCase):
    data: ClassVar[DashboardData]

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = MartRepository.from_env().fetch_all()

    def test_mart_shapes_match_published_snapshot(self) -> None:
        self.assertEqual(self.data.acquisition.shape, (124, 9))
        self.assertEqual(self.data.activation.shape, (85, 17))
        self.assertEqual(self.data.marketing.shape, (45, 22))
        self.assertEqual(self.data.downstream.shape, (4463, 9))

    def test_global_kpis_reconcile(self) -> None:
        acquisition = acquisition_summary(self.data.acquisition)
        activation = activation_summary(self.data.activation)
        downstream = downstream_summary(self.data.downstream)
        marketing = marketing_summary(self.data.marketing)

        self.assertEqual(acquisition["mqls"], 8000)
        self.assertEqual(acquisition["acquired_sellers"], 842)
        self.assertAlmostEqual(acquisition["conversion_rate"] or 0, 0.10525)
        self.assertEqual(activation["mature_sellers"], 745)
        self.assertEqual(activation["activated_sellers"], 314)
        self.assertAlmostEqual(activation["activation_rate"] or 0, 0.4214765100671141)
        self.assertAlmostEqual(activation["gmv_90d"] or 0.0, 373845.70, places=2)
        self.assertEqual(downstream["orders"], 4457)
        self.assertAlmostEqual(
            downstream["eligible_gmv"] or 0.0,
            664858.00,
            places=2,
        )
        self.assertAlmostEqual(
            marketing["synthetic_spend"] or 0.0,
            333127.59,
            places=2,
        )
        self.assertAlmostEqual(marketing["cpl"] or 0, 106.80589612055146)
        self.assertAlmostEqual(
            marketing["seller_acquisition_cost"] or 0,
            1586.321857142857,
        )
        self.assertAlmostEqual(marketing["gmv_roas"] or 0, 0.2619794415707207)


if __name__ == "__main__":
    unittest.main()
