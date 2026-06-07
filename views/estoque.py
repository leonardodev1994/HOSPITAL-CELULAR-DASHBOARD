import pandas as pd
import streamlit as st

from utils.audit import log_action
from utils.auth import current_user
from utils.dashboard_ui import light_page_header, metric_card, moeda
from utils.permissions import has_permission
from utils.estoque import (
    add_stock_product,
    adjust_stock,
    apply_inventory_import,
    export_stock_to_excel,
    import_template_excel,
    load_stock,
    load_stock_movements,
    preview_inventory_import,
    produto_label,
    deactivate_stock_product,
    update_stock_product,
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


def _render_spreadsheet_tools(conn, df, user):
    st.subheader("Planilha de estoque")
    st.caption("Exporte, baixe o modelo ou importe produtos em massa com pré-visualização antes de gravar.")

    col_export, col_template = st.columns(2)
    with col_export:
        st.download_button(
            "Exportar estoque",
            data=export_stock_to_excel(df),
            file_name="estoque_tx_system.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with col_template:
        st.download_button(
            "Baixar modelo de importação",
            data=import_template_excel(),
            file_name="modelo_importacao_estoque_tx.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

    with st.expander("Importar estoque", expanded=False):
        uploaded_file = st.file_uploader(
            "Enviar planilha .xlsx",
            type=["xlsx"],
            key="importar_estoque_xlsx",
        )

        if not uploaded_file:
            st.info("Envie uma planilha para conferir a prévia antes da importação.")
            return

        try:
            uploaded_file.seek(0)
            preview_df, summary = preview_inventory_import(conn, uploaded_file, user=user)
        except Exception as error:
            st.error(f"Não foi possível ler a planilha: {error}")
            return

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_card("Cadastrar", summary["cadastrar"], "Novos produtos", "#18C29C")
        with m2:
            metric_card("Atualizar", summary["atualizar"], "Produtos existentes", "#5B8DEF")
        with m3:
            metric_card("Ignorar", summary["ignorar"], "Linhas vazias", "#64748B")
        with m4:
            metric_card("Erros", summary["erro"], "Corrigir antes de importar", "#EF4444")

        preview_cols = [
            "linha",
            "acao",
            "codigo",
            "produto",
            "categoria",
            "marca",
            "modelo",
            "quantidade",
            "custo",
            "valor_venda",
            "fornecedor",
            "estoque_minimo",
            "erro",
        ]
        available_cols = [col for col in preview_cols if col in preview_df.columns]
        st.dataframe(
            preview_df[available_cols],
            width="stretch",
            hide_index=True,
            column_config={
                "linha": st.column_config.NumberColumn("Linha", format="%d"),
                "acao": "Ação",
                "codigo": "Código/SKU",
                "produto": "Produto",
                "quantidade": st.column_config.NumberColumn("Quantidade", format="%.0f"),
                "custo": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
                "valor_venda": st.column_config.NumberColumn("Preço de venda", format="R$ %.2f"),
                "estoque_minimo": st.column_config.NumberColumn("Estoque mínimo", format="%.0f"),
                "erro": "Validação",
            },
        )

        if summary["erro"] > 0:
            st.warning("Corrija as linhas com erro na planilha antes de confirmar a importação.")
            return

        importable = summary["cadastrar"] + summary["atualizar"]
        if importable <= 0:
            st.info("Nenhum produto válido para importar.")
            return

        confirmed = st.checkbox(
            "Confirmo que revisei a prévia e quero importar/atualizar o estoque.",
            key="confirmar_importacao_estoque",
        )
        if st.button("Confirmar importação", width="stretch", disabled=not confirmed):
            result = apply_inventory_import(conn, preview_df, filename=uploaded_file.name, user=user)
            log_action(conn, user, "importou_estoque", "estoque", None, {
                "arquivo": uploaded_file.name,
                **result,
            })
            st.success(
                "Importação concluída: "
                f"{result['cadastrados']} cadastrados, "
                f"{result['atualizados']} atualizados, "
                f"{result['ignorados']} ignorados."
            )
            st.rerun()


def render_estoque(conn):
    user = current_user()
    can_manage_stock = has_permission("manage_stock")
    st.session_state.setdefault("estoque_form_aberto", False)
    st.session_state.setdefault("estoque_salvando", False)
    st.session_state.setdefault("estoque_ajuste_salvando", False)
    st.session_state.setdefault("estoque_editando_id", None)
    st.session_state.setdefault("estoque_excluir_id", None)

    light_page_header("📦", "Estoque", "Controle seus produtos com rapidez e precisão.")

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

    if can_manage_stock:
        if not st.session_state["estoque_form_aberto"]:
            if st.button("➕ Cadastrar produto", width="stretch"):
                st.session_state["estoque_form_aberto"] = True
                st.rerun()

        if st.session_state["estoque_form_aberto"]:
            st.subheader("➕ Cadastrar novo produto")
            st.caption("Use este formulário para colocar um produto novo no estoque sem depender da planilha.")

            with st.form("novo_produto_estoque_form"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    codigo = st.text_input("Código/SKU", placeholder="Opcional")
                    produto = st.text_input("Produto")
                    modelo = st.text_input("Modelo", placeholder="Opcional")

                with col2:
                    categoria = st.text_input("Categoria", placeholder="Ex.: Carregadores, Películas")
                    marca = st.text_input("Marca", placeholder="Opcional")
                    quantidade = st.number_input("Quantidade inicial", min_value=0.0, value=1.0, step=1.0)

                with col3:
                    custo = st.number_input("Custo", min_value=0.0, value=0.0, step=1.0)
                    valor_venda = st.number_input("Valor de venda", min_value=0.0, value=0.0, step=1.0)
                    estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0, value=1.0, step=1.0)

                fornecedor = st.text_input("Fornecedor", placeholder="Opcional")
                observacao = st.text_area("Observação")
                col_salvar, col_cancelar = st.columns(2)
                with col_salvar:
                    submitted = st.form_submit_button("Salvar produto", disabled=st.session_state["estoque_salvando"])
                with col_cancelar:
                    cancel = st.form_submit_button("Cancelar")

            if cancel:
                st.session_state["estoque_form_aberto"] = False
                st.rerun()

            if submitted and not st.session_state["estoque_salvando"]:
                try:
                    st.session_state["estoque_salvando"] = True
                    product_id, updated = add_stock_product(
                        conn,
                        produto,
                        modelo,
                        categoria,
                        quantidade,
                        valor_venda,
                        estoque_minimo,
                        observacao,
                        codigo=codigo,
                        marca=marca,
                        custo=custo,
                        fornecedor=fornecedor,
                    )
                    if updated:
                        st.success("✅ Produto já existia. A quantidade foi somada ao estoque.")
                    else:
                        st.success("✅ Produto cadastrado no estoque.")
                    log_action(conn, user, "atualizou_produto_estoque" if updated else "criou_produto_estoque", "estoque", product_id, {
                        "dados_novos": {
                            "codigo": codigo,
                            "produto": produto,
                            "modelo": modelo,
                            "categoria": categoria,
                            "marca": marca,
                            "quantidade": quantidade,
                            "custo": custo,
                            "valor_venda": valor_venda,
                            "estoque_minimo": estoque_minimo,
                            "fornecedor": fornecedor,
                        },
                    })
                    st.session_state["estoque_form_aberto"] = False
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
                except Exception as error:
                    st.error(f"Erro ao salvar produto: {error}")
                finally:
                    st.session_state["estoque_salvando"] = False

        st.divider()
        _render_spreadsheet_tools(conn, df, user)

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
    st.caption("Lista compacta. Clique no lápis para editar e na lixeira para inativar.")

    for row in df_filtrado.head(120).itertuples():
        col_info, col_edit, col_delete = st.columns([7, 1, 1])
        with col_info:
            status = "Baixo" if row.quantidade <= row.estoque_minimo else "OK"
            st.markdown(
                f"**{produto_label(row)}** · {row.categoria or 'Sem categoria'} · "
                f"Qtd: **{row.quantidade:g}** · Venda: **{moeda(row.valor_venda)}** · {status}"
            )
        if can_manage_stock:
            with col_edit:
                if st.button("✏️", key=f"editar_produto_{row.id}", help="Editar produto"):
                    st.session_state["estoque_editando_id"] = row.id
                    st.session_state["estoque_excluir_id"] = None
                    st.rerun()
            with col_delete:
                if st.button("🗑️", key=f"excluir_produto_{row.id}", help="Inativar produto"):
                    st.session_state["estoque_excluir_id"] = row.id
                    st.session_state["estoque_editando_id"] = None
                    st.rerun()

        if st.session_state.get("estoque_editando_id") == row.id:
            with st.container(border=True):
                st.markdown(f"#### Editar {produto_label(row)}")
                with st.form(f"editar_produto_form_{row.id}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        codigo_edit = st.text_input("Código/SKU", value=row.codigo or "")
                        produto_edit = st.text_input("Produto", value=row.produto or "")
                        modelo_edit = st.text_input("Modelo", value=row.modelo or "")
                    with c2:
                        categoria_edit = st.text_input("Categoria", value=row.categoria or "")
                        marca_edit = st.text_input("Marca", value=row.marca or "")
                        quantidade_edit = st.number_input("Quantidade", min_value=0.0, value=float(row.quantidade or 0), step=1.0)
                    with c3:
                        custo_edit = st.number_input("Custo", min_value=0.0, value=float(row.custo or 0), step=1.0)
                        valor_edit = st.number_input("Valor de venda", min_value=0.0, value=float(row.valor_venda or 0), step=1.0)
                        minimo_edit = st.number_input("Estoque mínimo", min_value=0.0, value=float(row.estoque_minimo or 0), step=1.0)
                    fornecedor_edit = st.text_input("Fornecedor", value=row.fornecedor or "")
                    observacao_edit = st.text_area("Observação", value=row.observacao or "")
                    salvar_edit = st.form_submit_button("Salvar edição", disabled=st.session_state["estoque_ajuste_salvando"])
                    cancelar_edit = st.form_submit_button("Cancelar")

                if cancelar_edit:
                    st.session_state["estoque_editando_id"] = None
                    st.rerun()
                if salvar_edit and not st.session_state["estoque_ajuste_salvando"]:
                    try:
                        st.session_state["estoque_ajuste_salvando"] = True
                        old_data = {
                            "codigo": row.codigo,
                            "produto": row.produto,
                            "modelo": row.modelo,
                            "categoria": row.categoria,
                            "marca": row.marca,
                            "quantidade": row.quantidade,
                            "custo": row.custo,
                            "valor_venda": row.valor_venda,
                            "estoque_minimo": row.estoque_minimo,
                            "fornecedor": row.fornecedor,
                        }
                        new_data = {
                            "codigo": codigo_edit,
                            "produto": produto_edit,
                            "modelo": modelo_edit,
                            "categoria": categoria_edit,
                            "marca": marca_edit,
                            "quantidade": quantidade_edit,
                            "custo": custo_edit,
                            "valor_venda": valor_edit,
                            "estoque_minimo": minimo_edit,
                            "fornecedor": fornecedor_edit,
                        }
                        update_stock_product(
                            conn,
                            row.id,
                            produto_edit,
                            modelo_edit,
                            categoria_edit,
                            quantidade_edit,
                            valor_edit,
                            minimo_edit,
                            observacao_edit,
                            codigo=codigo_edit,
                            marca=marca_edit,
                            custo=custo_edit,
                            fornecedor=fornecedor_edit,
                        )
                        log_action(conn, user, "editou_produto_estoque", "estoque", row.id, {
                            "dados_antigos": old_data,
                            "dados_novos": new_data,
                        })
                        st.session_state["estoque_editando_id"] = None
                        st.success("Produto atualizado.")
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))
                    finally:
                        st.session_state["estoque_ajuste_salvando"] = False

        if st.session_state.get("estoque_excluir_id") == row.id:
            with st.container(border=True):
                st.warning(f"Inativar {produto_label(row)}? O produto não será apagado definitivamente.")
                confirmar = st.checkbox("Confirmo que quero inativar este produto", key=f"confirmar_inativar_produto_{row.id}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Cancelar", key=f"cancelar_inativar_produto_{row.id}", width="stretch"):
                        st.session_state["estoque_excluir_id"] = None
                        st.rerun()
                with c2:
                    if st.button("Inativar produto", key=f"inativar_produto_{row.id}", width="stretch", disabled=not confirmar):
                        deactivate_stock_product(conn, row.id)
                        log_action(conn, user, "inativou_produto_estoque", "estoque", row.id, {
                            "dados_antigos": {
                                "produto": row.produto,
                                "modelo": row.modelo,
                                "categoria": row.categoria,
                                "valor_venda": row.valor_venda,
                                "custo": row.custo,
                            },
                            "dados_novos": {"ativo": 0},
                        })
                        st.session_state["estoque_excluir_id"] = None
                        st.success("Produto inativado.")
                        st.rerun()

    if not can_manage_stock:
        st.caption("Seu perfil permite consultar o estoque, mas não alterar quantidades ou valores.")
        return

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
