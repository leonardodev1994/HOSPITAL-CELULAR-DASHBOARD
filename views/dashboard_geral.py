from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from utils.dashboard_ui import PLOTLY_CONFIG, empty_state, metric_card, moeda, page_banner, page_header, pie_chart
from utils.permissions import has_permission, require_permission
from utils.quiosques import scope_clause, user_can_view_all


META_DIARIA_PADRAO = 1000.0
SANGRIA_ALERTA_PADRAO = 500.0


def _today():
    return date.today()


def _date_period(periodo):
    hoje = _today()
    if periodo == "Semana":
        return hoje - timedelta(days=hoje.weekday()), hoje
    if periodo == "Mês":
        return hoje.replace(day=1), hoje
    return hoje, hoje


def _datetime_bounds(day):
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _pct(value, total):
    total = _safe_float(total)
    if total <= 0:
        return 0
    return min(100, int(round((_safe_float(value) / total) * 100)))


def _growth_label(current, previous):
    current = _safe_float(current)
    previous = _safe_float(previous)
    if previous <= 0 and current > 0:
        return "Novo movimento"
    if previous <= 0:
        return "Sem base ontem"

    growth = ((current - previous) / previous) * 100
    arrow = "↗" if growth >= 0 else "↘"
    return f"{arrow} {growth:+.0f}% vs ontem"


def _lancamentos_periodo(conn, inicio, fim):
    scope, params = scope_clause("l", prefix="AND")
    return pd.read_sql_query(
        f"""
        SELECT
            COALESCE(l.tipo, 'Outros') AS tipo,
            COALESCE(SUM(l.valor), 0) AS valor,
            COUNT(*) AS quantidade
        FROM lancamentos l
        WHERE l.data >= ?
          AND l.data <= ?
          AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
          {scope}
        GROUP BY COALESCE(l.tipo, 'Outros')
        """,
        conn,
        params=(inicio.isoformat(), fim.isoformat()) + params,
    )


def _total_lancamentos(conn, inicio, fim, tipo=None):
    scope, params = scope_clause("l", prefix="AND")
    tipo_clause = ""
    fixed_params = [inicio.isoformat(), fim.isoformat()]
    if tipo:
        tipo_clause = " AND COALESCE(l.tipo, '') = ?"
        fixed_params.append(tipo)

    row = pd.read_sql_query(
        f"""
        SELECT COALESCE(SUM(l.valor), 0) AS valor, COUNT(*) AS quantidade
        FROM lancamentos l
        WHERE l.data >= ?
          AND l.data <= ?
          AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
          {tipo_clause}
          {scope}
        """,
        conn,
        params=tuple(fixed_params) + params,
    )
    if row.empty:
        return 0.0, 0
    return _safe_float(row.iloc[0]["valor"]), int(row.iloc[0]["quantidade"] or 0)


def _pagamentos_periodo(conn, inicio, fim):
    scope, params = scope_clause("l", prefix="AND")
    return pd.read_sql_query(
        f"""
        SELECT
            COALESCE(p.forma_pagamento, 'Não informado') AS forma_pagamento,
            COALESCE(SUM(p.valor), 0) AS valor,
            COUNT(*) AS quantidade
        FROM pagamentos p
        INNER JOIN lancamentos l ON l.id = p.lancamento_id
        WHERE l.data >= ?
          AND l.data <= ?
          AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
          {scope}
        GROUP BY COALESCE(p.forma_pagamento, 'Não informado')
        """,
        conn,
        params=(inicio.isoformat(), fim.isoformat()) + params,
    )


def _despesas_periodo(conn, inicio, fim):
    if not has_permission("view_profit"):
        return 0.0

    scope, params = scope_clause("d", prefix="AND")
    row = pd.read_sql_query(
        f"""
        SELECT COALESCE(SUM(d.valor), 0) AS total
        FROM despesas d
        WHERE d.data >= ?
          AND d.data <= ?
          {scope}
        """,
        conn,
        params=(inicio.isoformat(), fim.isoformat()) + params,
    )
    return _safe_float(row.iloc[0]["total"]) if not row.empty else 0.0


