-- Fails if any item has a negative price or freight value.
select *
from {{ ref('fct_order_items') }}
where price < 0
   or freight_value < 0
