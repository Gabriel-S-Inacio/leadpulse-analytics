# MVP Physical Data Platform

## Purpose and boundary

The MVP runs one PostgreSQL database through Docker Compose, loads source snapshots with Python, and transforms them with dbt. The implemented surface covers the MQL/Closed Deals funnel and the Sellers/Orders/Order Items commerce core through staging. It does not implement approved dimensions/facts, lifecycle logic, orchestration, dashboards, or synthetic spend.

## PostgreSQL schemas

| Schema | Responsibility |
| --- | --- |
| `raw` | Source-shaped ingested data with minimal technical handling and load lineage. |
| `staging` | Type normalization, consistent names, and technical source rules. |
| `analytics` | Approved dimensional models and consumption-ready marts. |

No `intermediate` schema is created because the implemented slices have no reusable multi-model transformation that justifies it.

Schemas are bootstrapped by `docker/postgres/init/001_create_schemas.sql` through PostgreSQL's `docker-entrypoint-initdb.d` mechanism. This is the simplest reproducible option for a new local named volume; no migration framework is justified at this stage.

## Raw naming contract

Raw relations use lowercase snake_case, retain the source entity name without the source file's `_dataset` suffix, and are qualified by `raw`:

- `raw.olist_marketing_qualified_leads`
- `raw.olist_closed_deals`
- `raw.olist_sellers`
- `raw.olist_orders`
- `raw.olist_order_items`
- `raw.olist_customers`
- `raw.olist_order_payments`

Five raw relations are implemented: `raw.olist_marketing_qualified_leads`, `raw.olist_closed_deals`, `raw.olist_sellers`, `raw.olist_orders`, and `raw.olist_order_items`.

## Implemented vertical slices

The contract-driven loader preserves every declared source column at source shape. It supports Marketing Funnel (MQL and Closed Deals) and Commerce Core (Sellers, Orders, and Order Items) through one source-selecting CLI. Each raw table adds only:

- `_loaded_at`: UTC timestamp of the successful load;
- `_source_file`: source basename, never a personal path;
- `_source_sha256`: content checksum for reproducibility and lineage.

The static Kaggle snapshots use transactional `TRUNCATE + reload`. Table creation, locking, truncation, copy, and row-count validation occur in one transaction, so a failed load rolls back and a repeated successful load replaces rather than duplicates rows. `mql_id` is the controlled raw primary key for both implemented sources. The observed Closed Deals `seller_id` uniqueness is revalidated in dbt, not treated as a timeless source invariant.

## Analytics foundation

The partially implemented analytics layer materializes `dim_date`, `dim_origin`, `dim_seller`, `fct_mql`, `fct_closed_deal`, and the central transaction fact `fct_order_item` as PostgreSQL tables. Full rebuilds are deterministic and small enough for the local MVP, so incremental materialization is not justified yet.

Dimension keys are deterministic: calendar dates use `YYYYMMDD` integers with reserved negative technical keys, while origin and seller members use namespaced content hashes. `dim_origin` distinguishes missing, explicit unknown, unrecognized, and not-applicable states. `dim_seller` is the governed union of funnel and e-commerce sellers, preserving funnel-only identities without invented geography.

`fct_order_item` remains at `(order_id, order_item_id)` grain. Eligible GMV is item `price` only for delivered, acquired-seller items purchased strictly after `won_timestamp`; all other observed items contribute zero. Freight and payment values are excluded, and Order counts require distinct `order_id` rather than summed item rows. Lifecycle, synthetic spend, dashboards, and other consumption models are not implemented.

One preserved Closed Deals source row has `won_date` two calendar days before its linked MQL `first_contact_date`. `fct_closed_deal.temporal_quality_status` classifies it as `INVALID_SEQUENCE`; all other rows are `VALID`. A governed dbt exception test fingerprints the known anonymized identifiers and dates, so any new, removed, or changed exception fails without inventing a corrected timestamp or dropping one of the 842 source rows.

## dbt foundation

The versioned profile contains only `env_var` references. Local credentials live in ignored `.env`/process environment state. The custom schema macro maps the staging model to the exact `staging` schema rather than a prefixed development schema.

The current dbt surface contains only:

```text
transform/
├── dbt_project.yml
├── profiles.yml
├── macros/
│   └── generate_schema_name.sql
├── models/
│   ├── staging/
│   └── marts/
└── tests/
```

Source freshness is intentionally absent. The Olist file is a historical static snapshot without a production arrival SLA.

## Security and operational boundary

- Docker publishes PostgreSQL only on loopback at the configured local port.
- The named volume is managed by Docker and is not stored in the repository.
- `.env`, raw datasets, dbt targets, packages, and logs are ignored.
- No credential appears in Compose, dbt profile, Python source, or versioned documentation.
- Future raw tables should follow this vertical slice only after their source contracts and row-count checks are carried forward explicitly.
