import pandas as pd
import streamlit as st

from utils.dashboard_ui import bar_chart, empty_state, metric_card, moeda, page_banner, page_header, pie_chart
from utils.permissions import has_permission, require_permission
from utils.quiosques import scope_clause


def render_dashboard_geral(conn):
    if not require_permission("view_dashboard_general"):
        return

    where_lancamentos, params_lancamentos = scope_clause()
    status_filter = "COALESCE(status, 'Ativo') <> 'Cancelado'"
    where_lancamentos = (
        where_lancamentos + " AND " + status_filter
        if where_lancamentos
        else " WHERE " + status_filter
    )
    where_pagamentos, params_pagamentos = scope_clause("pagamentos", prefix="AND")
    df_resumo = pd.read_sql_query(
        f"""
        SELECT tipo, COALESCE(SUM(valor), 0) AS valor, COUNT(*) AS quantidade
        FROM lancamentos
        {where_lancamentos}
        GROUP BY tipo
        """,
        conn,
        params=params_lancamentos,
    )
    df_pagamentos = pd.read_sql_query(
        f"""
        SELECT pagamentos.forma_pagamento, COALESCE(SUM(pagamentos.valor), 0) AS valor
        FROM pagamentos
        INNER JOIN lancamentos ON lancamentos.id = pagamentos.lancamento_id
        WHERE COALESCE(lancamentos.status, 'Ativo') <> 'Cancelado'
        {where_pagamentos}
        GROUP BY pagamentos.forma_pagamento
        """,
        conn,
        params=params_pagamentos,
    )
    if has_permission("view_profit"):
        where_despesas, params_despesas = scope_clause()
        despesas_row = pd.read_sql_query(
            f"SELECT COALESCE(SUM(valor), 0) AS total FROM despesas{where_despesas}",
            conn,
            params=params_despesas,
        )
        despesas = float(despesas_row.iloc[0]["total"] or 0) if not despesas_row.empty else 0
    else:
        despesas = 0

    page_banner("tx_dashboard_banner.webp", "TX System - Dashboard Geral")
    page_header(
        "Dashboard Geral",
        "Visão consolidada do faturamento, mix de vendas e formas de pagamento.",
    )

    faturamento = df_resumo["valor"].sum() if not df_resumo.empty else 0
    lucro = faturamento - despesas

    servicos = df_resumo[df_resumo["tipo"] == "Serviço"]["valor"].sum() if not df_resumo.empty else 0
    produtos = df_resumo[df_resumo["tipo"] == "Produto"]["valor"].sum() if not df_resumo.empty else 0

    cols = st.columns(4 if has_permission("view_profit") else 3)
    c1, c2, c3 = cols[:3]
    with c1:
        metric_card("Faturamento", moeda(faturamento), "Receita total lançada", "#5B8DEF")
    with c2:
        metric_card("Serviços", moeda(servicos), "Reparos e mão de obra", "#18C29C")
    with c3:
        metric_card("Produtos", moeda(produtos), "Produtos vendidos", "#F59E0B")
    if has_permission("view_profit"):
        with cols[3]:
            metric_card("Lucro estimado", moeda(lucro), f"Despesas: {moeda(despesas)}", "#EF4444")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if df_pagamentos.empty:
            empty_state("Nenhum pagamento cadastrado ainda.")
        else:
            st.plotly_chart(
                pie_chart(df_pagamentos, "forma_pagamento", "valor", "Formas de pagamento"),
                width="stretch",
            )

    with col2:
        if df_resumo.empty:
            empty_state("Nenhum lançamento cadastrado ainda.")
        else:
            st.plotly_chart(
                bar_chart(df_resumo, "tipo", "valor", "Serviços x Produtos"),
                width="stretch",
            )

    if not df_resumo.empty:
        st.divider()
        with st.expander("Itens mais relevantes", expanded=False):
            top = pd.read_sql_query(
                f"""
                SELECT descricao, COALESCE(SUM(valor), 0) AS valor, COUNT(*) AS quantidade
                FROM lancamentos
                {where_lancamentos}
                GROUP BY descricao
                ORDER BY valor DESC
                LIMIT 8
                """,
                conn,
                params=params_lancamentos,
            )
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
