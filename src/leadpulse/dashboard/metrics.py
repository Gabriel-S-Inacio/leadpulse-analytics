"""Composable KPI calculations over dashboard-ready semantic marts."""

from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd


def safe_divide(numerator: float, denominator: float) -> float | None:
    numerator_value = float(numerator)
    denominator_value = float(denominator)
    if not math.isfinite(numerator_value) or not math.isfinite(denominator_value):
        return None
    if denominator_value == 0:
        return None
    return numerator_value / denominator_value


def sum_column(frame: pd.DataFrame, column: str) -> float:
    if frame.empty:
        return 0.0
    return float(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum())


def weighted_average(
    frame: pd.DataFrame,
    value_column: str,
    weight_column: str,
) -> float | None:
    values = pd.to_numeric(frame[value_column], errors="coerce")
    weights = pd.to_numeric(frame[weight_column], errors="coerce")
    valid = values.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return None
    return safe_divide(float((values[valid] * weights[valid]).sum()), float(weights[valid].sum()))


def single_slice_value(frame: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if len(frame) != 1 or len(values) != 1:
        return None
    return float(values.iloc[0])


def acquisition_summary(frame: pd.DataFrame) -> dict[str, float | None]:
    mqls = sum_column(frame, "mqls")
    closed_deals = sum_column(frame, "closed_deals")
    acquired_sellers = sum_column(frame, "acquired_sellers")
    return {
        "mqls": mqls,
        "closed_deals": closed_deals,
        "acquired_sellers": acquired_sellers,
        "conversion_rate": safe_divide(acquired_sellers, mqls),
    }


def activation_summary(frame: pd.DataFrame) -> dict[str, float | None]:
    mature = sum_column(frame, "acquired_sellers_mature")
    activated = sum_column(frame, "activated_sellers_90d")
    gmv = sum_column(frame, "gmv_90d")
    orders = sum_column(frame, "orders_90d")
    return {
        "mature_sellers": mature,
        "activated_sellers": activated,
        "activation_rate": safe_divide(activated, mature),
        "avg_time_to_first_order_days": weighted_average(
            frame,
            "avg_time_to_first_order_days",
            "activated_sellers_90d",
        ),
        "median_time_to_first_order_days": single_slice_value(
            frame, "median_time_to_first_order_days"
        ),
        "gmv_90d": gmv,
        "orders_90d": orders,
        "gmv_per_activated_seller": safe_divide(gmv, activated),
        "orders_per_activated_seller": safe_divide(orders, activated),
    }


def marketing_summary(frame: pd.DataFrame) -> dict[str, float | None]:
    spend = sum_column(frame, "synthetic_marketing_spend")
    mqls = sum_column(frame, "mqls")
    acquired = sum_column(frame, "acquired_sellers")
    gmv = sum_column(frame, "eligible_gmv_90d")
    return {
        "synthetic_spend": spend,
        "mqls": mqls,
        "acquired_sellers": acquired,
        "eligible_gmv_90d": gmv,
        "cpl": safe_divide(spend, mqls),
        "seller_acquisition_cost": safe_divide(spend, acquired),
        "gmv_roas": safe_divide(gmv, spend),
    }


def downstream_summary(frame: pd.DataFrame) -> dict[str, float | None]:
    orders = 0 if frame.empty else int(frame["order_id"].nunique(dropna=True))
    return {
        "orders": float(orders),
        "seller_order_participations": sum_column(frame, "seller_order_participations"),
        "eligible_gmv": sum_column(frame, "eligible_gmv"),
    }


def group_acquisition(frame: pd.DataFrame, dimensions: Sequence[str]) -> pd.DataFrame:
    columns = [*dimensions, "mqls", "closed_deals", "acquired_sellers"]
    if frame.empty:
        return pd.DataFrame(columns=[*columns, "conversion_rate"])
    grouped = frame.groupby(list(dimensions), dropna=False, as_index=False)[
        ["mqls", "closed_deals", "acquired_sellers"]
    ].sum()
    grouped["conversion_rate"] = grouped["acquired_sellers"].div(
        grouped["mqls"].replace(0, float("nan"))
    )
    return grouped


def group_activation(frame: pd.DataFrame, dimensions: Sequence[str]) -> pd.DataFrame:
    columns = [
        *dimensions,
        "acquired_sellers_mature",
        "activated_sellers_90d",
        "gmv_90d",
        "orders_90d",
        "activation_rate",
        "avg_time_to_first_order_days",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    prepared = frame.copy()
    prepared["weighted_time"] = (
        pd.to_numeric(prepared["avg_time_to_first_order_days"], errors="coerce")
        * pd.to_numeric(prepared["activated_sellers_90d"], errors="coerce")
    ).fillna(0)
    grouped = prepared.groupby(list(dimensions), dropna=False, as_index=False).agg(
        acquired_sellers_mature=("acquired_sellers_mature", "sum"),
        activated_sellers_90d=("activated_sellers_90d", "sum"),
        gmv_90d=("gmv_90d", "sum"),
        orders_90d=("orders_90d", "sum"),
        weighted_time=("weighted_time", "sum"),
    )
    grouped["activation_rate"] = grouped["activated_sellers_90d"].div(
        grouped["acquired_sellers_mature"].replace(0, float("nan"))
    )
    grouped["avg_time_to_first_order_days"] = grouped["weighted_time"].div(
        grouped["activated_sellers_90d"].replace(0, float("nan"))
    )
    return grouped.drop(columns="weighted_time")


def group_marketing(frame: pd.DataFrame, dimensions: Sequence[str]) -> pd.DataFrame:
    columns = [
        *dimensions,
        "synthetic_marketing_spend",
        "mqls",
        "acquired_sellers",
        "eligible_gmv_90d",
        "cpl",
        "seller_acquisition_cost",
        "gmv_roas",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    grouped = frame.groupby(list(dimensions), dropna=False, as_index=False)[
        ["synthetic_marketing_spend", "mqls", "acquired_sellers", "eligible_gmv_90d"]
    ].sum()
    spend = grouped["synthetic_marketing_spend"].replace(0, float("nan"))
    grouped["cpl"] = grouped["synthetic_marketing_spend"].div(
        grouped["mqls"].replace(0, float("nan"))
    )
    grouped["seller_acquisition_cost"] = grouped["synthetic_marketing_spend"].div(
        grouped["acquired_sellers"].replace(0, float("nan"))
    )
    grouped["gmv_roas"] = grouped["eligible_gmv_90d"].div(spend)
    return grouped


def group_downstream(frame: pd.DataFrame, dimensions: Sequence[str]) -> pd.DataFrame:
    columns = [*dimensions, "orders", "seller_order_participations", "eligible_gmv"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    return frame.groupby(list(dimensions), dropna=False, as_index=False).agg(
        orders=("order_id", "nunique"),
        seller_order_participations=("seller_order_participations", "sum"),
        eligible_gmv=("eligible_gmv", "sum"),
    )
