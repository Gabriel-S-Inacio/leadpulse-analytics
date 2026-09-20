"""In-memory filters that preserve each mart's governed period semantics."""

from __future__ import annotations

from datetime import date

import pandas as pd

MISSING_ORIGIN_LABEL = "Origem ausente ou não observada"


def origin_labels(frame: pd.DataFrame) -> list[str]:
    values = frame["source_origin"].fillna(MISSING_ORIGIN_LABEL).astype(str)
    return sorted(values.unique().tolist())


def channel_labels(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["normalized_channel"].dropna().astype(str).unique().tolist())


def apply_filters(
    frame: pd.DataFrame,
    *,
    period_column: str,
    start_date: date,
    end_date: date,
    origins: list[str] | None = None,
    channels: list[str] | None = None,
) -> pd.DataFrame:
    if period_column not in frame.columns:
        raise ValueError(f"Unknown period column: {period_column}")
    if start_date > end_date:
        return frame.iloc[0:0].copy()

    period = pd.to_datetime(frame[period_column], errors="coerce")
    mask = period.between(pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="both")

    selected_origins = origins or []
    if selected_origins:
        labels = frame["source_origin"].fillna(MISSING_ORIGIN_LABEL).astype(str)
        mask &= labels.isin(selected_origins)

    selected_channels = channels or []
    if selected_channels:
        mask &= frame["normalized_channel"].astype(str).isin(selected_channels)

    return frame.loc[mask].copy()
