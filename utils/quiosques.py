import pandas as pd
import streamlit as st

from utils.permissions import has_permission


DEFAULT_QUIOSQUE_ID = 1
ALL_QUIOSQUES_ID = 0


def load_quiosques(conn, active_only=True):
    query = "SELECT id, nome, ativo FROM quiosques"
    params = ()
    if active_only:
        query += " WHERE ativo = ?"
        params = (1,)
    query += " ORDER BY id"
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception:
        from database.database import ensure_quiosques_schema

        ensure_quiosques_schema(conn)
        return pd.read_sql_query(query, conn, params=params)


def user_can_view_all(user=None):
    user = user or st.session_state.get("usuario_logado") or {}
    return bool(user.get("acesso_todos_quiosques")) and has_permission("view_all_quiosques", user)


def user_quiosque_id(user=None):
    user = user or st.session_state.get("usuario_logado") or {}
    return int(user.get("quiosque_id") or DEFAULT_QUIOSQUE_ID)


def selected_quiosque_id(user=None):
    if not user_can_view_all(user):
        return user_quiosque_id(user)

    return st.session_state.get("quiosque_filtro", ALL_QUIOSQUES_ID)


def current_quiosque_id(user=None):
    selected = selected_quiosque_id(user)
    if selected == ALL_QUIOSQUES_ID:
        return user_quiosque_id(user)
    return int(selected)


def render_quiosque_filter(conn, user=None):
    user = user or st.session_state.get("usuario_logado") or {}

    if not user_can_view_all(user):
        st.session_state["quiosque_filtro"] = user_quiosque_id(user)
        return

    quiosques = load_quiosques(conn)
    options = {ALL_QUIOSQUES_ID: "Todos os quiosques"}
    options.update({int(row.id): row.nome for row in quiosques.itertuples()})

    current = st.session_state.get("quiosque_filtro", ALL_QUIOSQUES_ID)
    if current not in options:
        current = ALL_QUIOSQUES_ID
        st.session_state["quiosque_filtro"] = current

    st.selectbox(
        "Filtrar por quiosque",
        list(options.keys()),
        format_func=lambda value: options[value],
        index=list(options.keys()).index(current),
        key="quiosque_filtro",
    )


def scope_clause(alias=None, user=None, prefix="WHERE"):
    quiosque_id = selected_quiosque_id(user)
    if user_can_view_all(user) and quiosque_id == ALL_QUIOSQUES_ID:
        return "", ()

    column = f"{alias}.quiosque_id" if alias else "quiosque_id"
    return f" {prefix} {column} = ?", (quiosque_id,)


def scoped_params(*params, user=None):
    quiosque_id = selected_quiosque_id(user)
    if user_can_view_all(user) and quiosque_id == ALL_QUIOSQUES_ID:
        return tuple(params)
    return tuple(params) + (quiosque_id,)
