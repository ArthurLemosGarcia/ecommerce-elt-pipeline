-- Grain: one row per customer_id, matching the grain of the source
-- orders table (Olist assigns a fresh customer_id per order; the
-- repeat-customer identity lives in customer_unique_id, kept here as
-- an attribute, not the key -- see schema.yml for details).
with customers as (
    select * from {{ ref('stg_customers') }}
),

regions as (
    select * from {{ ref('state_region_mapping') }}
)

select
    c.customer_id,
    c.customer_unique_id,
    c.zip_code_prefix,
    c.city,
    c.state,
    coalesce(r.region, 'Unknown') as region
from customers c
left join regions r on c.state = r.state
