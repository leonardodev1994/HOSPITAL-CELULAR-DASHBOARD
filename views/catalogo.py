import streamlit as st

from utils.audit import log_action
from utils.auth import current_user
from utils.catalogo import (
    MARCAS_PADRAO,
    apply_catalog_import,
    catalog_import_template_excel,
    create_catalog_item,
    enrich_catalog_df,
    load_imported_catalog_values,
    load_catalog_items,
    preview_catalog_import,
)
from utils.dashboard_ui import metric_card, moeda, page_banner, page_header
from utils.permissions import has_permission


def _item_descricao(row, tipo_aro):
    aro = "com aro" if tipo_aro == "com" else "sem aro"
    return f"Tela {row.modelo} {row.qualidade or ''} {aro}".strip()


def _item_valor(row, tipo_aro):
    return float(row.venda_com_aro if tipo_aro == "com" else row.venda_sem_aro or 0)


def _show_catalog_costs_toggle(key_prefix):
    state_key = "catalogo_mostrar_custo_lucro"
    st.session_state.setdefault(state_key, False)
    showing = st.session_state[state_key]
    label = "Custo e lucro visíveis" if showing else "Custo e lucro ocultos"
    icon = ":material/visibility:" if showing else ":material/visibility_off:"

    if st.button(label, key=f"catalogo_toggle_custos_{key_prefix}", icon=icon):
        st.session_state[state_key] = not showing
        st.rerun()

    return st.session_state[state_key]


def _render_catalog_results(conn, df, key_prefix):
    if df.empty:
        st.info("Nenhum item encontrado.")
        return

    show_costs = _show_catalog_costs_toggle(key_prefix)

    for row in enrich_catalog_df(df).itertuples():
        widget_key = f"{key_prefix}_{row.id}"
        with st.container(border=True):
            st.markdown(f"**{row.marca or 'Sem marca'} · {row.modelo} · {row.qualidade or '-'}**")
            c1, c2, c3 = st.columns(3)
            custo_sa = f"Custo {moeda(row.custo_sem_aro)}" if show_costs else "Custo oculto"
            custo_ca = f"Custo {moeda(row.custo_com_aro)}" if show_costs else "Custo oculto"
            lucro = moeda(max(row.lucro_sem_aro, row.lucro_com_aro)) if show_costs else "••••"
            c1.metric("S/A", moeda(row.venda_sem_aro), custo_sa)
            c2.metric("C/A", moeda(row.venda_com_aro), custo_ca)
            c3.metric("Lucro melhor", lucro)

            tipo_aro = st.segmented_control(
                "Opção",
                ["sem", "com"],
                default="sem" if float(row.venda_sem_aro or 0) > 0 else "com",
                format_func=lambda value: "Sem aro" if value == "sem" else "Com aro",
                key=f"catalogo_aro_{widget_key}",
            )
            valor = _item_valor(row, tipo_aro)
            descricao = _item_descricao(row, tipo_aro)

            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("Criar orçamento", key=f"orcamento_{widget_key}", width="stretch"):
                    st.session_state["catalogo_orcamento"] = {
                        "descricao": descricao,
                        "marca": row.marca,
                        "modelo": row.modelo,
                        "qualidade": row.qualidade,
                        "valor": valor,
                    }
                    st.rerun()
            with a2:
                if st.button("Abrir OS", key=f"abrir_os_catalogo_{widget_key}", width="stretch"):
                    st.session_state["catalogo_os_prefill"] = {
                        "servico": descricao,
                        "marca": row.marca,
                        "modelo": row.modelo,
                        "valor": valor,
                        "observacao": f"Orçamento gerado pelo catálogo. Qualidade: {row.qualidade or '-'}",
                    }
                    st.session_state["menu_atual"] = "Ordem de Serviço"
                    st.rerun()
            with a3:
                if st.button("Lançar venda", key=f"venda_catalogo_{widget_key}", width="stretch"):
                    st.session_state["catalogo_venda_prefill"] = {
                        "descricao": descricao,
                        "valor": valor,
                    }
                    st.session_state["menu_atual"] = "Novo Lançamento"
                    st.rerun()


