select
    spend_date_key,
    origin_key,
    scenario_id
from {{ ref('fct_marketing_spend') }}
group by spend_date_key, origin_key, scenario_id
having count(*) > 1
