# LeadPulse Analytics

LeadPulse Analytics é uma iniciativa de Analytics Engineering, Data Engineering e Business Intelligence para consolidar dados de marketing e CRM em uma visão confiável do desempenho comercial.

## Problema de negócio

Dados de campanhas, leads, oportunidades e vendas costumam permanecer fragmentados entre plataformas, dificultando a atribuição de receita, a comparação entre canais e o acompanhamento do funil.

## Objetivo

Construir uma base analítica consistente que conecte cenários de investimento em marketing à aquisição de sellers e ao GMV downstream, com métricas rastreáveis e definições compartilhadas.

## Perguntas de negócio

- Quais origens e canais estão associados à aquisição de sellers e ao GMV downstream?
- Qual é o CPL e o Seller Acquisition Cost em cenários sintéticos claramente identificados?
- Qual é a conversão de MQL para AcquiredSeller e a ativação em 90 dias?
- Qual é o GMV ROAS dos cenários controlados, sem confundi-lo com retorno contábil?
- Como MQLs evoluem até ClosedDeals, AcquiredSellers e atividade entregue no marketplace?

## Visão preliminar da arquitetura

Fontes de marketing e CRM alimentarão uma camada de ingestão. Os dados brutos serão transformados e modelados para consumo por uma camada analítica, dashboards e, se necessário, APIs. Esta visão é conceitual e será refinada por decisões arquiteturais registradas.

## Status

**Data Platform Foundation** — os slices executáveis validam MQL, Closed Deals, Sellers, Orders e Order Items de CSV → PostgreSQL raw → dbt staging. As tabelas dimensionais analíticas continuam fora desta etapa.

## Fontes planejadas para o MVP

- **Dados reais:** Olist Marketing Funnel e Olist Brazilian E-Commerce.
- **Dados sintéticos controlados:** Advertising Spend, sempre identificado como sintético e nunca apresentado como dado observado da Olist.

## Documentação de domínio

- [Modelo de domínio](docs/business/domain-model.md)
- [Modelo de atribuição](docs/business/attribution-model.md)
- [Contrato de KPIs](docs/business/kpi-contract.md)
- [Semântica analítica do MVP](docs/business/analytics-semantics.md)

## Documentação de fontes

- [Manifesto de fontes](docs/data/source-manifest.md)
- [Contratos das fontes](docs/data/source-contracts.md)
- [Contratos de dados analíticos](docs/data/analytics-data-contracts.md)

## Documentação de arquitetura

- [Modelo dimensional conceitual](docs/architecture/dimensional-model.md)
- [Schema lógico analítico](docs/architecture/logical-schema.md)
- [Plataforma física de dados](docs/architecture/physical-data-platform.md)
- [ADR 0001 — estratégia do modelo dimensional](docs/decisions/0001-dimensional-model-strategy.md)

Datasets raw permanecem locais em `data/raw/` e não são versionados pelo Git.

## Desenvolvimento local — ingestão e staging

Os comandos abaixo partem da raiz do repositório e usam somente o ambiente virtual local.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,data]"
Copy-Item .env.example .env
```

Revise a senha de desenvolvimento em `.env` e carregue as variáveis na sessão atual:
Se a porta 5432 não estiver disponível, altere somente `POSTGRES_PORT` no `.env` local.

```powershell
Get-Content .env | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
    $name, $value = $_.Split('=', 2)
    Set-Item -Path "Env:$name" -Value $value
}
```

Suba e valide o PostgreSQL, carregue os snapshots implementados e execute o staging dbt:

```powershell
docker compose up -d postgres
docker compose ps
python -m leadpulse.ingestion mql
python -m leadpulse.ingestion closed-deals
python -m leadpulse.ingestion sellers
python -m leadpulse.ingestion orders
python -m leadpulse.ingestion order-items
dbt debug --project-dir transform --profiles-dir transform
dbt run --project-dir transform --profiles-dir transform --select path:models/staging
dbt test --project-dir transform --profiles-dir transform --select path:models/staging
```

Valide os testes Python e, opcionalmente, as contagens no PostgreSQL:

```powershell
python -m unittest discover -s tests -v
docker compose exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT COUNT(*) FROM raw.olist_marketing_qualified_leads;"
docker compose exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT COUNT(*) FROM raw.olist_closed_deals;"
docker compose exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT COUNT(*) FROM raw.olist_sellers;"
docker compose exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT COUNT(*) FROM raw.olist_orders;"
docker compose exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT COUNT(*) FROM raw.olist_order_items;"
docker compose exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT COUNT(*) FROM staging.stg_olist_marketing_qualified_leads;"
docker compose exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT COUNT(*) FROM staging.stg_olist_closed_deals;"
```

## Roadmap macro

1. Discovery, glossário de negócio e decisões arquiteturais.
2. Contratos de dados e estratégia de ingestão.
3. Modelagem, qualidade e métricas analíticas.
4. Camada de consumo e visualização.
5. Observabilidade, automação e operação.

## Stack planejada

As candidatas incluem Python 3.12+, SQL, armazenamento analítico, ferramenta de transformação, orquestração, BI, contêineres e CI/CD. Todas estão **sujeitas a validação arquitetural**; nenhuma escolha tecnológica além da fundação Python deste repositório é definitiva nesta etapa.
