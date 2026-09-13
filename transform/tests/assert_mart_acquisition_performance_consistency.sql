select 'invalid_row_metrics' as issue
where exists (
    select 1
    from {{ ref('mart_acquisition_performance') }}
    where mqls < 0
       or closed_deals < 0
       or acquired_sellers < 0
       or closed_deals <> acquired_sellers
       or acquired_sellers > mqls
       or mql_to_acquired_seller_conversion_rate not between 0 and 1
       or mql_to_acquired_seller_conversion_rate
            <> acquired_sellers::numeric / nullif(mqls, 0)
)

union all

select 'mql_fanout_or_loss'
where (select sum(mqls) from {{ ref('mart_acquisition_performance') }})
    <> (select sum(mql_count) from {{ ref('fct_mql') }})

union all

select 'closed_deal_fanout_or_loss'
where (select sum(closed_deals) from {{ ref('mart_acquisition_performance') }})
    <> (select sum(closed_deal_count) from {{ ref('fct_closed_deal') }})

union all

select 'acquired_seller_fanout_or_loss'
where (select sum(acquired_sellers) from {{ ref('mart_acquisition_performance') }})
    <> (select sum(acquired_seller_count) from {{ ref('fct_closed_deal') }})
