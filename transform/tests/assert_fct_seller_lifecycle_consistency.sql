with expected_parameters as (
    select max(order_purchase_timestamp) as observation_cutoff_timestamp
    from {{ ref('stg_olist_orders') }}
),

expected_source_version as (
    select md5(
        'seller_lifecycle|'
        || (select min(source_snapshot_id) from {{ ref('fct_closed_deal') }})
        || '|'
        || (select min(source_snapshot_id) from {{ ref('fct_order_item') }})
    ) as source_snapshot_id
)

select lifecycle.seller_key
from {{ ref('fct_seller_lifecycle') }} as lifecycle
inner join {{ ref('fct_closed_deal') }} as acquisitions using (seller_key)
inner join {{ ref('dim_date') }} as activation_dates
    on lifecycle.activation_date_key = activation_dates.date_key
inner join {{ ref('dim_date') }} as cutoff_dates
    on lifecycle.observation_cutoff_date_key = cutoff_dates.date_key
cross join expected_parameters
cross join expected_source_version
where lifecycle.origin_key <> acquisitions.origin_key
   or lifecycle.won_date_key <> acquisitions.won_date_key
   or lifecycle.won_timestamp <> acquisitions.won_timestamp
   or lifecycle.temporal_quality_status <> acquisitions.temporal_quality_status
   or lifecycle.observation_cutoff_timestamp
        <> expected_parameters.observation_cutoff_timestamp
   or cutoff_dates.calendar_date <> lifecycle.observation_cutoff_timestamp::date
   or lifecycle.source_snapshot_id <> expected_source_version.source_snapshot_id
   or lifecycle.is_mature_90d <> (
        lifecycle.temporal_quality_status = 'VALID'
        and lifecycle.observation_cutoff_timestamp
            >= lifecycle.won_timestamp + interval '90 days'
   )
   or lifecycle.mature_seller_count <> lifecycle.is_mature_90d::integer
   or lifecycle.activated_seller_count
        <> coalesce(lifecycle.is_activated_90d, false)::integer
   or (
        lifecycle.is_activated_90d = true
        and (
            not lifecycle.is_mature_90d
            or lifecycle.activation_timestamp is null
            or lifecycle.first_eligible_order_id is null
            or lifecycle.time_to_first_order_days is null
            or lifecycle.activation_timestamp
                > lifecycle.won_timestamp + interval '90 days'
        )
   )
   or (
        lifecycle.is_activated_90d = false
        and (
            not lifecycle.is_mature_90d
            or lifecycle.activation_timestamp
                <= lifecycle.won_timestamp + interval '90 days'
        )
   )
   or (
        not lifecycle.is_mature_90d
        and lifecycle.is_activated_90d is not null
   )
   or (
        lifecycle.temporal_quality_status = 'INVALID_SEQUENCE'
        and (
            lifecycle.is_mature_90d
            or lifecycle.is_activated_90d is not null
            or lifecycle.first_eligible_order_id is not null
            or lifecycle.activation_timestamp is not null
            or lifecycle.time_to_first_order_days is not null
            or activation_dates.date_classification <> 'UNKNOWN'
        )
   )
   or (
        lifecycle.temporal_quality_status = 'VALID'
        and lifecycle.activation_timestamp is null
        and activation_dates.date_classification <> 'NOT_OBSERVED'
   )
   or (
        lifecycle.activation_timestamp is not null
        and (
            activation_dates.calendar_date <> lifecycle.activation_timestamp::date
            or lifecycle.time_to_first_order_days is null
            or lifecycle.time_to_first_order_days <= 0
            or lifecycle.time_to_first_order_days <> extract(
                epoch from lifecycle.activation_timestamp - lifecycle.won_timestamp
            ) / 86400.0
        )
   )
