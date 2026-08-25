with source as (
    select * from {{ source('raw', 'olist_order_items_dataset') }}
)

select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    nullif(trim(shipping_limit_date), '')::timestamp as shipping_limit_date,
    price,
    freight_value
from source
