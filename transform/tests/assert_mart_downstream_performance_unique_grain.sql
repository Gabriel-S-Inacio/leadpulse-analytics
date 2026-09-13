select
    purchase_month,
    origin_key,
    seller_key,
    order_id,
    count(*) as row_count
from {{ ref('mart_downstream_performance') }}
group by 1, 2, 3, 4
having count(*) <> 1
