# Public demo deployment

## Target and request flow

`leadpulse.docodigoadecisao.com.br` must resolve in DNS to the infrastructure that
hosts the service. No provider or IP address is assumed by this repository.

```text
Browser → HTTPS → Caddy → Streamlit :8501 → read-only PostgreSQL semantic layer
```

Caddy is the only internet-facing service. It obtains and renews the TLS
certificate automatically after the hostname resolves to the host and ports 80
and 443 are reachable. Streamlit is exposed only to the private Compose network.
PostgreSQL is external to this Compose file and must be reachable only on a
private network or an infrastructure firewall allowlist.

## Required deployment inputs

- a host with Docker Engine and Compose;
- DNS control for `leadpulse.docodigoadecisao.com.br`;
- inbound TCP 80/443 for Caddy;
- a private PostgreSQL endpoint populated by the release dbt models;
- a secret-store value for the `demo_reader` password;
- `POSTGRES_DB`, `POSTGRES_USER=demo_reader`, `POSTGRES_PASSWORD`,
  `POSTGRES_HOST` and optionally `POSTGRES_PORT` in the deployment environment.

Do not copy a local `.env` into the image. Inject production values from the host
or its secret manager, then start the stack:

```sh
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

## Database permission contract

Run [`deploy/postgres/public-demo-reader.sql`](../../deploy/postgres/public-demo-reader.sql)
as an administrator after `dbt run`, and set the role password out of band. The
role is read-only, has no raw or staging grants, and receives column-level SELECT
only for the four semantic marts consumed by the app.

`mart_downstream_performance` has the governed grain purchase month × origin ×
seller × order. The dashboard never renders seller or order identifiers.
`seller_key` is excluded from both its query and the production grant. `order_id`
is retained only inside the private server-to-database path so the app can preserve
the contractually required globally distinct order count (4,457); it is never sent
to a browser or public endpoint. An aggregate public view was intentionally not
introduced because it would change distinct-order behavior for multi-origin
filters.

Verify the effective role before publication:

```sql
SET ROLE demo_reader;
SHOW transaction_read_only;
SELECT * FROM raw.olist_orders LIMIT 1; -- must fail
SELECT * FROM staging.stg_olist_orders LIMIT 1; -- must fail
SELECT seller_key FROM analytics.mart_downstream_performance LIMIT 1; -- must fail
SELECT order_id FROM analytics.mart_downstream_performance LIMIT 1; -- allowed server-side only
RESET ROLE;
```

## Operations and acceptance

Check `https://leadpulse.docodigoadecisao.com.br/_stcore/health`, load every
navigation section, confirm that no database error detail reaches the browser,
and capture the three screenshots listed in `docs/assets/README.md`. Backups,
database patching, host monitoring and log retention belong to the chosen hosting
infrastructure and must be defined before go-live.
