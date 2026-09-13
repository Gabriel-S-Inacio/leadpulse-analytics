select closed_deals.mql_id
from {{ ref('fct_closed_deal') }} as closed_deals
inner join {{ ref('fct_mql') }} as mql using (mql_id)
inner join {{ ref('dim_seller') }} as sellers using (seller_key)
inner join {{ ref('dim_date') }} as won_dates
    on closed_deals.won_date_key = won_dates.date_key
where closed_deals.origin_key <> mql.origin_key
   or closed_deals.contact_date_key <> mql.contact_date_key
   or closed_deals.seller_id <> sellers.seller_id
   or closed_deals.won_timestamp::date <> won_dates.calendar_date
