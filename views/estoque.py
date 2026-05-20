import os

import pandas as pd
import streamlit as st

from utils.dashboard_ui import metric_card, moeda, page_header
from utils.estoque import (
    PLANILHA_PADRAO,
    add_stock_product,
    adjust_stock,
    import_inventory_from_excel,
    load_stock,
    load_stock_movements,
    produto_label,
)


def _stock_table(df):
    tabela = df.copy()
    tabela["Produto"] = tabela.apply(produto_label, axis=1)
    tabela["Status"] = tabela.apply(
        lambda row: "Baixo" if row["quantidade"] <= row["estoque_minimo"] else "OK",
        axis=1,
    )
    tabela = tabela.rename(columns={
        "categoria": "Categoria",
        "quantidade": "Qtd",
        "valor_venda": "Valor Venda",
        "estoque_minimo": "Mínimo",
        "observacao": "Observação",
    })
    return tabela[["id", "Produto", "Categoria", "Qtd", "Valor Venda", "Mínimo", "Status", "Observação"]]


def render_estoque(conn):
    page_header(
        "Estoque",
        "Controle de produtos, importação da planilha e alerta de estoque baixo.",
    )

    df = load_stock(conn)
    total_produtos = len(df)
    total_unidades = df["quantidade"].sum() if not df.empty else 0
    baixo = len(df[df["quantidade"] <= df["estoque_minimo"]]) if not df.empty else 0
    valor_estimado = (df["quantidade"] * df["valor_venda"]).sum() if not df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Produtos", total_produtos, "Itens cadastrados", "#5B8DEF")
    with c2:
        metric_card("Unidades", int(total_unidades), "Saldo em estoque", "#18C29C")
    with c3:
        metric_card("Estoque baixo", baixo, "Itens para repor", "#EF4444")
    with c4:
        metric_card("Valor estimado", moeda(valor_estimado), "Preço de venda", "#F59E0B")

    st.divider()

    st.subheader("➕ Cadastrar novo produto")
    st.caption("Use este formulário para colocar um produto novo no estoque sem depender da planilha.")

    with st.expander("Formulário de cadastro", expanded=True):
        with st.form("novo_produto_estoque_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                produto = st.text_input("Produto")
                modelo = st.text_input("Modelo", placeholder="Opcional")

            with col2:
                categoria = st.text_input("Categoria", placeholder="Ex.: Carregadores, Películas")
                quantidade = st.number_input("Quantidade inicial", min_value=0.0, value=1.0, step=1.0)

            with col3:
                valor_venda = st.number_input("Valor de venda", min_value=0.0, value=0.0, step=1.0)
                estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0, value=1.0, step=1.0)

            observacao = st.text_area("Observação")
            submitted = st.form_submit_button("Salvar produto")

        if submitted:
            try:
                _, updated = add_stock_product(
                    conn,
                    produto,
                    modelo,
                    categoria,
                    quantidade,
                    valor_venda,
                    estoque_minimo,
                    observacao,
                )
                if updated:
                    st.success("✅ Produto já existia. A quantidade foi somada ao estoque.")
                else:
                    st.success("✅ Produto cadastrado no estoque.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except Exception as error:
                st.error(f"Erro ao salvar produto: {error}")

    with st.expander("Importar planilha de estoque", expanded=df.empty):
        st.caption("Películas serão consolidadas automaticamente como Película 3D.")

        uploaded_file = st.file_uploader(
            "Enviar arquivo Excel",
            type=["xlsx"],
            key="importar_estoque_xlsx",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Importar planilha padrão", width="stretch"):
                try:
                    created, updated, total = import_inventory_from_excel(conn, PLANILHA_PADRAO)
                    st.success(f"✅ Importação concluída: {created} novos, {updated} atualizados, {total} produtos lidos.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Erro ao importar: {error}")

        with col2:
            if uploaded_file and st.button("Importar arquivo enviado", width="stretch"):
                temp_path = "uploads/estoque_importado.xlsx"
                os.makedirs("uploads", exist_ok=True)
                with open(temp_path, "wb") as file:
                    file.write(uploaded_file.getbuffer())
                try:
                    created, updated, total = import_inventory_from_excel(conn, temp_path)
                    st.success(f"✅ Importação concluída: {created} novos, {updated} atualizados, {total} produtos lidos.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Erro ao importar: {error}")

    df = load_stock(conn)

    if df.empty:
        st.info("Nenhum produto cadastrado ainda. Importe a planilha para começar.")
        return

    busca = st.text_input("Buscar produto, modelo ou categoria")
    df_filtrado = df.copy()
    if busca.strip():
        termo = busca.strip().lower()
        df_filtrado = df_filtrado[
            df_filtrado["produto"].fillna("").str.lower().str.contains(termo)
            | df_filtrado["modelo"].fillna("").str.lower().str.contains(termo)
            | df_filtrado["categoria"].fillna("").str.lower().str.contains(termo)
        ]

    st.subheader("Produtos em estoque")
    tabela = _stock_table(df_filtrado)
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "id": None,
            "Valor Venda": st.column_config.NumberColumn("Valor Venda", format="R$ %.2f"),
        },
    )

    st.divider()
    st.subheader("Ajustar produto")

    options = {
        f"{produto_label(row)} | Qtd: {row.quantidade:g}": row.id
        for row in df.itertuples()
    }
    selected_label = st.selectbox("Produto", list(options.keys()))
    produto_id = options[selected_label]
    selected = df[df["id"] == produto_id].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        quantidade = st.number_input("Quantidade", min_value=0.0, value=float(selected["quantidade"]), step=1.0)
    with col2:
        valor_venda = st.number_input("Valor de venda", min_value=0.0, value=float(selected["valor_venda"]), step=1.0)
    with col3:
        estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0, value=float(selected["estoque_minimo"]), step=1.0)

    observacao = st.text_area("Observação", value=selected["observacao"] or "")

    if st.button("Salvar ajuste", width="stretch"):
        adjust_stock(conn, produto_id, quantidade, valor_venda, estoque_minimo, observacao)
        st.success("✅ Estoque atualizado.")
        st.rerun()

    st.divider()
    st.subheader("Movimentações recentes")

    movimentos = load_stock_movements(conn)
    if movimentos.empty:
        st.caption("Nenhuma movimentação registrada ainda.")
    else:
        movimentos["Produto"] = movimentos.apply(produto_label, axis=1)
        movimentos = movimentos.rename(columns={
            "data": "Data",
            "tipo": "Tipo",
            "quantidade": "Qtd",
            "motivo": "Motivo",
            "lancamento_id": "Lançamento",
            "responsavel": "Responsável",
        })
        st.dataframe(
            movimentos[["Data", "Produto", "Tipo", "Qtd", "Motivo", "Lançamento", "Responsável"]],
            width="stretch",
            hide_index=True,
        )
