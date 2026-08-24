with source as (
    select * from {{ source('raw', 'olist_sellers_dataset') }}
)

select
    seller_id,
    seller_zip_code_prefix as zip_code_prefix,
    seller_city as city,
    seller_state as state
from source
