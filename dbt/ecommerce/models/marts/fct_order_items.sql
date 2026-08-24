-- Grain: one row per order item. review_score is the order's average
-- review score (a small number of orders have more than one review),
-- broadcast across all items of that order -- reviews are given per
-- order, not per item, so this repeats a coarser-grain attribute at
-- the fact's finer grain, which is what the business question needs.
--
-- Indexed on every FK column: see docs/optimization.md for the
-- before/after EXPLAIN ANALYZE that motivated this.
{{
    config(
        indexes=[
            {'columns': ['customer_id']},
            {'columns': ['product_id']},
            {'columns': ['seller_id']},
            {'columns': ['purchase_date_key']},
            {'columns': ['delivered_date_key']},
        ]
    )
}}

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

review_scores as (
    select
        order_id,
        avg(review_score) as avg_review_score
    from {{ ref('stg_order_reviews') }}
    group by order_id
)

select
    {{ surrogate_key(['oi.order_id', 'oi.order_item_id']) }} as order_item_key,
    oi.order_id,
    oi.order_item_id,
    o.customer_id,
    oi.product_id,
    oi.seller_id,
    o.purchase_timestamp::date as purchase_date_key,
    o.delivered_customer_date::date as delivered_date_key,
    o.order_status,
    oi.price,
    oi.freight_value,
    case
        when o.delivered_customer_date is not null
            then o.delivered_customer_date::date - o.purchase_timestamp::date
    end as delivery_time_days,
    case
        when o.delivered_customer_date is not null
            then o.delivered_customer_date > o.estimated_delivery_date
    end as is_late,
    rs.avg_review_score as review_score
from order_items oi
left join orders o on oi.order_id = o.order_id
left join review_scores rs on oi.order_id = rs.order_id
