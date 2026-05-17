from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from utils.dashboard_ui import (
    bar_chart,
    empty_state,
    metric_card,
    moeda,
    page_header,
    pie_chart,
)


FORMAS_PAGAMENTO = ["Dinheiro", "Pix", "Crédito", "Débito"]


def _moeda(valor):
    return moeda(valor)


def _pagamentos_do_dia(conn, data):
    return pd.read_sql_query("""
    SELECT
        pagamentos.id,
        pagamentos.lancamento_id,
        pagamentos.forma_pagamento,
        pagamentos.valor,
        lancamentos.tipo,
        lancamentos.descricao,
        lancamentos.data
    FROM pagamentos
    INNER JOIN lancamentos ON lancamentos.id = pagamentos.lancamento_id
    WHERE lancamentos.data = ?
    """, conn, params=(data,))


def _formatar_pagamentos_lancamento(grupo):
    pagamentos = (
        grupo.groupby("forma_pagamento")["valor"]
        .sum()
        .reset_index()
    )

    ordem = {forma: indice for indice, forma in enumerate(FORMAS_PAGAMENTO)}
    pagamentos["ordem"] = pagamentos["forma_pagamento"].map(ordem).fillna(99)
    pagamentos = pagamentos.sort_values(["ordem", "forma_pagamento"])

    return " + ".join(
        f"{linha.forma_pagamento}: {_moeda(linha.valor)}"
        for linha in pagamentos.itertuples()
    )


def _pagamentos_por_lancamento(df_pagamentos):
    if df_pagamentos.empty:
        return pd.DataFrame(columns=["lancamento_id", "pagamento_calculado"])

    return (
        df_pagamentos.groupby("lancamento_id")
        .apply(_formatar_pagamentos_lancamento, include_groups=False)
        .reset_index(name="pagamento_calculado")
    )


def _montar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo):
    df_tipo = df_lancamentos[df_lancamentos["tipo"] == tipo].copy()

    if df_tipo.empty:
        return df_tipo

    pagamentos_lancamento = _pagamentos_por_lancamento(df_pagamentos)
    df_tipo = df_tipo.merge(
        pagamentos_lancamento,
        left_on="id",
        right_on="lancamento_id",
        how="left",
    )

    pagamento_antigo = df_tipo["pagamento"] if "pagamento" in df_tipo.columns else ""
    df_tipo["Pagamento"] = (
        df_tipo["pagamento_calculado"]
        .fillna(pagamento_antigo)
        .fillna("Não informado")
        .replace("", "Não informado")
    )

    tabela = df_tipo[["data", "descricao", "Pagamento", "valor"]].rename(columns={
        "data": "Data",
        "descricao": "Descrição",
        "valor": "Valor",
    })

    return tabela.sort_values(["Data", "Descrição"]).reset_index(drop=True)


def _mostrar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo):
    tabela = _montar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo)

    if tabela.empty:
        empty_state(f"Nenhum {tipo.lower()} cadastrado no dia selecionado.")
        return

    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
            "Pagamento": st.column_config.TextColumn("Pagamento", width="medium"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )


def _total_por_forma(df_pagamentos, forma, tipo=None):
    filtro = df_pagamentos["forma_pagamento"] == forma

    if tipo:
        filtro = filtro & (df_pagamentos["tipo"] == tipo)

    return df_pagamentos[filtro]["valor"].sum()


def _render_pagamentos_por_tipo(df_pagamentos, tipo, titulo):
    st.subheader(titulo)

    df_tipo = df_pagamentos[df_pagamentos["tipo"] == tipo]

    c1, c2, c3, c4 = st.columns(4)
    colunas = [c1, c2, c3, c4]
    accents = ["#5B8DEF", "#18C29C", "#A855F7", "#F59E0B"]

    for coluna, forma, accent in zip(colunas, FORMAS_PAGAMENTO, accents):
        total = _total_por_forma(df_pagamentos, forma, tipo)
        with coluna:
            metric_card(forma, _moeda(total), f"{tipo}", accent)

    if df_tipo.empty:
        empty_state(f"Nenhum pagamento de {tipo.lower()} no dia selecionado.")


def _safe_date_range(df):
    if df.empty:
        hoje = datetime.today().date()
        return hoje, hoje

    datas = pd.to_datetime(df["data"], errors="coerce").dropna()
    if datas.empty:
        hoje = datetime.today().date()
        return hoje, hoje

    return datas.min().date(), datas.max().date()


def _resumo_top_itens(df_dia):
    if df_dia.empty:
        return pd.DataFrame(columns=["descricao", "valor", "quantidade"])

    return (
        df_dia.groupby("descricao", as_index=False)
        .agg(valor=("valor", "sum"), quantidade=("id", "count"))
        .sort_values("valor", ascending=False)
        .head(8)
    )


