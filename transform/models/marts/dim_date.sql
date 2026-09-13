with source_bounds as (
    select
        least(
            (select min(first_contact_date) from {{ ref('stg_olist_marketing_qualified_leads') }}),
            (select min(won_date::date) from {{ ref('stg_olist_closed_deals') }}),
            (select min(order_purchase_timestamp::date) from {{ ref('stg_olist_orders') }})
        ) as min_date,
        greatest(
            (select max(first_contact_date) from {{ ref('stg_olist_marketing_qualified_leads') }}),
            (select max(won_date::date) from {{ ref('stg_olist_closed_deals') }}),
            (select max(order_purchase_timestamp::date) from {{ ref('stg_olist_orders') }})
        ) as max_date
),

calendar as (
    select generated_at::date as calendar_date
    from source_bounds
    cross join lateral generate_series(
        min_date::timestamp,
        max_date::timestamp,
        interval '1 day'
    ) as generated_at
),

calendar_members as (
    select
        to_char(calendar_date, 'YYYYMMDD')::integer as date_key,
        calendar_date,
        'CALENDAR'::text as date_classification,
        extract(year from calendar_date)::integer as year,
        extract(quarter from calendar_date)::integer as quarter,
        extract(month from calendar_date)::integer as month,
        case extract(month from calendar_date)::integer
            when 1 then 'January'
            when 2 then 'February'
            when 3 then 'March'
            when 4 then 'April'
            when 5 then 'May'
            when 6 then 'June'
            when 7 then 'July'
            when 8 then 'August'
            when 9 then 'September'
            when 10 then 'October'
            when 11 then 'November'
            when 12 then 'December'
        end as month_name,
        to_char(calendar_date, 'YYYY-MM') as year_month,
        extract(day from calendar_date)::integer as day_of_month,
        extract(isodow from calendar_date)::integer as day_of_week,
        case extract(isodow from calendar_date)::integer
            when 1 then 'Monday'
            when 2 then 'Tuesday'
            when 3 then 'Wednesday'
            when 4 then 'Thursday'
            when 5 then 'Friday'
            when 6 then 'Saturday'
            when 7 then 'Sunday'
        end as day_name,
        extract(isodow from calendar_date)::integer in (6, 7) as is_weekend
    from calendar
),

technical_members as (
    select *
    from (
        values
            (-1, 'UNKNOWN'),
            (-2, 'NOT_OBSERVED'),
            (-3, 'NOT_APPLICABLE')
    ) as members(date_key, date_classification)
)

select * from calendar_members
union all
select
    date_key,
    null::date as calendar_date,
    date_classification,
    null::integer as year,
    null::integer as quarter,
    null::integer as month,
    null::text as month_name,
    null::text as year_month,
    null::integer as day_of_month,
    null::integer as day_of_week,
    null::text as day_name,
    null::boolean as is_weekend
from technical_members
