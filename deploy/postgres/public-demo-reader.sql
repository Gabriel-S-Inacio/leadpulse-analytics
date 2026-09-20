-- Run as a PostgreSQL administrator after dbt has built the analytics marts.
-- Set the role password out of band through the deployment secret store.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'demo_reader') THEN
        CREATE ROLE demo_reader LOGIN NOINHERIT;
    END IF;
END
$$;

ALTER ROLE demo_reader SET default_transaction_read_only = on;
ALTER ROLE demo_reader SET statement_timeout = '30s';

DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO demo_reader', current_database());
END
$$;

REVOKE ALL ON SCHEMA raw FROM demo_reader;
REVOKE ALL ON SCHEMA staging FROM demo_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA raw FROM demo_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA staging FROM demo_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA analytics FROM demo_reader;

GRANT USAGE ON SCHEMA analytics TO demo_reader;

GRANT SELECT (
    cohort_month_key,
    cohort_month,
    origin_key,
    source_origin,
    normalized_channel,
    mqls,
    closed_deals,
    acquired_sellers,
    mql_to_acquired_seller_conversion_rate
) ON analytics.mart_acquisition_performance TO demo_reader;

GRANT SELECT (
    cohort_month_key,
    cohort_month,
    origin_key,
    source_origin,
    normalized_channel,
    observation_cutoff_timestamp,
    lifecycle_rule_version,
    source_snapshot_id,
    acquired_sellers_mature,
    activated_sellers_90d,
    seller_activation_rate,
    avg_time_to_first_order_days,
    median_time_to_first_order_days,
    gmv_90d,
    orders_90d,
    gmv_per_activated_seller,
    orders_per_activated_seller
) ON analytics.mart_seller_activation TO demo_reader;

GRANT SELECT (
    period_key,
    period,
    coverage_start_date,
    coverage_end_date,
    origin_key,
    source_origin,
    normalized_channel,
    scenario_id,
    methodology_version,
    generation_seed,
    currency,
    data_classification,
    observation_cutoff_timestamp,
    lifecycle_rule_version,
    lifecycle_source_snapshot_id,
    synthetic_marketing_spend,
    mqls,
    acquired_sellers,
    eligible_gmv_90d,
    cpl,
    seller_acquisition_cost,
    gmv_roas
) ON analytics.mart_marketing_efficiency TO demo_reader;

-- order_id is required server-side only to preserve the governed globally distinct
-- order count. seller_key is deliberately excluded. Neither value is rendered by
-- the dashboard, and PostgreSQL must remain on a private network.
GRANT SELECT (
    purchase_month_key,
    purchase_month,
    origin_key,
    source_origin,
    normalized_channel,
    order_id,
    orders,
    seller_order_participations,
    eligible_gmv
) ON analytics.mart_downstream_performance TO demo_reader;
