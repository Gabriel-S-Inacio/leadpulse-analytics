"""Tests for dashboard formatting, filtering, and governed KPI aggregation."""

from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from leadpulse.dashboard.data import MART_QUERIES
from leadpulse.dashboard.filters import MISSING_ORIGIN_LABEL, apply_filters
from leadpulse.dashboard.formatting import (
    format_brl,
    format_days,
    format_decimal,
    format_integer,
    format_percent,
    format_roas,
)
from leadpulse.dashboard.metrics import (
    acquisition_summary,
    activation_summary,
    downstream_summary,
    group_downstream,
    marketing_summary,
    safe_divide,
)


class FormattingTest(unittest.TestCase):
    def test_formats_pt_br_business_values(self) -> None:
        self.assertEqual(format_integer(8000), "8.000")
        self.assertEqual(format_brl(664858), "R$ 664.858,00")
        self.assertEqual(format_percent(0.10525), "10,53%")
        self.assertEqual(format_roas(0.261979), "0,26x")
        self.assertEqual(format_decimal(7.92), "7,92")
        self.assertEqual(format_days(44.26), "44,26 dias")

    def test_formats_missing_and_non_finite_as_na(self) -> None:
        self.assertEqual(format_brl(None), "N/A")
        self.assertEqual(format_percent(float("nan")), "N/A")
        self.assertEqual(format_roas(float("inf")), "N/A")


class AggregationTest(unittest.TestCase):
    def test_safe_divide_handles_zero_and_non_finite_values(self) -> None:
        self.assertEqual(safe_divide(5, 2), 2.5)
        self.assertIsNone(safe_divide(5, 0))
        self.assertIsNone(safe_divide(float("nan"), 2))

    def test_acquisition_recomputes_overall_conversion(self) -> None:
        frame = pd.DataFrame(
            {
                "mqls": [90, 10],
                "closed_deals": [9, 5],
                "acquired_sellers": [9, 5],
                "mql_to_acquired_seller_conversion_rate": [0.1, 0.5],
            }
        )
        summary = acquisition_summary(frame)
        self.assertEqual(summary["mqls"], 100)
        self.assertEqual(summary["acquired_sellers"], 14)
        self.assertAlmostEqual(summary["conversion_rate"] or 0, 0.14)

    def test_activation_uses_weighted_average_and_never_combines_medians(self) -> None:
        frame = pd.DataFrame(
            {
                "acquired_sellers_mature": [10, 20],
                "activated_sellers_90d": [2, 8],
                "avg_time_to_first_order_days": [10.0, 20.0],
                "median_time_to_first_order_days": [8.0, 18.0],
                "gmv_90d": [100.0, 400.0],
                "orders_90d": [4, 16],
            }
        )
        summary = activation_summary(frame)
        self.assertAlmostEqual(summary["activation_rate"] or 0, 1 / 3)
        self.assertAlmostEqual(summary["avg_time_to_first_order_days"] or 0, 18.0)
        self.assertIsNone(summary["median_time_to_first_order_days"])

    def test_marketing_ratios_use_summed_components(self) -> None:
        frame = pd.DataFrame(
            {
                "synthetic_marketing_spend": [100.0, 300.0],
                "mqls": [10, 30],
                "acquired_sellers": [1, 3],
                "eligible_gmv_90d": [25.0, 75.0],
            }
        )
        summary = marketing_summary(frame)
        self.assertEqual(summary["cpl"], 10.0)
        self.assertEqual(summary["seller_acquisition_cost"], 100.0)
        self.assertEqual(summary["gmv_roas"], 0.25)

    def test_downstream_counts_distinct_orders_and_participations_separately(self) -> None:
        frame = pd.DataFrame(
            {
                "order_id": ["order-1", "order-1", "order-2"],
                "seller_order_participations": [1, 1, 1],
                "eligible_gmv": [10.0, 20.0, 30.0],
            }
        )
        summary = downstream_summary(frame)
        self.assertEqual(summary["orders"], 2)
        self.assertEqual(summary["seller_order_participations"], 3)
        self.assertEqual(summary["eligible_gmv"], 60)

    def test_grouped_downstream_retains_distinct_order_semantics(self) -> None:
        frame = pd.DataFrame(
            {
                "purchase_month": pd.to_datetime(["2018-01-01"] * 3),
                "order_id": ["order-1", "order-1", "order-2"],
                "seller_order_participations": [1, 1, 1],
                "eligible_gmv": [10.0, 20.0, 30.0],
            }
        )
        grouped = group_downstream(frame, ["purchase_month"])
        self.assertEqual(grouped.iloc[0]["orders"], 2)
        self.assertEqual(grouped.iloc[0]["seller_order_participations"], 3)


class FilterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "period": pd.to_datetime(["2018-01-01", "2018-02-01", "2018-03-01"]),
                "source_origin": ["paid_search", None, "social"],
                "normalized_channel": ["paid_search", "unattributed", "social"],
                "value": [1, 2, 3],
            }
        )

    def test_combines_period_origin_and_channel_filters(self) -> None:
        result = apply_filters(
            self.frame,
            period_column="period",
            start_date=date(2018, 1, 1),
            end_date=date(2018, 2, 1),
            origins=[MISSING_ORIGIN_LABEL],
            channels=["unattributed"],
        )
        self.assertEqual(result["value"].tolist(), [2])

    def test_invalid_date_range_returns_empty_frame(self) -> None:
        result = apply_filters(
            self.frame,
            period_column="period",
            start_date=date(2018, 3, 1),
            end_date=date(2018, 1, 1),
        )
        self.assertTrue(result.empty)


class DataAccessBoundaryTest(unittest.TestCase):
    def test_queries_are_constant_and_restricted_to_semantic_marts(self) -> None:
        self.assertEqual(len(MART_QUERIES), 4)
        for query in MART_QUERIES.values():
            lowered = query.lower()
            self.assertIn(" from analytics.mart_", lowered)
            self.assertNotIn(" raw.", lowered)
            self.assertNotIn(" staging.", lowered)
            self.assertNotIn(" fct_", lowered)
            self.assertNotIn("%s", query)
            self.assertNotIn("{", query)
        self.assertNotIn("seller_key", MART_QUERIES["downstream"])


if __name__ == "__main__":
    unittest.main()
