# Data directory

## `raw/` — Olist dataset (not committed)

RootLens uses the **Olist Brazilian E-Commerce Public Dataset**:
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

This repository does not redistribute the dataset. To set it up locally:

1. Create a Kaggle account and accept the dataset's terms on the page above.
2. Download the dataset (via the website, or the `kaggle` CLI with your own
   API token: `kaggle datasets download -d olistbr/brazilian-ecommerce`).
3. Unzip the CSVs directly into `data/raw/` (this directory is gitignored
   except for `.gitkeep`). Expected files:
   - `olist_customers_dataset.csv`
   - `olist_orders_dataset.csv`
   - `olist_order_items_dataset.csv`
   - `olist_order_payments_dataset.csv`
   - `olist_order_reviews_dataset.csv`
   - `olist_products_dataset.csv`
   - `olist_sellers_dataset.csv`
   - `olist_geolocation_dataset.csv`
   - `product_category_name_translation.csv`
4. Run `make ingest SOURCE=data/raw` to load them into Postgres.

## `fixtures/` — golden test data (committed)

A small, hand-authored subset of Olist-shaped CSVs plus
`expected_metrics.json` (hand-computed KPI values). Used by the automated
test suite so CI never depends on the full licensed dataset. Loaded via
`make ingest-fixtures`.

## `scenarios/` — incident benchmark scenarios (Milestone 5, not yet used)

Empty placeholder. Populated when the incident-injection and evaluation
runner work (Milestone 5) begins.
