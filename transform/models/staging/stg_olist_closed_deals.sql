select
    mql_id,
    seller_id,
    sdr_id,
    sr_id,
    cast(won_date as timestamp) as won_date,
    business_segment,
    lead_type,
    lead_behaviour_profile,
    has_company,
    has_gtin,
    average_stock,
    business_type,
    declared_product_catalog_size,
    declared_monthly_revenue,
    _loaded_at,
    _source_file,
    _source_sha256
from {{ source('olist_raw', 'olist_closed_deals') }}
