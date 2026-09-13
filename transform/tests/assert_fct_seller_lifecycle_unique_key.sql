select
    seller_key,
    observation_cutoff_timestamp,
    lifecycle_rule_version,
    source_snapshot_id
from {{ ref('fct_seller_lifecycle') }}
group by
    seller_key,
    observation_cutoff_timestamp,
    lifecycle_rule_version,
    source_snapshot_id
having count(*) > 1
