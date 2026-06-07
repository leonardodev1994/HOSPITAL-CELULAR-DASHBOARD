from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.dashboard_ui import light_page_header, moeda
from utils.permissions import require_permission
from utils.quiosques import scope_clause


def _load_canceled_sales(conn, data_inicio, data_fim, limit=300):
    scope, params = scope_clause("l", prefix="AND")
    df = pd.read_sql_query("""
    SELECT
        l.id,
        l.data,
        q.nome AS quiosque,
        v.usuario_nome AS atendente_original,
        l.cancelado_por_nome,
        l.cancelado_por_perfil,
        l.cancelado_motivo,
        l.valor,
        l.tipo,
        l.descricao,
        l.cancelado_em
    FROM lancamentos l
    LEFT JOIN vendas v ON v.id = l.venda_id
    LEFT JOIN quiosques q ON q.id = l.quiosque_id
    WHERE COALESCE(l.status, 'Ativo') = 'Cancelado'
      AND l.data BETWEEN ? AND ?
    """ + scope + """
    ORDER BY l.cancelado_em DESC, l.id DESC
    LIMIT ?
    """, conn, params=(str(data_inicio), str(data_fim)) + params + (limit,))

    if df.empty:
        return df

    placeholders = ", ".join(["?"] * len(df))
    pagamentos = pd.read_sql_query(f"""
    SELECT lancamento_id, forma_pagamento, valor
    FROM pagamentos
    WHERE lancamento_id IN ({placeholders})
    ORDER BY id
    """, conn, params=tuple(int(value) for value in df["id"].tolist()))

    if pagamentos.empty:
        df["forma_pagamento"] = "Não informado"
        return df

    resumo = (
        pagamentos.groupby("lancamento_id")
        .apply(
            lambda grupo: " + ".join(
                f"{row.forma_pagamento}: {moeda(row.valor)}"
                for row in grupo.itertuples()
            ),
            include_groups=False,
        )
        .reset_index(name="forma_pagamento")
    )
    return df.merge(resumo, left_on="id", right_on="lancamento_id", how="left").fillna({"forma_pagamento": "Não informado"})


def render_lancamentos_cancelados(conn):
    if not require_permission("view_canceled_sales"):
        return

    light_page_header("🚫", "Lançamentos Cancelados", "Auditoria de cancelamentos, autorizações e motivos informados.")

    hoje = date.today()
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data inicial", value=hoje - timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data final", value=hoje)

    if data_inicio > data_fim:
        st.warning("A data inicial não pode ser maior que a data final.")
        return

    df = _load_canceled_sales(conn, data_inicio, data_fim)
    if df.empty:
        st.info("Nenhum lançamento cancelado no período selecionado.")
        return

    total = float(df["valor"].sum() or 0)
    c1, c2 = st.columns(2)
    c1.metric("Cancelamentos", len(df))
    c2.metric("Valor cancelado", moeda(total))

    tabela = df.rename(columns={
        "data": "Data da venda",
        "quiosque": "Loja/Quiosque",
        "atendente_original": "Atendente original",
        "cancelado_por_nome": "Autorizado por",
        "cancelado_por_perfil": "Cargo",
        "cancelado_motivo": "Motivo",
        "valor": "Valor",
        "forma_pagamento": "Forma de pagamento",
        "cancelado_em": "Cancelado em",
        "descricao": "Descrição",
        "tipo": "Tipo",
    })

    st.dataframe(
        tabela[[
            "Data da venda",
            "Loja/Quiosque",
            "Atendente original",
            "Autorizado por",
            "Cargo",
            "Motivo",
            "Valor",
            "Forma de pagamento",
            "Cancelado em",
            "Tipo",
            "Descrição",
        ]],
        width="stretch",
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )
