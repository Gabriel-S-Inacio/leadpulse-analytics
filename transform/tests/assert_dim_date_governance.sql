with technical_member_counts as (
    select date_classification, count(*) as member_count
    from {{ ref('dim_date') }}
    where date_classification <> 'CALENDAR'
    group by date_classification
),

invalid_calendar as (
    select date_key
    from {{ ref('dim_date') }}
    where date_classification = 'CALENDAR'
      and (
          date_key <> to_char(calendar_date, 'YYYYMMDD')::integer
          or year <> extract(year from calendar_date)::integer
          or quarter <> extract(quarter from calendar_date)::integer
          or month <> extract(month from calendar_date)::integer
          or year_month <> to_char(calendar_date, 'YYYY-MM')
          or day_of_month <> extract(day from calendar_date)::integer
          or day_of_week <> extract(isodow from calendar_date)::integer
          or is_weekend <> (extract(isodow from calendar_date)::integer in (6, 7))
      )
),

invalid_technical as (
    select date_key
    from {{ ref('dim_date') }}
    where date_classification <> 'CALENDAR'
      and (
          calendar_date is not null
          or year is not null
          or quarter is not null
          or month is not null
          or month_name is not null
          or year_month is not null
          or day_of_month is not null
          or day_of_week is not null
          or day_name is not null
          or is_weekend is not null
      )
),

invalid_technical_counts as (
    select date_classification
    from technical_member_counts
    where member_count <> 1
    union all
    select expected.classification
    from (
        values ('UNKNOWN'), ('NOT_OBSERVED'), ('NOT_APPLICABLE')
    ) as expected(classification)
    left join technical_member_counts actual
        on expected.classification = actual.date_classification
    where actual.date_classification is null
)

select 'calendar' as failure_type, date_key::text as failure_key from invalid_calendar
union all
select 'technical_attributes', date_key::text from invalid_technical
union all
select 'technical_count', date_classification from invalid_technical_counts
