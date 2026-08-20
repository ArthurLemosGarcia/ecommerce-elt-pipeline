# Build Spec — E-commerce ELT & Analytics Pipeline

> This document is a build specification for an AI coding agent (Claude Code).
> Follow it phase by phase. Ask before installing anything with side effects
> outside the project folder. Generate all code, comments, commit messages,
> and documentation in **English**.

---

## 1. What you are building

An end-to-end **ELT data pipeline** on top of a public e-commerce dataset:
raw ingestion → PostgreSQL → dbt transformations into a **star schema** →
**data quality tests** → a small analytics layer that answers one business
question.

This is a portfolio project. Optimize for three things, in order:
1. **Clean dimensional modeling** (star schema, correct grain, normalized dims).
2. **Data quality** (explicit, documented tests).
3. **Clear business framing** (the README leads with a business problem, not the stack).

## 2. Business framing (use this narrative everywhere)

Frame the project around this problem, not around technology:

> An e-commerce operation is losing revenue and reputation to late deliveries,
> and its sales data is fragmented across many source tables, making it hard to
> answer basic operational questions reliably.

The pipeline exists to **consolidate** that fragmented data into a trustworthy,
tested model, and then answer: **"How do delivery delays affect customer review
scores, broken down by product category and region?"**

## 3. Tech stack (fixed)

- **Language:** Python 3.11+ (ingestion/load), SQL (transforms).
- **Database:** PostgreSQL. **Run it locally by default** (Docker Compose or a
  local install). Nothing needs to be exposed to the internet.
  - *Optional:* if a live hosted demo is wanted later, the same code should work
    against a hosted Postgres (e.g. Supabase/Neon) by only changing the
    connection string. Do not require this.
- **Transformation:** dbt (`dbt-postgres`).
- **Ingestion:** Python + `pandas` + `SQLAlchemy`.
- **Analytics app:** Streamlit, run locally. Its output (charts) is captured as
  screenshots/GIF for the README. Do not deploy anything.
- **Data model diagram:** produce a Mermaid ER diagram in the README (no external
  tool needed).
- **Version control:** git. English commit messages, small and logical commits.

Keep dependencies minimal and pinned in `requirements.txt`. Use a Python virtual
environment. Provide a `docker-compose.yml` for Postgres so setup is one command.
**Pin the Postgres image to an explicit major version (e.g. `postgres:16`), never
`latest`**, so the environment is reproducible over time.

## 4. Data source

- **Dataset:** Olist Brazilian E-Commerce Public Dataset (Kaggle,
  `olistbr/brazilian-ecommerce`). ~9 CSV files (orders, order_items, customers,
  products, sellers, payments, reviews, geolocation, category translation).
- The user will place the CSVs in `data/raw/`. Do **not** attempt to download
  from Kaggle automatically; read whatever CSVs are present in that folder.
- Handle the dataset being messy: nullable dates, duplicate geolocation rows,
  Portuguese category names (there is a translation file — use it).

## 5. Repository structure (target)

```
.
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example                # connection vars, no secrets committed
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml              # CI: spins up Postgres, runs dbt build + test
├── data/
│   └── raw/                    # user drops Olist CSVs here (gitignored)
├── ingestion/
│   └── load_raw.py             # CSV -> Postgres schema `raw`
├── dbt/
│   └── ecommerce/              # dbt project
│       ├── dbt_project.yml
│       ├── models/
│       │   ├── staging/        # stg_*.sql + schema.yml (tests + docs)
│       │   └── marts/          # dim_*.sql, fct_*.sql + schema.yml
│       └── ...
├── app/
│   └── streamlit_app.py        # reads from marts, answers the business question
└── docs/
    ├── optimization.md         # EXPLAIN ANALYZE before/after an index
    └── governance.md           # PII handling & data governance notes
```

## 6. Ingestion (`ingestion/load_raw.py`)

- Read each CSV in `data/raw/` and load it into a `raw` schema in Postgres, one
  table per file, column names snake_cased, types inferred sensibly.
