with mart_version as (
    select distinct
        observation_cutoff_timestamp,
        lifecycle_rule_version,
        source_snapshot_id
    from {{ ref('mart_seller_activation') }}
),

selected_lifecycle as (
    select lifecycle.*
    from {{ ref('fct_seller_lifecycle') }} as lifecycle
    inner join mart_version as mart
        on lifecycle.observation_cutoff_timestamp = mart.observation_cutoff_timestamp
        and lifecycle.lifecycle_rule_version = mart.lifecycle_rule_version
        and lifecycle.source_snapshot_id = mart.source_snapshot_id
),

expected_performance as (
    select
        sum(order_items.eligible_gmv_amount)::numeric(18, 2) as gmv_90d,
        count(distinct (order_items.seller_key, order_items.order_id))::bigint
            as orders_90d
    from selected_lifecycle as lifecycle
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
)

select 'multiple_lifecycle_versions' as issue
where (select count(*) from mart_version) <> 1

union all

select 'invalid_row_metrics'
where exists (
    select 1
    from {{ ref('mart_seller_activation') }}
    where acquired_sellers_mature < 0
       or activated_sellers_90d < 0
       or activated_sellers_90d > acquired_sellers_mature
       or seller_activation_rate not between 0 and 1
       or seller_activation_rate
            <> activated_sellers_90d::numeric
                / nullif(acquired_sellers_mature, 0)
       or gmv_90d < 0
       or orders_90d < 0
       or gmv_per_activated_seller
            <> gmv_90d / nullif(activated_sellers_90d, 0)
       or orders_per_activated_seller
            <> orders_90d::numeric / nullif(activated_sellers_90d, 0)
)

union all

select 'lifecycle_fanout_or_loss'
where (select sum(acquired_sellers_mature) from {{ ref('mart_seller_activation') }})
    <> (select sum(mature_seller_count) from selected_lifecycle)
   or (select sum(activated_sellers_90d) from {{ ref('mart_seller_activation') }})
    <> (select sum(activated_seller_count) from selected_lifecycle)

union all

select 'gmv_fanout_or_loss'
where (select sum(gmv_90d) from {{ ref('mart_seller_activation') }})
    <> (select gmv_90d from expected_performance)

union all

select 'order_fanout_or_loss'
where (select sum(orders_90d) from {{ ref('mart_seller_activation') }})
    <> (select orders_90d from expected_performance)
