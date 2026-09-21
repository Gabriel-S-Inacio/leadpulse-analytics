# LeadPulse Analytics

Produto analítico de portfólio que conecta aquisição, ativação e desempenho de
vendedores em uma camada semântica governada e um dashboard executivo.

Desenvolvido para o portfólio **Do Código à Decisão**, o projeto utiliza dados
públicos da Olist e um cenário de investimento de marketing explicitamente
simulado.

## O problema

Leads, aquisição de vendedores e pedidos acontecem em momentos e fontes diferentes.

Sem contratos claros de dados, torna-se difícil responder perguntas como:

- quantos leads se tornaram vendedores;
- quantos vendedores começaram efetivamente a vender;
- quanto GMV esses vendedores geraram;
- quais origens apresentaram melhor desempenho;
- como um cenário de investimento em marketing se relaciona com esses resultados.

O projeto estrutura essas informações sem confundir associação com causalidade.

## A solução

O LeadPulse implementa um pipeline analítico completo:

1. ingestão de dados públicos da Olist com Python;
2. persistência em PostgreSQL;
3. transformação e testes com dbt;
4. modelagem dimensional com dimensões e fatos;
5. criação de marts semânticos orientados ao negócio;
6. dashboard executivo desenvolvido em Streamlit.

A interface apresenta o funil de aquisição, ativação dos vendedores em 90 dias,
pedidos, GMV e indicadores de eficiência de marketing, com filtros por período,
origem e canal.

## Principais resultados

- **8.000** leads qualificados;
- **842** vendedores adquiridos;
- **10,53%** de conversão de lead para vendedor;
- **42,15%** de taxa de ativação entre vendedores com janela completa de 90 dias;
- **4.457** pedidos realizados por vendedores adquiridos;
- **R$ 664,9 mil** de GMV observado;
- **R$ 333,1 mil** de investimento no cenário sintético de marketing.

> O investimento de marketing é simulado e não representa gasto observado da Olist.

## Arquitetura

```mermaid
flowchart LR
    A[Dados públicos Olist] --> B[Ingestão Python]
    B --> C[(PostgreSQL RAW)]
    C --> D[dbt staging]
    D --> E[Dimensões e fatos]
    E --> F[Marts semânticos]
    F --> G[Dashboard Streamlit]
