select
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    _loaded_at,
    _source_file,
    _source_sha256
from {{ source('olist_raw', 'olist_sellers') }}
