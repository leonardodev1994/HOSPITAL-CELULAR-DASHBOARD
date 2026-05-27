from datetime import datetime

import pandas as pd
import streamlit as st

from utils.dashboard_ui import pie_chart


def _pagamentos_do_dia(conn, data):
    return pd.read_sql_query("""
    SELECT pagamentos.*
    FROM pagamentos
    INNER JOIN lancamentos ON lancamentos.id = pagamentos.lancamento_id
    WHERE lancamentos.data = ?
    """, conn, params=(data,))


def render_caixa_diario(conn):
    cursor = conn.cursor()
    hoje = datetime.today().strftime("%Y-%m-%d")

    st.subheader("💰 Caixa Diário")

    valor_inicial = st.number_input("Valor Inicial", min_value=0.0)

    if st.button("Abrir Caixa"):
        caixa_existente = cursor.execute("""
        SELECT * FROM caixa
        WHERE data = ?
        """, (hoje,)).fetchone()

        if caixa_existente:
            st.warning("⚠️ Caixa já aberto hoje.")
        else:
            cursor.execute("""
            INSERT INTO caixa (data, valor_inicial)
            VALUES (?, ?)
            """, (hoje, valor_inicial))

            conn.commit()
            st.success("✅ Caixa aberto!")

    df_pagamentos = _pagamentos_do_dia(conn, hoje)
    df_despesas = pd.read_sql_query("SELECT * FROM despesas", conn)
    df_caixa = pd.read_sql_query("SELECT * FROM caixa", conn)

    despesas_hoje = df_despesas[df_despesas["data"] == hoje]
    caixa_hoje = df_caixa[df_caixa["data"] == hoje]

    abertura = 0
    if not caixa_hoje.empty:
        abertura = caixa_hoje.iloc[0]["valor_inicial"]

    dinheiro = df_pagamentos[df_pagamentos["forma_pagamento"] == "Dinheiro"]["valor"].sum()
    pix = df_pagamentos[df_pagamentos["forma_pagamento"] == "Pix"]["valor"].sum()
    credito = df_pagamentos[df_pagamentos["forma_pagamento"] == "Crédito"]["valor"].sum()
    debito = df_pagamentos[df_pagamentos["forma_pagamento"] == "Débito"]["valor"].sum()

    total_despesas = despesas_hoje["valor"].sum() if not despesas_hoje.empty else 0

    caixa_final = abertura + dinheiro - total_despesas
    total_geral = dinheiro + pix + credito + debito

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌅 Abertura", f"R$ {abertura:.2f}")
    c2.metric("💵 Dinheiro", f"R$ {dinheiro:.2f}")
    c3.metric("💸 Despesas", f"R$ {total_despesas:.2f}")
    c4.metric("🧾 Caixa Atual", f"R$ {caixa_final:.2f}")

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📲 Pix", f"R$ {pix:.2f}")
    c2.metric("💳 Crédito", f"R$ {credito:.2f}")
    c3.metric("💳 Débito", f"R$ {debito:.2f}")
    c4.metric("💰 Total Geral", f"R$ {total_geral:.2f}")

    st.divider()

    if df_pagamentos.empty:
        st.info("Nenhum pagamento cadastrado hoje.")
    else:
        fig = pie_chart(df_pagamentos, "forma_pagamento", "valor", "Formas de Pagamento")
        st.plotly_chart(fig, width="stretch")
