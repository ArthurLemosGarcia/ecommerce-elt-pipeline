select
    product_id,
    category_name_pt,
    category_name_english,
    weight_g,
    length_cm,
    height_cm,
    width_cm
from {{ ref('stg_products') }}
