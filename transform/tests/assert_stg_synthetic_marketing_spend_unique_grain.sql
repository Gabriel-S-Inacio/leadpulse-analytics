select
    spend_date,
    source_origin,
    scenario_id
from {{ ref('stg_synthetic_marketing_spend') }}
group by spend_date, source_origin, scenario_id
having count(*) > 1
