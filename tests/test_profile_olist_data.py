"""Focused tests for CSV profiling and relationship measurements."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "profile_olist_data.py"
SPEC = importlib.util.spec_from_file_location("profile_olist_data", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load profiling module for tests.")
profile = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = profile
SPEC.loader.exec_module(profile)


class ProfilingHelpersTest(unittest.TestCase):
    def test_profile_measures_nulls_distinct_keys_dates_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "olist_marketing_qualified_leads_dataset.csv"
            path.write_text(
                "mql_id,first_contact_date,landing_page_id,origin\n"
                "m1,2018-01-01,lp1,organic\n"
                "m2,2018-01-03,lp2,\n"
                "m2,2018-01-03,lp2,\n",
                encoding="utf-8",
            )

            result = profile.profile_csv(path, profile.TABLES[0])

            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["columns"], 4)
            self.assertEqual(result["duplicate_full_rows"], 1)
            self.assertEqual(result["column_profile"]["origin"]["null_count"], 2)
            self.assertEqual(result["column_profile"]["mql_id"]["distinct_non_null_count"], 2)
            self.assertEqual(result["candidate_keys"]["mql_id"]["duplicate_key_rows"], 1)
            self.assertFalse(
                result["candidate_keys"]["mql_id"]["is_unique_and_non_null"]
            )
            self.assertEqual(
                result["date_ranges"]["first_contact_date"],
                {"min": "2018-01-01", "max": "2018-01-03"},
            )
            self.assertEqual(
                result["categorical_findings"]["origin"]["examples"], ["organic"]
            )

    def test_relationship_profile_reports_matches_and_multiplicity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            left = directory / "left.csv"
            right = directory / "right.csv"
            left.write_text("id\na\nb\nb\nc\n", encoding="utf-8")
            right.write_text("id\nb\nb\nc\nd\n", encoding="utf-8")

            result = profile.relationship_profile("left -> right", left, "id", right, "id")

            self.assertEqual(result["left_distinct_keys"], 3)
            self.assertEqual(result["right_distinct_keys"], 3)
            self.assertEqual(result["matched_distinct_keys"], 2)
            self.assertEqual(result["unmatched_left_keys"], 1)
            self.assertEqual(result["unmatched_right_keys"], 1)
            self.assertEqual(result["observed_row_multiplicity"], "N:N")
            self.assertAlmostEqual(result["left_match_percentage"], 66.666667)

    def test_numeric_profile_reports_zero_negative_null_and_exact_sum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "numeric.csv"
            path.write_text(
                "id,amount\n"
                "1,10.50\n"
                "2,0\n"
                "3,-1.25\n"
                "4,\n",
                encoding="utf-8",
            )
            spec = profile.TableSpec(
                name="numeric",
                filename="numeric.csv",
                candidate_keys=(("id",),),
                numeric_fields=("amount",),
            )

            result = profile.profile_csv(path, spec)["numeric_findings"]["amount"]

            self.assertEqual(result["count"], 3)
            self.assertEqual(result["null_count"], 1)
            self.assertEqual(result["zero_count"], 1)
            self.assertEqual(result["negative_count"], 1)
            self.assertEqual(result["min"], "-1.25")
            self.assertEqual(result["max"], "10.50")
            self.assertEqual(result["sum"], "9.25")

    def test_seller_activation_uses_first_observed_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            closed = directory / "closed.csv"
            items = directory / "items.csv"
            orders = directory / "orders.csv"
            closed.write_text(
                "seller_id,won_date\ns1,2020-01-02 00:00:00\ns2,2020-01-02 00:00:00\n",
                encoding="utf-8",
            )
            items.write_text(
                "seller_id,order_id\ns1,o1\ns1,o2\n",
                encoding="utf-8",
            )
            orders.write_text(
                "order_id,order_purchase_timestamp\n"
                "o1,2020-01-03 00:00:00\n"
                "o2,2019-12-31 00:00:00\n",
                encoding="utf-8",
            )

            result = profile.seller_activation_profile(closed, items, orders)

            self.assertEqual(result["closed_deal_sellers"], 2)
            self.assertEqual(result["sellers_with_order_items"], 1)
            self.assertEqual(result["sellers_without_order_items"], 1)
            self.assertEqual(result["observed_activation_percentage"], 50.0)
            self.assertEqual(result["days_to_first_order_min"], -2.0)
            self.assertEqual(result["negative_days_to_first_order"], 1)

    def test_mvp_activation_requires_delivered_post_win_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            closed = directory / "closed.csv"
            items = directory / "items.csv"
            orders = directory / "orders.csv"
            closed.write_text(
                "seller_id,won_date\n"
                "s1,2020-01-01 00:00:00\n"
                "s2,2020-01-01 00:00:00\n"
                "s3,2020-01-01 00:00:00\n",
                encoding="utf-8",
            )
            items.write_text(
                "seller_id,order_id\n"
                "s1,before\n"
                "s1,after\n"
                "s2,shipped\n",
                encoding="utf-8",
            )
            orders.write_text(
                "order_id,order_status,order_purchase_timestamp\n"
                "before,delivered,2019-12-31 00:00:00\n"
                "after,delivered,2020-01-11 00:00:00\n"
                "shipped,shipped,2020-01-05 00:00:00\n"
                "cutoff,created,2020-07-01 00:00:00\n",
                encoding="utf-8",
            )

            result = profile.mvp_seller_activation_candidate_profile(
                closed, items, orders
            )

            self.assertEqual(result["sellers_with_post_win_eligible_order"], 1)
            self.assertEqual(result["sellers_without_post_win_eligible_order"], 2)
            self.assertEqual(result["rejected_item_rows_at_or_before_won"], 1)
            self.assertEqual(result["days_to_first_eligible_order"]["median"], 10.0)
            self.assertEqual(
                result["window_analysis_days"]["90"]["mature_cohort_sellers"],
                3,
            )


if __name__ == "__main__":
    unittest.main()
