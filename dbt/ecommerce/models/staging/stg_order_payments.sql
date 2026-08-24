with source as (
    select * from {{ source('raw', 'olist_order_payments_dataset') }}
)

select
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
from source
