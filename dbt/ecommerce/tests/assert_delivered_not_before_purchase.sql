-- Fails if any item's delivery date is earlier than its purchase date.
select *
from {{ ref('fct_order_items') }}
where delivered_date_key is not null
  and delivered_date_key < purchase_date_key
