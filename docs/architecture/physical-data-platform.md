# MVP Physical Data Platform

## Purpose and boundary

The MVP runs one PostgreSQL database through Docker Compose, loads source snapshots with Python, and transforms them with dbt. This foundation proves the MQL and Closed Deals funnel paths; it does not implement the remaining approved dimensions/facts, orchestration, dashboards, or synthetic spend.

## PostgreSQL schemas

| Schema | Responsibility |
| --- | --- |
| `raw` | Source-shaped ingested data with minimal technical handling and load lineage. |
| `staging` | Type normalization, consistent names, and technical source rules. |
| `analytics` | Approved dimensional models and consumption-ready marts. |

No `intermediate` schema is created because the first slice has no reusable multi-model transformation that justifies it.

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

Only `raw.olist_marketing_qualified_leads` and `raw.olist_closed_deals` are implemented in the current funnel slices.

## Funnel vertical slices

The contract-driven loader preserves every declared source column at source shape. MQL retains its four source columns, while Closed Deals retains all 14 source columns. Each raw table adds only:

- `_loaded_at`: UTC timestamp of the successful load;
- `_source_file`: source basename, never a personal path;
- `_source_sha256`: content checksum for reproducibility and lineage.

The static Kaggle snapshots use transactional `TRUNCATE + reload`. Table creation, locking, truncation, copy, and row-count validation occur in one transaction, so a failed load rolls back and a repeated successful load replaces rather than duplicates rows. `mql_id` is the controlled raw primary key for both implemented sources. The observed Closed Deals `seller_id` uniqueness is revalidated in dbt, not treated as a timeless source invariant.

## dbt foundation

The versioned profile contains only `env_var` references. Local credentials live in ignored `.env`/process environment state. The custom schema macro maps the staging model to the exact `staging` schema rather than a prefixed development schema.

The current dbt surface contains only:

```text
transform/
├── dbt_project.yml
├── profiles.yml
├── macros/
│   └── generate_schema_name.sql
└── models/
    └── staging/
        ├── _olist_sources.yml
        ├── _staging_models.yml
        ├── stg_olist_closed_deals.sql
        └── stg_olist_marketing_qualified_leads.sql
```

Source freshness is intentionally absent. The Olist file is a historical static snapshot without a production arrival SLA.

## Security and operational boundary

- Docker publishes PostgreSQL only on loopback at the configured local port.
- The named volume is managed by Docker and is not stored in the repository.
- `.env`, raw datasets, dbt targets, packages, and logs are ignored.
- No credential appears in Compose, dbt profile, Python source, or versioned documentation.
- Future raw tables should follow this vertical slice only after their source contracts and row-count checks are carried forward explicitly.
