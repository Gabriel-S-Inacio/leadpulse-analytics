# System Context

## Propósito

O LeadPulse Analytics ocupará a fronteira entre sistemas operacionais de marketing e CRM e os consumidores de informação analítica. Este documento apresenta somente o contexto conceitual inicial.

## Fluxo conceitual

```text
Marketing Sources        CRM Sources
         \                  /
          \                /
             Data Ingestion
                    |
                Raw Data
                    |
       Transformation / Modeling
                    |
             Analytics Layer
                    |
              Dashboard / API
```

## Responsabilidades conceituais

- **Fontes:** produzir dados operacionais de campanhas, custos, leads e eventos comerciais.
- **Ingestão:** transportar dados preservando rastreabilidade e contexto de origem.
- **Dados brutos:** manter uma representação auditável do que foi recebido.
- **Transformação e modelagem:** padronizar, relacionar e aplicar regras de negócio aprovadas.
- **Camada analítica:** disponibilizar entidades e métricas consistentes para consumo.
- **Consumo:** apoiar análises e decisões por dashboards e, se necessário, APIs.

## Limites e decisões em aberto

Tecnologias, padrões de integração, frequência de atualização, estratégia de identidade, método de atribuição e plataforma de consumo ainda serão avaliados. Python, SQL, ferramentas de transformação, armazenamento analítico e orquestração são candidatos, não decisões consolidadas.
