with lifecycle_parameters as (
    select
        max(order_purchase_timestamp) as observation_cutoff_timestamp,
        'seller_activation_v1'::text as lifecycle_rule_version
    from {{ ref('stg_olist_orders') }}
),

source_versions as (
    select
        md5(
            'seller_lifecycle|'
            || (select min(source_snapshot_id) from {{ ref('fct_closed_deal') }})
            || '|'
            || (select min(source_snapshot_id) from {{ ref('fct_order_item') }})
        ) as source_snapshot_id
),

seller_order_events as (
    select
        order_items.seller_key,
        order_items.order_id,
        min(order_items.order_purchase_timestamp) as order_purchase_timestamp
    from {{ ref('fct_order_item') }} as order_items
    inner join {{ ref('fct_closed_deal') }} as acquisitions using (seller_key)
    where acquisitions.temporal_quality_status = 'VALID'
      and order_items.is_acquired_seller
      and order_items.is_eligible_order
      and order_items.is_post_acquisition
    group by order_items.seller_key, order_items.order_id
),

ranked_events as (
    select
        seller_key,
        order_id,
        order_purchase_timestamp,
        row_number() over (
            partition by seller_key
            order by order_purchase_timestamp, order_id
        ) as event_rank
    from seller_order_events
),

first_events as (
    select
        seller_key,
        order_id as first_eligible_order_id,
        order_purchase_timestamp as activation_timestamp
    from ranked_events
    where event_rank = 1
),

technical_dates as (
    select
        max(date_key) filter (where date_classification = 'UNKNOWN') as unknown_date_key,
        max(date_key) filter (where date_classification = 'NOT_OBSERVED')
            as not_observed_date_key
    from {{ ref('dim_date') }}
),

prepared as (
    select
        acquisitions.seller_key,
        acquisitions.origin_key,
        acquisitions.won_date_key,
        acquisitions.won_timestamp,
        parameters.observation_cutoff_timestamp::date as observation_cutoff_date,
        parameters.observation_cutoff_timestamp,
        parameters.lifecycle_rule_version,
        versions.source_snapshot_id,
        acquisitions.temporal_quality_status,
        case
            when acquisitions.temporal_quality_status = 'VALID'
                then first_events.first_eligible_order_id
        end as first_eligible_order_id,
        case
            when acquisitions.temporal_quality_status = 'VALID'
                then first_events.activation_timestamp
        end as activation_timestamp,
        acquisitions.temporal_quality_status = 'VALID'
            and parameters.observation_cutoff_timestamp
                >= acquisitions.won_timestamp + interval '90 days'
            as is_mature_90d
    from {{ ref('fct_closed_deal') }} as acquisitions
    cross join lifecycle_parameters as parameters
    cross join source_versions as versions
    left join first_events using (seller_key)
),

classified as (
    select
        prepared.*,
        case
            when temporal_quality_status = 'INVALID_SEQUENCE' then null::boolean
            when not is_mature_90d then null::boolean
            when activation_timestamp <= won_timestamp + interval '90 days' then true
            else false
        end as is_activated_90d
    from prepared
)

select
    classified.seller_key,
    classified.origin_key,
    classified.won_date_key,
    classified.won_timestamp,
    cutoff_dates.date_key as observation_cutoff_date_key,
    classified.observation_cutoff_timestamp,
    classified.lifecycle_rule_version,
    classified.source_snapshot_id,
    classified.temporal_quality_status,
    classified.first_eligible_order_id,
    case
        when classified.temporal_quality_status = 'INVALID_SEQUENCE'
            then technical_dates.unknown_date_key
        when classified.activation_timestamp is null
            then technical_dates.not_observed_date_key
        else activation_dates.date_key
    end as activation_date_key,
    classified.activation_timestamp,
    case
        when classified.temporal_quality_status = 'VALID'
             and classified.activation_timestamp is not null
            then extract(
                epoch from classified.activation_timestamp - classified.won_timestamp
            ) / 86400.0
    end as time_to_first_order_days,
    classified.is_mature_90d,
    classified.is_activated_90d,
    classified.is_mature_90d::integer as mature_seller_count,
    coalesce(classified.is_activated_90d, false)::integer as activated_seller_count
from classified
inner join {{ ref('dim_date') }} as cutoff_dates
    on classified.observation_cutoff_date = cutoff_dates.calendar_date
left join {{ ref('dim_date') }} as activation_dates
    on classified.activation_timestamp::date = activation_dates.calendar_date
cross join technical_dates
