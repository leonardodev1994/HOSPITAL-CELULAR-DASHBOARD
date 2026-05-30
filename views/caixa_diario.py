from datetime import datetime

import pandas as pd
import streamlit as st

from utils.dashboard_ui import pie_chart
from utils.permissions import has_permission
from utils.quiosques import current_quiosque_id, scope_clause, scoped_params


def _pagamentos_do_dia(conn, data):
    scope, _ = scope_clause("lancamentos", prefix="AND")
    return pd.read_sql_query("""
    SELECT pagamentos.*
    FROM pagamentos
    INNER JOIN lancamentos ON lancamentos.id = pagamentos.lancamento_id
    WHERE lancamentos.data = ?
    """ + scope, conn, params=scoped_params(data))


def render_caixa_diario(conn):
    cursor = conn.cursor()
    hoje = datetime.today().strftime("%Y-%m-%d")

    st.subheader("💰 Caixa Diário")

    valor_inicial = st.number_input("Valor Inicial", min_value=0.0)

    if st.button("Abrir Caixa"):
        caixa_existente = cursor.execute("""
        SELECT * FROM caixa
        WHERE data = ? AND quiosque_id = ?
        """, (hoje, current_quiosque_id())).fetchone()

        if caixa_existente:
            st.warning("⚠️ Caixa já aberto hoje.")
        else:
            cursor.execute("""
            INSERT INTO caixa (data, valor_inicial, quiosque_id)
            VALUES (?, ?, ?)
            """, (hoje, valor_inicial, current_quiosque_id()))

            conn.commit()
            st.success("✅ Caixa aberto!")

    df_pagamentos = _pagamentos_do_dia(conn, hoje)
    where_caixa, params_caixa = scope_clause()
    if has_permission("view_expenses"):
        where_despesas, params_despesas = scope_clause()
        df_despesas = pd.read_sql_query(f"SELECT * FROM despesas{where_despesas}", conn, params=params_despesas)
    else:
        df_despesas = pd.DataFrame(columns=["data", "valor"])
    df_caixa = pd.read_sql_query(f"SELECT * FROM caixa{where_caixa}", conn, params=params_caixa)

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

    cols = st.columns(4 if has_permission("view_expenses") else 3)
    c1, c2 = cols[:2]
    c1.metric("🌅 Abertura", f"R$ {abertura:.2f}")
    c2.metric("💵 Dinheiro", f"R$ {dinheiro:.2f}")
    if has_permission("view_expenses"):
        cols[2].metric("💸 Despesas", f"R$ {total_despesas:.2f}")
        cols[3].metric("🧾 Caixa Atual", f"R$ {caixa_final:.2f}")
    else:
        cols[2].metric("🧾 Recebido em dinheiro", f"R$ {dinheiro:.2f}")

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
