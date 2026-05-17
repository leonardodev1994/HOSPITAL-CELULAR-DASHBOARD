from datetime import datetime

import pandas as pd
import streamlit as st


def render_despesas(conn):
    cursor = conn.cursor()

    st.subheader("💸 Nova Despesa")

    data_despesa = st.date_input("Data", datetime.today())
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor", min_value=0.0)

    if st.button("Salvar Despesa"):
        cursor.execute("""
        INSERT INTO despesas (data, descricao, valor)
        VALUES (?, ?, ?)
        """, (str(data_despesa), descricao, valor))

        conn.commit()
        st.success("✅ Despesa salva!")

    df_despesas = pd.read_sql_query("SELECT * FROM despesas", conn)
    st.dataframe(df_despesas, width="stretch")
