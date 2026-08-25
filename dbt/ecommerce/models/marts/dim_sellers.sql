with sellers as (
    select * from {{ ref('stg_sellers') }}
),

regions as (
    select * from {{ ref('state_region_mapping') }}
)

select
    s.seller_id,
    s.zip_code_prefix,
    s.city,
    s.state,
    coalesce(r.region, 'Unknown') as region
from sellers s
left join regions r on s.state = r.state