def _ultimos_lancamentos(conn, inicio, fim, tipo=None, limit=5):
    scope, params = scope_clause("l", prefix="AND")
    tipo_clause = ""
    fixed_params = [inicio.isoformat(), fim.isoformat()]
    if tipo:
        tipo_clause = " AND COALESCE(l.tipo, '') = ?"
        fixed_params.append(tipo)

    return pd.read_sql_query(
        f"""
        SELECT l.data, l.tipo, l.descricao, l.valor
        FROM lancamentos l
        WHERE l.data >= ?
          AND l.data <= ?
          AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
          {tipo_clause}
          {scope}
        ORDER BY l.data DESC, l.id DESC
        LIMIT ?
        """,
        conn,
        params=tuple(fixed_params) + params + (int(limit),),
    )


def _top_descricao(conn, inicio, fim, tipo=None, limit=5):
    scope, params = scope_clause("l", prefix="AND")
    tipo_clause = ""
    fixed_params = [inicio.isoformat(), fim.isoformat()]
    if tipo:
        tipo_clause = " AND COALESCE(l.tipo, '') = ?"
        fixed_params.append(tipo)

    return pd.read_sql_query(
        f"""
        SELECT l.descricao, COALESCE(SUM(l.valor), 0) AS valor, COUNT(*) AS quantidade
        FROM lancamentos l
        WHERE l.data >= ?
          AND l.data <= ?
          AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
          {tipo_clause}
          {scope}
        GROUP BY l.descricao
        ORDER BY valor DESC
        LIMIT ?
        """,
        conn,
        params=tuple(fixed_params) + params + (int(limit),),
    )


def _estoque_baixo(conn, limit=3):
    scope, params = scope_clause("e", prefix="AND")
    return pd.read_sql_query(
        f"""
        SELECT e.produto, e.modelo, e.quantidade, e.estoque_minimo
        FROM estoque e
        WHERE COALESCE(e.ativo, 1) = 1
          AND COALESCE(e.quantidade, 0) <= COALESCE(e.estoque_minimo, 0)
          {scope}
        ORDER BY e.quantidade ASC, e.produto ASC
        LIMIT ?
        """,
        conn,
        params=params + (int(limit),),
    )


def _os_count(conn, statuses=None):
    scope, params = scope_clause("os", prefix="AND")
    status_clause = ""
    fixed_params = []
    if statuses:
        placeholders = ", ".join(["?"] * len(statuses))
        status_clause = f" AND COALESCE(os.status, '') IN ({placeholders})"
        fixed_params.extend(statuses)
    row = pd.read_sql_query(
        f"""
        SELECT COUNT(*) AS total
        FROM ordens_servico os
        WHERE 1 = 1
          {status_clause}
          {scope}
        """,
        conn,
        params=tuple(fixed_params) + params,
    )
    return int(row.iloc[0]["total"] or 0) if not row.empty else 0


def _os_summary(conn):
    return {
        "Em reparo": _os_count(conn, ["Em reparo"]),
        "Aguardando peça": _os_count(conn, ["Aguardando peça"]),
        "Pronto para entrega": _os_count(conn, ["Pronto para entrega"]),
        "Entregues": _os_count(conn, ["Entregue", "Finalizado"]),
    }


def _sangrias_total(conn, day):
    start, end = _datetime_bounds(day)
    scope, params = scope_clause("s", prefix="AND")
    row = pd.read_sql_query(
        f"""
        SELECT COALESCE(SUM(s.valor), 0) AS total, COUNT(*) AS quantidade
        FROM sangrias s
        WHERE s.data_hora >= ?
          AND s.data_hora < ?
          {scope}
        """,
        conn,
        params=(start, end) + params,
    )
    if row.empty:
        return 0.0, 0
    return _safe_float(row.iloc[0]["total"]), int(row.iloc[0]["quantidade"] or 0)


