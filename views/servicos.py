import streamlit as st

from utils.audit import log_action
from utils.auth import current_user
from utils.dashboard_ui import light_page_header, moeda
from utils.permissions import has_permission
from utils.servicos import create_service, deactivate_service, load_services, servico_label, update_service


def render_servicos(conn):
    user = current_user()
    can_manage = has_permission("manage_services", user)
    st.session_state.setdefault("servico_form_aberto", False)
    st.session_state.setdefault("servico_salvando", False)
    st.session_state.setdefault("servico_editando_id", None)
    st.session_state.setdefault("servico_excluir_id", None)

    light_page_header("🧰", "Serviços", "Tabela de serviços para vendas e ordens de serviço.")

    if can_manage:
        if not st.session_state["servico_form_aberto"]:
            if st.button("➕ Cadastrar serviço", width="stretch"):
                st.session_state["servico_form_aberto"] = True
                st.rerun()

        if st.session_state["servico_form_aberto"]:
            with st.container(border=True):
                with st.form("novo_servico_form"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        nome = st.text_input("Nome do serviço")
                        categoria = st.text_input("Categoria")
                        modelo = st.text_input("Aparelho/modelo")
                    with c2:
                        valor_padrao = st.number_input("Valor padrão", min_value=0.0, value=0.0, step=1.0)
                        custo_estimado = st.number_input("Custo estimado", min_value=0.0, value=0.0, step=1.0)
                        tempo_estimado = st.text_input("Tempo estimado")
                    with c3:
                        garantia = st.text_input("Garantia", placeholder="Ex.: 90 dias")
                        observacao = st.text_area("Observação")
                    salvar = st.form_submit_button("Salvar serviço", disabled=st.session_state["servico_salvando"])
                    cancelar = st.form_submit_button("Cancelar")

                if cancelar:
                    st.session_state["servico_form_aberto"] = False
                    st.rerun()
                if salvar and not st.session_state["servico_salvando"]:
                    try:
                        st.session_state["servico_salvando"] = True
                        create_service(conn, nome, categoria, modelo, valor_padrao, custo_estimado, tempo_estimado, garantia, observacao)
                        log_action(conn, user, "criou_servico", "servicos", None, {"nome": nome, "valor_padrao": valor_padrao})
                        st.session_state["servico_form_aberto"] = False
                        st.success("Serviço cadastrado.")
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))
                    finally:
                        st.session_state["servico_salvando"] = False

    busca = st.text_input("Pesquisar serviço, categoria ou aparelho/modelo")
    df = load_services(conn, only_active=True)
    if busca.strip() and not df.empty:
        termo = busca.strip().lower()
        df = df[
            df["nome"].fillna("").str.lower().str.contains(termo)
            | df["categoria"].fillna("").str.lower().str.contains(termo)
            | df["modelo"].fillna("").str.lower().str.contains(termo)
        ]

    if df.empty:
        st.info("Nenhum serviço cadastrado.")
        return

    st.caption("Lista compacta. Atendentes usam estes serviços em vendas e OS; admin/gerente gerenciam a tabela.")
    for row in df.head(200).itertuples():
        col_info, col_edit, col_delete = st.columns([7, 1, 1])
        with col_info:
            st.markdown(
                f"**{servico_label(row)}** · {row.categoria or 'Sem categoria'} · "
                f"{moeda(row.valor_padrao)} · Garantia: {row.garantia or '-'}"
            )
        if can_manage:
            with col_edit:
                if st.button("✏️", key=f"editar_servico_{row.id}", help="Editar serviço"):
                    st.session_state["servico_editando_id"] = row.id
                    st.session_state["servico_excluir_id"] = None
                    st.rerun()
            with col_delete:
                if st.button("🗑️", key=f"excluir_servico_{row.id}", help="Inativar serviço"):
                    st.session_state["servico_excluir_id"] = row.id
                    st.session_state["servico_editando_id"] = None
                    st.rerun()

        if st.session_state.get("servico_editando_id") == row.id:
            with st.container(border=True):
                with st.form(f"editar_servico_form_{row.id}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        nome_edit = st.text_input("Nome do serviço", value=row.nome or "")
                        categoria_edit = st.text_input("Categoria", value=row.categoria or "")
                        modelo_edit = st.text_input("Aparelho/modelo", value=row.modelo or "")
                    with c2:
                        valor_edit = st.number_input("Valor padrão", min_value=0.0, value=float(row.valor_padrao or 0), step=1.0)
                        custo_edit = st.number_input("Custo estimado", min_value=0.0, value=float(row.custo_estimado or 0), step=1.0)
                        tempo_edit = st.text_input("Tempo estimado", value=row.tempo_estimado or "")
                    with c3:
                        garantia_edit = st.text_input("Garantia", value=row.garantia or "")
                        obs_edit = st.text_area("Observação", value=row.observacao or "")
                    salvar_edit = st.form_submit_button("Salvar edição")
                    cancelar_edit = st.form_submit_button("Cancelar")

                if cancelar_edit:
                    st.session_state["servico_editando_id"] = None
                    st.rerun()
                if salvar_edit:
                    try:
                        update_service(conn, row.id, nome_edit, categoria_edit, modelo_edit, valor_edit, custo_edit, tempo_edit, garantia_edit, obs_edit)
                        log_action(conn, user, "editou_servico", "servicos", row.id, {"nome": nome_edit, "valor_padrao": valor_edit})
                        st.session_state["servico_editando_id"] = None
                        st.success("Serviço atualizado.")
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))

        if st.session_state.get("servico_excluir_id") == row.id:
            with st.container(border=True):
                st.warning(f"Inativar serviço: {servico_label(row)}?")
                confirmar = st.checkbox("Confirmo que quero inativar este serviço", key=f"confirmar_inativar_servico_{row.id}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Cancelar", key=f"cancelar_inativar_servico_{row.id}", width="stretch"):
                        st.session_state["servico_excluir_id"] = None
                        st.rerun()
                with c2:
                    if st.button("Inativar serviço", key=f"inativar_servico_{row.id}", width="stretch", disabled=not confirmar):
                        deactivate_service(conn, row.id)
                        log_action(conn, user, "inativou_servico", "servicos", row.id, {"nome": row.nome})
                        st.session_state["servico_excluir_id"] = None
                        st.success("Serviço inativado.")
                        st.rerun()
