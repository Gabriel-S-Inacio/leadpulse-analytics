select 'invalid_row_metrics' as issue
where exists (
    select 1
    from {{ ref('mart_marketing_efficiency') }}
    where synthetic_marketing_spend < 0
       or mqls < 0
       or acquired_sellers < 0
       or eligible_gmv_90d < 0
       or cpl <> synthetic_marketing_spend / nullif(mqls, 0)
       or seller_acquisition_cost
            <> synthetic_marketing_spend / nullif(acquired_sellers, 0)
       or gmv_roas <> eligible_gmv_90d
            / nullif(synthetic_marketing_spend, 0)
)

union all

select 'spend_fanout_or_loss'
where exists (
    select 1
    from (
        select
            scenario_id,
            methodology_version,
            generation_seed,
            currency,
            sum(synthetic_marketing_spend) as mart_spend
        from {{ ref('mart_marketing_efficiency') }}
        group by 1, 2, 3, 4
    ) as mart
    full outer join (
        select
            scenario_id,
            methodology_version,
            generation_seed,
            currency,
            sum(spend_amount) as fact_spend
        from {{ ref('fct_marketing_spend') }}
        group by 1, 2, 3, 4
    ) as fact using (
        scenario_id,
        methodology_version,
        generation_seed,
        currency
    )
    where mart.mart_spend is distinct from fact.fact_spend
)

union all

select 'component_recomposition_failure'
where exists (
    select 1
    from {{ ref('mart_marketing_efficiency') }} as mart
    where mart.mqls <> (
        select coalesce(sum(mql.mql_count), 0)
        from {{ ref('fct_mql') }} as mql
        inner join {{ ref('dim_date') }} as dates
            on mql.contact_date_key = dates.date_key
        where mql.origin_key = mart.origin_key
          and dates.calendar_date between
              mart.coverage_start_date and mart.coverage_end_date
    )
       or mart.acquired_sellers <> (
        select coalesce(sum(closed_deals.acquired_seller_count), 0)
        from {{ ref('fct_closed_deal') }} as closed_deals
        where closed_deals.origin_key = mart.origin_key
          and closed_deals.won_timestamp::date between
              mart.coverage_start_date and mart.coverage_end_date
    )
       or mart.eligible_gmv_90d <> (
        select coalesce(sum(order_items.eligible_gmv_amount), 0)
        from {{ ref('fct_seller_lifecycle') }} as lifecycle
        inner join {{ ref('fct_order_item') }} as order_items
            on lifecycle.seller_key = order_items.seller_key
            and order_items.is_eligible_order
            and order_items.is_post_acquisition
            and order_items.order_purchase_timestamp > lifecycle.won_timestamp
            and order_items.order_purchase_timestamp
                <= lifecycle.won_timestamp + interval '90 days'
        where lifecycle.observation_cutoff_timestamp
                = mart.observation_cutoff_timestamp
          and lifecycle.lifecycle_rule_version = mart.lifecycle_rule_version
          and lifecycle.source_snapshot_id = mart.lifecycle_source_snapshot_id
          and lifecycle.origin_key = mart.origin_key
          and lifecycle.won_timestamp::date between
              mart.coverage_start_date and mart.coverage_end_date
          and lifecycle.temporal_quality_status = 'VALID'
          and lifecycle.is_mature_90d
          and lifecycle.is_activated_90d is true
    )
)

union all

select 'scenario_contract_mixed'
where exists (
    select 1
    from {{ ref('mart_marketing_efficiency') }}
    group by scenario_id
    having count(distinct (methodology_version, generation_seed, currency)) <> 1
       or count(distinct data_classification) <> 1
       or min(data_classification) <> 'SYNTHETIC'
)

union all

select 'multiple_lifecycle_versions'
where (
    select count(distinct (
        observation_cutoff_timestamp,
        lifecycle_rule_version,
        lifecycle_source_snapshot_id
    ))
    from {{ ref('mart_marketing_efficiency') }}
) <> 1
