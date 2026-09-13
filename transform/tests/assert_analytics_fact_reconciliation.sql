select 'fct_mql' as model_name
where (select count(*) from {{ ref('fct_mql') }})
    <> (select count(*) from {{ ref('stg_olist_marketing_qualified_leads') }})

union all

select 'fct_closed_deal'
where (select count(*) from {{ ref('fct_closed_deal') }})
    <> (select count(*) from {{ ref('stg_olist_closed_deals') }})

union all

select 'fct_order_item'
where (select count(*) from {{ ref('fct_order_item') }})
    <> (select count(*) from {{ ref('stg_olist_order_items') }})
