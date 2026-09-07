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

**Source Contracts / Semantic Freeze** — o profiling empírico das fontes Olist foi concluído e as regras analíticas do MVP foram congeladas para orientar a futura modelagem dimensional; nenhuma transformação analítica ou funcionalidade do produto está implementada.

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

Datasets raw permanecem locais em `data/raw/` e não são versionados pelo Git.

## Roadmap macro

1. Discovery, glossário de negócio e decisões arquiteturais.
2. Contratos de dados e estratégia de ingestão.
3. Modelagem, qualidade e métricas analíticas.
4. Camada de consumo e visualização.
5. Observabilidade, automação e operação.

## Stack planejada

As candidatas incluem Python 3.12+, SQL, armazenamento analítico, ferramenta de transformação, orquestração, BI, contêineres e CI/CD. Todas estão **sujeitas a validação arquitetural**; nenhuma escolha tecnológica além da fundação Python deste repositório é definitiva nesta etapa.