- Idempotent: re-running replaces the raw tables cleanly.
- Print a small summary (table name + row count) so the load is verifiable.
- Connection details come from environment variables (see `.env.example`).

## 7. Data model (target star schema)

Grain of the fact table is **one row per item per order**.

| Model             | Type      | Grain / notes                                             |
|-------------------|-----------|-----------------------------------------------------------|
| `fct_order_items` | Fact      | One row per order item. Measures: price, freight, delivery time (days), is_late flag. FKs to all dims. |
| `dim_customers`   | Dimension | One row per customer. Includes state/region.              |
| `dim_products`    | Dimension | One row per product. Includes English category name.      |
| `dim_sellers`     | Dimension | One row per seller. Includes state/region.                |
| `dim_dates`       | Dimension | One row per calendar date used by the fact (purchase, delivery). Standard date attributes. |

Derive delivery metrics in the model: actual delivery time, estimated vs actual,
and a boolean `is_late` (delivered after the estimated date). These power the
business question.

## 8. dbt layer

**Staging (`models/staging/`)** — one `stg_<source>.sql` per raw table. Only
cleaning here: rename columns, cast types, drop obvious junk, deduplicate
geolocation. No business logic.

**Marts (`models/marts/`)** — build the dims and the fact using `ref()`. This is
where delivery metrics and the star schema are assembled.

**Tests (in `schema.yml`)** — these are a headline feature, make them explicit
and documented:
- `not_null` + `unique` on every dimension primary key and the fact's surrogate key.
- `relationships` from `fct_order_items` FKs to each dimension (referential integrity).
- `accepted_values` on `order_status`.
- At least one **singular test** (custom SQL) that encodes a real rule, e.g.
  delivered date is not earlier than purchase date, and price is non-negative.
- Add `description:` fields so `dbt docs` renders a meaningful data dictionary.

**Docs** — the build should support `dbt docs generate`; mention this in the README.

## 9. Performance task (`docs/optimization.md`)

Demonstrate optimization awareness:
- Pick a representative join query (fact + a couple of dims, filtered/grouped).
- Run `EXPLAIN ANALYZE` **before** adding indexes; record the plan/time.
- Add indexes on the fact's foreign-key columns.
- Run `EXPLAIN ANALYZE` **after**; record the improvement.
- Write both results into `docs/optimization.md` with a short explanation.

## 10. Analytics app (`app/streamlit_app.py`)

- Connects to the marts and answers the business question with 2–3 charts:
  late-delivery rate by product category, and its relationship to average review
  score, sliced by customer region.
- Runs locally (`streamlit run`). Keep it simple and readable.
- The README shows this via screenshots/GIF; no deployment.

## 11. Version control workflow (part of scope, not optional)

Work in a Git flow that demonstrates real collaboration habits, not a single
dump on `main`:
- One branch per phase (e.g. `feat/phase-1-ingestion`, `feat/phase-2-modeling`,
  `feat/phase-3-presentation`).
- Merge each branch into `main` through a **Pull Request** with a short
  description of what it delivers. Squash or keep clean, logical commits.
