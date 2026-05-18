from datetime import datetime

import streamlit as st

from database.database import execute_insert_returning_id
from utils.estoque import load_stock, produto_label, reduce_stock


def render_novo_lancamento(conn):
    cursor = conn.cursor()
    df_estoque = load_stock(conn)

    st.subheader("➕ Novo Lançamento")

    col1, col2 = st.columns(2)

    with col1:
        data = st.date_input("Data", datetime.today())
        tipo = st.selectbox("Tipo", ["Serviço", "Produto"])

        produto_id = None
        quantidade = 1.0

        if tipo == "Produto":
            if df_estoque.empty:
                st.warning("Nenhum produto cadastrado no estoque. Cadastre ou importe o estoque primeiro.")
                descricao = ""
                valor_sugerido = 0.0
            else:
                produtos_disponiveis = df_estoque[df_estoque["quantidade"] > 0].copy()
                if produtos_disponiveis.empty:
                    st.warning("Todos os produtos estão com estoque zerado.")
                    descricao = ""
                    valor_sugerido = 0.0
                else:
                    options = {
                        f"{produto_label(row)} | Qtd: {row.quantidade:g} | R$ {row.valor_venda:.2f}": row.id
                        for row in produtos_disponiveis.itertuples()
                    }
                    selected_label = st.selectbox("Produto do estoque", list(options.keys()))
                    produto_id = options[selected_label]
                    produto = produtos_disponiveis[produtos_disponiveis["id"] == produto_id].iloc[0]
                    descricao = produto_label(produto)
                    max_qtd = float(produto["quantidade"])
                    quantidade = st.number_input(
                        "Quantidade vendida",
                        min_value=1.0,
                        max_value=max_qtd,
                        value=1.0,
                        step=1.0,
                    )
                    valor_sugerido = float(produto["valor_venda"]) * quantidade
                    st.caption(f"Valor sugerido: R$ {valor_sugerido:.2f}")
        else:
            descricao = st.text_input("Descrição")

    with col2:
        st.subheader("💳 Pagamentos")
        pix = st.number_input("Pix", min_value=0.0)
        dinheiro = st.number_input("Dinheiro", min_value=0.0)
        credito = st.number_input("Crédito", min_value=0.0)
        debito = st.number_input("Débito", min_value=0.0)

    valor_total = pix + dinheiro + credito + debito
    st.metric("💰 Valor Total", f"R$ {valor_total:.2f}")

    if st.button("Salvar"):
        if tipo == "Produto" and not produto_id:
            st.error("Selecione um produto com estoque disponível.")
            return

        if not descricao.strip():
            st.error("Informe uma descrição para o lançamento.")
            return

        if valor_total <= 0:
            st.error("Informe pelo menos uma forma de pagamento com valor maior que zero.")
            return

        lancamento_id = execute_insert_returning_id(conn, cursor, """
        INSERT INTO lancamentos (data, tipo, descricao, valor, produto_id, quantidade)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (str(data), tipo, descricao, valor_total, produto_id, quantidade if tipo == "Produto" else None))

        if tipo == "Produto":
            try:
                reduce_stock(conn, produto_id, quantidade, lancamento_id=lancamento_id)
            except ValueError as error:
                cursor.execute("DELETE FROM lancamentos WHERE id = ?", (lancamento_id,))
                conn.commit()
                st.error(str(error))
                return

        formas = [
            ("Pix", pix),
            ("Dinheiro", dinheiro),
            ("Crédito", credito),
            ("Débito", debito),
        ]

        for forma, valor_pg in formas:
            if valor_pg > 0:
                cursor.execute("""
                INSERT INTO pagamentos (lancamento_id, forma_pagamento, valor)
                VALUES (?, ?, ?)
                """, (lancamento_id, forma, valor_pg))

        conn.commit()
        st.success("✅ Lançamento salvo!")
