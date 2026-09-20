"""LeadPulse Analytics executive dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, cast

import pandas as pd
import plotly.express as px  # type: ignore[import-untyped]
import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st

from leadpulse.dashboard.data import DashboardData, MartRepository
from leadpulse.dashboard.errors import classify_dashboard_error
from leadpulse.dashboard.filters import (
    MISSING_ORIGIN_LABEL,
    apply_filters,
    channel_labels,
    origin_labels,
)
from leadpulse.dashboard.formatting import (
    format_brl,
    format_days,
    format_decimal,
    format_integer,
    format_percent,
    format_roas,
)
from leadpulse.dashboard.metrics import (
    acquisition_summary,
    activation_summary,
    downstream_summary,
    group_acquisition,
    group_activation,
    group_downstream,
    group_marketing,
    marketing_summary,
)


@dataclass(frozen=True)
class PageMetadata:
    navigation_label: str
    title: str
    eyebrow: str
    description: str


PAGES = {
    "overview": PageMetadata(
        navigation_label="Visão geral",
        title="Visão geral executiva",
        eyebrow="Resumo do negócio",
        description="Resumo do funil de aquisição, ativação, vendas e eficiência de marketing.",
    ),
    "acquisition": PageMetadata(
        navigation_label="Aquisição",
        title="Aquisição de vendedores",
        eyebrow="Funil de aquisição",
        description="Como os leads avançam pelo funil até se tornarem vendedores.",
    ),
    "activation": PageMetadata(
        navigation_label="Ativação",
        title="Ativação dos vendedores",
        eyebrow="Primeiros 90 dias",
        description="Quanto tempo os vendedores levam para começar a vender após a aquisição.",
    ),
    "marketing": PageMetadata(
        navigation_label="Eficiência de marketing",
        title="Eficiência de marketing",
        eyebrow="Cenário simulado",
        description="Comparação entre investimento simulado, aquisição e GMV gerado.",
    ),
    "downstream": PageMetadata(
        navigation_label="Desempenho após aquisição",
        title="Desempenho após aquisição",
        eyebrow="Resultado comercial",
        description="Pedidos e GMV gerados pelos vendedores adquiridos pelo funil.",
    ),
}
PAGE_BY_NAVIGATION = {page.navigation_label: page_id for page_id, page in PAGES.items()}

KPI_HELP = {
    "Leads qualificados": "Quantidade de leads que entraram no funil de aquisição.",
    "Negócios fechados": "Leads que avançaram até um negócio fechado.",
    "Vendedores adquiridos": "Vendedores que chegaram a um negócio fechado.",
    "Conversão de lead para vendedor": (
        "Percentual de leads qualificados que se tornaram vendedores adquiridos."
    ),
    "Vendedores com janela completa de 90 dias": (
        "Vendedores adquiridos que puderam ser observados por toda a janela de 90 dias."
    ),
    "Vendedores ativados": (
        "Vendedores com janela completa de 90 dias que realizaram a primeira venda "
        "dentro desse período."
    ),
    "Taxa de ativação": (
        "Percentual dos vendedores com janela completa que ativaram em até 90 dias."
    ),
    "Tempo médio até a primeira venda": (
        "Média de dias entre a aquisição e a primeira venda elegível."
    ),
    "Tempo mediano até a primeira venda": (
        "Mediana de dias até a primeira venda; não é combinada entre agrupamentos."
    ),
    "GMV nos primeiros 90 dias": (
        "Soma do valor dos itens vendidos nos primeiros 90 dias; frete não incluído."
    ),
    "GMV por vendedor ativado": (
        "GMV dos primeiros 90 dias dividido pelos vendedores ativados maduros."
    ),
    "Pedidos por vendedor ativado": (
        "Pedidos dos primeiros 90 dias divididos pelos vendedores ativados maduros."
    ),
    "Pedidos de vendedores adquiridos": (
        "Pedidos únicos elegíveis realizados por vendedores adquiridos pelo funil."
    ),
    "GMV dos vendedores adquiridos": (
        "Valor dos itens vendidos por vendedores adquiridos; não é receita corporativa e "
        "não inclui frete."
    ),
    "Investimento de marketing simulado": (
        "Investimento sintético e determinístico para demonstrar a análise."
    ),
    "Custo por lead": (
        "Investimento simulado dividido pelos leads das origens pagas cobertas."
    ),
    "Custo por vendedor adquirido": (
        "Investimento simulado dividido pelos vendedores adquiridos nas origens pagas."
    ),
    "Retorno de GMV sobre investimento": (
        "GMV de 90 dias dividido pelo investimento simulado; métrica não causal."
    ),
    "Participações vendedor–pedido": (
        "Quantidade de combinações entre vendedor e pedido; um pedido pode ter mais de um vendedor."
    ),
}

ORIGIN_LABELS = {
    "direct_traffic": "Tráfego direto",
    "display": "Mídia display",
    "email": "E-mail",
    "organic_search": "Busca orgânica",
    "other": "Outras origens",
    "other_publicities": "Outras mídias pagas",
    "paid_search": "Busca paga",
    "referral": "Indicação",
    "social": "Redes sociais",
    "unknown": "Origem desconhecida",
}
CHANNEL_LABELS = {
    "direct": "Direto",
    "display": "Mídia display",
    "email": "E-mail",
    "organic": "Orgânico",
    "other_paid": "Outras mídias pagas",
    "paid_search": "Busca paga",
    "referral": "Indicação",
    "social": "Redes sociais",
    "unattributed": "Não atribuído",
}

CHART_LABELS = {
    "cohort_month": "Mês de entrada no funil",
    "purchase_month": "Mês da compra",
    "mqls": "Leads",
    "closed_deals": "Negócios fechados",
    "acquired_sellers": "Vendedores adquiridos",
    "conversion_rate": "Conversão",
    "acquired_sellers_mature": "Vendedores com janela completa",
    "activated_sellers_90d": "Vendedores ativados",
    "activation_rate": "Taxa de ativação",
    "avg_time_to_first_order_days": "Dias até a primeira venda",
    "gmv_90d": "GMV em 90 dias",
    "orders_90d": "Pedidos em 90 dias",
    "synthetic_marketing_spend": "Investimento simulado",
    "cpl": "Custo por lead",
    "seller_acquisition_cost": "Custo por vendedor adquirido",
    "gmv_roas": "Retorno de GMV",
    "eligible_gmv": "GMV",
    "orders": "Pedidos únicos",
    "origin_label": "Origem",
    "channel_label": "Canal",
    "metric": "Indicador",
    "value": "Valor",
}
ACTIVATION_CHART_LABELS = {**CHART_LABELS, "cohort_month": "Mês da aquisição"}
ACCENT = "#2DD4BF"
SECONDARY = "#60A5FA"
TERTIARY = "#F59E0B"
MUTED = "#94A3B8"


@st.cache_data(ttl=300, show_spinner="Carregando indicadores...")
def load_dashboard_data() -> DashboardData:
    return MartRepository.from_env().fetch_all()


def configure_page() -> None:
    st.set_page_config(
        page_title="LeadPulse Analytics",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .stApp { background: #0B1020; }
        h1, h2, h3 { letter-spacing: -0.02em; }
        .lp-kicker {
            color: #2DD4BF;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.3rem;
        }
        .lp-subtitle { color: #94A3B8; margin-top: -0.6rem; margin-bottom: 1.6rem; }
        .lp-context {
            color: #A8B3C7;
            background: #101827;
            border: 1px solid #22304A;
            border-radius: 10px;
            padding: 0.7rem 0.9rem;
            margin: 0.6rem 0 1.2rem 0;
            font-size: 0.86rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(metadata: PageMetadata) -> None:
    st.markdown(f'<div class="lp-kicker">{metadata.eyebrow}</div>', unsafe_allow_html=True)
    st.title(metadata.title)
    st.markdown(
        f'<div class="lp-subtitle">{metadata.description}</div>',
        unsafe_allow_html=True,
    )


def context_note(text: str) -> None:
    st.markdown(f'<div class="lp-context">{text}</div>', unsafe_allow_html=True)


def plot_chart(figure: go.Figure) -> None:
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        legend_title_text="",
        font={"color": "#DCE6F5"},
        hoverlabel={"bgcolor": "#111C31"},
        separators=",.",
    )
    figure.update_xaxes(gridcolor="rgba(148,163,184,0.10)")
    figure.update_yaxes(gridcolor="rgba(148,163,184,0.10)")
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False, "locale": "pt-BR"},
    )


def metric_row(items: list[tuple[str, str]], columns: int | None = None) -> None:
    layout = st.columns(columns or len(items))
    for column, (label, value) in zip(layout, items, strict=True):
        column.metric(label, value, help=KPI_HELP[label])


def origin_display(value: Any) -> str:
    if value is None or pd.isna(value) or str(value) == MISSING_ORIGIN_LABEL:
        return MISSING_ORIGIN_LABEL
    raw_value = str(value)
    return ORIGIN_LABELS.get(raw_value, raw_value.replace("_", " ").capitalize())


def channel_display(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Canal não atribuído"
    raw_value = str(value)
    return CHANNEL_LABELS.get(raw_value, raw_value.replace("_", " ").capitalize())


def scenario_display(value: str) -> str:
    return {"baseline_v1": "Cenário base"}.get(value, value.replace("_", " ").capitalize())


def methodology_display(value: str) -> str:
    return {"paid_media_daily_v1": "Geração diária por canal — versão 1"}.get(
        value, value.replace("_", " ").capitalize()
    )


def lifecycle_display(value: str) -> str:
    return {"seller_activation_v1": "Primeira venda em até 90 dias — versão 1"}.get(
        value, value.replace("_", " ").capitalize()
    )


def _origin_label(frame: pd.DataFrame) -> pd.DataFrame:
    labeled = frame.copy()
    labeled["origin_label"] = labeled["source_origin"].map(origin_display)
    if "normalized_channel" in labeled.columns:
        labeled["channel_label"] = labeled["normalized_channel"].map(channel_display)
    return labeled


def _all_filter_values(data: DashboardData) -> pd.DataFrame:
    return pd.concat(
        [
            data.acquisition[["source_origin", "normalized_channel"]],
            data.activation[["source_origin", "normalized_channel"]],
            data.marketing[["source_origin", "normalized_channel"]],
            data.downstream[["source_origin", "normalized_channel"]],
        ],
        ignore_index=True,
    ).drop_duplicates()


def _date_range(values: list[pd.Series]) -> tuple[date, date]:
    combined = pd.concat([pd.to_datetime(value, errors="coerce") for value in values])
    return combined.min().date(), combined.max().date()


def sidebar_filters(
    frame: pd.DataFrame,
    *,
    period_column: str,
    key: str,
    available_dimensions: pd.DataFrame | None = None,
    date_bounds: tuple[date, date] | None = None,
) -> tuple[date, date, list[str], list[str]]:
    dimensions = frame if available_dimensions is None else available_dimensions
    minimum, maximum = date_bounds or _date_range([frame[period_column]])
    selected_period = st.sidebar.date_input(
        "Período",
        value=(minimum, maximum),
        min_value=minimum,
        max_value=maximum,
        key=f"{key}_period",
    )
    if isinstance(selected_period, tuple) and len(selected_period) == 2:
        start_date, end_date = selected_period
    else:
        start_date = end_date = selected_period  # type: ignore[assignment]

    origins = st.sidebar.multiselect(
        "Origem",
        options=origin_labels(dimensions),
        format_func=origin_display,
        key=f"{key}_origins",
        placeholder="Todas as origens",
    )
    channels = st.sidebar.multiselect(
        "Canal",
        options=channel_labels(dimensions),
        format_func=channel_display,
        key=f"{key}_channels",
        placeholder="Todos os canais",
    )
    return start_date, end_date, origins, channels


def filter_for_page(
    frame: pd.DataFrame,
    period_column: str,
    filters: tuple[date, date, list[str], list[str]],
) -> pd.DataFrame:
    start_date, end_date, origins, channels = filters
    return apply_filters(
        frame,
        period_column=period_column,
        start_date=start_date,
        end_date=end_date,
        origins=origins,
        channels=channels,
    )


def current_activation_version(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    columns = [
        "observation_cutoff_timestamp",
        "lifecycle_rule_version",
        "source_snapshot_id",
    ]
    versions = frame[columns].drop_duplicates().sort_values(columns, ascending=False)
    options = list(versions.itertuples(index=False, name=None))
    if not options:
        return frame.iloc[0:0].copy()
    # Technical versions are governed metadata, not user-facing filters. The latest
    # contract is selected deterministically and disclosed below.
    selected = cast(tuple[Any, str, str], options[0])
    with st.sidebar.expander("Detalhes metodológicos · ativação"):
        st.caption(f"Regra: {lifecycle_display(selected[1])}")
        st.caption(f"Dados observados até: {pd.Timestamp(selected[0]):%d/%m/%Y}")
        st.caption(f"Referência dos dados: {str(selected[2])[:12]}")
    mask = (
        (frame[columns[0]] == selected[0])
        & (frame[columns[1]] == selected[1])
        & (frame[columns[2]] == selected[2])
    )
    return cast(pd.DataFrame, frame.loc[mask].copy())


def current_marketing_contract(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    scenarios = sorted(frame["scenario_id"].astype(str).unique().tolist())
    if not scenarios:
        return frame.iloc[0:0].copy()
    if len(scenarios) == 1:
        scenario = scenarios[0]
    else:
        scenario = cast(
            str,
            st.sidebar.selectbox(
                "Cenário",
                scenarios,
                format_func=scenario_display,
                key=f"{key}_scenario",
            ),
        )
    scenario_frame = frame.loc[frame["scenario_id"] == scenario]
    methodologies = sorted(scenario_frame["methodology_version"].astype(str).unique().tolist())
    # Methodology, seed, currency and lifecycle version are technical contract
    # metadata. They are disclosed, but never promoted to business filters.
    methodology = methodologies[-1]
    method_frame = scenario_frame.loc[scenario_frame["methodology_version"] == methodology]
    contract_columns = [
        "generation_seed",
        "currency",
        "observation_cutoff_timestamp",
        "lifecycle_rule_version",
        "lifecycle_source_snapshot_id",
    ]
    contracts = list(
        method_frame[contract_columns]
        .drop_duplicates()
        .sort_values(contract_columns, ascending=False)
        .itertuples(index=False, name=None)
    )
    contract = cast(tuple[int, str, Any, str, str], contracts[0])
    with st.sidebar.expander("Detalhes metodológicos · marketing"):
        st.caption(f"Cenário: {scenario_display(scenario)}")
        st.caption(f"Metodologia: {methodology_display(methodology)}")
        st.caption(f"Moeda: {contract[1]}")
        st.caption(f"Regra de ativação: {lifecycle_display(contract[3])}")
        st.caption(f"Dados observados até: {pd.Timestamp(contract[2]):%d/%m/%Y}")
        st.caption(f"Identificador de reprodução: {contract[0]}")
    mask = (
        (method_frame[contract_columns[0]] == contract[0])
        & (method_frame[contract_columns[1]] == contract[1])
        & (method_frame[contract_columns[2]] == contract[2])
        & (method_frame[contract_columns[3]] == contract[3])
        & (method_frame[contract_columns[4]] == contract[4])
    )
    return cast(pd.DataFrame, method_frame.loc[mask].copy())


def empty_state(frame: pd.DataFrame) -> bool:
    if not frame.empty:
        return False
    st.info("Dado não disponível para este recorte.")
    return True


def methodology_help() -> None:
    with st.expander("Entenda os indicadores"):
        st.markdown(
            """
            - **Lead qualificado:** contato que entrou no funil de aquisição de vendedores.
            - **Vendedor adquirido:** lead associado a um negócio fechado.
            - **Vendedor ativado:** vendedor com janela completa que fez a primeira venda em até 90 dias.
            - **GMV:** valor bruto dos itens vendidos por vendedores adquiridos. Frete é excluído e valor de pagamento não é utilizado.
            - **Investimento simulado:** cenário sintético e determinístico, não um gasto observado.
            - **Retorno de GMV:** GMV de 90 dias dividido pelo investimento simulado. O indicador é não causal e utiliza GMV de marketplace como proxy.
            """
        )


def render_overview(data: DashboardData) -> None:
    st.sidebar.subheader("Filtros da visão geral")
    activation_version = current_activation_version(data.activation, "overview_activation")
    marketing_contract = current_marketing_contract(data.marketing, "overview_marketing")
    bounds = _date_range(
        [
            data.acquisition["cohort_month"],
            data.activation["cohort_month"],
            data.marketing["period"],
            data.downstream["purchase_month"],
        ]
    )
    filters = sidebar_filters(
        data.acquisition,
        period_column="cohort_month",
        key="overview",
        available_dimensions=_all_filter_values(data),
        date_bounds=bounds,
    )
    acquisition = filter_for_page(data.acquisition, "cohort_month", filters)
    activation = filter_for_page(activation_version, "cohort_month", filters)
    marketing = filter_for_page(marketing_contract, "period", filters)
    downstream = filter_for_page(data.downstream, "purchase_month", filters)

    context_note(
        "O período respeita a data própria de cada análise: entrada do lead, aquisição do "
        "vendedor, investimento ou compra. As versões de ativação e do cenário são mantidas "
        "consistentes automaticamente."
    )
    acquisition_kpis = acquisition_summary(acquisition)
    activation_kpis = activation_summary(activation)
    marketing_kpis = marketing_summary(marketing)
    downstream_kpis = downstream_summary(downstream)

    st.subheader("Funil de aquisição")
    metric_row(
        [
            ("Leads qualificados", format_integer(acquisition_kpis["mqls"])),
            ("Vendedores adquiridos", format_integer(acquisition_kpis["acquired_sellers"])),
            (
                "Conversão de lead para vendedor",
                format_percent(acquisition_kpis["conversion_rate"]),
            ),
        ]
    )
    st.subheader("Ativação")
    metric_row(
        [
            (
                "Vendedores com janela completa de 90 dias",
                format_integer(activation_kpis["mature_sellers"]),
            ),
            ("Vendedores ativados", format_integer(activation_kpis["activated_sellers"])),
            ("Taxa de ativação", format_percent(activation_kpis["activation_rate"])),
        ]
    )
    st.subheader("Resultado comercial")
    metric_row(
        [
            ("Pedidos de vendedores adquiridos", format_integer(downstream_kpis["orders"])),
            ("GMV dos vendedores adquiridos", format_brl(downstream_kpis["eligible_gmv"])),
        ]
    )
    st.subheader("Eficiência de marketing")
    metric_row(
        [
            (
                "Investimento de marketing simulado",
                format_brl(marketing_kpis["synthetic_spend"]),
            ),
            ("Custo por lead", format_brl(marketing_kpis["cpl"])),
            (
                "Custo por vendedor adquirido",
                format_brl(marketing_kpis["seller_acquisition_cost"]),
            ),
            (
                "Retorno de GMV sobre investimento",
                format_roas(marketing_kpis["gmv_roas"]),
            ),
        ]
    )
    st.caption(
        "Cenário de investimento simulado. Os valores de mídia são sintéticos e "
        "determinísticos, utilizados para demonstrar a camada de eficiência de marketing. "
        "O indicador de retorno é não causal e utiliza GMV de marketplace como proxy."
    )
    methodology_help()

    if acquisition.empty and downstream.empty:
        empty_state(acquisition)
        return

    st.subheader("Evolução dos resultados")
    left, right = st.columns(2)
    monthly_acquisition = group_acquisition(acquisition, ["cohort_month"])
    with left:
        melted = monthly_acquisition.melt(
            id_vars="cohort_month",
            value_vars=["mqls", "acquired_sellers"],
            var_name="metric",
            value_name="value",
        )
        melted["metric"] = melted["metric"].replace(
            {"mqls": "Leads qualificados", "acquired_sellers": "Vendedores adquiridos"}
        )
        plot_chart(
            px.line(
                melted,
                x="cohort_month",
                y="value",
                color="metric",
                markers=True,
                title="Leads e vendedores adquiridos ao longo do tempo",
                color_discrete_map={
                    "Leads qualificados": SECONDARY,
                    "Vendedores adquiridos": ACCENT,
                },
                labels=CHART_LABELS,
                hover_data={"value": ":,.0f"},
            )
        )
    with right:
        figure = px.line(
            monthly_acquisition,
            x="cohort_month",
            y="conversion_rate",
            markers=True,
            title="Como a conversão evolui ao longo do tempo?",
            color_discrete_sequence=[ACCENT],
            labels=CHART_LABELS,
            hover_data={"conversion_rate": ":.2%"},
        )
        figure.update_yaxes(tickformat=".1%")
        plot_chart(figure)

    left, right = st.columns(2)
    monthly_downstream = group_downstream(downstream, ["purchase_month"])
    with left:
        plot_chart(
            px.bar(
                monthly_downstream,
                x="purchase_month",
                y="eligible_gmv",
                title="GMV dos vendedores adquiridos ao longo do tempo",
                color_discrete_sequence=[SECONDARY],
                labels=CHART_LABELS,
                hover_data={"eligible_gmv": ":,.2f"},
            )
        )
    with right:
        by_origin = _origin_label(
            group_acquisition(acquisition, ["source_origin", "normalized_channel"])
        ).sort_values("acquired_sellers", ascending=True)
        plot_chart(
            px.bar(
                by_origin,
                x="acquired_sellers",
                y="origin_label",
                orientation="h",
                color="channel_label",
                title="Quais origens trazem mais vendedores adquiridos?",
                labels=CHART_LABELS,
                hover_data={"acquired_sellers": ":,.0f"},
            )
        )


def render_acquisition(data: DashboardData) -> None:
    st.sidebar.subheader("Filtros de aquisição")
    filters = sidebar_filters(
        data.acquisition,
        period_column="cohort_month",
        key="acquisition",
    )
    frame = filter_for_page(data.acquisition, "cohort_month", filters)
    context_note(
        "O período representa o mês em que o lead entrou no funil. A conversão compara "
        "vendedores adquiridos com todos os leads qualificados do mesmo recorte."
    )
    if empty_state(frame):
        return
    kpis = acquisition_summary(frame)
    metric_row(
        [
            ("Leads qualificados", format_integer(kpis["mqls"])),
            ("Negócios fechados", format_integer(kpis["closed_deals"])),
            ("Vendedores adquiridos", format_integer(kpis["acquired_sellers"])),
            (
                "Conversão de lead para vendedor",
                format_percent(kpis["conversion_rate"]),
            ),
        ]
    )

    st.subheader("Avanço pelo funil")
    left, right = st.columns(2)
    with left:
        funnel = go.Figure(
            go.Funnel(
                y=["Leads qualificados", "Negócios fechados", "Vendedores adquiridos"],
                x=[kpis["mqls"], kpis["closed_deals"], kpis["acquired_sellers"]],
                marker={"color": [SECONDARY, ACCENT, "#14B8A6"]},
                textinfo="value+percent initial",
            )
        )
        funnel.update_layout(title="Como os leads avançam até a aquisição?")
        plot_chart(funnel)
    with right:
        monthly = group_acquisition(frame, ["cohort_month"])
        melted = monthly.melt(
            id_vars="cohort_month",
            value_vars=["mqls", "acquired_sellers"],
            var_name="metric",
            value_name="value",
        )
        melted["metric"] = melted["metric"].replace(
            {"mqls": "Leads qualificados", "acquired_sellers": "Vendedores adquiridos"}
        )
        plot_chart(
            px.line(
                melted,
                x="cohort_month",
                y="value",
                color="metric",
                markers=True,
                title="Leads e vendedores adquiridos ao longo do tempo",
                color_discrete_map={
                    "Leads qualificados": SECONDARY,
                    "Vendedores adquiridos": ACCENT,
                },
                labels=CHART_LABELS,
                hover_data={"value": ":,.0f"},
            )
        )

    left, right = st.columns(2)
    by_origin = _origin_label(group_acquisition(frame, ["source_origin"]))
    with left:
        ranking = by_origin.sort_values("mqls", ascending=True).melt(
            id_vars="origin_label",
            value_vars=["mqls", "acquired_sellers"],
            var_name="metric",
            value_name="value",
        )
        ranking["metric"] = ranking["metric"].replace(
            {"mqls": "Leads qualificados", "acquired_sellers": "Vendedores adquiridos"}
        )
        plot_chart(
            px.bar(
                ranking,
                x="value",
                y="origin_label",
                color="metric",
                barmode="group",
                orientation="h",
                title="Quais origens trazem mais leads e vendedores?",
                color_discrete_map={
                    "Leads qualificados": SECONDARY,
                    "Vendedores adquiridos": ACCENT,
                },
                labels=CHART_LABELS,
                hover_data={"value": ":,.0f"},
            )
        )
    with right:
        conversion = by_origin.sort_values("conversion_rate", ascending=True)
        figure = px.bar(
            conversion,
            x="conversion_rate",
            y="origin_label",
            orientation="h",
            title="Quais origens mais convertem leads em vendedores?",
            color_discrete_sequence=[ACCENT],
            labels=CHART_LABELS,
            hover_data={"conversion_rate": ":.2%"},
        )
        figure.update_xaxes(tickformat=".1%")
        plot_chart(figure)


def render_activation(data: DashboardData) -> None:
    st.sidebar.subheader("Filtros de ativação")
    versioned = current_activation_version(data.activation, "activation")
    filters = sidebar_filters(
        versioned,
        period_column="cohort_month",
        key="activation",
    )
    frame = filter_for_page(versioned, "cohort_month", filters)
    context_note(
        "O período representa o mês de aquisição do vendedor. A ativação ocorre quando um "
        "vendedor com janela completa realiza a primeira venda em até 90 dias."
    )
    if empty_state(frame):
        return
    kpis = activation_summary(frame)
    metric_row(
        [
            (
                "Vendedores com janela completa de 90 dias",
                format_integer(kpis["mature_sellers"]),
            ),
            ("Vendedores ativados", format_integer(kpis["activated_sellers"])),
            ("Taxa de ativação", format_percent(kpis["activation_rate"])),
            (
                "Tempo médio até a primeira venda",
                format_days(kpis["avg_time_to_first_order_days"]),
            ),
        ]
    )
    st.write("")
    metric_row(
        [
            (
                "Tempo mediano até a primeira venda",
                format_days(kpis["median_time_to_first_order_days"]),
            ),
            ("GMV nos primeiros 90 dias", format_brl(kpis["gmv_90d"])),
            ("GMV por vendedor ativado", format_brl(kpis["gmv_per_activated_seller"])),
            (
                "Pedidos por vendedor ativado",
                format_decimal(kpis["orders_per_activated_seller"]),
            ),
        ]
    )
    if kpis["median_time_to_first_order_days"] is None:
        st.caption(
            "A mediana não é calculada neste agrupamento para evitar combinação incorreta de medianas."
        )

    st.subheader("Qualidade da ativação")
    left, right = st.columns(2)
    by_origin = _origin_label(group_activation(frame, ["source_origin"]))
    with left:
        figure = px.bar(
            by_origin.sort_values("activation_rate", ascending=True),
            x="activation_rate",
            y="origin_label",
            orientation="h",
            title="Quais origens geram vendedores que ativam mais?",
            color_discrete_sequence=[ACCENT],
            labels=ACTIVATION_CHART_LABELS,
            hover_data={"activation_rate": ":.2%"},
        )
        figure.update_xaxes(tickformat=".1%")
        plot_chart(figure)
    with right:
        plot_chart(
            px.bar(
                by_origin.sort_values("avg_time_to_first_order_days", ascending=True),
                x="avg_time_to_first_order_days",
                y="origin_label",
                orientation="h",
                title="Quanto tempo os vendedores levam para fazer a primeira venda?",
                color_discrete_sequence=[SECONDARY],
                labels=ACTIVATION_CHART_LABELS,
                hover_data={"avg_time_to_first_order_days": ":.1f"},
            )
        )

    left, right = st.columns(2)
    by_cohort = group_activation(frame, ["cohort_month"])
    with left:
        plot_chart(
            px.bar(
                by_cohort,
                x="cohort_month",
                y="gmv_90d",
                title="GMV nos primeiros 90 dias por mês de aquisição",
                color_discrete_sequence=[TERTIARY],
                labels=ACTIVATION_CHART_LABELS,
                hover_data={"gmv_90d": ":,.2f"},
            )
        )
    with right:
        plot_chart(
            px.bar(
                by_cohort,
                x="cohort_month",
                y="activated_sellers_90d",
                title="Vendedores ativados por mês de aquisição",
                color_discrete_sequence=[ACCENT],
                labels=ACTIVATION_CHART_LABELS,
                hover_data={"activated_sellers_90d": ":,.0f"},
            )
        )


def render_marketing(data: DashboardData) -> None:
    st.sidebar.subheader("Filtros de marketing")
    contracted = current_marketing_contract(data.marketing, "marketing")
    filters = sidebar_filters(
        contracted,
        period_column="period",
        key="marketing",
    )
    frame = filter_for_page(contracted, "period", filters)
    context_note(
        "Cenário de investimento simulado. Os valores de mídia são sintéticos e "
        "determinísticos, utilizados para demonstrar a camada de eficiência de marketing."
    )
    if empty_state(frame):
        return
    kpis = marketing_summary(frame)
    metric_row(
        [
            (
                "Investimento de marketing simulado",
                format_brl(kpis["synthetic_spend"]),
            ),
            ("Custo por lead", format_brl(kpis["cpl"])),
            (
                "Custo por vendedor adquirido",
                format_brl(kpis["seller_acquisition_cost"]),
            ),
            (
                "Retorno de GMV sobre investimento",
                format_roas(kpis["gmv_roas"]),
            ),
        ]
    )
    st.caption(
        "O indicador é não causal e utiliza GMV de marketplace como proxy."
    )

    st.subheader("Eficiência por origem")
    by_origin = _origin_label(group_marketing(frame, ["source_origin"]))
    left, right = st.columns(2)
    with left:
        plot_chart(
            px.bar(
                by_origin.sort_values("synthetic_marketing_spend", ascending=True),
                x="synthetic_marketing_spend",
                y="origin_label",
                orientation="h",
                title="Investimento simulado por origem",
                color_discrete_sequence=[SECONDARY],
                labels=CHART_LABELS,
                hover_data={"synthetic_marketing_spend": ":,.2f"},
            )
        )
    with right:
        plot_chart(
            px.bar(
                by_origin.sort_values("cpl", ascending=True),
                x="cpl",
                y="origin_label",
                orientation="h",
                title="Quanto custa cada lead por origem?",
                color_discrete_sequence=[ACCENT],
                labels=CHART_LABELS,
                hover_data={"cpl": ":,.2f"},
            )
        )
    left, right = st.columns(2)
    with left:
        plot_chart(
            px.bar(
                by_origin.sort_values("seller_acquisition_cost", ascending=True),
                x="seller_acquisition_cost",
                y="origin_label",
                orientation="h",
                title="Quanto custa adquirir um vendedor por origem?",
                color_discrete_sequence=[TERTIARY],
                labels=CHART_LABELS,
                hover_data={"seller_acquisition_cost": ":,.2f"},
            )
        )
    with right:
        plot_chart(
            px.bar(
                by_origin.sort_values("gmv_roas", ascending=True),
                x="gmv_roas",
                y="origin_label",
                orientation="h",
                title="Retorno de GMV sobre investimento por origem",
                color_discrete_sequence=[ACCENT],
                labels=CHART_LABELS,
                hover_data={"gmv_roas": ":.2f"},
            )
        )


def render_downstream(data: DashboardData) -> None:
    st.sidebar.subheader("Filtros de desempenho")
    filters = sidebar_filters(
        data.downstream,
        period_column="purchase_month",
        key="downstream",
    )
    frame = filter_for_page(data.downstream, "purchase_month", filters)
    context_note(
        "O período representa o mês da compra. São considerados pedidos elegíveis de "
        "vendedores adquiridos pelo funil."
    )
    if empty_state(frame):
        return
    kpis = downstream_summary(frame)
    metric_row(
        [
            ("Pedidos de vendedores adquiridos", format_integer(kpis["orders"])),
            ("GMV dos vendedores adquiridos", format_brl(kpis["eligible_gmv"])),
            (
                "Participações vendedor–pedido",
                format_integer(kpis["seller_order_participations"]),
            ),
        ]
    )
    st.caption(
        "Um mesmo pedido pode conter itens de mais de um vendedor. Por isso, participações "
        "vendedor–pedido podem ser maiores que o número de pedidos únicos."
    )

    st.subheader("Evolução das vendas")
    monthly = group_downstream(frame, ["purchase_month"])
    left, right = st.columns(2)
    with left:
        plot_chart(
            px.bar(
                monthly,
                x="purchase_month",
                y="eligible_gmv",
                title="GMV dos vendedores adquiridos ao longo do tempo",
                color_discrete_sequence=[SECONDARY],
                labels=CHART_LABELS,
                hover_data={"eligible_gmv": ":,.2f"},
            )
        )
    with right:
        plot_chart(
            px.line(
                monthly,
                x="purchase_month",
                y="orders",
                markers=True,
                title="Pedidos únicos ao longo do tempo",
                color_discrete_sequence=[ACCENT],
                labels=CHART_LABELS,
                hover_data={"orders": ":,.0f"},
            )
        )
    by_origin = _origin_label(group_downstream(frame, ["source_origin"]))
    plot_chart(
        px.bar(
            by_origin.sort_values("eligible_gmv", ascending=True),
            x="eligible_gmv",
            y="origin_label",
            orientation="h",
            title="GMV gerado por origem de aquisição",
            color_discrete_sequence=[TERTIARY],
            labels=CHART_LABELS,
            hover_data={"eligible_gmv": ":,.2f"},
        )
    )


def main() -> None:
    configure_page()
    st.sidebar.markdown("## LeadPulse Analytics")
    st.sidebar.caption("Do Código à Decisão")
    navigation = st.sidebar.radio(
        "Navegação",
        tuple(page.navigation_label for page in PAGES.values()),
    )
    page_id = PAGE_BY_NAVIGATION[navigation]
    page_header(PAGES[page_id])
    if st.sidebar.button("Atualizar dados", width="stretch"):
        load_dashboard_data.clear()
        st.rerun()

    try:
        data = load_dashboard_data()
    # The UI boundary converts every internal failure into a safe, non-secret message.
    except Exception as error:  # noqa: BLE001
        public_error = classify_dashboard_error(error)
        st.error(public_error.message)
        st.caption(public_error.action)
        st.stop()

    renderers = {
        "overview": render_overview,
        "acquisition": render_acquisition,
        "activation": render_activation,
        "marketing": render_marketing,
        "downstream": render_downstream,
    }
    renderers[page_id](data)
    with st.expander("Sobre esta demonstração"):
        st.caption(
            "Projeto demonstrativo de engenharia e analytics baseado no dataset público "
            "Olist. O investimento de marketing é sintético e o GMV representa o valor "
            "bruto dos itens vendidos, usado como proxy — não como receita ou lucro."
        )
    st.sidebar.divider()
    st.sidebar.caption("Projeto desenvolvido para o portfólio Do Código à Decisão.")
    st.sidebar.caption("Dados governados · acesso somente para leitura")


if __name__ == "__main__":
    main()
