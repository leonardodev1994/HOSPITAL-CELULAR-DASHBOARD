from datetime import datetime

import pandas as pd
import streamlit as st

from utils.audit import log_action
from utils.auth import current_user
from utils.dashboard_ui import page_banner, pie_chart
from utils.permissions import has_permission
from utils.quiosques import current_quiosque_id, scope_clause, scoped_params


def _pagamentos_do_dia(conn, data):
    scope, _ = scope_clause("lancamentos", prefix="AND")
    return pd.read_sql_query("""
    SELECT pagamentos.*
    FROM pagamentos
    INNER JOIN lancamentos ON lancamentos.id = pagamentos.lancamento_id
    WHERE lancamentos.data = ?
      AND COALESCE(lancamentos.status, 'Ativo') <> 'Cancelado'
    """ + scope, conn, params=scoped_params(data))


def _sangrias_do_dia(conn, data):
    scope, params = scope_clause("s", prefix="AND")
    return pd.read_sql_query("""
    SELECT
        s.id,
        s.data_hora,
        s.valor,
        s.retirado_por,
        s.usuario_nome,
        s.observacao,
        q.nome AS quiosque_nome
    FROM sangrias s
    LEFT JOIN quiosques q ON q.id = s.quiosque_id
    WHERE SUBSTR(s.data_hora, 1, 10) = ?
    """ + scope + """
    ORDER BY s.data_hora DESC, s.id DESC
    LIMIT 100
    """, conn, params=(data,) + params)


def _registrar_sangria(conn, valor, retirado_por, observacao, user):
    if float(valor or 0) <= 0:
        raise ValueError("Informe um valor maior que zero.")
    if not str(retirado_por or "").strip():
        raise ValueError("Informe quem retirou o dinheiro.")

    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sangrias (
        data_hora,
        valor,
        retirado_por,
        usuario_id,
        usuario_nome,
        observacao,
        quiosque_id
    )
    VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
    """, (
        float(valor),
        retirado_por.strip(),
        None if not user else user.get("id"),
        None if not user else user.get("nome"),
        str(observacao or "").strip(),
        current_quiosque_id(user),
    ))
    conn.commit()
    log_action(conn, user, "registrou_sangria", "sangrias", None, {
        "valor": float(valor),
        "retirado_por": retirado_por.strip(),
        "observacao": str(observacao or "").strip(),
    })


def render_caixa_diario(conn):
    cursor = conn.cursor()
    user = current_user()
    hoje = datetime.today().strftime("%Y-%m-%d")
    can_register_sangria = has_permission("register_cash_withdrawal", user)

    page_banner("tx_caixa_banner.webp", "TX System - Caixa Diário")
    st.subheader("💰 Caixa Diário")

    valor_inicial = st.number_input("Valor Inicial", min_value=0.0)

    if st.button("Abrir Caixa"):
        caixa_existente = cursor.execute("""
        SELECT id FROM caixa
        WHERE data = ? AND quiosque_id = ?
        """, (hoje, current_quiosque_id())).fetchone()

        if caixa_existente:
            st.warning("⚠️ Caixa já aberto hoje.")
        else:
            cursor.execute("""
            INSERT INTO caixa (data, valor_inicial, quiosque_id)
            VALUES (?, ?, ?)
            """, (hoje, valor_inicial, current_quiosque_id()))

            conn.commit()
            st.success("✅ Caixa aberto!")

    df_pagamentos = _pagamentos_do_dia(conn, hoje)
    df_sangrias = _sangrias_do_dia(conn, hoje)
    where_caixa, params_caixa = scope_clause()
    if has_permission("view_expenses"):
        where_despesas, params_despesas = scope_clause()
        df_despesas = pd.read_sql_query(
            f"SELECT data, valor FROM despesas{where_despesas}",
            conn,
            params=params_despesas,
        )
    else:
        df_despesas = pd.DataFrame(columns=["data", "valor"])
    df_caixa = pd.read_sql_query(
        f"SELECT data, valor_inicial FROM caixa{where_caixa}",
        conn,
        params=params_caixa,
    )

    despesas_hoje = df_despesas[df_despesas["data"] == hoje]
    caixa_hoje = df_caixa[df_caixa["data"] == hoje]

    abertura = 0
    if not caixa_hoje.empty:
        abertura = caixa_hoje.iloc[0]["valor_inicial"]

    dinheiro = df_pagamentos[df_pagamentos["forma_pagamento"] == "Dinheiro"]["valor"].sum()
    pix = df_pagamentos[df_pagamentos["forma_pagamento"] == "Pix"]["valor"].sum()
    credito = df_pagamentos[df_pagamentos["forma_pagamento"] == "Crédito"]["valor"].sum()
    debito = df_pagamentos[df_pagamentos["forma_pagamento"] == "Débito"]["valor"].sum()

    total_despesas = despesas_hoje["valor"].sum() if not despesas_hoje.empty else 0
    total_sangrias = df_sangrias["valor"].sum() if not df_sangrias.empty else 0

    caixa_final = abertura + dinheiro - total_despesas - total_sangrias
    total_geral = dinheiro + pix + credito + debito

    cols = st.columns(4 if has_permission("view_expenses") else 3)
    c1, c2 = cols[:2]
    c1.metric("🌅 Abertura", f"R$ {abertura:.2f}")
    c2.metric("💵 Dinheiro", f"R$ {dinheiro:.2f}")
    if has_permission("view_expenses"):
        cols[2].metric("💸 Despesas", f"R$ {total_despesas:.2f}")
        cols[3].metric("🧾 Caixa Atual", f"R$ {caixa_final:.2f}")
    else:
        cols[2].metric("🧾 Recebido em dinheiro", f"R$ {dinheiro:.2f}")

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📲 Pix", f"R$ {pix:.2f}")
    c2.metric("💳 Crédito", f"R$ {credito:.2f}")
    c3.metric("💳 Débito", f"R$ {debito:.2f}")
    c4.metric("🏦 Sangrias", f"R$ {total_sangrias:.2f}")

    st.metric("💰 Total Geral", f"R$ {total_geral:.2f}")

    st.divider()

    st.subheader("Sangria")
    if can_register_sangria:
        with st.expander("Registrar sangria", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                valor_sangria = st.number_input("Valor retirado", min_value=0.0, value=0.0, step=1.0)
            with col2:
                retirado_por = st.text_input("Nome de quem retirou")
            observacao_sangria = st.text_area("Observação opcional")
            if st.button("Registrar sangria", width="stretch"):
                try:
                    _registrar_sangria(conn, valor_sangria, retirado_por, observacao_sangria, user)
                    st.success("Sangria registrada.")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))
    else:
        st.caption("Seu perfil não permite registrar sangria.")

    if df_sangrias.empty:
        st.caption("Nenhuma sangria registrada hoje.")
    else:
        tabela_sangrias = df_sangrias.rename(columns={
            "data_hora": "Data/Hora",
            "valor": "Valor",
            "retirado_por": "Retirado por",
            "usuario_nome": "Registrado por",
            "quiosque_nome": "Quiosque",
            "observacao": "Observação",
        })
        st.dataframe(
            tabela_sangrias[["Data/Hora", "Valor", "Retirado por", "Registrado por", "Quiosque", "Observação"]],
            width="stretch",
            hide_index=True,
            column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
        )

    st.divider()

    if df_pagamentos.empty:
        st.info("Nenhum pagamento cadastrado hoje.")
    else:
        fig = pie_chart(df_pagamentos, "forma_pagamento", "valor", "Formas de Pagamento")
        st.plotly_chart(fig, width="stretch")
