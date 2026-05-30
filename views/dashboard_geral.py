import pandas as pd
import streamlit as st

from utils.dashboard_ui import bar_chart, empty_state, metric_card, moeda, page_header, pie_chart
from utils.quiosques import scope_clause


def render_dashboard_geral(conn):
    where_lancamentos, params_lancamentos = scope_clause()
    where_pagamentos, params_pagamentos = scope_clause("pagamentos")
    where_despesas, params_despesas = scope_clause()
    df = pd.read_sql_query(f"SELECT * FROM lancamentos{where_lancamentos}", conn, params=params_lancamentos)
    df_pagamentos = pd.read_sql_query(f"SELECT * FROM pagamentos{where_pagamentos}", conn, params=params_pagamentos)
    df_despesas = pd.read_sql_query(f"SELECT * FROM despesas{where_despesas}", conn, params=params_despesas)

    page_header(
        "Dashboard Geral",
        "Visão consolidada do faturamento, mix de vendas e formas de pagamento.",
    )

    faturamento = df["valor"].sum() if not df.empty else 0
    despesas = df_despesas["valor"].sum() if not df_despesas.empty else 0
    lucro = faturamento - despesas

    servicos = df[df["tipo"] == "Serviço"]["valor"].sum() if not df.empty else 0
    produtos = df[df["tipo"] == "Produto"]["valor"].sum() if not df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Faturamento", moeda(faturamento), "Receita total lançada", "#5B8DEF")
    with c2:
        metric_card("Serviços", moeda(servicos), "Reparos e mão de obra", "#18C29C")
    with c3:
        metric_card("Produtos", moeda(produtos), "Produtos vendidos", "#F59E0B")
    with c4:
        metric_card("Lucro estimado", moeda(lucro), f"Despesas: {moeda(despesas)}", "#EF4444")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if df_pagamentos.empty:
            empty_state("Nenhum pagamento cadastrado ainda.")
        else:
            resumo_pag = df_pagamentos.groupby("forma_pagamento", as_index=False)["valor"].sum()
            st.plotly_chart(
                pie_chart(resumo_pag, "forma_pagamento", "valor", "Formas de pagamento"),
                width="stretch",
            )

    with col2:
        if df.empty:
            empty_state("Nenhum lançamento cadastrado ainda.")
        else:
            resumo = df.groupby("tipo", as_index=False)["valor"].sum()
            st.plotly_chart(
                bar_chart(resumo, "tipo", "valor", "Serviços x Produtos"),
                width="stretch",
            )

    if not df.empty:
        st.divider()
        top = (
            df.groupby("descricao", as_index=False)
            .agg(valor=("valor", "sum"), quantidade=("id", "count"))
            .sort_values("valor", ascending=False)
            .head(8)
        )
        st.subheader("Itens mais relevantes")
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
