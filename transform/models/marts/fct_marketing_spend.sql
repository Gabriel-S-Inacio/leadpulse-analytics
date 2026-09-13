select
    dates.date_key as spend_date_key,
    origins.origin_key,
    spend.source_origin,
    spend.scenario_id,
    spend.methodology_version,
    spend.generation_seed,
    spend.currency,
    spend.spend_amount,
    spend.data_classification,
    spend._source_sha256 as source_snapshot_id,
    spend._source_file as source_file_name
from {{ ref('stg_synthetic_marketing_spend') }} as spend
inner join {{ ref('dim_date') }} as dates
    on spend.spend_date = dates.calendar_date
inner join {{ ref('dim_origin') }} as origins
    on spend.source_origin = origins.source_origin
