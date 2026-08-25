-- Grain: one row per calendar date spanning every purchase, delivery,
-- and estimated-delivery date referenced by fct_order_items.
with bounds as (
    select
        least(
            min(purchase_timestamp)::date,
            min(delivered_customer_date)::date,
            min(estimated_delivery_date)::date
        ) as min_date,
        greatest(
            max(purchase_timestamp)::date,
            max(delivered_customer_date)::date,
            max(estimated_delivery_date)::date
        ) as max_date
    from {{ ref('stg_orders') }}
),

date_spine as (
    select generate_series(
        (select min_date from bounds),
        (select max_date from bounds),
        interval '1 day'
    )::date as date_key
)

select
    date_key,
    extract(year from date_key)::int as year,
    extract(quarter from date_key)::int as quarter,
    extract(month from date_key)::int as month,
    to_char(date_key, 'Month') as month_name,
    extract(day from date_key)::int as day_of_month,
    extract(dow from date_key)::int as day_of_week,
    to_char(date_key, 'Day') as day_name,
    extract(dow from date_key) in (0, 6) as is_weekend
from date_spine