def _ultima_sangria(conn, day):
    start, end = _datetime_bounds(day)
    scope, params = scope_clause("s", prefix="AND")
    return pd.read_sql_query(
        f"""
        SELECT s.data_hora, s.valor, s.retirado_por, s.usuario_nome, s.observacao, q.nome AS quiosque
        FROM sangrias s
        LEFT JOIN quiosques q ON q.id = s.quiosque_id
        WHERE s.data_hora >= ?
          AND s.data_hora < ?
          {scope}
        ORDER BY s.data_hora DESC, s.id DESC
        LIMIT 1
        """,
        conn,
        params=(start, end) + params,
    )


def _historico_sangrias(conn, day, limit=50):
    start, end = _datetime_bounds(day)
    scope, params = scope_clause("s", prefix="AND")
    return pd.read_sql_query(
        f"""
        SELECT s.data_hora, q.nome AS quiosque, s.retirado_por, s.usuario_nome, s.valor, s.observacao
        FROM sangrias s
        LEFT JOIN quiosques q ON q.id = s.quiosque_id
        WHERE s.data_hora >= ?
          AND s.data_hora < ?
          {scope}
        ORDER BY s.data_hora DESC, s.id DESC
        LIMIT ?
        """,
        conn,
        params=(start, end) + params + (int(limit),),
    )


def _ranking_quiosques(conn, inicio, fim):
    if not user_can_view_all():
        return pd.DataFrame()

    return pd.read_sql_query(
        """
        SELECT
            q.nome AS quiosque,
            COALESCE(SUM(l.valor), 0) AS faturamento,
            COUNT(l.id) AS vendas,
            COALESCE(AVG(l.valor), 0) AS ticket_medio
        FROM quiosques q
        LEFT JOIN lancamentos l
          ON l.quiosque_id = q.id
         AND l.data >= ?
         AND l.data <= ?
         AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
        WHERE COALESCE(q.ativo, 1) = 1
        GROUP BY q.id, q.nome
        ORDER BY faturamento DESC, vendas DESC, q.nome ASC
        LIMIT 4
        """,
        conn,
        params=(inicio.isoformat(), fim.isoformat()),
    )


def _manager_alerts(conn, total_hoje, meta, sangrias_hoje):
    alerts = []
    percent_meta = (total_hoje / meta * 100) if meta else 0

    pendencias = _os_count(conn, ["Em análise", "Em reparo", "Aguardando peça"])
    if pendencias:
        alerts.append(f"{pendencias} OS em andamento ou aguardando peça")

    baixo = _estoque_baixo(conn, limit=3)
    if not baixo.empty:
        nomes = ", ".join(
            [str(row.produto) for row in baixo.itertuples() if str(row.produto or "").strip()][:2]
        )
        alerts.append(f"Estoque baixo: {nomes or 'itens críticos'}")

    if sangrias_hoje >= SANGRIA_ALERTA_PADRAO:
        alerts.append(f"Sangrias acima de {moeda(SANGRIA_ALERTA_PADRAO)} hoje")

    if meta and percent_meta < 50:
        alerts.append(f"Meta diária abaixo de 50% ({percent_meta:.0f}%)")

    return alerts


