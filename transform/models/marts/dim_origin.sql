with observed_source_values as (
    select distinct source_origin
    from {{ ref('stg_olist_marketing_qualified_leads') }}
    where source_origin is not null
),

observed_members as (
    select
        source_origin as origin_member_code,
        source_origin,
        case
            when source_origin = 'direct_traffic' then 'direct'
            when source_origin = 'unknown' then 'unattributed'
            when source_origin in (
                'organic_search',
                'paid_search',
                'social',
                'email',
                'referral',
                'display',
                'other_publicities',
                'other'
            ) then source_origin
            else 'unattributed'
        end as normalized_channel,
        case
            when source_origin = 'unknown' then 'EXPLICIT_UNKNOWN'
            when source_origin in (
                'organic_search',
                'paid_search',
                'social',
                'direct_traffic',
                'email',
                'referral',
                'display',
                'other_publicities',
                'other'
            ) then 'OBSERVED'
            else 'UNRECOGNIZED'
        end as classification
    from observed_source_values
),

technical_members as (
    select *
    from (
        values
            ('__MISSING__', null::text, 'unattributed', 'MISSING'),
            ('__NOT_APPLICABLE__', null::text, 'not_applicable', 'NOT_APPLICABLE')
    ) as members(
        origin_member_code,
        source_origin,
        normalized_channel,
        classification
    )
),

governed_members as (
    select * from observed_members
    union all
    select * from technical_members
)

select
    md5('origin|' || origin_member_code) as origin_key,
    origin_member_code,
    source_origin,
    normalized_channel,
    classification,
    'v1'::text as mapping_version
from governed_members
