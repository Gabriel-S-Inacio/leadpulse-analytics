select
    period,
    origin_key,
    scenario_id,
    methodology_version,
    generation_seed,
    currency,
    observation_cutoff_timestamp,
    lifecycle_rule_version,
    lifecycle_source_snapshot_id,
    count(*) as row_count
from {{ ref('mart_marketing_efficiency') }}
group by 1, 2, 3, 4, 5, 6, 7, 8, 9
having count(*) <> 1