def _render_company_status(alerts):
    total = len(alerts)
    if total == 0:
        icon, title, message, accent = "🟢", "Loja Saudável", "Tudo sob controle hoje", "#16A34A"
    elif total <= 2:
        icon, title, message, accent = "🟡", "Atenção", "Existem pontos que precisam de atenção", "#F59E0B"
    else:
        icon, title, message, accent = "🔴", "Crítica", "Ação imediata necessária", "#E63946"

    details = "".join([f"<li>{alert}</li>" for alert in alerts[:4]]) or "<li>Nenhum alerta crítico no momento.</li>"
    st.markdown(
        f"""
        <div class="company-status-card" style="--status-accent:{accent};">
            <div>
                <span>{icon} Status da empresa</span>
                <strong>{title}</strong>
                <p>{message}</p>
            </div>
            <ul>{details}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_goal_card(meta, faturado):
    percent = 0 if meta <= 0 else (faturado / meta) * 100
    progress = min(100, max(0, percent))
    if faturado >= meta:
        message = f"Meta batida! Excedeu {moeda(faturado - meta)}."
        accent = "#16A34A"
    else:
        message = f"Faltam {moeda(meta - faturado)} para bater a meta."
        accent = "#F59E0B" if percent >= 50 else "#E63946"

    st.markdown(
        f"""
        <div class="daily-goal-card" style="--goal-accent:{accent}; --goal-progress:{progress:.0f}%;">
            <div class="daily-goal-head">
                <span>Meta Diária</span>
                <strong>{percent:.0f}% concluído</strong>
            </div>
            <div class="daily-goal-value">{moeda(faturado)} <small>/ {moeda(meta)}</small></div>
            <p>{message}</p>
            <div class="daily-goal-track"><i></i></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _toggle_detail(key):
    st.session_state[key] = not st.session_state.get(key, False)


def _render_metric_with_detail(label, value, detail, accent, key):
    metric_card(label, value, detail, accent)
    st.button("ℹ️ Detalhes", key=f"{key}_btn", on_click=_toggle_detail, args=(key,), width="stretch")
    return st.session_state.get(key, False)


def _render_metric_detail(conn, inicio, fim, title, tipo=None):
    atual_valor, atual_qtd = _total_lancamentos(conn, inicio, fim, tipo=tipo)
    ontem_inicio = inicio - timedelta(days=1)
    ontem_fim = fim - timedelta(days=1)
    ontem_valor, _ = _total_lancamentos(conn, ontem_inicio, ontem_fim, tipo=tipo)
    ticket = atual_valor / atual_qtd if atual_qtd else 0

    st.markdown(f"**{title}**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Quantidade", atual_qtd)
    c2.metric("Ticket médio", moeda(ticket))
    c3.metric("Tendência", _growth_label(atual_valor, ontem_valor))

    latest = _ultimos_lancamentos(conn, inicio, fim, tipo=tipo, limit=5)
    if not latest.empty:
        st.dataframe(
            latest.rename(
                columns={
                    "data": "Data",
                    "tipo": "Tipo",
                    "descricao": "Descrição",
                    "valor": "Valor",
                }
            ),
            hide_index=True,
            width="stretch",
            column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
        )
    else:
        empty_state("Nenhum lançamento relacionado neste período.")


def _render_manager_attention(alerts):
    items = "".join([f"<li>⚠ {alert}</li>" for alert in alerts]) or "<li>Tudo sob controle no momento.</li>"
    st.markdown(
        f"""
        <div class="manager-alert-card">
            <span>Atenção do Gestor</span>
            <strong>Resumo inteligente de pontos que merecem olhar rápido</strong>
            <ul>{items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quiosque_ranking(conn, inicio, fim):
    if not user_can_view_all():
        return

    df = _ranking_quiosques(conn, inicio, fim)
    if df.empty:
        return

    medals = ["🥇", "🥈", "🥉", "4º"]
    rows = []
    for idx, row in enumerate(df.itertuples()):
        rows.append(
            f"""
            <div class="ranking-row">
                <em>{medals[idx] if idx < len(medals) else idx + 1}</em>
                <div>
                    <strong>{row.quiosque}</strong>
                    <span>{int(row.vendas or 0)} vendas • Ticket {moeda(row.ticket_medio)}</span>
                </div>
                <strong>{moeda(row.faturamento)}</strong>
            </div>
            """
        )

    st.markdown(
        f"""
        <div class="ranking-card">
            <strong>Ranking dos Quiosques</strong>
            {''.join(rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_payment_values(df_pagamentos):
    aliases = [
        ("Dinheiro", "#16A34A"),
        ("Pix", "#2563EB"),
        ("Débito", "#F59E0B"),
        ("Crédito", "#E63946"),
    ]
    values = {str(row.forma_pagamento).lower(): _safe_float(row.valor) for row in df_pagamentos.itertuples()}
    cards = []
    for label, color in aliases:
        total = sum(value for key, value in values.items() if label.lower() in key)
        cards.append(
            f"""
            <div style="--pay-accent:{color};">
                <span>{label}</span>
                <strong>{moeda(total)}</strong>
            </div>
            """
        )
    st.markdown(f"<div class='payment-value-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _render_mix_servicos_produtos(servicos, produtos):
    total = servicos + produtos
    serv_pct = _pct(servicos, total)
    prod_pct = _pct(produtos, total)
    if total <= 0:
        empty_state("Nenhum lançamento cadastrado ainda.")
        return

    st.markdown(
        f"""
        <div class="tx-mix-card">
            <strong>Serviços x Produtos</strong>
            <p>Mix de faturamento do período</p>
            <div class="tx-mix-row">
                <div><strong>Serviços</strong><span>{serv_pct}% • {moeda(servicos)}</span></div>
                <div class="tx-mix-track"><i style="width:{serv_pct}%; background:#16A34A;"></i></div>
            </div>
            <div class="tx-mix-row">
                <div><strong>Produtos</strong><span>{prod_pct}% • {moeda(produtos)}</span></div>
                <div class="tx-mix-track"><i style="width:{prod_pct}%; background:#E63946;"></i></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_os_card(conn):
    os_data = _os_summary(conn)
    st.markdown(
        f"""
        <div class="os-status-grid">
            <strong>Ordens de Serviço</strong>
            <div><span>Em reparo</span><b>{os_data["Em reparo"]}</b></div>
            <div><span>Aguardando peça</span><b>{os_data["Aguardando peça"]}</b></div>
            <div><span>Pronto para entrega</span><b>{os_data["Pronto para entrega"]}</b></div>
            <div><span>Entregues</span><b>{os_data["Entregues"]}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sangria_card(conn, day):
    total, quantidade = _sangrias_total(conn, day)
    latest = _ultima_sangria(conn, day)
    if latest.empty:
        last_text = "Nenhuma retirada hoje"
        last_value = moeda(0)
    else:
        row = latest.iloc[0]
        actor = row.get("retirado_por") or row.get("usuario_nome") or "Não informado"
        hour = str(row.get("data_hora") or "")[11:16]
        last_text = f"{hour} - {actor}"
        last_value = moeda(row.get("valor"))

    st.markdown(
        f"""
        <div class="sangria-summary-card">
            <span>Sangrias do dia</span>
            <strong>{moeda(total)}</strong>
            <p>{quantidade} retirada(s)</p>
            <small>Última: {last_text} • {last_value}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Ver histórico completo", expanded=False):
        history = _historico_sangrias(conn, day)
        if history.empty:
            empty_state("Nenhuma sangria registrada hoje.")
        else:
            st.dataframe(
                history.rename(
                    columns={
                        "data_hora": "Data/Hora",
                        "quiosque": "Quiosque",
                        "retirado_por": "Retirado por",
                        "usuario_nome": "Usuário",
                        "valor": "Valor",
                        "observacao": "Observação",
                    }
                ),
                hide_index=True,
                width="stretch",
                column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
            )


def render_dashboard_geral(conn):
    if not require_permission("view_dashboard_general"):
        return

    page_banner("tx_dashboard_banner.webp", "TX System - Dashboard Geral")
    page_header(
        "Dashboard Geral",
        "Painel executivo para acompanhar saúde da operação, meta, quiosques e alertas.",
    )

    hoje = _today()
    periodo = st.segmented_control("Período", ["Hoje", "Semana", "Mês"], default="Hoje", key="dash_geral_periodo")
    inicio, fim = _date_period(periodo)

    df_resumo = _lancamentos_periodo(conn, inicio, fim)
    df_pagamentos = _pagamentos_periodo(conn, inicio, fim)
    despesas = _despesas_periodo(conn, inicio, fim)
    faturamento = _safe_float(df_resumo["valor"].sum()) if not df_resumo.empty else 0.0
    quantidade = int(df_resumo["quantidade"].sum()) if not df_resumo.empty else 0
    servicos = _safe_float(df_resumo[df_resumo["tipo"] == "Serviço"]["valor"].sum()) if not df_resumo.empty else 0.0
    produtos = _safe_float(df_resumo[df_resumo["tipo"] == "Produto"]["valor"].sum()) if not df_resumo.empty else 0.0
    lucro = faturamento - despesas
    faturamento_hoje, _ = _total_lancamentos(conn, hoje, hoje)
    sangrias_hoje, _ = _sangrias_total(conn, hoje)
    alerts = _manager_alerts(conn, faturamento_hoje, META_DIARIA_PADRAO, sangrias_hoje)

    _render_company_status(alerts)
    st.write("")
    _render_goal_card(META_DIARIA_PADRAO, faturamento_hoje)

    st.divider()

    cols = st.columns(4 if has_permission("view_profit") else 3)
    with cols[0]:
        show_fat = _render_metric_with_detail(
            "Faturamento",
            moeda(faturamento),
            f"{quantidade} lançamentos • {periodo}",
            "#16A34A",
            "dash_geral_faturamento_detail",
        )
    with cols[1]:
        show_serv = _render_metric_with_detail(
            "Serviços",
            moeda(servicos),
            "Reparos e mão de obra",
            "#2563EB",
            "dash_geral_servicos_detail",
        )
    with cols[2]:
        show_prod = _render_metric_with_detail(
            "Produtos",
            moeda(produtos),
            "Produtos vendidos",
            "#F59E0B",
            "dash_geral_produtos_detail",
        )
    show_lucro = False
    if has_permission("view_profit"):
        with cols[3]:
            show_lucro = _render_metric_with_detail(
                "Lucro estimado",
                moeda(lucro),
                f"Despesas: {moeda(despesas)}",
                "#E63946",
                "dash_geral_lucro_detail",
            )

    if show_fat:
        _render_metric_detail(conn, inicio, fim, "Detalhes do faturamento")
    if show_serv:
        _render_metric_detail(conn, inicio, fim, "Detalhes de serviços", tipo="Serviço")
    if show_prod:
        _render_metric_detail(conn, inicio, fim, "Detalhes de produtos", tipo="Produto")
    if show_lucro:
        st.info(f"Lucro estimado considera faturamento do período menos despesas registradas: {moeda(lucro)}.")

    st.divider()

    left, right = st.columns([1.15, 0.85])
    with left:
        _render_manager_attention(alerts)
    with right:
        _render_sangria_card(conn, hoje)

    st.divider()

    rank_col, os_col = st.columns([1.1, 0.9])
    with rank_col:
        _render_quiosque_ranking(conn, inicio, fim)
    with os_col:
        _render_os_card(conn)

    st.divider()

    pay_col, mix_col = st.columns(2)
    with pay_col:
        if df_pagamentos.empty:
            empty_state("Nenhum pagamento cadastrado neste período.")
        else:
            st.plotly_chart(
                pie_chart(df_pagamentos, "forma_pagamento", "valor", "Formas de pagamento"),
                width="stretch",
                config=PLOTLY_CONFIG,
            )
            _render_payment_values(df_pagamentos)

    with mix_col:
        _render_mix_servicos_produtos(servicos, produtos)

    with st.expander("Itens mais relevantes", expanded=False):
        top = _top_descricao(conn, inicio, fim, limit=8)
        if top.empty:
            empty_state("Nenhum item relevante no período.")
        else:
            st.dataframe(
                top.rename(
                    columns={
                        "descricao": "Descrição",
                        "valor": "Faturamento",
                        "quantidade": "Quantidade",
                    }
                ),
                width="stretch",
                hide_index=True,
                column_config={"Faturamento": st.column_config.NumberColumn("Faturamento", format="R$ %.2f")},
            )
