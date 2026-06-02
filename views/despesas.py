from datetime import datetime

import pandas as pd
import streamlit as st

from utils.audit import log_action
from utils.auth import current_user
from utils.dashboard_ui import moeda, page_banner
from utils.permissions import has_permission, require_permission
from utils.quiosques import current_quiosque_id, load_quiosques, scope_clause, user_can_view_all


def _load_despesas(conn, limit=200):
    where_despesas, params_despesas = scope_clause("d")
    return pd.read_sql_query("""
    SELECT
        d.id,
        d.data,
        d.descricao,
        d.valor,
        d.quiosque_id,
        q.nome AS quiosque_nome
    FROM despesas d
    LEFT JOIN quiosques q ON q.id = d.quiosque_id
    """ + where_despesas + """
    ORDER BY d.data DESC, d.id DESC
    LIMIT ?
    """, conn, params=params_despesas + (limit,))


def _update_despesa(conn, despesa_id, data, descricao, valor, quiosque_id, user):
    if not str(descricao or "").strip():
        raise ValueError("Informe a descrição da despesa.")
    if float(valor or 0) <= 0:
        raise ValueError("Informe um valor maior que zero.")

    cursor = conn.cursor()
    old = cursor.execute("""
    SELECT id, data, descricao, valor, quiosque_id
    FROM despesas
    WHERE id = ?
    """, (int(despesa_id),)).fetchone()

    cursor.execute("""
    UPDATE despesas
    SET data = ?,
        descricao = ?,
        valor = ?,
        quiosque_id = ?
    WHERE id = ?
    """, (str(data), descricao.strip(), float(valor), int(quiosque_id), int(despesa_id)))
    conn.commit()
    log_action(conn, user, "editou_despesa", "despesas", int(despesa_id), {
        "dados_antigos": None if not old else {
            "data": old[1],
            "descricao": old[2],
            "valor": old[3],
            "quiosque_id": old[4],
        },
        "dados_novos": {
            "data": str(data),
            "descricao": descricao.strip(),
            "valor": float(valor),
            "quiosque_id": int(quiosque_id),
        },
    })


def _delete_despesa(conn, despesa, user):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM despesas WHERE id = ?", (int(despesa["id"]),))
    conn.commit()
    log_action(conn, user, "excluiu_despesa", "despesas", int(despesa["id"]), {
        "data": despesa.get("data"),
        "descricao": despesa.get("descricao"),
        "valor": despesa.get("valor"),
        "quiosque_id": despesa.get("quiosque_id"),
    })


def render_despesas(conn):
    if not require_permission("view_expenses"):
        return

    cursor = conn.cursor()
    user = current_user()
    is_admin = has_permission("delete_records", user)
    st.session_state.setdefault("despesa_form_aberto", False)
    st.session_state.setdefault("despesa_salvando", False)
    st.session_state.setdefault("despesa_editando_id", None)
    st.session_state.setdefault("despesa_excluir_id", None)

    page_banner("tx_despesas_banner.webp", "TX System - Despesas")
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

    st.divider()
    st.subheader("Despesas cadastradas")
    df_despesas = _load_despesas(conn)
    if df_despesas.empty:
        st.info("Nenhuma despesa cadastrada.")
        return

    quiosques = load_quiosques(conn) if user_can_view_all(user) else pd.DataFrame()
    quiosque_options = {
        int(row.id): row.nome
        for row in quiosques.itertuples()
    } if not quiosques.empty else {}

    for row in df_despesas.itertuples():
        col_info, col_edit, col_delete = st.columns([7, 1, 1])
        with col_info:
            quiosque_label = f" · {row.quiosque_nome}" if row.quiosque_nome else ""
            st.markdown(f"**{row.data}** · {row.descricao} · **{moeda(row.valor)}**{quiosque_label}")

        with col_edit:
            if is_admin and st.button("✏️", key=f"editar_despesa_{row.id}", help="Editar despesa"):
                st.session_state["despesa_editando_id"] = row.id
                st.session_state["despesa_excluir_id"] = None
                st.rerun()

        with col_delete:
            if is_admin and st.button("🗑️", key=f"excluir_despesa_{row.id}", help="Excluir despesa"):
                st.session_state["despesa_excluir_id"] = row.id
                st.session_state["despesa_editando_id"] = None
                st.rerun()

        if st.session_state.get("despesa_editando_id") == row.id:
            with st.container(border=True):
                with st.form(f"editar_despesa_form_{row.id}"):
                    edit_data = st.date_input("Data", value=pd.to_datetime(row.data).date(), key=f"despesa_data_{row.id}")
                    edit_descricao = st.text_input("Descrição", value=row.descricao or "", key=f"despesa_desc_{row.id}")
                    edit_valor = st.number_input("Valor", min_value=0.01, value=float(row.valor or 0), step=1.0, key=f"despesa_valor_{row.id}")
                    if quiosque_options:
                        ids = list(quiosque_options.keys())
                        atual = int(row.quiosque_id or current_quiosque_id(user))
                        if atual not in ids:
                            atual = ids[0]
                        edit_quiosque = st.selectbox(
                            "Quiosque",
                            ids,
                            format_func=lambda value: quiosque_options[value],
                            index=ids.index(atual),
                            key=f"despesa_quiosque_{row.id}",
                        )
                    else:
                        edit_quiosque = int(row.quiosque_id or current_quiosque_id(user))

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        salvar_edicao = st.form_submit_button("Salvar edição")
                    with col_cancel:
                        cancelar_edicao = st.form_submit_button("Cancelar")

                if cancelar_edicao:
                    st.session_state["despesa_editando_id"] = None
                    st.rerun()
                if salvar_edicao:
                    try:
                        _update_despesa(conn, row.id, edit_data, edit_descricao, edit_valor, edit_quiosque, user)
                        st.session_state["despesa_editando_id"] = None
                        st.success("Despesa atualizada.")
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))

        if st.session_state.get("despesa_excluir_id") == row.id:
            with st.container(border=True):
                st.warning(f"Excluir despesa: {row.descricao} ({moeda(row.valor)})?")
                confirmar = st.checkbox("Confirmo que quero excluir esta despesa", key=f"confirmar_excluir_despesa_{row.id}")
                col_cancel, col_confirm = st.columns(2)
                with col_cancel:
                    if st.button("Cancelar", key=f"cancelar_excluir_despesa_{row.id}", width="stretch"):
                        st.session_state["despesa_excluir_id"] = None
                        st.rerun()
                with col_confirm:
                    if st.button("Excluir", key=f"confirmar_excluir_despesa_btn_{row.id}", width="stretch", disabled=not confirmar):
                        _delete_despesa(conn, row._asdict(), user)
                        st.session_state["despesa_excluir_id"] = None
                        st.success("Despesa excluída.")
                        st.rerun()
