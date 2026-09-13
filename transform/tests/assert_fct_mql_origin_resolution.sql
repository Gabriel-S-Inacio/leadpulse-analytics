select facts.mql_id
from {{ ref('fct_mql') }} as facts
inner join {{ ref('stg_olist_marketing_qualified_leads') }} as source using (mql_id)
inner join {{ ref('dim_origin') }} as origins using (origin_key)
where (source.source_origin is null and origins.classification <> 'MISSING')
   or (source.source_origin is not null and origins.source_origin <> source.source_origin)
