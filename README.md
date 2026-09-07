# LeadPulse Analytics

LeadPulse Analytics é uma iniciativa de Analytics Engineering, Data Engineering e Business Intelligence para consolidar dados de marketing e CRM em uma visão confiável do desempenho comercial.

## Problema de negócio

Dados de campanhas, leads, oportunidades e vendas costumam permanecer fragmentados entre plataformas, dificultando a atribuição de receita, a comparação entre canais e o acompanhamento do funil.

## Objetivo

Construir uma base analítica consistente que conecte investimento em marketing à evolução dos leads e à receita gerada, com métricas rastreáveis e definições compartilhadas.

## Perguntas de negócio

- Quais canais e campanhas geram receita?
- Qual é o CAC e o CPL por canal e campanha?
- Quais são as taxas de conversão entre as etapas do funil?
- Qual é o ROAS e o ROI das iniciativas de marketing?
- Como leads evoluem até oportunidades e vendas?

## Visão preliminar da arquitetura

Fontes de marketing e CRM alimentarão uma camada de ingestão. Os dados brutos serão transformados e modelados para consumo por uma camada analítica, dashboards e, se necessário, APIs. Esta visão é conceitual e será refinada por decisões arquiteturais registradas.

## Status

**Business Domain / Source Alignment** — o domínio e os contratos semânticos estão sendo alinhados às fontes escolhidas; nenhuma funcionalidade do produto está implementada.

## Fontes planejadas para o MVP

- **Dados reais:** Olist Marketing Funnel e Olist Brazilian E-Commerce.
- **Dados sintéticos controlados:** Advertising Spend, sempre identificado como sintético e nunca apresentado como dado observado da Olist.

## Documentação de domínio

- [Modelo de domínio](docs/business/domain-model.md)
- [Modelo de atribuição](docs/business/attribution-model.md)
- [Contrato de KPIs](docs/business/kpi-contract.md)

## Roadmap macro

1. Discovery, glossário de negócio e decisões arquiteturais.
2. Contratos de dados e estratégia de ingestão.
3. Modelagem, qualidade e métricas analíticas.
4. Camada de consumo e visualização.
5. Observabilidade, automação e operação.

## Stack planejada

As candidatas incluem Python 3.12+, SQL, armazenamento analítico, ferramenta de transformação, orquestração, BI, contêineres e CI/CD. Todas estão **sujeitas a validação arquitetural**; nenhuma escolha tecnológica além da fundação Python deste repositório é definitiva nesta etapa.
