"""Profile local Olist CSVs with the Python standard library."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT = RAW_DIR / "_profiling" / "profile.json"
NULL_STRINGS = {"", "null", "none", "na", "n/a"}
MAX_CATEGORY_EXAMPLES = 10


@dataclass(frozen=True)
class TableSpec:
    name: str
    filename: str
    candidate_keys: tuple[tuple[str, ...], ...]
    date_fields: tuple[str, ...] = ()
    categorical_fields: tuple[str, ...] = ()
    id_fields: tuple[str, ...] = ()
    numeric_fields: tuple[str, ...] = ()


TABLES = (
    TableSpec(
        name="marketing_qualified_leads",
        filename="olist_marketing_qualified_leads_dataset.csv",
        candidate_keys=(("mql_id",),),
        date_fields=("first_contact_date",),
        categorical_fields=("origin",),
        id_fields=("mql_id", "landing_page_id"),
    ),
    TableSpec(
        name="closed_deals",
        filename="olist_closed_deals_dataset.csv",
        candidate_keys=(("mql_id", "seller_id"), ("mql_id",), ("seller_id",)),
        date_fields=("won_date",),
        categorical_fields=(
            "business_segment",
            "lead_type",
            "lead_behaviour_profile",
            "business_type",
        ),
        id_fields=("mql_id", "seller_id", "sdr_id", "sr_id"),
    ),
    TableSpec(
        name="sellers",
        filename="olist_sellers_dataset.csv",
        candidate_keys=(("seller_id",),),
        categorical_fields=("seller_state",),
        id_fields=("seller_id",),
    ),
    TableSpec(
        name="orders",
        filename="olist_orders_dataset.csv",
        candidate_keys=(("order_id",),),
        date_fields=(
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
        categorical_fields=("order_status",),
        id_fields=("order_id", "customer_id"),
    ),
    TableSpec(
        name="order_items",
        filename="olist_order_items_dataset.csv",
        candidate_keys=(("order_id", "order_item_id"),),
        date_fields=("shipping_limit_date",),
        id_fields=("order_id", "order_item_id", "product_id", "seller_id"),
        numeric_fields=("price", "freight_value"),
    ),
    TableSpec(
        name="customers",
        filename="olist_customers_dataset.csv",
        candidate_keys=(("customer_id",), ("customer_unique_id",)),
        categorical_fields=("customer_state",),
        id_fields=("customer_id", "customer_unique_id"),
    ),
    TableSpec(
        name="payments",
        filename="olist_order_payments_dataset.csv",
        candidate_keys=(("order_id", "payment_sequential"),),
        categorical_fields=("payment_type",),
        id_fields=("order_id", "payment_sequential"),
        numeric_fields=("payment_value",),
    ),
)

RELATIONSHIPS = (
    (
        "marketing_qualified_leads.mql_id -> closed_deals.mql_id",
        "olist_marketing_qualified_leads_dataset.csv",
        "mql_id",
        "olist_closed_deals_dataset.csv",
        "mql_id",
    ),
    (
        "closed_deals.seller_id -> sellers.seller_id",
        "olist_closed_deals_dataset.csv",
        "seller_id",
        "olist_sellers_dataset.csv",
        "seller_id",
    ),
    (
        "closed_deals.seller_id -> order_items.seller_id",
        "olist_closed_deals_dataset.csv",
        "seller_id",
        "olist_order_items_dataset.csv",
        "seller_id",
    ),
    (
        "sellers.seller_id -> order_items.seller_id",
        "olist_sellers_dataset.csv",
        "seller_id",
        "olist_order_items_dataset.csv",
        "seller_id",
    ),
    (
        "order_items.order_id -> orders.order_id",
        "olist_order_items_dataset.csv",
        "order_id",
        "olist_orders_dataset.csv",
        "order_id",
    ),
    (
        "orders.customer_id -> customers.customer_id",
        "olist_orders_dataset.csv",
        "customer_id",
        "olist_customers_dataset.csv",
        "customer_id",
    ),
    (
        "orders.order_id -> payments.order_id",
        "olist_orders_dataset.csv",
        "order_id",
        "olist_order_payments_dataset.csv",
        "order_id",
    ),
)


class ProfilingError(RuntimeError):
    """Raised when a local raw file cannot be profiled safely."""


def is_null(value: str | None) -> bool:
    return value is None or value.strip().lower() in NULL_STRINGS


def detect_csv_format(path: Path) -> tuple[str, str]:
    with path.open("rb") as source:
        sample_bytes = source.read(128 * 1024)
    selected_encoding: str | None = None
    sample_text = ""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            sample_text = sample_bytes.decode(encoding)
            selected_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if selected_encoding is None:
        raise ProfilingError(f"Could not detect a supported encoding for {path}")

    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    return selected_encoding, delimiter


def open_dict_reader(path: Path) -> tuple[object, csv.DictReader[str], str, str]:
    encoding, delimiter = detect_csv_format(path)
    handle = path.open("r", encoding=encoding, newline="")
    reader = csv.DictReader(handle, delimiter=delimiter)
    if not reader.fieldnames:
        handle.close()
        raise ProfilingError(f"CSV has no header: {path}")
    return handle, reader, encoding, delimiter


def row_fingerprint(values: Iterable[str]) -> bytes:
    payload = json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).digest()


def inventory_csv(path: Path) -> dict[str, object]:
    handle, reader, encoding, delimiter = open_dict_reader(path)
    fieldnames = tuple(reader.fieldnames or ())
    row_count = 0
    duplicate_rows = 0
    fingerprints: set[bytes] = set()
    try:
        for row in reader:
            row_count += 1
            fingerprint = row_fingerprint((row.get(column) or "") for column in fieldnames)
            if fingerprint in fingerprints:
                duplicate_rows += 1
            else:
                fingerprints.add(fingerprint)
    finally:
        handle.close()
    return {
        "filename": path.name,
        "relative_path": path.relative_to(RAW_DIR).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "encoding": encoding,
        "delimiter": delimiter,
        "rows": row_count,
        "columns": len(fieldnames),
        "column_names": list(fieldnames),
        "duplicate_full_rows": duplicate_rows,
    }


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decimal_text(value: object) -> str | None:
    if value is None:
        return None
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    return format(decimal_value, "f")


def _casefold_variants(values: Counter[str]) -> dict[str, list[str]]:
    variants: dict[str, list[str]] = {}
    for value in values:
        variants.setdefault(value.casefold(), []).append(value)
    return {key: sorted(group) for key, group in variants.items()}


def profile_csv(path: Path, spec: TableSpec) -> dict[str, object]:
    handle, reader, encoding, delimiter = open_dict_reader(path)
    fieldnames = tuple(reader.fieldnames or ())
    missing_configured_columns = sorted(
        {
            column
            for columns in spec.candidate_keys
            for column in columns
            if column not in fieldnames
        }
        | {column for column in spec.date_fields if column not in fieldnames}
        | {column for column in spec.categorical_fields if column not in fieldnames}
        | {column for column in spec.id_fields if column not in fieldnames}
        | {column for column in spec.numeric_fields if column not in fieldnames}
    )

    null_counts = {column: 0 for column in fieldnames}
    distinct_values = {column: set() for column in fieldnames}
    date_ranges = {
        column: {"min": None, "max": None}
        for column in spec.date_fields
        if column in fieldnames
    }
    categorical_values = {
        column: Counter()
        for column in spec.categorical_fields
        if column in fieldnames
    }
    categorical_whitespace_rows = {
        column: 0 for column in categorical_values
    }
    numeric_state = {
        column: {
            "count": 0,
            "null_count": 0,
            "invalid_count": 0,
            "zero_count": 0,
            "negative_count": 0,
            "min": None,
            "max": None,
            "sum": Decimal("0"),
        }
        for column in spec.numeric_fields
        if column in fieldnames
    }
    candidate_state = {
        "|".join(columns): {
            "columns": columns,
            "seen": set(),
            "null_rows": 0,
            "duplicate_key_rows": 0,
        }
        for columns in spec.candidate_keys
        if all(column in fieldnames for column in columns)
    }
    fingerprints: set[bytes] = set()
    row_count = 0
    duplicate_rows = 0

    try:
        for row in reader:
            row_count += 1
            normalized = {column: (row.get(column) or "").strip() for column in fieldnames}
            fingerprint = row_fingerprint(normalized[column] for column in fieldnames)
            if fingerprint in fingerprints:
                duplicate_rows += 1
            else:
                fingerprints.add(fingerprint)

            for column, value in normalized.items():
                if is_null(value):
                    null_counts[column] += 1
                else:
                    distinct_values[column].add(value)

            for column, bounds in date_ranges.items():
                value = normalized[column]
                if is_null(value):
                    continue
                bounds["min"] = value if bounds["min"] is None else min(bounds["min"], value)
                bounds["max"] = value if bounds["max"] is None else max(bounds["max"], value)

            for column, values in categorical_values.items():
                raw_value = row.get(column) or ""
                value = raw_value.strip()
                if raw_value != value:
                    categorical_whitespace_rows[column] += 1
                if not is_null(value):
                    values[value] += 1

            for column, state in numeric_state.items():
                value = normalized[column]
                if is_null(value):
                    state["null_count"] += 1
                    continue
                try:
                    number = Decimal(value)
                except InvalidOperation:
                    state["invalid_count"] += 1
                    continue
                state["count"] += 1
                state["sum"] += number
                state["zero_count"] += int(number == 0)
                state["negative_count"] += int(number < 0)
                state["min"] = number if state["min"] is None else min(state["min"], number)
                state["max"] = number if state["max"] is None else max(state["max"], number)

            for state in candidate_state.values():
                columns = state["columns"]
                key = tuple(normalized[column] for column in columns)
                if any(is_null(value) for value in key):
                    state["null_rows"] += 1
                elif key in state["seen"]:
                    state["duplicate_key_rows"] += 1
                else:
                    state["seen"].add(key)
    finally:
        handle.close()

    columns_profile = {
        column: {
            "null_count": null_counts[column],
            "null_percentage": round(
                (null_counts[column] / row_count * 100) if row_count else 0.0, 6
            ),
            "distinct_non_null_count": len(distinct_values[column]),
        }
        for column in fieldnames
    }
    candidate_keys = {
        name: {
            "columns": list(state["columns"]),
            "distinct_non_null_keys": len(state["seen"]),
            "null_rows": state["null_rows"],
            "duplicate_key_rows": state["duplicate_key_rows"],
            "is_unique_and_non_null": (
                state["null_rows"] == 0 and state["duplicate_key_rows"] == 0
            ),
        }
        for name, state in candidate_state.items()
    }
    return {
        "table": spec.name,
        "filename": path.name,
        "encoding": encoding,
        "delimiter": delimiter,
        "rows": row_count,
        "columns": len(fieldnames),
        "column_names": list(fieldnames),
        "duplicate_full_rows": duplicate_rows,
        "column_profile": columns_profile,
        "candidate_keys": candidate_keys,
        "date_ranges": date_ranges,
        "categorical_findings": {
            column: {
                "distinct_count": len(values),
                "examples": sorted(values)[:MAX_CATEGORY_EXAMPLES],
                "examples_truncated": len(values) > MAX_CATEGORY_EXAMPLES,
                "value_counts": dict(
                    sorted(values.items(), key=lambda item: (-item[1], item[0]))
                ),
                "rare_values_under_one_percent": {
                    value: count
                    for value, count in sorted(values.items())
                    if sum(values.values()) and count / sum(values.values()) < 0.01
                },
                "leading_or_trailing_whitespace_rows": categorical_whitespace_rows[column],
                "casefold_collisions": {
                    folded: variants
                    for folded, variants in _casefold_variants(values).items()
                    if len(variants) > 1
                },
            }
            for column, values in categorical_values.items()
        },
        "numeric_findings": {
            column: {
                "count": state["count"],
                "null_count": state["null_count"],
                "invalid_count": state["invalid_count"],
                "zero_count": state["zero_count"],
                "negative_count": state["negative_count"],
                "min": _decimal_text(state["min"]),
                "max": _decimal_text(state["max"]),
                "sum": _decimal_text(state["sum"]),
            }
            for column, state in numeric_state.items()
        },
        "id_cardinality": {
            column: len(distinct_values[column])
            for column in spec.id_fields
            if column in distinct_values
        },
        "missing_configured_columns": missing_configured_columns,
    }


def find_unique_file(filename: str) -> Path | None:
    matches = sorted(RAW_DIR.rglob(filename)) if RAW_DIR.exists() else []
    matches = [path for path in matches if "_profiling" not in path.parts]
    if len(matches) > 1:
        raise ProfilingError(
            f"Multiple raw files named {filename}; provenance is ambiguous."
        )
    return matches[0] if matches else None


def load_key_counts(path: Path, column: str) -> Counter[str]:
    handle, reader, _encoding, _delimiter = open_dict_reader(path)
    if column not in (reader.fieldnames or ()):
        handle.close()
        raise ProfilingError(f"Missing relationship column {column} in {path.name}")
    counts: Counter[str] = Counter()
    try:
        for row in reader:
            value = (row.get(column) or "").strip()
            if not is_null(value):
                counts[value] += 1
    finally:
        handle.close()
    return counts


def relationship_profile(
    name: str,
    left_path: Path,
    left_column: str,
    right_path: Path,
    right_column: str,
) -> dict[str, object]:
    left_counts = load_key_counts(left_path, left_column)
    right_counts = load_key_counts(right_path, right_column)
    left_keys = set(left_counts)
    right_keys = set(right_counts)
    matched = left_keys & right_keys
    unmatched_left = left_keys - right_keys
    unmatched_right = right_keys - left_keys
    left_max = max(left_counts.values(), default=0)
    right_max = max(right_counts.values(), default=0)
    left_symbol = "N" if left_max > 1 else "1"
    right_symbol = "N" if right_max > 1 else "1"
    multiplicity = (
        f"{left_symbol}:{right_symbol}"
        if left_counts and right_counts
        else "UNDETERMINED_EMPTY"
    )
    return {
        "relationship": name,
        "left_distinct_keys": len(left_keys),
        "right_distinct_keys": len(right_keys),
        "matched_distinct_keys": len(matched),
        "unmatched_left_keys": len(unmatched_left),
        "unmatched_right_keys": len(unmatched_right),
        "left_match_percentage": (
            round(len(matched) / len(left_keys) * 100, 6) if left_keys else None
        ),
        "observed_row_multiplicity": multiplicity,
        "left_max_rows_per_key": left_max,
        "right_max_rows_per_key": right_max,
        "left_keys_with_multiple_rows": sum(
            1 for count in left_counts.values() if count > 1
        ),
        "right_keys_with_multiple_rows": sum(
            1 for count in right_counts.values() if count > 1
        ),
    }


def _parse_source_datetime(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def seller_activation_profile(
    closed_deals_path: Path,
    order_items_path: Path,
    orders_path: Path,
) -> dict[str, object]:
    """Measure first observed Order timing for sellers from Closed Deals."""
    closed_handle, closed_reader, _encoding, _delimiter = open_dict_reader(
        closed_deals_path
    )
    seller_won_dates: dict[str, datetime] = {}
    closed_sellers: set[str] = set()
    missing_or_invalid_won_dates = 0
    try:
        for row in closed_reader:
            seller_id = (row.get("seller_id") or "").strip()
            if is_null(seller_id):
                continue
            closed_sellers.add(seller_id)
            won_date = _parse_source_datetime(row.get("won_date") or "")
            if won_date is None:
                missing_or_invalid_won_dates += 1
                continue
            current = seller_won_dates.get(seller_id)
            seller_won_dates[seller_id] = (
                won_date if current is None else min(current, won_date)
            )
    finally:
        closed_handle.close()

    order_handle, order_reader, _encoding, _delimiter = open_dict_reader(orders_path)
    order_purchase_dates: dict[str, datetime] = {}
    try:
        for row in order_reader:
            order_id = (row.get("order_id") or "").strip()
            purchase_date = _parse_source_datetime(
                row.get("order_purchase_timestamp") or ""
            )
            if not is_null(order_id) and purchase_date is not None:
                order_purchase_dates[order_id] = purchase_date
    finally:
        order_handle.close()

    item_handle, item_reader, _encoding, _delimiter = open_dict_reader(order_items_path)
    seller_first_order: dict[str, datetime] = {}
    sellers_in_items: set[str] = set()
    item_orders_without_purchase_date = 0
    try:
        for row in item_reader:
            seller_id = (row.get("seller_id") or "").strip()
            order_id = (row.get("order_id") or "").strip()
            if is_null(seller_id):
                continue
            sellers_in_items.add(seller_id)
            purchase_date = order_purchase_dates.get(order_id)
            if purchase_date is None:
                item_orders_without_purchase_date += 1
                continue
            current = seller_first_order.get(seller_id)
            seller_first_order[seller_id] = (
                purchase_date if current is None else min(current, purchase_date)
            )
    finally:
        item_handle.close()

    activated_sellers = closed_sellers & sellers_in_items
    non_activated_sellers = closed_sellers - sellers_in_items
    days_to_first_order = [
        (seller_first_order[seller_id] - seller_won_dates[seller_id]).total_seconds()
        / 86400
        for seller_id in sorted(activated_sellers)
        if seller_id in seller_first_order and seller_id in seller_won_dates
    ]
    return {
        "definition": "Presence in Order Items; no status filter and no activation contract.",
        "closed_deal_sellers": len(closed_sellers),
        "sellers_with_order_items": len(activated_sellers),
        "sellers_without_order_items": len(non_activated_sellers),
        "observed_activation_percentage": round(
            len(activated_sellers) / len(closed_sellers) * 100, 6
        )
        if closed_sellers
        else None,
        "sellers_with_timing": len(days_to_first_order),
        "negative_days_to_first_order": sum(
            1 for value in days_to_first_order if value < 0
        ),
        "days_to_first_order_min": round(min(days_to_first_order), 6)
        if days_to_first_order
        else None,
        "days_to_first_order_median": round(median(days_to_first_order), 6)
        if days_to_first_order
        else None,
        "days_to_first_order_max": round(max(days_to_first_order), 6)
        if days_to_first_order
        else None,
        "missing_or_invalid_won_dates": missing_or_invalid_won_dates,
        "order_items_without_order_purchase_date": item_orders_without_purchase_date,
    }


def _linear_percentile(sorted_values: list[float], probability: float) -> float | None:
    """Return a linearly interpolated percentile over pre-sorted values."""
    if not sorted_values:
        return None
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (
        sorted_values[upper] - sorted_values[lower]
    ) * fraction


def mvp_seller_activation_candidate_profile(
    closed_deals_path: Path,
    order_items_path: Path,
    orders_path: Path,
    eligible_statuses: frozenset[str] = frozenset({"delivered"}),
    windows: tuple[int, ...] = (30, 60, 90, 180),
) -> dict[str, object]:
    """Evaluate the proposed post-win, eligible-Order activation semantics."""
    closed_handle, closed_reader, _encoding, _delimiter = open_dict_reader(
        closed_deals_path
    )
    seller_won_dates: dict[str, datetime] = {}
    try:
        for row in closed_reader:
            seller_id = (row.get("seller_id") or "").strip()
            won_date = _parse_source_datetime(row.get("won_date") or "")
            if is_null(seller_id) or won_date is None:
                continue
            current = seller_won_dates.get(seller_id)
            seller_won_dates[seller_id] = (
                won_date if current is None else min(current, won_date)
            )
    finally:
        closed_handle.close()

    order_handle, order_reader, _encoding, _delimiter = open_dict_reader(orders_path)
    eligible_order_dates: dict[str, datetime] = {}
    all_purchase_dates: list[datetime] = []
    try:
        for row in order_reader:
            order_id = (row.get("order_id") or "").strip()
            purchase_date = _parse_source_datetime(
                row.get("order_purchase_timestamp") or ""
            )
            if is_null(order_id) or purchase_date is None:
                continue
            all_purchase_dates.append(purchase_date)
            status = (row.get("order_status") or "").strip().casefold()
            if status in eligible_statuses:
                eligible_order_dates[order_id] = purchase_date
    finally:
        order_handle.close()

    seller_first_eligible_order: dict[str, datetime] = {}
    rejected_item_rows_at_or_before_won = 0
    item_handle, item_reader, _encoding, _delimiter = open_dict_reader(order_items_path)
    try:
        for row in item_reader:
            seller_id = (row.get("seller_id") or "").strip()
            order_id = (row.get("order_id") or "").strip()
            won_date = seller_won_dates.get(seller_id)
            purchase_date = eligible_order_dates.get(order_id)
            if won_date is None or purchase_date is None:
                continue
            if purchase_date <= won_date:
                rejected_item_rows_at_or_before_won += 1
                continue
            current = seller_first_eligible_order.get(seller_id)
            seller_first_eligible_order[seller_id] = (
                purchase_date if current is None else min(current, purchase_date)
            )
    finally:
        item_handle.close()

    days_to_first = sorted(
        (seller_first_eligible_order[seller_id] - seller_won_dates[seller_id])
        .total_seconds()
        / 86400
        for seller_id in seller_first_eligible_order
    )
    source_cutoff = max(all_purchase_dates) if all_purchase_dates else None

    window_analysis: dict[str, dict[str, object]] = {}
    for window in windows:
        activated_within = sum(value <= window for value in days_to_first)
        mature_sellers = {
            seller_id
            for seller_id, won_date in seller_won_dates.items()
            if source_cutoff is not None
            and won_date + timedelta(days=window) <= source_cutoff
        }
        mature_activated = sum(
            seller_id in seller_first_eligible_order
            and (
                seller_first_eligible_order[seller_id] - seller_won_dates[seller_id]
            ).total_seconds()
            / 86400
            <= window
            for seller_id in mature_sellers
        )
        window_analysis[str(window)] = {
            "activated_within_window": activated_within,
            "activated_within_window_percentage_of_observed_activations": round(
                activated_within / len(days_to_first) * 100, 6
            )
            if days_to_first
            else None,
            "mature_cohort_sellers": len(mature_sellers),
            "mature_cohort_activated_sellers": mature_activated,
            "mature_cohort_activation_percentage": round(
                mature_activated / len(mature_sellers) * 100, 6
            )
            if mature_sellers
            else None,
        }

    percentiles = {
        name: round(value, 6) if value is not None else None
        for name, value in {
            "min": min(days_to_first) if days_to_first else None,
            "p25": _linear_percentile(days_to_first, 0.25),
            "median": _linear_percentile(days_to_first, 0.50),
            "p75": _linear_percentile(days_to_first, 0.75),
            "p90": _linear_percentile(days_to_first, 0.90),
            "p95": _linear_percentile(days_to_first, 0.95),
            "max": max(days_to_first) if days_to_first else None,
        }.items()
    }
    return {
        "candidate_rule": (
            "AcquiredSeller with at least one Order Item on an eligible Order whose "
            "purchase timestamp is strictly later than won_date."
        ),
        "eligible_order_statuses": sorted(eligible_statuses),
        "source_observation_cutoff": source_cutoff.isoformat(sep=" ")
        if source_cutoff
        else None,
        "acquired_sellers": len(seller_won_dates),
        "sellers_with_post_win_eligible_order": len(seller_first_eligible_order),
        "sellers_without_post_win_eligible_order": len(seller_won_dates)
        - len(seller_first_eligible_order),
        "rejected_item_rows_at_or_before_won": rejected_item_rows_at_or_before_won,
        "days_to_first_eligible_order": percentiles,
        "window_analysis_days": window_analysis,
        "percentile_method": "linear interpolation over sorted observed activations",
    }


def gmv_candidate_profile(tables: dict[str, object]) -> dict[str, object] | None:
    try:
        order_item_numeric = tables["order_items"]["numeric_findings"]
        payment_numeric = tables["payments"]["numeric_findings"]
        price = Decimal(order_item_numeric["price"]["sum"])
        freight = Decimal(order_item_numeric["freight_value"]["sum"])
        payment = Decimal(payment_numeric["payment_value"]["sum"])
    except (KeyError, InvalidOperation, TypeError):
        return None
    price_plus_freight = price + freight
    return {
        "scope": "All raw rows; no Order status, cancellation, or refund filter.",
        "sum_price": _decimal_text(price),
        "sum_freight_value": _decimal_text(freight),
        "sum_price_plus_freight": _decimal_text(price_plus_freight),
        "sum_payment_value": _decimal_text(payment),
        "payment_minus_price": _decimal_text(payment - price),
        "payment_minus_price_plus_freight": _decimal_text(
            payment - price_plus_freight
        ),
    }


def build_profile() -> tuple[dict[str, object], list[str]]:
    missing: list[str] = []
    locations: dict[str, Path] = {}
    for spec in TABLES:
        path = find_unique_file(spec.filename)
        if path is None:
            missing.append(spec.filename)
        else:
            locations[spec.filename] = path

    all_csv_files = (
        sorted(
            path
            for path in RAW_DIR.rglob("*.csv")
            if "_profiling" not in path.parts
        )
        if RAW_DIR.exists()
        else []
    )
    inventory = [inventory_csv(path) for path in all_csv_files]
    tables = {
        spec.name: profile_csv(locations[spec.filename], spec)
        for spec in TABLES
        if spec.filename in locations
    }

    relationships: list[dict[str, object]] = []
    for name, left_file, left_column, right_file, right_column in RELATIONSHIPS:
        if left_file not in locations or right_file not in locations:
            continue
        relationships.append(
            relationship_profile(
                name,
                locations[left_file],
                left_column,
                locations[right_file],
                right_column,
            )
        )

    activation = None
    activation_files = (
        "olist_closed_deals_dataset.csv",
        "olist_order_items_dataset.csv",
        "olist_orders_dataset.csv",
    )
    if all(filename in locations for filename in activation_files):
        activation = seller_activation_profile(
            locations[activation_files[0]],
            locations[activation_files[1]],
            locations[activation_files[2]],
        )
        mvp_activation_candidate = mvp_seller_activation_candidate_profile(
            locations[activation_files[0]],
            locations[activation_files[1]],
            locations[activation_files[2]],
        )
    else:
        mvp_activation_candidate = None

    profile: dict[str, object] = {
        "schema_version": 1,
        "pii_policy": "No raw rows or unrestricted values are emitted.",
        "inventory": inventory,
        "tables": tables,
        "relationships": relationships,
        "seller_activation": activation,
        "mvp_seller_activation_candidate": mvp_activation_candidate,
        "gmv_candidates": gmv_candidate_profile(tables),
        "missing_mvp_files": sorted(missing),
    }
    return profile, missing


def write_profile(profile: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(profile, indent=2, sort_keys=True) + "\n"
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory, profile, and validate relationships in local Olist CSVs."
    )
    return parser.parse_args()


def main() -> int:
    parse_args()
    try:
        profile, missing = build_profile()
        write_profile(profile, DEFAULT_OUTPUT)
    except (OSError, csv.Error, ProfilingError) as error:
        print(f"profiling_status=failed: {error}")
        return 1

    print(f"inventory_files={len(profile['inventory'])}")
    print(f"profiled_mvp_tables={len(profile['tables'])}")
    print(f"profiled_relationships={len(profile['relationships'])}")
    print(f"missing_mvp_files={len(missing)}")
    print(f"output={DEFAULT_OUTPUT}")
    if missing:
        for filename in missing:
            print(f"missing={filename}")
        print("profiling_status=partial")
        return 2
    print("profiling_status=complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
