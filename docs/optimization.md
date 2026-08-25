# Query optimization: indexing `fct_order_items`

## The query

A representative drill-down query for the business question: for a given
seller, the late-delivery rate and average review score of their items,
broken down by product category and customer region. It joins the fact
table to two dimensions and filters on one of the fact's foreign keys:

```sql
SELECT
    dp.category_name_english,
    dc.region,
    count(*) AS total_items,
    sum(CASE WHEN f.is_late THEN 1 ELSE 0 END)::numeric
        / nullif(count(*) FILTER (WHERE f.is_late IS NOT NULL), 0) AS late_rate,
    avg(f.review_score) AS avg_review_score
FROM marts.fct_order_items f
JOIN marts.dim_products dp ON f.product_id = dp.product_id
JOIN marts.dim_customers dc ON f.customer_id = dc.customer_id
WHERE f.seller_id = '6560211a19b47992c3666cc44a7e94c0'
GROUP BY dp.category_name_english, dc.region
ORDER BY late_rate DESC;
```

`fct_order_items` has 112,650 rows; the filtered seller has 2,033 of them
(~1.8%). Measured with `EXPLAIN ANALYZE` against the full Olist dataset
loaded locally, with `max_parallel_workers_per_gather = 0` so both runs are
directly comparable (parallel workers otherwise make Postgres's choice
between plans noisy on a table this size).

## Before: no index on `fct_order_items`

```
->  Hash Join  (cost=1255.40..6338.62 rows=1971 width=52) (actual time=18.986..46.323 rows=2033 loops=1)
      Hash Cond: (f.product_id = dp.product_id)
      ->  Seq Scan on fct_order_items f  (cost=0.00..5056.12 rows=1971 width=72) (actual time=0.012..26.052 rows=2033 loops=1)
            Filter: (seller_id = '6560211a19b47992c3666cc44a7e94c0'::text)
            Rows Removed by Filter: 110617
...
Planning Time: 1.285 ms
Execution Time: 109.646 ms
```

Postgres has no way to jump to the matching rows, so it sequentially scans
and discards all 110,617 non-matching rows to find the 2,033 that match:
26.05 ms just for that scan step.

## After: index on every FK column of `fct_order_items`

Added via the model's `indexes` config in
[`dbt/ecommerce/models/marts/fct_order_items.sql`](../dbt/ecommerce/models/marts/fct_order_items.sql)
— one index each on `customer_id`, `product_id`, `seller_id`,
`purchase_date_key`, `delivered_date_key`:

```
->  Hash Join  (cost=1282.89..4487.88 rows=1945 width=52) (actual time=19.296..25.317 rows=2033 loops=1)
      Hash Cond: (f.product_id = dp.product_id)
      ->  Bitmap Heap Scan on fct_order_items f  (cost=27.49..3205.74 rows=1945 width=72) (actual time=0.718..5.124 rows=2033 loops=1)
            Recheck Cond: (seller_id = '6560211a19b47992c3666cc44a7e94c0'::text)
            Heap Blocks: exact=1462
            ->  Bitmap Index Scan on fct_order_items_seller_id_idx  (cost=0.00..27.00 rows=1945 width=0) (actual time=0.422..0.422 rows=2033 loops=1)
                  Index Cond: (seller_id = '6560211a19b47992c3666cc44a7e94c0'::text)
...
Planning Time: 1.423 ms
Execution Time: 100.395 ms
```

The planner switches to a bitmap index scan: it uses the new
`seller_id` index to find exactly the 2,033 matching row locations first,
then fetches only those heap pages. That step drops from 26.05 ms to
5.12 ms — roughly **5x faster** for the part of the query the index
actually targets.

## Why the *total* query time barely moved (109.6 ms -> 100.4 ms)

Indexing `fct_order_items.seller_id` only fixes the scan of
`fct_order_items`. The query's other join, against `dim_customers`
(99,441 rows, un-indexed, no filter to exploit), still costs ~21-26 ms via
a full sequential scan and is now the larger share of total time. This is
the real lesson of the exercise: `EXPLAIN ANALYZE` shows *where* time is
actually spent, and indexing the table you assumed was the bottleneck
doesn't help once a different, unindexed scan becomes the new bottleneck.
(`dim_customers`/`dim_products` weren't indexed here because the task was
scoped to the fact table's foreign keys, per the project spec.)

## Takeaway

- Index columns that are actually filtered on with reasonable selectivity
  (here, `seller_id` narrows to ~1.8% of rows) -- an index on a column
  that returns most of the table gets ignored by the planner anyway, since
  a sequential scan is cheaper once the filter isn't selective.
- One index fixes one scan, not a whole query. Re-run `EXPLAIN ANALYZE`
  after each change instead of assuming the job is done.
