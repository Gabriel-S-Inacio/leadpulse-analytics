with invalid_members as (
    select origin_member_code
    from {{ ref('dim_origin') }}
    where mapping_version <> 'v1'
       or case classification
            when 'OBSERVED' then not (
                source_origin in (
                    'organic_search',
                    'paid_search',
                    'social',
                    'direct_traffic',
                    'email',
                    'referral',
                    'display',
                    'other_publicities',
                    'other'
                )
                and normalized_channel = case
                    when source_origin = 'direct_traffic' then 'direct'
                    else source_origin
                end
            )
            when 'EXPLICIT_UNKNOWN' then not (
                source_origin = 'unknown' and normalized_channel = 'unattributed'
            )
            when 'MISSING' then not (
                source_origin is null and normalized_channel = 'unattributed'
            )
            when 'UNRECOGNIZED' then not (
                source_origin is not null and normalized_channel = 'unattributed'
            )
            when 'NOT_APPLICABLE' then not (
                source_origin is null and normalized_channel = 'not_applicable'
            )
            else true
        end
),

required_technical_members as (
    select classification
    from (
        values ('MISSING'), ('NOT_APPLICABLE')
    ) as required(classification)
    where (
        select count(*)
        from {{ ref('dim_origin') }} as origins
        where origins.classification = required.classification
    ) <> 1
)

select 'invalid_mapping' as failure_type, origin_member_code as failure_key
from invalid_members
union all
select 'technical_count', classification
from required_technical_members
