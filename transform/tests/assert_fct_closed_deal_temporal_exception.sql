with known_exceptions as (
    select
        'b91cf8812365f50ff4bda4bcd6206b05'::text as mql_id,
        '5e063e85d44b0f5c3e6ec3131103a57e'::text as seller_id,
        '2018-03-08'::date as first_contact_date,
        '2018-03-06 19:38:55'::timestamp as won_timestamp
),

actual_exceptions as (
    select
        closed_deals.mql_id,
        closed_deals.seller_id,
        to_date(mql.contact_date_key::text, 'YYYYMMDD') as first_contact_date,
        closed_deals.won_timestamp
    from {{ ref('fct_closed_deal') }} as closed_deals
    inner join {{ ref('fct_mql') }} as mql using (mql_id)
    where closed_deals.won_timestamp::date
        < to_date(mql.contact_date_key::text, 'YYYYMMDD')
),

exception_drift as (
    select
        coalesce(actual.mql_id, expected.mql_id) as mql_id
    from actual_exceptions as actual
    full outer join known_exceptions as expected
        on actual.mql_id = expected.mql_id
       and actual.seller_id = expected.seller_id
       and actual.first_contact_date = expected.first_contact_date
       and actual.won_timestamp = expected.won_timestamp
    where actual.mql_id is null or expected.mql_id is null
),

status_mismatch as (
    select closed_deals.mql_id
    from {{ ref('fct_closed_deal') }} as closed_deals
    inner join {{ ref('fct_mql') }} as mql using (mql_id)
    where closed_deals.temporal_quality_status <> case
        when closed_deals.won_timestamp::date
            >= to_date(mql.contact_date_key::text, 'YYYYMMDD')
            then 'VALID'
        else 'INVALID_SEQUENCE'
    end
)

select 'exception_drift' as failure_type, mql_id from exception_drift
union all
select 'status_mismatch', mql_id from status_mismatch
