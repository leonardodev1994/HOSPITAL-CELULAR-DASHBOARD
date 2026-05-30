from datetime import datetime

import pandas as pd
import streamlit as st

from utils.permissions import require_permission
from utils.quiosques import current_quiosque_id, scope_clause


def render_despesas(conn):
    if not require_permission("view_expenses"):
        return

    cursor = conn.cursor()
    st.session_state.setdefault("despesa_form_aberto", False)
    st.session_state.setdefault("despesa_salvando", False)

    st.subheader("💸 Nova Despesa")

    if not st.session_state["despesa_form_aberto"]:
        if st.button("➕ Cadastrar despesa", width="stretch"):
            st.session_state["despesa_form_aberto"] = True
            st.rerun()

    if st.session_state["despesa_form_aberto"]:
        data_despesa = st.date_input("Data", datetime.today())
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.0)

        col_salvar, col_cancelar = st.columns(2)
        with col_salvar:
            salvar = st.button("Salvar Despesa", disabled=st.session_state["despesa_salvando"])
        with col_cancelar:
            cancelar = st.button("Cancelar")

        if cancelar:
            st.session_state["despesa_form_aberto"] = False
            st.rerun()

        if salvar and not st.session_state["despesa_salvando"]:
            try:
                st.session_state["despesa_salvando"] = True
                cursor.execute("""
                INSERT INTO despesas (data, descricao, valor, quiosque_id)
                VALUES (?, ?, ?, ?)
                """, (str(data_despesa), descricao, valor, current_quiosque_id()))
                conn.commit()
                st.session_state["despesa_form_aberto"] = False
                st.success("✅ Despesa salva!")
                st.rerun()
            finally:
                st.session_state["despesa_salvando"] = False

    where_despesas, params_despesas = scope_clause()
    df_despesas = pd.read_sql_query(f"SELECT * FROM despesas{where_despesas}", conn, params=params_despesas)
    st.dataframe(df_despesas, width="stretch")
