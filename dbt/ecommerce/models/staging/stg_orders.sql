with source as (
    select * from {{ source('raw', 'olist_orders_dataset') }}
)

select
    order_id,
    md5(customer_id || '{{ env_var("CUSTOMER_ID_HASH_SALT", "changeme") }}') as customer_id,
    order_status,
    nullif(trim(order_purchase_timestamp), '')::timestamp as purchase_timestamp,
    nullif(trim(order_approved_at), '')::timestamp as approved_at,
    nullif(trim(order_delivered_carrier_date), '')::timestamp as delivered_carrier_date,
    nullif(trim(order_delivered_customer_date), '')::timestamp as delivered_customer_date,
    nullif(trim(order_estimated_delivery_date), '')::timestamp as estimated_delivery_date
from source
