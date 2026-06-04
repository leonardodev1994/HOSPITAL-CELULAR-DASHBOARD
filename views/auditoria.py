import json
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st

from utils.dashboard_ui import page_header
from utils.permissions import require_permission
from utils.quiosques import load_quiosques


MODULE_LABELS = {
    "lancamentos": "Lançamentos",
    "despesas": "Despesas",
    "catalogo_pecas": "Catálogo",
    "estoque": "Estoque",
    "estoque_movimentacoes": "Estoque",
    "ordens_servico": "Ordem de Serviço",
    "clientes": "Clientes",
    "caixa": "Caixa",
    "sangrias": "Caixa",
    "servicos": "Serviços",
    "usuarios": "Usuários",
}


def _module_label(entidade):
    return MODULE_LABELS.get(str(entidade or ""), str(entidade or "Sistema").replace("_", " ").title())


def _load_filter_options(conn):
    usuarios = pd.read_sql_query(
        """
        SELECT DISTINCT usuario_nome
        FROM auditoria
        WHERE usuario_nome IS NOT NULL AND TRIM(usuario_nome) <> ''
        ORDER BY usuario_nome
        LIMIT 300
        """,
        conn,
    )
    acoes = pd.read_sql_query(
        """
        SELECT DISTINCT acao
        FROM auditoria
        WHERE acao IS NOT NULL AND TRIM(acao) <> ''
        ORDER BY acao
        LIMIT 300
        """,
        conn,
    )
    modulos = pd.read_sql_query(
        """
        SELECT DISTINCT entidade
        FROM auditoria
        WHERE entidade IS NOT NULL AND TRIM(entidade) <> ''
        ORDER BY entidade
        LIMIT 300
        """,
        conn,
    )
    return usuarios, acoes, modulos


def _details_dict(value):
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def _compact_json(value):
    if value in (None, "", {}):
        return ""
    return json.dumps(value, ensure_ascii=False, default=str)


def _describe_log(row, details):
    action = str(row.get("acao") or "").replace("_", " ")
    module = _module_label(row.get("entidade"))
    entity_id = row.get("entidade_id")
    suffix = f" #{int(entity_id)}" if pd.notna(entity_id) and str(entity_id) != "" else ""

    if row.get("entidade") == "catalogo_pecas" and row.get("acao") == "importou_catalogo_pecas":
        return (
            "Importou planilha do catálogo: "
            f"{details.get('cadastrados', 0)} cadastrados, "
            f"{details.get('atualizados', 0)} atualizados, "
            f"{details.get('ignorados', 0)} ignorados"
        )

    motivo = details.get("motivo") or details.get("observacao") or details.get("cancelado_motivo")
    text = f"{action.title()} em {module}{suffix}"
    if motivo:
        text += f" | Motivo: {motivo}"
    return text


def _extract_before_after(details):
    before = details.get("dados_antigos")
    after = details.get("dados_novos")

    if before is None and "valor" in details:
        before = {"valor": details.get("valor")}
    if after is None and "status" in details:
        after = {"status": details.get("status")}

    return _compact_json(before), _compact_json(after)


def _format_audit_df(df):
    if df.empty:
        return df

    rows = []
    for row in df.to_dict("records"):
        details = _details_dict(row.get("detalhes"))
        before, after = _extract_before_after(details)
        rows.append({
            "Data/Hora": row.get("data_hora"),
            "Usuário": row.get("usuario_nome") or "Sistema",
            "Perfil": row.get("perfil") or "-",
            "Quiosque": row.get("quiosque_nome") or "-",
            "Módulo": _module_label(row.get("entidade")),
            "Ação": row.get("acao") or "-",
            "Descrição": _describe_log(row, details),
            "Antes": before,
            "Depois": after,
            "Detalhes": _compact_json(details),
        })
    return pd.DataFrame(rows)


