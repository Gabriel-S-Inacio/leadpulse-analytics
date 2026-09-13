with seller_order_events as (
    select
        order_items.seller_key,
        order_items.order_id,
        min(order_items.order_purchase_timestamp) as order_purchase_timestamp
    from {{ ref('fct_order_item') }} as order_items
    inner join {{ ref('fct_closed_deal') }} as acquisitions using (seller_key)
    where acquisitions.temporal_quality_status = 'VALID'
      and order_items.is_acquired_seller
      and order_items.is_eligible_order
      and order_items.is_post_acquisition
    group by order_items.seller_key, order_items.order_id
),

ranked_events as (
    select
        seller_key,
        order_id,
        order_purchase_timestamp,
        row_number() over (
            partition by seller_key
            order by order_purchase_timestamp, order_id
        ) as event_rank
    from seller_order_events
),

expected as (
    select
        acquisitions.seller_key,
        events.order_id as first_eligible_order_id,
        events.order_purchase_timestamp as activation_timestamp
    from {{ ref('fct_closed_deal') }} as acquisitions
    left join ranked_events as events
        on acquisitions.seller_key = events.seller_key
       and events.event_rank = 1
)

select coalesce(expected.seller_key, actual.seller_key) as seller_key
from expected
full outer join {{ ref('fct_seller_lifecycle') }} as actual using (seller_key)
where expected.seller_key is null
   or actual.seller_key is null
   or expected.first_eligible_order_id is distinct from actual.first_eligible_order_id
   or expected.activation_timestamp is distinct from actual.activation_timestamp