- Commit messages in English, imperative mood (e.g. "Add referential-integrity
  tests to fact table").
- `main` should always be in a working state.

## 12. Data governance & PII (`docs/governance.md`)

The dataset contains customer-level data (location, zip code prefixes), so treat
governance as a first-class concern:
- In a staging model, **anonymize or hash the customer identifier** so downstream
  models never expose a raw personal ID. Document why.
- Keep any location data at an aggregated grain (e.g. state/region), not
  precise geolocation, in the marts used for analytics.
- Write `docs/governance.md` covering: what PII exists in the source, how it is
  masked/handled in the pipeline, and a short note on access-control practices
  you would apply in a production/cloud setting (least privilege, column masking).
- Reference this section briefly in the README.

## 13. Continuous Integration (`.github/workflows/ci.yml`)

Automate the quality checks so they run on every push — this mirrors how data
pipelines are validated in production:
- A GitHub Actions workflow that: spins up a Postgres **service container**,
  loads a small sample of the data (or seeds), runs `dbt build` and `dbt test`.
- The workflow must **fail if any dbt test fails**.
- Add a CI **status badge** to the top of the README.
- Keep it lightweight and fast; use a data sample if the full load is too slow in CI.

## 14. README (English) — required sections, in this order

0. **CI status badge** at the very top of the README (GitHub Actions).
1. **Business problem** — the narrative from section 2. Lead with this, not the stack.
2. **Architecture** — a Mermaid diagram of the flow (CSV → raw → dbt staging →
   marts → app) and a Mermaid ER diagram of the star schema.
3. **Data model** — the dims/fact table and a short justification of the star
   schema choice.
4. **Data quality** — list each test category and, in one line each, what it
   protects. Note that these tests also run automatically in CI on every push.
5. **Data governance** — a short paragraph on PII handling (link to
   `docs/governance.md`): what is masked and why.
6. **A design-tradeoff note** titled *"Why a star schema and not a Data Vault?"* —
   two or three sentences: Data Vault favors auditability and agile ingestion from
   many changing sources; a star schema optimizes read/BI consumption, which is the
   goal here. (Keep it only if it reads naturally; it should not feel like keyword-stuffing.)
7. **How to run** — prerequisites, the docker-compose command, load, dbt run, dbt
   test, streamlit run. Reproducible from a clean clone.
8. **Results** — the charts (screenshots/GIF) and the answer to the business question.

## 15. Constraints — do NOT

- Do **not** mention any specific company, employer, or job posting anywhere in
  the repo. This is a generic, standalone portfolio project.
- Do **not** deploy anything or require internet access to run the pipeline.
- Do **not** over-scope: no extra data sources, no orchestration tool, no
  additional dashboards beyond what answers the one business question. A finished,
  tested, well-documented project beats an ambitious half-built one.
- Do **not** commit secrets or the raw data CSVs (`.gitignore` them).

## 16. Build order (phased)

Each phase is developed on its own branch and merged to `main` via a Pull
Request (see section 11).

**Phase 1 — Foundation** (branch `feat/phase-1-ingestion`)
- Repo scaffold, `.gitignore`, `requirements.txt`, `docker-compose.yml` for Postgres
  (pin an explicit version such as `postgres:16`, not `latest`), `.env.example`.
- `ingestion/load_raw.py` loading CSVs into the `raw` schema, with a row-count summary.

**Phase 2 — Model & quality** (branch `feat/phase-2-modeling`)
- dbt project init and connection.
- Staging models for all sources, including customer-ID anonymization (section 12).
- Marts: the four dims + `fct_order_items` with delivery metrics.
- All tests from section 8, passing.
- `docs/optimization.md` with the before/after EXPLAIN ANALYZE.
- `docs/governance.md` with PII handling notes.
- `.github/workflows/ci.yml` running `dbt build` + `dbt test` on push.

**Phase 3 — Presentation** (branch `feat/phase-3-presentation`)
- `app/streamlit_app.py` answering the business question.
- README with every section from section 14, including Mermaid diagrams and the CI badge.
- Final pass: clean history, PRs merged, verify a clean clone runs end to end.

## 17. Definition of done (acceptance checklist)

- [ ] `docker compose up` brings up Postgres (pinned version); `load_raw.py` populates the `raw` schema.
- [ ] `dbt run` builds staging + marts (4 dims + 1 fact) into a star schema.
- [ ] `dbt test` passes, including `relationships` and at least one singular test.
- [ ] Customer identifier is anonymized in staging; `docs/governance.md` explains PII handling.
- [ ] `docs/optimization.md` shows a real before/after EXPLAIN ANALYZE.
- [ ] GitHub Actions CI runs `dbt build` + `dbt test` on push and fails on a broken test; badge is green in the README.
- [ ] Work was done across per-phase branches merged via Pull Requests; `main` is clean and working.
- [ ] Streamlit app runs locally and answers the delivery-vs-reviews question.
- [ ] README (English) leads with the business problem and includes both Mermaid diagrams, the data-quality and governance sections, and results.
- [ ] No company name anywhere; no secrets or raw CSVs committed; clean clone runs end to end.
