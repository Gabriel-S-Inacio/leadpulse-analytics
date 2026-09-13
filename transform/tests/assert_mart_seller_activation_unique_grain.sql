select
    cohort_month,
    origin_key,
    observation_cutoff_timestamp,
    lifecycle_rule_version,
    source_snapshot_id,
    count(*) as row_count
from {{ ref('mart_seller_activation') }}
group by 1, 2, 3, 4, 5
having count(*) <> 1
