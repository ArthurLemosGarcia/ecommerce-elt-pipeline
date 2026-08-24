-- Customer identifiers are salted and hashed here so no raw personal ID
-- reaches downstream models (see docs/governance.md).
with source as (
    select * from {{ source('raw', 'olist_customers_dataset') }}
)

select
    md5(customer_id || '{{ env_var("CUSTOMER_ID_HASH_SALT", "changeme") }}') as customer_id,
    md5(customer_unique_id || '{{ env_var("CUSTOMER_ID_HASH_SALT", "changeme") }}') as customer_unique_id,
    customer_zip_code_prefix as zip_code_prefix,
    customer_city as city,
    customer_state as state
from source
