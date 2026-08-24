with source as (
    select * from {{ source('raw', 'olist_products_dataset') }}
),

translation as (
    select * from {{ source('raw', 'product_category_name_translation') }}
)

select
    p.product_id,
    p.product_category_name as category_name_pt,
    coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as category_name_english,
    p.product_weight_g as weight_g,
    p.product_length_cm as length_cm,
    p.product_height_cm as height_cm,
    p.product_width_cm as width_cm
from source p
left join translation t on p.product_category_name = t.product_category_name
