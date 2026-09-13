with source_rows as (
    select
        mql_id,
        first_contact_date,
        landing_page_id,
        source_origin,
        _source_file,
        _source_sha256,
        case
            when source_origin is null then '__MISSING__'
            else source_origin
        end as origin_member_code
    from {{ ref('stg_olist_marketing_qualified_leads') }}
)

select
    source_rows.mql_id,
    dates.date_key as contact_date_key,
    origins.origin_key,
    source_rows.landing_page_id,
    1::integer as mql_count,
    source_rows._source_sha256 as source_snapshot_id,
    source_rows._source_file as source_file_name
from source_rows
inner join {{ ref('dim_date') }} as dates
    on source_rows.first_contact_date = dates.calendar_date
inner join {{ ref('dim_origin') }} as origins
    on source_rows.origin_member_code = origins.origin_member_code
