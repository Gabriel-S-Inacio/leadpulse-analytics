select
    mql_id,
    cast(first_contact_date as date) as first_contact_date,
    landing_page_id,
    origin as source_origin,
    _loaded_at,
    _source_file,
    _source_sha256
from {{ source('olist_raw', 'olist_marketing_qualified_leads') }}
