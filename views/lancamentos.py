from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.auth import current_user
from utils.dashboard_ui import moeda, page_banner, page_header
from views.novo_lancamento import (
    _load_lancamentos,
    _render_lancamento_action_dialog,
    _request_lancamento_action,
)


def _load_pagamentos_lancamento(conn, lancamento_id):
    return pd.read_sql_query("""
    SELECT forma_pagamento, valor
    FROM pagamentos
    WHERE lancamento_id = ?
    ORDER BY id
    """, conn, params=(int(lancamento_id),))


def _pagamento_label(df_pagamentos):
    if df_pagamentos.empty:
        return "Não informado"
    return " + ".join(
        f"{row.forma_pagamento}: {moeda(row.valor)}"
        for row in df_pagamentos.itertuples()
    )


def _linha_resumo(row):
    return f"#{row.id} · {row.data} · {row.tipo} · {row.descricao} · {moeda(row.valor)}"


def _render_detalhes_lancamento(conn, row):
    pagamentos = _load_pagamentos_lancamento(conn, row.id)
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Descrição")
        st.write(row.descricao)
        st.caption("Pagamento")
        st.write(_pagamento_label(pagamentos))
        st.caption("Usuário responsável")
        st.write(getattr(row, "usuario_responsavel", None) or "Não informado")
    with col2:
        st.caption("Quiosque")
        st.write(getattr(row, "quiosque_nome", None) or getattr(row, "quiosque_id", ""))
        st.caption("Quantidade")
        st.write(getattr(row, "quantidade", None) or "-")
        st.caption("Observação")
        st.write(getattr(row, "observacao_alteracao_preco", None) or "-")


def render_lancamentos(conn):
    user = current_user()
    st.session_state.setdefault("lancamento_aberto", None)

    page_banner("tx_lancamento_banner.webp", "TX System - Lançamentos")
    page_header(
        "Lançamentos",
        "Consulte, edite ou cancele vendas já registradas sem pesar a tela inicial.",
    )

    hoje = date.today()
    col1, col2, col3 = st.columns([1, 1, 0.7])
    with col1:
        data_inicio = st.date_input("Data inicial", value=hoje - timedelta(days=7), key="lancamentos_data_inicio")
    with col2:
        data_fim = st.date_input("Data final", value=hoje, key="lancamentos_data_fim")
    with col3:
        limit = st.number_input("Limite", min_value=25, max_value=300, value=100, step=25)

    if data_inicio > data_fim:
        st.warning("A data inicial não pode ser maior que a data final.")
        return

    df_lancamentos = _load_lancamentos(conn, data_inicio=data_inicio, data_fim=data_fim, limit=limit)
    if df_lancamentos.empty:
        st.info("Nenhum lançamento encontrado no período.")
        return

    st.caption("Clique em um lançamento para abrir detalhes e ações.")

    for row in df_lancamentos.itertuples():
        is_open = st.session_state.get("lancamento_aberto") == row.id
        col_info, col_toggle = st.columns([8, 1])
        with col_info:
            if st.button(_linha_resumo(row), key=f"abrir_lancamento_{row.id}", width="stretch"):
                st.session_state["lancamento_aberto"] = None if is_open else row.id
                st.rerun()
        with col_toggle:
            st.button("▾" if not is_open else "▴", key=f"toggle_lancamento_{row.id}", disabled=True)

        if is_open:
            with st.container(border=True):
                _render_detalhes_lancamento(conn, row)
                col_edit, col_cancel = st.columns(2)
                with col_edit:
                    if st.button("✏️ Editar", key=f"editar_lancamento_lista_{row.id}", width="stretch"):
                        _request_lancamento_action("edit", row.id)
                        st.rerun()
                with col_cancel:
                    if st.button("🗑️ Apagar", key=f"cancelar_lancamento_lista_{row.id}", width="stretch"):
                        _request_lancamento_action("cancel", row.id)
                        st.rerun()

    action_data = st.session_state.get("lancamento_action")
    if action_data:
        selected_id = int(action_data["lancamento_id"])
        selected_rows = df_lancamentos[df_lancamentos["id"] == selected_id]
        if selected_rows.empty:
            st.session_state.pop("lancamento_action", None)
        else:
            _render_lancamento_action_dialog(conn, selected_rows.iloc[0].to_dict(), user)
