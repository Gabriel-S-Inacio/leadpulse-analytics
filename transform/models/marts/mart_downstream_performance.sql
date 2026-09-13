with eligible_seller_orders as (
    select
        date_trunc('month', order_items.order_purchase_timestamp)::date
            as purchase_month,
        order_items.origin_key,
        order_items.seller_key,
        order_items.order_id,
        sum(order_items.eligible_gmv_amount)::numeric(18, 2) as eligible_gmv
    from {{ ref('fct_order_item') }} as order_items
    where order_items.is_acquired_seller
      and order_items.is_eligible_order
      and order_items.is_post_acquisition
    group by 1, 2, 3, 4
)

select
    to_char(orders.purchase_month, 'YYYYMM')::integer as purchase_month_key,
    orders.purchase_month,
    orders.origin_key,
    origins.source_origin,
    origins.normalized_channel,
    orders.seller_key,
    orders.order_id,
    1::integer as orders,
    1::integer as seller_order_participations,
    orders.eligible_gmv
from eligible_seller_orders as orders
inner join {{ ref('dim_origin') }} as origins using (origin_key)
