from datetime import datetime
from datetime import timedelta

import pandas as pd
import streamlit as st

from utils.dashboard_ui import bar_chart, empty_state, metric_card, moeda, page_header, pie_chart


def _date_bounds(df):
    hoje = datetime.today().date()

    if df.empty:
        return hoje.replace(day=1), hoje

    datas = pd.to_datetime(df["data"], errors="coerce").dropna()
    if datas.empty:
        return hoje.replace(day=1), hoje

    return datas.min().date(), max(datas.max().date(), hoje)


def _month_start(date_value):
    return date_value.replace(day=1)


def _next_month(date_value):
    if date_value.month == 12:
        return date_value.replace(year=date_value.year + 1, month=1, day=1)
    return date_value.replace(month=date_value.month + 1, day=1)


def _period_label(start, end):
    return f"{start.strftime('%d/%m/%Y')} até {end.strftime('%d/%m/%Y')}"


def render_dashboard_mensal(conn):
    df = pd.read_sql_query("SELECT * FROM lancamentos", conn)
    df_despesas = pd.read_sql_query("SELECT * FROM despesas", conn)

    min_date, max_date = _date_bounds(df)

    modo = st.segmented_control(
        "Tipo de análise",
        ["Mês fechado", "Período personalizado"],
        default="Mês fechado",
    )

    if modo == "Mês fechado":
        meses = pd.date_range(_month_start(min_date), _month_start(max_date), freq="MS")
        opcoes = [mes.date() for mes in meses]
        labels = {mes: mes.strftime("%m/%Y") for mes in opcoes}
        selected_month = st.selectbox(
            "Escolha o mês",
            opcoes,
            format_func=lambda value: labels[value],
            index=len(opcoes) - 1 if opcoes else 0,
        )
        start_date = selected_month
        end_date = _next_month(selected_month) - timedelta(days=1)
    else:
        start_date, end_date = st.date_input(
            "Escolha o período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    page_header(
        "Dashboard Mensal",
        f"Visão financeira e comercial: {_period_label(start_date, end_date)}",
    )

    if df.empty:
        empty_state("Nenhum lançamento cadastrado ainda.")
        return

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df_periodo = df[
        (df["data_dt"].dt.date >= start_date)
        & (df["data_dt"].dt.date <= end_date)
    ].copy()

    if not df_despesas.empty:
        df_despesas["data_dt"] = pd.to_datetime(df_despesas["data"], errors="coerce")
        df_despesas_periodo = df_despesas[
            (df_despesas["data_dt"].dt.date >= start_date)
            & (df_despesas["data_dt"].dt.date <= end_date)
        ]
    else:
        df_despesas_periodo = df_despesas

    faturamento = df_periodo["valor"].sum() if not df_periodo.empty else 0
    despesas = df_despesas_periodo["valor"].sum() if not df_despesas_periodo.empty else 0
    lucro = faturamento - despesas
    servicos = df_periodo[df_periodo["tipo"] == "Serviço"]["valor"].sum() if not df_periodo.empty else 0
    produtos = df_periodo[df_periodo["tipo"] == "Produto"]["valor"].sum() if not df_periodo.empty else 0

    dias_periodo = max((end_date - start_date).days + 1, 1)
    media_dia = faturamento / dias_periodo
    projecao = media_dia * 30

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Faturamento", moeda(faturamento), f"Média/dia: {moeda(media_dia)}", "#5B8DEF")
    with c2:
        metric_card("Serviços", moeda(servicos), "Receita de reparos", "#18C29C")
    with c3:
        metric_card("Produtos", moeda(produtos), "Receita de vendas", "#F59E0B")
    with c4:
        metric_card("Lucro estimado", moeda(lucro), f"Projeção 30d: {moeda(projecao)}", "#EF4444")

    st.divider()

    if df_periodo.empty:
        empty_state("Nenhum lançamento no período selecionado.")
        return

    df_periodo["dia"] = df_periodo["data_dt"].dt.strftime("%d/%m")
    diario = df_periodo.groupby("dia", as_index=False)["valor"].sum()
    tipo = df_periodo.groupby("tipo", as_index=False)["valor"].sum()
    top = (
        df_periodo.groupby("descricao", as_index=False)
        .agg(valor=("valor", "sum"), quantidade=("id", "count"))
        .sort_values("valor", ascending=False)
        .head(10)
    )

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            bar_chart(diario, "dia", "valor", "Faturamento por dia"),
            width="stretch",
        )
    with col2:
        st.plotly_chart(
            pie_chart(tipo, "tipo", "valor", "Serviços x Produtos"),
            width="stretch",
        )

    st.divider()

    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Mais vendidos / maior faturamento")
        st.dataframe(
            top.rename(columns={
                "descricao": "Descrição",
                "valor": "Faturamento",
                "quantidade": "Quantidade",
            }),
            width="stretch",
            hide_index=True,
            column_config={
                "Faturamento": st.column_config.NumberColumn("Faturamento", format="R$ %.2f"),
            },
        )
    with col2:
        st.plotly_chart(
            bar_chart(top, "valor", "descricao", "Top itens"),
            width="stretch",
        )
