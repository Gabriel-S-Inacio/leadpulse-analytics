with funnel as (
    select distinct seller_id from {{ ref('stg_olist_closed_deals') }}
),

ecommerce as (
    select distinct seller_id from {{ ref('stg_olist_sellers') }}
),

expected as (
    select
        sellers.seller_id,
        case
            when funnel.seller_id is not null and ecommerce.seller_id is not null then 'both'
            when funnel.seller_id is not null then 'funnel_only'
            else 'ecommerce_only'
        end as seller_source_presence
    from (
        select seller_id from funnel
        union
        select seller_id from ecommerce
    ) as sellers
    left join funnel using (seller_id)
    left join ecommerce using (seller_id)
)

select coalesce(expected.seller_id, actual.seller_id) as seller_id
from expected
full outer join {{ ref('dim_seller') }} as actual using (seller_id)
where expected.seller_id is null
   or actual.seller_id is null
   or expected.seller_source_presence <> actual.seller_source_presence
