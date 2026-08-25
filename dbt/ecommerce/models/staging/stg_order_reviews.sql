-- The source data has a small number of duplicate review_id rows;
-- keep the most recently answered one per review_id.
with source as (
    select * from {{ source('raw', 'olist_order_reviews_dataset') }}
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by review_id
            order by nullif(trim(review_answer_timestamp), '')::timestamp desc nulls last
        ) as row_num
    from source
)

select
    review_id,
    order_id,
    review_score,
    nullif(trim(review_creation_date), '')::timestamp as review_creation_date,
    nullif(trim(review_answer_timestamp), '')::timestamp as review_answer_timestamp
from deduplicated
where row_num = 1
