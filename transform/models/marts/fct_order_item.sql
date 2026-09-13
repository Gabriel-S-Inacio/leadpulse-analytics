with not_applicable_members as (
    select
        origins.origin_key as origin_key,
        dates.date_key as date_key
    from {{ ref('dim_origin') }} as origins
    cross join {{ ref('dim_date') }} as dates
    where origins.classification = 'NOT_APPLICABLE'
      and dates.date_classification = 'NOT_APPLICABLE'
),

joined as (
    select
        items.order_id,
        items.order_item_id,
        items.seller_id,
        sellers.seller_key,
        coalesce(acquisitions.origin_key, technical.origin_key) as origin_key,
        purchase_dates.date_key as purchase_date_key,
        coalesce(acquisitions.won_date_key, technical.date_key) as seller_won_date_key,
        orders.order_purchase_timestamp,
        acquisitions.won_timestamp as seller_won_timestamp,
        orders.order_status,
        items.price as item_price,
        items.freight_value,
        acquisitions.seller_key is not null as is_acquired_seller,
        orders.order_status = 'delivered' as is_eligible_order,
        case
            when acquisitions.seller_key is null then null
            else orders.order_purchase_timestamp > acquisitions.won_timestamp
        end as is_post_acquisition,
        case
            when acquisitions.seller_key is null then null
            else orders.order_purchase_timestamp > acquisitions.won_timestamp
                and orders.order_purchase_timestamp
                    <= acquisitions.won_timestamp + interval '90 days'
        end as is_within_90d_of_acquisition,
        items._source_file,
        items._source_sha256 as item_snapshot_id,
        orders._source_sha256 as order_snapshot_id
    from {{ ref('stg_olist_order_items') }} as items
    inner join {{ ref('stg_olist_orders') }} as orders using (order_id)
    inner join {{ ref('dim_seller') }} as sellers using (seller_id)
    inner join {{ ref('dim_date') }} as purchase_dates
        on orders.order_purchase_timestamp::date = purchase_dates.calendar_date
    left join {{ ref('fct_closed_deal') }} as acquisitions using (seller_id)
    cross join not_applicable_members as technical
)

select
    order_id,
    order_item_id,
    seller_id,
    seller_key,
    origin_key,
    purchase_date_key,
    seller_won_date_key,
    order_purchase_timestamp,
    seller_won_timestamp,
    order_status,
    item_price,
    freight_value,
    1::integer as order_item_count,
    is_acquired_seller,
    is_eligible_order,
    is_post_acquisition,
    is_within_90d_of_acquisition,
    case
        when is_acquired_seller and is_eligible_order and is_post_acquisition
            then item_price
        else 0::numeric(12, 2)
    end as eligible_gmv_amount,
    md5(item_snapshot_id || '|' || order_snapshot_id) as source_snapshot_id,
    _source_file as source_file_name
from joined
