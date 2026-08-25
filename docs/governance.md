# Data governance & PII handling

## What PII exists in the source data

The Olist dataset is already de-identified by the source (no names, emails,
or phone numbers), but it still carries data that ties a person to
repeated behavior and a location:

- `customer_id` / `customer_unique_id` -- opaque IDs, but `customer_unique_id`
  links every order placed by the same real person. Left as-is, anyone with
  query access could build a full purchase history per person.
- `customer_zip_code_prefix`, `customer_city`, `customer_state` (and the
  same for sellers) -- location data, down to a postal-code-prefix grain.
- `review_comment_title` / `review_comment_message` -- free text a customer
  wrote; free text is unpredictable and can occasionally contain
  self-identifying details (a name, an address, an order number).

## How it's handled in the pipeline

- **Identifier hashing.** `models/staging/stg_customers.sql` (and
  `stg_orders.sql`, for the FK) hash both `customer_id` and
  `customer_unique_id` with `md5(id || salt)`, where the salt comes from
  the `CUSTOMER_ID_HASH_SALT` env var (see `.env.example`). Hashing alone
  isn't enough on a dataset this size -- rainbow-tabling every possible ID
  value back to its hash is trivial without a salt. Every model from
  staging onward only ever sees the hashed value; the original
  `customer_id` exists solely in the `raw` schema (see *Access control*
  below for why that's still a gap worth flagging).
- **Location kept at a coarse grain in the marts.** `dim_customers` and
  `dim_sellers` expose `zip_code_prefix`, `city`, `state`, and a derived
  `region` (via the `state_region_mapping` seed) -- never the precise
  lat/long geolocation. `stg_geolocation.sql` does load and deduplicate
  the raw lat/long table (Olist's geolocation file has ~1M rows collapsing
  to ~19k zip prefixes), but that model is *not* joined into any mart --
  it exists for potential future geo-analysis, kept firmly out of what the
  Streamlit app or any BI tool can query today.
- **Free text excluded.** `stg_order_reviews.sql` and `fct_order_items`
  carry `review_score` (a number) but deliberately drop
  `review_comment_title`/`review_comment_message`. The analytics use case
  (delivery delay vs. review score) never needed the comment text, so it
  wasn't pulled past the raw schema.

## Known gap: the `raw` schema is unmasked by design

`ingestion/load_raw.py` loads the source CSVs as-is -- masking happens in
the staging layer, not at ingestion time, so `raw.olist_customers_dataset`
still holds the original `customer_id`/`customer_unique_id`. This is
intentional: staging models need the real source data to build from, and
re-hashing on top of already-hashed data would just add an unnecessary
layer. In a real deployment, this means the `raw` schema must be locked
down harder than the schemas built on top of it -- see below.

## Access control in a production/cloud setting

This project runs against a local, single-user Postgres, so none of the
below is implemented -- but here's what a real deployment would need:

- **Least privilege by schema.** The ELT service account (ingestion + dbt)
  is the only role with write access to `raw` and `staging`. A separate
  read-only role, scoped to `marts` only, is what the analytics app (and
  any human running ad-hoc SQL) actually connects as -- it never sees
  `raw`, so it never sees an unhashed customer ID.
- **Column-level masking / row-level security** on anything that lands in
  `raw` before staging can mask it, for cases where a raw table must be
  queryable directly (e.g. Postgres `REVOKE` on sensitive columns, or a
  dynamic data masking extension), rather than relying on "nobody happens
  to query `raw`."
- **Audit logging** on who queried `raw`/`staging` and when, since those
  are the only places an original identifier exists at rest.
- **Secrets management** for the hash salt itself (`CUSTOMER_ID_HASH_SALT`)
  -- it should live in a secrets manager, not a `.env` file, and rotating
  it would need a documented re-hash/backfill process since it changes
  every downstream hashed value.
