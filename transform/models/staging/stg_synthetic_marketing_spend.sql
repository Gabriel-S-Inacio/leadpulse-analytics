select
    cast(spend_date as date) as spend_date,
    source_origin,
    scenario_id,
    methodology_version,
    cast(generation_seed as bigint) as generation_seed,
    currency,
    cast(spend_amount as numeric(12, 2)) as spend_amount,
    data_classification,
    _loaded_at,
    _source_file,
    _source_sha256
from {{ source('synthetic_raw', 'synthetic_marketing_spend') }}