def _render_catalog_import(conn, user):
    st.subheader("Planilha do catálogo")
    st.caption("Importe telas e peças em massa sem duplicar registros. A referência é Marca + Modelo + Qualidade.")

    col_template, col_import = st.columns(2)
    with col_template:
        st.download_button(
            "Baixar modelo",
            data=catalog_import_template_excel(),
            file_name="modelo_catalogo_tx.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with col_import:
        st.caption("Use o botão abaixo para enviar a planilha e revisar antes de gravar.")

    with st.expander("Importar planilha", expanded=False):
        uploaded_file = st.file_uploader(
            "Enviar arquivo .xlsx",
            type=["xlsx"],
            key="catalogo_import_xlsx",
        )

        if not uploaded_file:
            st.info("Envie uma planilha para visualizar a prévia antes da importação.")
            return

        try:
            uploaded_file.seek(0)
            preview_df, summary = preview_catalog_import(conn, uploaded_file)
        except Exception as error:
            st.error(f"Não foi possível ler a planilha: {error}")
            return

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_card("Cadastrar", summary["cadastrar"], "Itens novos", "#18C29C")
        with m2:
            metric_card("Atualizar", summary["atualizar"], "Itens existentes", "#5B8DEF")
        with m3:
            metric_card("Ignorar", summary["ignorar"], "Linhas vazias", "#64748B")
        with m4:
            metric_card("Erros", summary["erro"], "Corrigir antes", "#EF4444")

        if summary.get("aba"):
            st.caption(f"Aba lida da planilha: {summary['aba']}")

        st.dataframe(
            preview_df[[
                "linha",
                "acao",
                "marca",
                "linha_aparelho",
                "modelo",
                "qualidade",
                "fornecedor",
                "custo_sa",
                "venda_sa",
                "lucro_sa",
                "custo_ca",
                "venda_ca",
                "lucro_ca",
                "erro",
            ]],
            width="stretch",
            hide_index=True,
            column_config={
                "linha": st.column_config.NumberColumn("Linha", format="%d"),
                "acao": "Ação",
                "marca": "Marca",
                "linha_aparelho": "Linha",
                "modelo": "Modelo",
                "qualidade": "Qualidade",
                "fornecedor": "Fornecedor",
                "custo_sa": st.column_config.NumberColumn("custo_sa", format="R$ %.2f"),
                "venda_sa": st.column_config.NumberColumn("venda_sa", format="R$ %.2f"),
                "lucro_sa": st.column_config.NumberColumn("lucro_sa", format="R$ %.2f"),
                "custo_ca": st.column_config.NumberColumn("custo_ca", format="R$ %.2f"),
                "venda_ca": st.column_config.NumberColumn("venda_ca", format="R$ %.2f"),
                "lucro_ca": st.column_config.NumberColumn("lucro_ca", format="R$ %.2f"),
                "erro": "Validação",
            },
        )

        with st.expander("Mapeamento técnico planilha → banco", expanded=False):
            st.dataframe(
                preview_df[[
                    "linha",
                    "marca",
                    "linha_aparelho",
                    "fornecedor",
                    "modelo",
                    "qualidade",
                    "custo_sem_aro",
                    "venda_sem_aro",
                    "lucro_sem_aro",
                    "custo_com_aro",
                    "venda_com_aro",
                    "lucro_com_aro",
                ]],
                width="stretch",
                hide_index=True,
                column_config={
                    "linha": st.column_config.NumberColumn("Linha", format="%d"),
                    "custo_sem_aro": st.column_config.NumberColumn("custo_sem_aro", format="R$ %.2f"),
                    "venda_sem_aro": st.column_config.NumberColumn("venda_sem_aro", format="R$ %.2f"),
                    "lucro_sem_aro": st.column_config.NumberColumn("lucro_sem_aro", format="R$ %.2f"),
                    "custo_com_aro": st.column_config.NumberColumn("custo_com_aro", format="R$ %.2f"),
                    "venda_com_aro": st.column_config.NumberColumn("venda_com_aro", format="R$ %.2f"),
                    "lucro_com_aro": st.column_config.NumberColumn("lucro_com_aro", format="R$ %.2f"),
                },
            )

        if summary["erro"] > 0:
            st.warning("Corrija as linhas com erro antes de confirmar a importação.")
            return

        importable = summary["cadastrar"] + summary["atualizar"]
        if importable <= 0:
            st.info("Nenhum item válido para importar.")
            return

        confirmed = st.checkbox(
            "Confirmo que revisei a prévia e quero importar/atualizar o catálogo.",
            key="confirmar_importacao_catalogo",
        )
        if st.button("Confirmar importação", width="stretch", disabled=not confirmed):
            result = apply_catalog_import(conn, preview_df, filename=uploaded_file.name, user=user)
            saved_df = load_imported_catalog_values(conn, preview_df)
            log_action(
                conn,
                user,
                "importou_catalogo_pecas",
                "catalogo_pecas",
                None,
                {
                    "arquivo": uploaded_file.name,
                    **result,
                    "valores_salvos": saved_df.head(10).to_dict(orient="records") if not saved_df.empty else [],
                },
            )
            st.success(
                "Importação concluída: "
                f"{result['cadastrados']} cadastrados, "
                f"{result['atualizados']} atualizados, "
                f"{result['ignorados']} ignorados."
            )
            if saved_df.empty:
                st.warning("Importação registrada, mas nenhum item foi encontrado na validação pós-gravação.")
            else:
                st.caption("Validação pós-importação: valores lidos diretamente do banco.")
                st.dataframe(
                    saved_df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "id": st.column_config.NumberColumn("id", format="%d"),
                        "custo_sa": st.column_config.NumberColumn("custo_sa", format="R$ %.2f"),
                        "venda_sa": st.column_config.NumberColumn("venda_sa", format="R$ %.2f"),
                        "lucro_sa": st.column_config.NumberColumn("lucro_sa", format="R$ %.2f"),
                        "custo_ca": st.column_config.NumberColumn("custo_ca", format="R$ %.2f"),
                        "venda_ca": st.column_config.NumberColumn("venda_ca", format="R$ %.2f"),
                        "lucro_ca": st.column_config.NumberColumn("lucro_ca", format="R$ %.2f"),
                    },
                )
            return

        st.dataframe(
            preview_df[[
                "linha",
                "acao",
                "marca",
                "modelo",
                "qualidade",
                "custo_sem_aro",
                "venda_sem_aro",
                "lucro_sem_aro",
                "custo_com_aro",
                "venda_com_aro",
                "lucro_com_aro",
                "erro",
            ]],
            width="stretch",
            hide_index=True,
            column_config={
                "linha": st.column_config.NumberColumn("Linha", format="%d"),
                "acao": "Ação",
                "marca": "Marca",
                "modelo": "Modelo",
                "qualidade": "Qualidade",
                "custo_sem_aro": st.column_config.NumberColumn("Custo S/A", format="R$ %.2f"),
                "venda_sem_aro": st.column_config.NumberColumn("Venda S/A", format="R$ %.2f"),
                "lucro_sem_aro": st.column_config.NumberColumn("Lucro S/A", format="R$ %.2f"),
                "custo_com_aro": st.column_config.NumberColumn("Custo C/A", format="R$ %.2f"),
                "venda_com_aro": st.column_config.NumberColumn("Venda C/A", format="R$ %.2f"),
                "lucro_com_aro": st.column_config.NumberColumn("Lucro C/A", format="R$ %.2f"),
                "erro": "Validação",
            },
        )


