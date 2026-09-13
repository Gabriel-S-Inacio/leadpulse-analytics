with ranked_versions as (
    select
        observation_cutoff_timestamp,
        lifecycle_rule_version,
        source_snapshot_id,
        row_number() over (
            order by
                observation_cutoff_timestamp desc,
                lifecycle_rule_version desc,
                source_snapshot_id desc
        ) as version_rank
    from (
        select distinct
            observation_cutoff_timestamp,
            lifecycle_rule_version,
            source_snapshot_id
        from {{ ref('fct_seller_lifecycle') }}
        where lifecycle_rule_version = 'seller_activation_v1'
    ) as versions
),

selected_version as (
    select
        observation_cutoff_timestamp,
        lifecycle_rule_version,
        source_snapshot_id
    from ranked_versions
    where version_rank = 1
),

selected_lifecycle as (
    select lifecycle.*
    from {{ ref('fct_seller_lifecycle') }} as lifecycle
    inner join selected_version as selected
        on lifecycle.observation_cutoff_timestamp
            = selected.observation_cutoff_timestamp
        and lifecycle.lifecycle_rule_version = selected.lifecycle_rule_version
        and lifecycle.source_snapshot_id = selected.source_snapshot_id
),

spend_by_period as (
    select
        date_trunc('month', dates.calendar_date)::date as period,
        spend.origin_key,
        spend.scenario_id,
        spend.methodology_version,
        spend.generation_seed,
        spend.currency,
        spend.data_classification,
        min(dates.calendar_date) as coverage_start_date,
        max(dates.calendar_date) as coverage_end_date,
        sum(spend.spend_amount)::numeric(18, 2) as synthetic_marketing_spend
    from {{ ref('fct_marketing_spend') }} as spend
    inner join {{ ref('dim_date') }} as dates
        on spend.spend_date_key = dates.date_key
    group by 1, 2, 3, 4, 5, 6, 7
),

mql_dated as (
    select
        mql.origin_key,
        dates.calendar_date as contact_date,
        mql.mql_count
    from {{ ref('fct_mql') }} as mql
    inner join {{ ref('dim_date') }} as dates
        on mql.contact_date_key = dates.date_key
),

mql_by_period as (
    select
        spend.period,
        spend.origin_key,
        spend.scenario_id,
        spend.methodology_version,
        spend.generation_seed,
        spend.currency,
        sum(mql.mql_count)::bigint as mqls
    from spend_by_period as spend
    left join mql_dated as mql
        on spend.origin_key = mql.origin_key
        and mql.contact_date between
            spend.coverage_start_date and spend.coverage_end_date
    group by 1, 2, 3, 4, 5, 6
),

acquisitions_by_period as (
    select
        spend.period,
        spend.origin_key,
        spend.scenario_id,
        spend.methodology_version,
        spend.generation_seed,
        spend.currency,
        sum(closed_deals.acquired_seller_count)::bigint as acquired_sellers
    from spend_by_period as spend
    left join {{ ref('fct_closed_deal') }} as closed_deals
        on spend.origin_key = closed_deals.origin_key
        and closed_deals.won_timestamp::date between
            spend.coverage_start_date and spend.coverage_end_date
    group by 1, 2, 3, 4, 5, 6
),

gmv_by_period as (
    select
        spend.period,
        spend.origin_key,
        spend.scenario_id,
        spend.methodology_version,
        spend.generation_seed,
        spend.currency,
        sum(order_items.eligible_gmv_amount)::numeric(18, 2) as eligible_gmv_90d
    from spend_by_period as spend
    inner join selected_lifecycle as lifecycle
        on spend.origin_key = lifecycle.origin_key
        and lifecycle.won_timestamp::date between
            spend.coverage_start_date and spend.coverage_end_date
        and lifecycle.temporal_quality_status = 'VALID'
        and lifecycle.is_mature_90d
        and lifecycle.is_activated_90d is true
    inner join {{ ref('fct_order_item') }} as order_items
        on lifecycle.seller_key = order_items.seller_key
        and order_items.is_eligible_order
        and order_items.is_post_acquisition
        and order_items.order_purchase_timestamp > lifecycle.won_timestamp
        and order_items.order_purchase_timestamp
            <= lifecycle.won_timestamp + interval '90 days'
    group by 1, 2, 3, 4, 5, 6
)

select
    to_char(spend.period, 'YYYYMM')::integer as period_key,
    spend.period,
    spend.coverage_start_date,
    spend.coverage_end_date,
    spend.origin_key,
    origins.source_origin,
    origins.normalized_channel,
    spend.scenario_id,
    spend.methodology_version,
    spend.generation_seed,
    spend.currency,
    spend.data_classification,
    selected.observation_cutoff_timestamp,
    selected.lifecycle_rule_version,
    selected.source_snapshot_id as lifecycle_source_snapshot_id,
    spend.synthetic_marketing_spend,
    coalesce(mql.mqls, 0)::bigint as mqls,
    coalesce(acquisitions.acquired_sellers, 0)::bigint as acquired_sellers,
    coalesce(gmv.eligible_gmv_90d, 0)::numeric(18, 2) as eligible_gmv_90d,
    spend.synthetic_marketing_spend / nullif(mql.mqls, 0) as cpl,
    spend.synthetic_marketing_spend
        / nullif(acquisitions.acquired_sellers, 0)
        as seller_acquisition_cost,
    coalesce(gmv.eligible_gmv_90d, 0)
        / nullif(spend.synthetic_marketing_spend, 0) as gmv_roas
from spend_by_period as spend
cross join selected_version as selected
left join mql_by_period as mql
    on spend.period = mql.period
    and spend.origin_key = mql.origin_key
    and spend.scenario_id = mql.scenario_id
    and spend.methodology_version = mql.methodology_version
    and spend.generation_seed = mql.generation_seed
    and spend.currency = mql.currency
left join acquisitions_by_period as acquisitions
    on spend.period = acquisitions.period
    and spend.origin_key = acquisitions.origin_key
    and spend.scenario_id = acquisitions.scenario_id
    and spend.methodology_version = acquisitions.methodology_version
    and spend.generation_seed = acquisitions.generation_seed
    and spend.currency = acquisitions.currency
left join gmv_by_period as gmv
    on spend.period = gmv.period
    and spend.origin_key = gmv.origin_key
    and spend.scenario_id = gmv.scenario_id
    and spend.methodology_version = gmv.methodology_version
    and spend.generation_seed = gmv.generation_seed
    and spend.currency = gmv.currency
inner join {{ ref('dim_origin') }} as origins
    on spend.origin_key = origins.origin_key
