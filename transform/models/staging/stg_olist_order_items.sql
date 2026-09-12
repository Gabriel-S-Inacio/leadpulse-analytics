select
    order_id,
    cast(order_item_id as integer) as order_item_id,
    product_id,
    seller_id,
    cast(shipping_limit_date as timestamp) as shipping_limit_date,
    cast(price as numeric(12, 2)) as price,
    cast(freight_value as numeric(12, 2)) as freight_value,
    _loaded_at,
    _source_file,
    _source_sha256
from {{ source('olist_raw', 'olist_order_items') }}
