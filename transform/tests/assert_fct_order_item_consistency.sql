select
    facts.order_id,
    facts.order_item_id
from {{ ref('fct_order_item') }} as facts
inner join {{ ref('dim_origin') }} as origins using (origin_key)
inner join {{ ref('dim_date') }} as won_dates
    on facts.seller_won_date_key = won_dates.date_key
where item_price < 0
   or freight_value < 0
   or eligible_gmv_amount < 0
   or is_eligible_order <> (order_status = 'delivered')
   or (
       is_acquired_seller
       and (
           seller_won_timestamp is null
           or is_post_acquisition is null
           or is_within_90d_of_acquisition is null
           or is_post_acquisition
               <> (order_purchase_timestamp > seller_won_timestamp)
           or is_within_90d_of_acquisition
               <> (
                   order_purchase_timestamp > seller_won_timestamp
                   and order_purchase_timestamp <= seller_won_timestamp + interval '90 days'
               )
           or origins.classification = 'NOT_APPLICABLE'
           or won_dates.date_classification <> 'CALENDAR'
       )
   )
   or (
       not is_acquired_seller
       and (
           seller_won_timestamp is not null
           or is_post_acquisition is not null
           or is_within_90d_of_acquisition is not null
           or origins.classification <> 'NOT_APPLICABLE'
           or won_dates.date_classification <> 'NOT_APPLICABLE'
       )
   )
   or is_within_90d_of_acquisition and not is_post_acquisition
   or eligible_gmv_amount <> case
       when is_acquired_seller and is_eligible_order and is_post_acquisition
           then item_price
       else 0::numeric(12, 2)
   end
