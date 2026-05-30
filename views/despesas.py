from datetime import datetime

import pandas as pd
import streamlit as st

from utils.permissions import require_permission
from utils.quiosques import current_quiosque_id, scope_clause


def render_despesas(conn):
    if not require_permission("view_expenses"):
        return

    cursor = conn.cursor()

    st.subheader("💸 Nova Despesa")

    data_despesa = st.date_input("Data", datetime.today())
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor", min_value=0.0)

    if st.button("Salvar Despesa"):
        cursor.execute("""
        INSERT INTO despesas (data, descricao, valor, quiosque_id)
        VALUES (?, ?, ?, ?)
        """, (str(data_despesa), descricao, valor, current_quiosque_id()))

        conn.commit()
        st.success("✅ Despesa salva!")

    where_despesas, params_despesas = scope_clause()
    df_despesas = pd.read_sql_query(f"SELECT * FROM despesas{where_despesas}", conn, params=params_despesas)
    st.dataframe(df_despesas, width="stretch")