def render_catalogo(conn):
    user = current_user()
    can_manage = has_permission("manage_stock", user)

    page_banner("tx_estoque_banner.webp", "TX System - Catálogo")
    page_header("Catálogo Inteligente", "Busca rápida de telas e peças com preço sugerido automático.")

    orcamento = st.session_state.get("catalogo_orcamento")
    if orcamento:
        with st.expander("Orçamento criado", expanded=True):
            st.write(orcamento["descricao"])
            st.metric("Valor sugerido", moeda(orcamento["valor"]))
            if st.button("Fechar orçamento", width="stretch"):
                st.session_state.pop("catalogo_orcamento", None)
                st.rerun()

    search = st.text_input("🔎 Pesquisar modelo, marca ou qualidade", placeholder="Ex.: iPhone 11, A10, Redmi Note...")
    if search.strip():
        _render_catalog_results(conn, load_catalog_items(conn, search=search, limit=40), "busca")
    else:
        st.caption("Digite acima para busca rápida ou abra uma marca abaixo.")

    if can_manage:
        _render_catalog_import(conn, user)

        with st.expander("Cadastrar tela/peça", expanded=False):
            with st.form("catalogo_item_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    marca = st.selectbox("Marca", MARCAS_PADRAO)
                    modelo = st.text_input("Modelo")
                    qualidade = st.text_input("Qualidade", placeholder="INCELL, OLED, PREMIUM...")
                with c2:
                    custo_sem_aro = st.number_input("Custo S/A", min_value=0.0, value=0.0, step=1.0)
                    custo_com_aro = st.number_input("Custo C/A", min_value=0.0, value=0.0, step=1.0)
                with c3:
                    observacao = st.text_area("Observação")
                salvar = st.form_submit_button("Salvar no catálogo")

            if salvar:
                try:
                    create_catalog_item(conn, marca, modelo, qualidade, custo_sem_aro, custo_com_aro, observacao)
                    log_action(conn, user, "criou_item_catalogo", "catalogo_pecas", None, {"modelo": modelo, "marca": marca})
                    st.success("Item cadastrado.")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))

    st.divider()
    st.subheader("Marcas")
    for marca in MARCAS_PADRAO:
        with st.expander(marca, expanded=False):
            marca_key = marca.lower().replace(" ", "_")
            _render_catalog_results(conn, load_catalog_items(conn, marca=marca, limit=60), f"marca_{marca_key}")
