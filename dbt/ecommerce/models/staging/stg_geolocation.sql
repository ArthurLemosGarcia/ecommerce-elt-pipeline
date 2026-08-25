-- The source has many duplicate/near-duplicate lat-lng pairs per zip
-- code prefix; collapse to one row per prefix (averaged coordinates,
-- one representative city/state) so it can be joined 1:1 if needed.
with source as (
    select
        geolocation_zip_code_prefix as zip_code_prefix,
        geolocation_lat as lat,
        geolocation_lng as lng,
        geolocation_city as city,
        geolocation_state as state
    from {{ source('raw', 'olist_geolocation_dataset') }}
),

averaged_coordinates as (
    select
        zip_code_prefix,
        avg(lat) as lat,
        avg(lng) as lng
    from source
    group by zip_code_prefix
),

representative_city as (
    select distinct on (zip_code_prefix)
        zip_code_prefix,
        city,
        state
    from source
    order by zip_code_prefix, city
)

select
    c.zip_code_prefix,
    c.lat,
    c.lng,
    r.city,
    r.state
from averaged_coordinates c
join representative_city r using (zip_code_prefix)
