select
    closed_deals.mql_id,
    closed_deals.seller_id,
    sellers.seller_key,
    mql.origin_key,
    mql.contact_date_key,
    won_dates.date_key as won_date_key,
    closed_deals.won_date as won_timestamp,
    case
        when closed_deals.won_date::date >= to_date(mql.contact_date_key::text, 'YYYYMMDD')
            then 'VALID'
        else 'INVALID_SEQUENCE'
    end as temporal_quality_status,
    1::integer as closed_deal_count,
    1::integer as acquired_seller_count,
    md5(closed_deals._source_sha256 || '|' || mql.source_snapshot_id)
        as source_snapshot_id,
    closed_deals._source_file as source_file_name
from {{ ref('stg_olist_closed_deals') }} as closed_deals
inner join {{ ref('fct_mql') }} as mql using (mql_id)
inner join {{ ref('dim_seller') }} as sellers using (seller_id)
inner join {{ ref('dim_date') }} as won_dates
    on closed_deals.won_date::date = won_dates.calendar_date