def _build_query(filters):
    where = ["1 = 1"]
    params = []

    if filters["start"]:
        where.append("a.data_hora >= ?")
        params.append(filters["start"].isoformat())
    if filters["end"]:
        where.append("a.data_hora < ?")
        params.append((filters["end"] + timedelta(days=1)).isoformat())
    if filters["usuario"] != "Todos":
        where.append("a.usuario_nome = ?")
        params.append(filters["usuario"])
    if filters["quiosque_id"] is not None:
        where.append("a.quiosque_id = ?")
        params.append(filters["quiosque_id"])
    if filters["acao"] != "Todas":
        where.append("a.acao = ?")
        params.append(filters["acao"])
    if filters["modulo"] != "Todos":
        where.append("a.entidade = ?")
        params.append(filters["modulo"])
    if filters["busca"]:
        term = f"%{filters['busca'].strip().lower()}%"
        where.append(
            "("
            "LOWER(COALESCE(a.usuario_nome, '')) LIKE ? OR "
            "LOWER(COALESCE(a.acao, '')) LIKE ? OR "
            "LOWER(COALESCE(a.entidade, '')) LIKE ? OR "
            "LOWER(COALESCE(a.detalhes, '')) LIKE ? OR "
            "LOWER(CAST(a.entidade_id AS TEXT)) LIKE ?"
            ")"
        )
        params.extend([term, term, term, term, term])

    query = f"""
    SELECT
        a.id,
        a.data_hora,
        a.usuario_id,
        a.usuario_nome,
        COALESCE(u.perfil, '-') AS perfil,
        a.acao,
        a.entidade,
        a.entidade_id,
        a.detalhes,
        a.quiosque_id,
        COALESCE(q.nome, '-') AS quiosque_nome
    FROM auditoria a
    LEFT JOIN usuarios u ON u.id = a.usuario_id
    LEFT JOIN quiosques q ON q.id = a.quiosque_id
    WHERE {" AND ".join(where)}
    ORDER BY a.data_hora DESC, a.id DESC
    LIMIT ?
    """
    params.append(int(filters["limit"]))
    return query, tuple(params)


def _load_audit_logs(conn, filters):
    query, params = _build_query(filters)
    return pd.read_sql_query(query, conn, params=params)


def _excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Auditoria")
    output.seek(0)
    return output.getvalue()


def render_auditoria(conn):
    if not require_permission("view_audit"):
        return

    page_header(
        "Auditoria",
        "Controle de alterações, importações, cancelamentos e ações importantes do sistema.",
    )

    usuarios, acoes, modulos = _load_filter_options(conn)
    quiosques = load_quiosques(conn)

    today = date.today()
    col1, col2, col3 = st.columns(3)
    with col1:
        start = st.date_input("Data inicial", value=today - timedelta(days=30), key="audit_start")
    with col2:
        end = st.date_input("Data final", value=today, key="audit_end")
    with col3:
        limit = st.selectbox("Limite", [100, 250, 500, 1000], index=1, key="audit_limit")

    col1, col2, col3 = st.columns(3)
    with col1:
        usuario_options = ["Todos"] + usuarios["usuario_nome"].dropna().astype(str).tolist()
        usuario = st.selectbox("Usuário", usuario_options, key="audit_usuario")
    with col2:
        quiosque_options = [("Todos", None)] + [
            (row.nome, int(row.id)) for row in quiosques.itertuples()
        ]
        quiosque_label = st.selectbox("Quiosque", [label for label, _ in quiosque_options], key="audit_quiosque")
        quiosque_id = dict(quiosque_options)[quiosque_label]
    with col3:
        acao_options = ["Todas"] + acoes["acao"].dropna().astype(str).tolist()
        acao = st.selectbox("Tipo de ação", acao_options, key="audit_acao")

    col1, col2 = st.columns([1, 1.4])
    with col1:
        modulo_options = ["Todos"] + modulos["entidade"].dropna().astype(str).tolist()
        modulo = st.selectbox(
            "Módulo",
            modulo_options,
            format_func=lambda value: "Todos" if value == "Todos" else _module_label(value),
            key="audit_modulo",
        )
    with col2:
        busca = st.text_input("Buscar", placeholder="cliente, OS, produto, valor, usuário...", key="audit_busca")

    filters = {
        "start": start,
        "end": end,
        "usuario": usuario,
        "quiosque_id": quiosque_id,
        "acao": acao,
        "modulo": modulo,
        "busca": busca,
        "limit": limit,
    }

    raw_df = _load_audit_logs(conn, filters)
    audit_df = _format_audit_df(raw_df)

    st.caption(f"{len(audit_df)} registro(s) encontrados. Logs são somente leitura.")

    if audit_df.empty:
        st.info("Nenhum log encontrado para os filtros selecionados.")
        return

    st.download_button(
        "Exportar auditoria para Excel",
        data=_excel_bytes(audit_df),
        file_name=f"auditoria_tx_{today.isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    st.dataframe(
        audit_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Data/Hora": "Data/Hora",
            "Usuário": "Usuário",
            "Perfil": "Perfil",
            "Quiosque": "Quiosque",
            "Módulo": "Módulo",
            "Ação": "Ação",
            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
            "Antes": st.column_config.TextColumn("Antes", width="medium"),
            "Depois": st.column_config.TextColumn("Depois", width="medium"),
            "Detalhes": st.column_config.TextColumn("Detalhes", width="large"),
        },
    )
