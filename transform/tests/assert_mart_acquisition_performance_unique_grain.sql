select
    cohort_month,
    origin_key,
    count(*) as row_count
from {{ ref('mart_acquisition_performance') }}
group by 1, 2
having count(*) <> 1
