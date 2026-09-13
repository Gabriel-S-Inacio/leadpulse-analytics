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

lifecycle_by_cohort as (
    select
        date_trunc('month', won_dates.calendar_date)::date as cohort_month,
        lifecycle.origin_key,
        lifecycle.observation_cutoff_timestamp,
        lifecycle.lifecycle_rule_version,
        lifecycle.source_snapshot_id,
        sum(lifecycle.mature_seller_count)::bigint as acquired_sellers_mature,
        sum(lifecycle.activated_seller_count)::bigint as activated_sellers_90d,
        avg(lifecycle.time_to_first_order_days) filter (
            where lifecycle.is_activated_90d is true
        ) as avg_time_to_first_order_days,
        percentile_cont(0.5) within group (
            order by lifecycle.time_to_first_order_days
        ) filter (
            where lifecycle.is_activated_90d is true
        ) as median_time_to_first_order_days
    from selected_lifecycle as lifecycle
    inner join {{ ref('dim_date') }} as won_dates
        on lifecycle.won_date_key = won_dates.date_key
    group by 1, 2, 3, 4, 5
),

performance_90d as (
    select
        date_trunc('month', won_dates.calendar_date)::date as cohort_month,
        lifecycle.origin_key,
        lifecycle.observation_cutoff_timestamp,
        lifecycle.lifecycle_rule_version,
        lifecycle.source_snapshot_id,
        sum(order_items.eligible_gmv_amount)::numeric(18, 2) as gmv_90d,
        count(distinct (order_items.seller_key, order_items.order_id))::bigint
            as orders_90d
    from selected_lifecycle as lifecycle
    inner join {{ ref('dim_date') }} as won_dates
        on lifecycle.won_date_key = won_dates.date_key
    inner join {{ ref('fct_order_item') }} as order_items
        on lifecycle.seller_key = order_items.seller_key
        and order_items.is_eligible_order
        and order_items.is_post_acquisition
        and order_items.order_purchase_timestamp > lifecycle.won_timestamp
        and order_items.order_purchase_timestamp
            <= lifecycle.won_timestamp + interval '90 days'
    where lifecycle.temporal_quality_status = 'VALID'
      and lifecycle.is_mature_90d
      and lifecycle.is_activated_90d is true
    group by 1, 2, 3, 4, 5
)

select
    to_char(lifecycle.cohort_month, 'YYYYMM')::integer as cohort_month_key,
    lifecycle.cohort_month,
    lifecycle.origin_key,
    origins.source_origin,
    origins.normalized_channel,
    lifecycle.observation_cutoff_timestamp,
    lifecycle.lifecycle_rule_version,
    lifecycle.source_snapshot_id,
    lifecycle.acquired_sellers_mature,
    lifecycle.activated_sellers_90d,
    lifecycle.activated_sellers_90d::numeric
        / nullif(lifecycle.acquired_sellers_mature, 0)
        as seller_activation_rate,
    lifecycle.avg_time_to_first_order_days,
    lifecycle.median_time_to_first_order_days,
    coalesce(performance.gmv_90d, 0)::numeric(18, 2) as gmv_90d,
    coalesce(performance.orders_90d, 0)::bigint as orders_90d,
    coalesce(performance.gmv_90d, 0)
        / nullif(lifecycle.activated_sellers_90d, 0)
        as gmv_per_activated_seller,
    coalesce(performance.orders_90d, 0)::numeric
        / nullif(lifecycle.activated_sellers_90d, 0)
        as orders_per_activated_seller
from lifecycle_by_cohort as lifecycle
left join performance_90d as performance
    on lifecycle.cohort_month = performance.cohort_month
    and lifecycle.origin_key = performance.origin_key
    and lifecycle.observation_cutoff_timestamp
        = performance.observation_cutoff_timestamp
    and lifecycle.lifecycle_rule_version = performance.lifecycle_rule_version
    and lifecycle.source_snapshot_id = performance.source_snapshot_id
inner join {{ ref('dim_origin') }} as origins
    on lifecycle.origin_key = origins.origin_key
