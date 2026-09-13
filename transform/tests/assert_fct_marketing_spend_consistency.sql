with actual as (
    select
        fact.*,
        dates.calendar_date as spend_date,
        dates.date_classification,
        origins.source_origin as dimension_source_origin,
        origins.classification as origin_classification
    from {{ ref('fct_marketing_spend') }} as fact
    inner join {{ ref('dim_date') }} as dates
        on fact.spend_date_key = dates.date_key
    inner join {{ ref('dim_origin') }} as origins
        on fact.origin_key = origins.origin_key
)

select
    coalesce(staged.spend_date, actual.spend_date) as spend_date,
    coalesce(staged.source_origin, actual.source_origin) as source_origin,
    coalesce(staged.scenario_id, actual.scenario_id) as scenario_id
from {{ ref('stg_synthetic_marketing_spend') }} as staged
full outer join actual
    on staged.spend_date = actual.spend_date
   and staged.source_origin = actual.source_origin
   and staged.scenario_id = actual.scenario_id
where staged.spend_date is null
   or actual.spend_date is null
   or actual.source_origin <> actual.dimension_source_origin
   or actual.date_classification <> 'CALENDAR'
   or actual.origin_classification <> 'OBSERVED'
   or actual.source_origin not in (
        'paid_search',
        'display',
        'social',
        'other_publicities'
   )
   or staged.methodology_version <> actual.methodology_version
   or staged.generation_seed <> actual.generation_seed
   or staged.currency <> actual.currency
   or staged.spend_amount <> actual.spend_amount
   or staged.data_classification <> actual.data_classification
   or staged._source_sha256 <> actual.source_snapshot_id
   or staged._source_file <> actual.source_file_name
