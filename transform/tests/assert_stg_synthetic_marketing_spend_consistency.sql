select
    spend_date,
    source_origin,
    scenario_id
from {{ ref('stg_synthetic_marketing_spend') }}
where spend_amount < 0
   or source_origin not in (
        'paid_search',
        'display',
        'social',
        'other_publicities'
   )
