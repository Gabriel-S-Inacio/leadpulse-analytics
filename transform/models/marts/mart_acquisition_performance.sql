with mql_by_cohort as (
    select
        date_trunc('month', dates.calendar_date)::date as cohort_month,
        mql.origin_key,
        sum(mql.mql_count)::bigint as mqls
    from {{ ref('fct_mql') }} as mql
    inner join {{ ref('dim_date') }} as dates
        on mql.contact_date_key = dates.date_key
    group by 1, 2
),

closed_deals_by_cohort as (
    select
        date_trunc('month', dates.calendar_date)::date as cohort_month,
        closed_deals.origin_key,
        sum(closed_deals.closed_deal_count)::bigint as closed_deals,
        sum(closed_deals.acquired_seller_count)::bigint as acquired_sellers
    from {{ ref('fct_closed_deal') }} as closed_deals
    inner join {{ ref('dim_date') }} as dates
        on closed_deals.contact_date_key = dates.date_key
    group by 1, 2
)

select
    to_char(mql.cohort_month, 'YYYYMM')::integer as cohort_month_key,
    mql.cohort_month,
    mql.origin_key,
    origins.source_origin,
    origins.normalized_channel,
    mql.mqls,
    coalesce(closed_deals.closed_deals, 0)::bigint as closed_deals,
    coalesce(closed_deals.acquired_sellers, 0)::bigint as acquired_sellers,
    coalesce(closed_deals.acquired_sellers, 0)::numeric
        / nullif(mql.mqls, 0) as mql_to_acquired_seller_conversion_rate
from mql_by_cohort as mql
left join closed_deals_by_cohort as closed_deals
    on mql.cohort_month = closed_deals.cohort_month
    and mql.origin_key = closed_deals.origin_key
inner join {{ ref('dim_origin') }} as origins
    on mql.origin_key = origins.origin_key