def _render_tabela_operacional(df_lancamentos, df_pagamentos, tipo, titulo, accent):
    df_tipo = df_lancamentos[df_lancamentos["tipo"] == tipo]
    total_tipo = df_tipo["valor"].sum() if not df_tipo.empty else 0
    quantidade = len(df_tipo)
    ticket_medio = total_tipo / quantidade if quantidade else 0

    st.markdown(
        f"""
        <div class="section-panel" style="border-left-color:{accent};">
            <div class="section-panel-header">
                <div>
                    <h3>{titulo}</h3>
                    <p>Detalhamento dos lançamentos do dia selecionado</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Quantidade", str(quantidade), f"{tipo.lower()} no dia", accent)
    with c2:
        metric_card("Total", _moeda(total_tipo), "Faturamento", accent)
    with c3:
        metric_card("Ticket médio", _moeda(ticket_medio), "Média por lançamento", accent)

    _mostrar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo)


def render_dashboard_diario(conn):
    df = pd.read_sql_query("SELECT * FROM lancamentos", conn)
    df_despesas = pd.read_sql_query("SELECT * FROM despesas", conn)

    min_date, max_date = _safe_date_range(df)
    selected_date = st.date_input(
        "Escolha o dia da análise",
        value=max_date,
        min_value=min_date,
        max_value=max(datetime.today().date(), max_date),
    )
    data_filtro = selected_date.strftime("%Y-%m-%d")
    data_anterior = (selected_date - timedelta(days=1)).strftime("%Y-%m-%d")

    page_header(
        "Dashboard Diário",
        f"Análise operacional de {selected_date.strftime('%d/%m/%Y')}",
    )

    df_pagamentos = _pagamentos_do_dia(conn, data_filtro)
    df_dia = df[df["data"] == data_filtro] if not df.empty else df
    df_anterior = df[df["data"] == data_anterior] if not df.empty else df
    df_despesas_dia = df_despesas[df_despesas["data"] == data_filtro] if not df_despesas.empty else df_despesas

    total = df_dia["valor"].sum() if not df_dia.empty else 0
    total_anterior = df_anterior["valor"].sum() if not df_anterior.empty else 0
    servicos = df_dia[df_dia["tipo"] == "Serviço"]["valor"].sum() if not df_dia.empty else 0
    produtos = df_dia[df_dia["tipo"] == "Produto"]["valor"].sum() if not df_dia.empty else 0
    despesas = df_despesas_dia["valor"].sum() if not df_despesas_dia.empty else 0
    lucro = total - despesas
    diferenca = total - total_anterior
    diferenca_label = f"{_moeda(diferenca)} vs. dia anterior"

    dinheiro = _total_por_forma(df_pagamentos, "Dinheiro")
    pix = _total_por_forma(df_pagamentos, "Pix")
    credito = _total_por_forma(df_pagamentos, "Crédito")
    debito = _total_por_forma(df_pagamentos, "Débito")

    meta = 1000
    progresso = min(total / meta, 1.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Faturamento", _moeda(total), diferenca_label, "#5B8DEF")
    with c2:
        metric_card("Serviços", _moeda(servicos), f"{len(df_dia[df_dia['tipo'] == 'Serviço']) if not df_dia.empty else 0} lançamentos", "#18C29C")
    with c3:
        metric_card("Produtos", _moeda(produtos), f"{len(df_dia[df_dia['tipo'] == 'Produto']) if not df_dia.empty else 0} vendas", "#F59E0B")
    with c4:
        metric_card("Lucro estimado", _moeda(lucro), f"Despesas: {_moeda(despesas)}", "#EF4444")

    st.divider()

    col_meta, col_pag = st.columns([1, 2])
    with col_meta:
        st.subheader("Meta diária")
        st.progress(progresso)
        st.caption(f"{_moeda(total)} / {_moeda(meta)}")
    with col_pag:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dinheiro", _moeda(dinheiro))
        c2.metric("Pix", _moeda(pix))
        c3.metric("Crédito", _moeda(credito))
        c4.metric("Débito", _moeda(debito))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if df_pagamentos.empty:
            empty_state("Sem pagamentos no dia selecionado.")
        else:
            resumo_pag = df_pagamentos.groupby("forma_pagamento", as_index=False)["valor"].sum()
            st.plotly_chart(
                pie_chart(resumo_pag, "forma_pagamento", "valor", "Formas de pagamento"),
                width="stretch",
            )
    with col2:
        top_itens = _resumo_top_itens(df_dia)
        if top_itens.empty:
            empty_state("Sem itens para ranking nesse dia.")
        else:
            st.plotly_chart(
                bar_chart(top_itens, "valor", "descricao", "Itens com maior faturamento"),
                width="stretch",
            )

    _render_pagamentos_por_tipo(
        df_pagamentos,
        "Serviço",
        "Formas de Pagamento dos Serviços",
    )

    st.divider()

    _render_pagamentos_por_tipo(
        df_pagamentos,
        "Produto",
        "Formas de Pagamento dos Produtos",
    )

    st.divider()

    _render_tabela_operacional(
        df_dia,
        df_pagamentos,
        "Serviço",
        "Serviços Realizados",
        "#18C29C",
    )

    st.divider()

    _render_tabela_operacional(
        df_dia,
        df_pagamentos,
        "Produto",
        "Produtos Vendidos",
        "#F59E0B",
    )

    st.divider()

    st.subheader("Resumo Final")
    metric_card("Faturamento Total do Dia", _moeda(total), "Serviços + Produtos", "#5B8DEF")
