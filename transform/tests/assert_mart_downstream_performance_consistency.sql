with expected as (
    select
        date_trunc('month', order_purchase_timestamp)::date as purchase_month,
        origin_key,
        seller_key,
        order_id,
        sum(eligible_gmv_amount)::numeric(18, 2) as eligible_gmv
    from {{ ref('fct_order_item') }}
    where is_acquired_seller
      and is_eligible_order
      and is_post_acquisition
    group by 1, 2, 3, 4
),

differences as (
    select
        coalesce(mart.order_id, expected.order_id) as order_id
    from {{ ref('mart_downstream_performance') }} as mart
    full outer join expected
        on mart.purchase_month = expected.purchase_month
        and mart.origin_key = expected.origin_key
        and mart.seller_key = expected.seller_key
        and mart.order_id = expected.order_id
    where mart.order_id is null
       or expected.order_id is null
       or mart.orders <> 1
       or mart.seller_order_participations <> 1
       or mart.eligible_gmv <> expected.eligible_gmv
       or mart.eligible_gmv < 0
)

select 'fact_recomposition_failure' as issue
where exists (select 1 from differences)

union all

select 'gmv_fanout_or_loss'
where (select sum(eligible_gmv) from {{ ref('mart_downstream_performance') }})
    <> (
        select sum(eligible_gmv_amount)
        from {{ ref('fct_order_item') }}
        where is_acquired_seller
          and is_eligible_order
          and is_post_acquisition
    )

union all

select 'seller_order_fanout_or_loss'
where (
    select sum(seller_order_participations)
    from {{ ref('mart_downstream_performance') }}
) <> (
    select count(distinct (seller_key, order_id))
    from {{ ref('fct_order_item') }}
    where is_acquired_seller
      and is_eligible_order
      and is_post_acquisition
)
