with funnel_sellers as (
    select distinct seller_id
    from {{ ref('stg_olist_closed_deals') }}
),

ecommerce_sellers as (
    select
        seller_id,
        seller_zip_code_prefix,
        seller_city,
        seller_state
    from {{ ref('stg_olist_sellers') }}
),

seller_union as (
    select seller_id from funnel_sellers
    union
    select seller_id from ecommerce_sellers
)

select
    md5('seller|' || sellers.seller_id) as seller_key,
    sellers.seller_id,
    ecommerce.seller_zip_code_prefix,
    ecommerce.seller_city,
    ecommerce.seller_state,
    case
        when funnel.seller_id is not null and ecommerce.seller_id is not null then 'both'
        when funnel.seller_id is not null then 'funnel_only'
        else 'ecommerce_only'
    end as seller_source_presence
from seller_union as sellers
left join funnel_sellers as funnel using (seller_id)
left join ecommerce_sellers as ecommerce using (seller_id)
