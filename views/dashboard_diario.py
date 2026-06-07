from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from utils.dashboard_ui import (
    PLOTLY_CONFIG,
    empty_state,
    metric_card,
    moeda,
    page_banner,
    page_header,
    pie_chart,
)
from utils.permissions import has_permission
from utils.quiosques import scope_clause, scoped_params, user_can_view_all


FORMAS_PAGAMENTO = ["Dinheiro", "Pix", "Crédito", "Débito"]


def _moeda(valor):
    return moeda(valor)


def _render_meta_diaria(total, meta=1000):
    percentual = (float(total or 0) / float(meta or 1)) * 100
    progresso = min(percentual, 100)
    diferenca = float(total or 0) - float(meta or 0)
    if diferenca >= 0:
        status = f"Meta batida! Excedeu {_moeda(diferenca)}"
        accent = "#16A34A"
    else:
        status = f"Faltam {_moeda(abs(diferenca))} para bater a meta"
        accent = "#E63946"

    st.markdown(
        f"""
        <div class="daily-goal-card" style="--goal-accent:{accent}; --goal-progress:{progresso:.2f}%;">
            <div class="daily-goal-head">
                <span>Meta Diária</span>
                <strong>{percentual:.0f}% concluído</strong>
            </div>
            <div class="daily-goal-value">{_moeda(total)} <small>/ {_moeda(meta)}</small></div>
            <p>{status}</p>
            <div class="daily-goal-track"><i></i></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_mix_servicos_produtos(servicos, produtos):
    total = float(servicos or 0) + float(produtos or 0)
    if total <= 0:
        empty_state("Sem serviços ou produtos no período selecionado.")
        return

    rows = [("Serviços", float(servicos or 0), "#18C29C"), ("Produtos", float(produtos or 0), "#F59E0B")]
    active = [row for row in rows if row[1] > 0]
    if len(active) == 1:
        st.markdown(
            f"""
            <div class="tx-mix-card">
                <strong>Serviços x Produtos</strong>
                <p>Serviços: {_moeda(servicos)}</p>
                <p>Produtos: {_moeda(produtos)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    bars = []
    for label, value, color in rows:
        percent = (value / total) * 100 if total else 0
        bars.append(
            f"""
            <div class="tx-mix-row">
                <div><strong>{label}</strong><span>{_moeda(value)} · {percent:.0f}%</span></div>
                <div class="tx-mix-track"><i style="width:{percent:.2f}%; background:{color};"></i></div>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="tx-mix-card">
            <strong>Serviços x Produtos</strong>
            {''.join(bars)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _pagamentos_do_dia(conn, data):
    scope, params = scope_clause("lancamentos", prefix="AND")
    return pd.read_sql_query("""
    SELECT
        pagamentos.id,
        pagamentos.lancamento_id,
        pagamentos.forma_pagamento,
        pagamentos.valor,
        lancamentos.tipo,
        lancamentos.descricao,
        lancamentos.data
    FROM pagamentos
    INNER JOIN lancamentos ON lancamentos.id = pagamentos.lancamento_id
    WHERE lancamentos.data = ?
      AND COALESCE(lancamentos.status, 'Ativo') <> 'Cancelado'
    """ + scope, conn, params=scoped_params(data))


def _caixa_inicial_do_dia(conn, data):
    where_caixa, params_caixa = scope_clause()
    row = pd.read_sql_query(
        f"""
        SELECT COALESCE(SUM(valor_inicial), 0) AS valor
        FROM caixa
        {where_caixa + " AND" if where_caixa else " WHERE"} data = ?
        """,
        conn,
        params=params_caixa + (data,),
    )
    return float(row.iloc[0]["valor"] or 0) if not row.empty else 0.0


def _sangrias_do_dia(conn, data, limit=100):
    scope, params = scope_clause("s", prefix="AND")
    inicio = datetime.strptime(data, "%Y-%m-%d")
    fim = inicio + timedelta(days=1)
    if getattr(conn, "backend", "sqlite") == "postgres":
        date_params = (inicio, fim)
    else:
        date_params = (inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"))

    return pd.read_sql_query(
        f"""
        SELECT
            s.data_hora,
            s.usuario_nome,
            s.retirado_por,
            s.valor,
            s.observacao,
            q.nome AS quiosque_nome
        FROM sangrias s
        LEFT JOIN quiosques q ON q.id = s.quiosque_id
        WHERE s.data_hora >= ? AND s.data_hora < ?
        {scope}
        ORDER BY s.data_hora DESC, s.id DESC
        LIMIT ?
        """,
        conn,
        params=date_params + params + (int(limit),),
    )


def _total_sangrias_do_dia(conn, data):
    scope, params = scope_clause("s", prefix="AND")
    inicio = datetime.strptime(data, "%Y-%m-%d")
    fim = inicio + timedelta(days=1)
    if getattr(conn, "backend", "sqlite") == "postgres":
        date_params = (inicio, fim)
    else:
        date_params = (inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d"))

    row = pd.read_sql_query(
        f"""
        SELECT COALESCE(SUM(s.valor), 0) AS total
        FROM sangrias s
        WHERE s.data_hora >= ? AND s.data_hora < ?
        {scope}
        """,
        conn,
        params=date_params + params,
    )
    return float(row.iloc[0]["total"] or 0) if not row.empty else 0.0


def _despesas_do_dia(conn, data):
    if not has_permission("view_expenses"):
        return pd.DataFrame(columns=["data", "valor", "descricao"])

    where_despesas, params_despesas = scope_clause()
    return pd.read_sql_query(
        f"""
        SELECT data, valor, descricao
        FROM despesas
        {where_despesas + " AND" if where_despesas else " WHERE"} data = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        conn,
        params=params_despesas + (data,),
    )


def _formatar_pagamentos_lancamento(grupo):
    pagamentos = (
        grupo.groupby("forma_pagamento")["valor"]
        .sum()
        .reset_index()
    )

    ordem = {forma: indice for indice, forma in enumerate(FORMAS_PAGAMENTO)}
    pagamentos["ordem"] = pagamentos["forma_pagamento"].map(ordem).fillna(99)
    pagamentos = pagamentos.sort_values(["ordem", "forma_pagamento"])

    return " + ".join(
        f"{linha.forma_pagamento}: {_moeda(linha.valor)}"
        for linha in pagamentos.itertuples()
    )


def _pagamentos_por_lancamento(df_pagamentos):
    if df_pagamentos.empty:
        return pd.DataFrame(columns=["lancamento_id", "pagamento_calculado"])

    return (
        df_pagamentos.groupby("lancamento_id")
        .apply(_formatar_pagamentos_lancamento, include_groups=False)
        .reset_index(name="pagamento_calculado")
    )


def _montar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo):
    df_tipo = df_lancamentos[df_lancamentos["tipo"] == tipo].copy()

    if df_tipo.empty:
        return df_tipo

    pagamentos_lancamento = _pagamentos_por_lancamento(df_pagamentos)
    df_tipo = df_tipo.merge(
        pagamentos_lancamento,
        left_on="id",
        right_on="lancamento_id",
        how="left",
    )

    pagamento_antigo = df_tipo["pagamento"] if "pagamento" in df_tipo.columns else ""
    df_tipo["Pagamento"] = (
        df_tipo["pagamento_calculado"]
        .fillna(pagamento_antigo)
        .fillna("Não informado")
        .replace("", "Não informado")
    )

    tabela = df_tipo[["data", "descricao", "Pagamento", "valor"]].rename(columns={
        "data": "Data",
        "descricao": "Descrição",
        "valor": "Valor",
    })

    return tabela.sort_values(["Data", "Descrição"]).reset_index(drop=True)


def _mostrar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo):
    tabela = _montar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo)

    if tabela.empty:
        empty_state(f"Nenhum {tipo.lower()} cadastrado no dia selecionado.")
        return

    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
            "Pagamento": st.column_config.TextColumn("Pagamento", width="medium"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )


def _total_por_forma(df_pagamentos, forma, tipo=None):
    filtro = df_pagamentos["forma_pagamento"] == forma

    if tipo:
        filtro = filtro & (df_pagamentos["tipo"] == tipo)

    return df_pagamentos[filtro]["valor"].sum()


def _trend_label(valor_atual, valor_anterior):
    atual = float(valor_atual or 0)
    anterior = float(valor_anterior or 0)
    if anterior <= 0:
        return "↗ novo" if atual > 0 else "0%"

    variacao = ((atual - anterior) / anterior) * 100
    seta = "↗" if variacao >= 0 else "↘"
    sinal = "+" if variacao >= 0 else ""
    return f"{seta} {sinal}{variacao:.0f}%"


def _toggle_detail(key):
    st.session_state[key] = not st.session_state.get(key, False)


def _render_finance_card(title, value, detail, accent, key):
    metric_card(title, _moeda(value), detail, accent)
    st.button(
        "ℹ️ Detalhes" if not st.session_state.get(key, False) else "Fechar detalhes",
        key=f"toggle_{key}",
        width="stretch",
        on_click=_toggle_detail,
        args=(key,),
    )


def _render_clickable_metric(title, value, detail, accent, key):
    metric_card(title, value, detail, accent)
    st.button(
        "ℹ️ Detalhes" if not st.session_state.get(key, False) else "Fechar detalhes",
        key=f"toggle_{key}",
        width="stretch",
        on_click=_toggle_detail,
        args=(key,),
    )


def _render_sales_card_details(df_dia, tipo=None):
    data = df_dia.copy()
    if tipo:
        data = data[data["tipo"] == tipo]
    quantidade = len(data)
    total = data["valor"].sum() if not data.empty else 0
    ticket = total / quantidade if quantidade else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Quantidade", quantidade)
    c2.metric("Total", _moeda(total))
    c3.metric("Ticket médio", _moeda(ticket))
    if data.empty:
        empty_state("Nenhum lançamento para detalhar.")
        return
    if tipo:
        ranking = (
            data.groupby("descricao", as_index=False)
            .agg(valor=("valor", "sum"), quantidade=("id", "count"))
            .sort_values("valor", ascending=False)
            .head(5)
        )
        st.dataframe(
            ranking.rename(columns={"descricao": "Descrição", "valor": "Valor", "quantidade": "Qtd"}),
            width="stretch",
            hide_index=True,
            column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
        )
    else:
        ultimos = data.sort_values("id", ascending=False).head(5)[["data", "tipo", "descricao", "valor"]]
        st.dataframe(
            ultimos.rename(columns={"data": "Data", "tipo": "Tipo", "descricao": "Descrição", "valor": "Valor"}),
            width="stretch",
            hide_index=True,
            column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
        )


def _load_manager_alerts(conn, data_filtro, total, meta):
    alerts = []
    scope_l, params_l = scope_clause("l", prefix="AND")
    pendencias = pd.read_sql_query(
        """
        SELECT COUNT(*) AS total
        FROM lancamentos l
        WHERE COALESCE(l.status, 'Ativo') NOT IN ('Ativo', 'Cancelado')
        """ + scope_l,
        conn,
        params=params_l,
    )
    pending_count = int(pendencias.iloc[0]["total"] or 0) if not pendencias.empty else 0
    if pending_count:
        alerts.append(f"⚠️ {pending_count} pendência(s) em aberto")

    scope_e, params_e = scope_clause("e", prefix="AND")
    low_stock = pd.read_sql_query(
        """
        SELECT e.produto, e.modelo, e.quantidade, e.estoque_minimo
        FROM estoque e
        WHERE COALESCE(e.ativo, 1) = 1
          AND COALESCE(e.quantidade, 0) <= COALESCE(e.estoque_minimo, 0)
        """ + scope_e + """
        ORDER BY e.quantidade ASC, e.produto
        LIMIT 3
        """,
        conn,
        params=params_e,
    )
    if not low_stock.empty:
        first = low_stock.iloc[0]
        label = f"{first['produto'] or ''} {first['modelo'] or ''}".strip()
        alerts.append(f"⚠️ Estoque baixo: {label}")

    total_sangrias = _total_sangrias_do_dia(conn, data_filtro)
    if total_sangrias > 500:
        alerts.append(f"⚠️ Sangria acima de R$ 500 hoje: {_moeda(total_sangrias)}")

    percent_meta = (float(total or 0) / float(meta or 1)) * 100
    if percent_meta < 50:
        alerts.append(f"⚠️ Meta diária abaixo de 50% ({percent_meta:.0f}%)")

    scope_os, params_os = scope_clause("os", prefix="AND")
    os_paradas = pd.read_sql_query(
        """
        SELECT COUNT(*) AS total
        FROM ordens_servico os
        WHERE COALESCE(os.status, '') IN ('Em análise', 'Em reparo', 'Aguardando peça')
        """ + scope_os,
        conn,
        params=params_os,
    )
    os_count = int(os_paradas.iloc[0]["total"] or 0) if not os_paradas.empty else 0
    if os_count:
        alerts.append(f"⚠️ {os_count} OS parada(s) ou em andamento")

    return alerts


def _render_manager_attention(conn, data_filtro, total, meta):
    alerts = _load_manager_alerts(conn, data_filtro, total, meta)
    if not alerts:
        alerts = ["Tudo certo no momento. Nenhum alerta crítico encontrado."]
    html = "".join(f"<li>{alert}</li>" for alert in alerts[:6])
    st.markdown(
        f"""
        <div class="manager-alert-card">
            <div>
                <span>🚨 Atenção do Gestor</span>
                <strong>Pontos que merecem ação rápida</strong>
            </div>
            <ul>{html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ranking_period_bounds(mode, selected_date, start=None, end=None):
    if mode == "Hoje":
        return selected_date.strftime("%Y-%m-%d"), selected_date.strftime("%Y-%m-%d")
    if mode == "Mês":
        month_start = selected_date.replace(day=1)
        return month_start.strftime("%Y-%m-%d"), selected_date.strftime("%Y-%m-%d")
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _load_quiosque_ranking(conn, start_date, end_date):
    return pd.read_sql_query(
        """
        SELECT
            q.nome AS quiosque,
            COALESCE(SUM(l.valor), 0) AS faturamento
        FROM quiosques q
        LEFT JOIN lancamentos l
          ON l.quiosque_id = q.id
         AND l.data >= ?
         AND l.data <= ?
         AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
        WHERE COALESCE(q.ativo, 1) = 1
        GROUP BY q.id, q.nome
        ORDER BY faturamento DESC, q.id
        LIMIT 4
        """,
        conn,
        params=(start_date, end_date),
    )


def _render_quiosque_ranking(conn, selected_date):
    if not user_can_view_all():
        return
    st.subheader("Ranking dos Quiosques")
    mode = st.segmented_control("Período do ranking", ["Hoje", "Mês", "Período personalizado"], default="Hoje")
    start_date = selected_date
    end_date = selected_date
    if mode == "Período personalizado":
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Início do ranking", value=selected_date.replace(day=1), key="ranking_inicio")
        with c2:
            end_date = st.date_input("Fim do ranking", value=selected_date, key="ranking_fim")
    start, end = _ranking_period_bounds(mode, selected_date, start_date, end_date)
    ranking = _load_quiosque_ranking(conn, start, end)
    medals = ["🥇", "🥈", "🥉", "4️⃣"]
    items = []
    for index, row in enumerate(ranking.itertuples()):
        items.append(
            f"""
            <div class="ranking-row">
                <span>{medals[index]}</span>
                <strong>{row.quiosque}</strong>
                <em>{_moeda(row.faturamento)}</em>
            </div>
            """
        )
    st.markdown(f"<div class='ranking-card'>{''.join(items)}</div>", unsafe_allow_html=True)


def _render_money_details(conn, data_filtro, df_pagamentos, total_dinheiro):
    caixa_inicial = _caixa_inicial_do_dia(conn, data_filtro)
    df_sangrias = _sangrias_do_dia(conn, data_filtro, limit=100)
    df_despesas = _despesas_do_dia(conn, data_filtro)
    total_sangrias = df_sangrias["valor"].sum() if not df_sangrias.empty else 0
    total_despesas = df_despesas["valor"].sum() if not df_despesas.empty else 0
    saldo = caixa_inicial + float(total_dinheiro or 0) - total_sangrias - total_despesas
    quantidade = len(df_pagamentos[df_pagamentos["forma_pagamento"] == "Dinheiro"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total em dinheiro", _moeda(total_dinheiro))
    c2.metric("Caixa inicial", _moeda(caixa_inicial))
    c3.metric("Saldo atual em caixa", _moeda(saldo))
    c1, c2, c3 = st.columns(3)
    c1.metric("Sangrias", _moeda(total_sangrias))
    c2.metric("Despesas do dia", _moeda(total_despesas))
    c3.metric("Vendas em dinheiro", quantidade)


def _render_payment_details(df_pagamentos, forma, total_dia, total_geral):
    df_forma = df_pagamentos[df_pagamentos["forma_pagamento"] == forma].copy()
    quantidade = len(df_forma)
    ticket = float(total_dia or 0) / quantidade if quantidade else 0
    participacao = (float(total_dia or 0) / float(total_geral or 1)) * 100 if total_geral else 0

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Total {forma}", _moeda(total_dia))
    c2.metric("Quantidade de vendas", quantidade)
    c3.metric("Ticket médio", _moeda(ticket))
    if forma in {"Crédito", "Débito"}:
        st.caption(f"Participação no faturamento do dia: {participacao:.0f}%")
    if forma == "Pix" and not df_forma.empty:
        st.markdown("**Últimas 5 vendas Pix do dia**")
        ultimas = df_forma.sort_values("id", ascending=False).head(5)[["descricao", "valor"]]
        st.dataframe(
            ultimas.rename(columns={"descricao": "Descrição", "valor": "Valor"}),
            width="stretch",
            hide_index=True,
            column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
        )


def _render_sangria_details(conn, data_filtro):
    df_sangrias = _sangrias_do_dia(conn, data_filtro, limit=200)
    total_sangrias = df_sangrias["valor"].sum() if not df_sangrias.empty else 0
    ultima = df_sangrias.iloc[0] if not df_sangrias.empty else None

    c1, c2 = st.columns(2)
    c1.metric("Total de sangrias do dia", _moeda(total_sangrias))
    if ultima is not None:
        hora = pd.to_datetime(ultima["data_hora"], errors="coerce")
        hora_label = hora.strftime("%H:%M") if pd.notna(hora) else "-"
        c2.metric("Última sangria", _moeda(ultima["valor"]), f"{hora_label} - {ultima['retirado_por'] or ultima['usuario_nome'] or '-'}")
    else:
        c2.metric("Última sangria", _moeda(0))

    if df_sangrias.empty:
        empty_state("Nenhuma sangria registrada no dia.")
        return

    tabela = df_sangrias.copy()
    tabela["data_hora"] = pd.to_datetime(tabela["data_hora"], errors="coerce")
    tabela["Data"] = tabela["data_hora"].dt.strftime("%d/%m/%Y")
    tabela["Hora"] = tabela["data_hora"].dt.strftime("%H:%M")
    tabela = tabela.rename(columns={
        "usuario_nome": "Usuário",
        "retirado_por": "Retirado por",
        "quiosque_nome": "Quiosque",
        "valor": "Valor retirado",
        "observacao": "Observação",
    })
    st.dataframe(
        tabela[["Data", "Hora", "Usuário", "Retirado por", "Quiosque", "Valor retirado", "Observação"]],
        width="stretch",
        hide_index=True,
        column_config={"Valor retirado": st.column_config.NumberColumn("Valor retirado", format="R$ %.2f")},
    )


def _render_total_details(totals, meta):
    bruto = totals["total"]
    liquido = bruto - totals["sangrias"]
    percentual_meta = (bruto / meta) * 100 if meta else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dinheiro", _moeda(totals["Dinheiro"]))
    c2.metric("Pix", _moeda(totals["Pix"]))
    c3.metric("Crédito", _moeda(totals["Crédito"]))
    c4.metric("Débito", _moeda(totals["Débito"]))
    c1, c2, c3 = st.columns(3)
    c1.metric("Sangrias", _moeda(totals["sangrias"]))
    c2.metric("Faturamento bruto", _moeda(bruto))
    c3.metric("Faturamento líquido", _moeda(liquido), f"Meta: {percentual_meta:.0f}%")


def _render_financial_summary(conn, data_filtro, df_pagamentos, df_pagamentos_anterior, total, meta):
    totals = {
        forma: _total_por_forma(df_pagamentos, forma)
        for forma in FORMAS_PAGAMENTO
    }
    previous = {
        forma: _total_por_forma(df_pagamentos_anterior, forma)
        for forma in FORMAS_PAGAMENTO
    }
    df_sangrias_preview = _sangrias_do_dia(conn, data_filtro, limit=1)
    total_sangrias_preview = _total_sangrias_do_dia(conn, data_filtro)
    ultima_sangria = "Sem retirada hoje"
    if not df_sangrias_preview.empty:
        latest = df_sangrias_preview.iloc[0]
        hora = pd.to_datetime(latest["data_hora"], errors="coerce")
        hora_label = hora.strftime("%H:%M") if pd.notna(hora) else "-"
        ultima_sangria = f"Última: {hora_label} - {latest['retirado_por'] or latest['usuario_nome'] or '-'}"

    totals["sangrias"] = total_sangrias_preview
    totals["total"] = total

    st.subheader("Resumo financeiro")
    c1, c2, c3 = st.columns(3)
    with c1:
        _render_finance_card("💵 Dinheiro", totals["Dinheiro"], _trend_label(totals["Dinheiro"], previous["Dinheiro"]), "#16A34A", "finance_dinheiro")
    with c2:
        _render_finance_card("📲 Pix", totals["Pix"], _trend_label(totals["Pix"], previous["Pix"]), "#18C29C", "finance_pix")
    with c3:
        _render_finance_card("💳 Crédito", totals["Crédito"], _trend_label(totals["Crédito"], previous["Crédito"]), "#5B8DEF", "finance_credito")
    c1, c2, c3 = st.columns(3)
    with c1:
        _render_finance_card("💳 Débito", totals["Débito"], _trend_label(totals["Débito"], previous["Débito"]), "#F59E0B", "finance_debito")
    with c2:
        _render_finance_card("💸 Sangrias", totals["sangrias"], ultima_sangria, "#E63946", "finance_sangrias")
    with c3:
        _render_finance_card("🏆 Total Geral", total, f"Meta {(total / meta) * 100 if meta else 0:.0f}%", "#111827", "finance_total")

    if st.session_state.get("finance_dinheiro"):
        with st.expander("Detalhes de Dinheiro", expanded=True):
            _render_money_details(conn, data_filtro, df_pagamentos, totals["Dinheiro"])
    if st.session_state.get("finance_pix"):
        with st.expander("Detalhes de Pix", expanded=True):
            _render_payment_details(df_pagamentos, "Pix", totals["Pix"], total)
    if st.session_state.get("finance_credito"):
        with st.expander("Detalhes de Crédito", expanded=True):
            _render_payment_details(df_pagamentos, "Crédito", totals["Crédito"], total)
    if st.session_state.get("finance_debito"):
        with st.expander("Detalhes de Débito", expanded=True):
            _render_payment_details(df_pagamentos, "Débito", totals["Débito"], total)
    if st.session_state.get("finance_sangrias"):
        with st.expander("Histórico de Sangrias", expanded=True):
            _render_sangria_details(conn, data_filtro)
    if st.session_state.get("finance_total"):
        with st.expander("Detalhes do Total Geral", expanded=True):
            _render_total_details(totals, meta)


def _render_pagamentos_por_tipo(df_pagamentos, tipo, titulo):
    st.subheader(titulo)

    df_tipo = df_pagamentos[df_pagamentos["tipo"] == tipo]

    c1, c2, c3, c4 = st.columns(4)
    colunas = [c1, c2, c3, c4]
    accents = ["#5B8DEF", "#18C29C", "#A855F7", "#F59E0B"]

    for coluna, forma, accent in zip(colunas, FORMAS_PAGAMENTO, accents):
        total = _total_por_forma(df_pagamentos, forma, tipo)
        with coluna:
            metric_card(forma, _moeda(total), f"{tipo}", accent)

    if df_tipo.empty:
        empty_state(f"Nenhum pagamento de {tipo.lower()} no dia selecionado.")


def _safe_date_range(df):
    if df.empty:
        hoje = datetime.today().date()
        return hoje, hoje

    datas = pd.to_datetime(df["data"], errors="coerce").dropna()
    if datas.empty:
        hoje = datetime.today().date()
        return hoje, hoje

    return datas.min().date(), datas.max().date()


def _resumo_top_itens(df_dia):
    if df_dia.empty:
        return pd.DataFrame(columns=["descricao", "valor", "quantidade"])

    return (
        df_dia.groupby("descricao", as_index=False)
        .agg(valor=("valor", "sum"), quantidade=("id", "count"))
        .sort_values("valor", ascending=False)
        .head(8)
    )


def _render_tabela_operacional(df_lancamentos, df_pagamentos, tipo, titulo, accent):
    df_tipo = df_lancamentos[df_lancamentos["tipo"] == tipo]
    total_tipo = df_tipo["valor"].sum() if not df_tipo.empty else 0
    quantidade = len(df_tipo)
    ticket_medio = total_tipo / quantidade if quantidade else 0

    st.markdown(
        f"""
        <div class="section-panel" style="border-left-color:{accent};">
            <div class="section-panel-header">
                <div>
                    <h3>{titulo}</h3>
                    <p>Detalhamento dos lançamentos do dia selecionado</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Quantidade", str(quantidade), f"{tipo.lower()} no dia", accent)
    with c2:
        metric_card("Total", _moeda(total_tipo), "Faturamento", accent)
    with c3:
        metric_card("Ticket médio", _moeda(ticket_medio), "Média por lançamento", accent)

    _mostrar_tabela_lancamentos(df_lancamentos, df_pagamentos, tipo)


def render_dashboard_diario(conn):
    where_lancamentos, params_lancamentos = scope_clause()
    status_filter = "COALESCE(status, 'Ativo') <> 'Cancelado'"
    where_lancamentos = (
        where_lancamentos + " AND " + status_filter
        if where_lancamentos
        else " WHERE " + status_filter
    )
    df = pd.read_sql_query(
        f"SELECT id, data, tipo, descricao, valor FROM lancamentos{where_lancamentos}",
        conn,
        params=params_lancamentos,
    )
    if has_permission("view_profit"):
        where_despesas, params_despesas = scope_clause()
        df_despesas = pd.read_sql_query(
            f"SELECT data, valor FROM despesas{where_despesas}",
            conn,
            params=params_despesas,
        )
    else:
        df_despesas = pd.DataFrame(columns=["data", "valor"])

    min_date, max_date = _safe_date_range(df)
    selected_date = st.date_input(
        "Escolha o dia da análise",
        value=max_date,
        min_value=min_date,
        max_value=max(datetime.today().date(), max_date),
    )
    data_filtro = selected_date.strftime("%Y-%m-%d")
    data_anterior = (selected_date - timedelta(days=1)).strftime("%Y-%m-%d")

    page_banner("tx_dashboard_diario_banner.webp", "TX System - Dashboard Diário")
    page_header(
        "Dashboard Diário",
        f"Análise operacional de {selected_date.strftime('%d/%m/%Y')}",
    )

    df_pagamentos = _pagamentos_do_dia(conn, data_filtro)
    df_pagamentos_anterior = _pagamentos_do_dia(conn, data_anterior)
    df_dia = df[df["data"] == data_filtro] if not df.empty else df
    df_anterior = df[df["data"] == data_anterior] if not df.empty else df
    df_despesas_dia = df_despesas[df_despesas["data"] == data_filtro] if not df_despesas.empty else df_despesas

    total = df_dia["valor"].sum() if not df_dia.empty else 0
    total_anterior = df_anterior["valor"].sum() if not df_anterior.empty else 0
    servicos = df_dia[df_dia["tipo"] == "Serviço"]["valor"].sum() if not df_dia.empty else 0
    produtos = df_dia[df_dia["tipo"] == "Produto"]["valor"].sum() if not df_dia.empty else 0
    despesas = df_despesas_dia["valor"].sum() if not df_despesas_dia.empty else 0
    lucro = total - despesas
    diferenca = total - total_anterior
    diferenca_label = f"{_moeda(diferenca)} vs. dia anterior"

    meta = 1000

    _render_manager_attention(conn, data_filtro, total, meta)

    st.divider()

    cols = st.columns(4 if has_permission("view_profit") else 3)
    c1, c2, c3 = cols[:3]
    with c1:
        _render_clickable_metric("💰 Faturamento", _moeda(total), diferenca_label, "#5B8DEF", "daily_detail_faturamento")
    with c2:
        _render_clickable_metric("🔧 Serviços", _moeda(servicos), f"{len(df_dia[df_dia['tipo'] == 'Serviço']) if not df_dia.empty else 0} lançamentos", "#18C29C", "daily_detail_servicos")
    with c3:
        _render_clickable_metric("📦 Produtos", _moeda(produtos), f"{len(df_dia[df_dia['tipo'] == 'Produto']) if not df_dia.empty else 0} vendas", "#F59E0B", "daily_detail_produtos")
    if has_permission("view_profit"):
        with cols[3]:
            metric_card("Lucro estimado", _moeda(lucro), f"Despesas: {_moeda(despesas)}", "#EF4444")

    if st.session_state.get("daily_detail_faturamento"):
        with st.expander("Detalhes do Faturamento", expanded=True):
            _render_sales_card_details(df_dia)
    if st.session_state.get("daily_detail_servicos"):
        with st.expander("Detalhes dos Serviços", expanded=True):
            _render_sales_card_details(df_dia, "Serviço")
    if st.session_state.get("daily_detail_produtos"):
        with st.expander("Detalhes dos Produtos", expanded=True):
            _render_sales_card_details(df_dia, "Produto")

    st.divider()

    _render_meta_diaria(total, meta)

    st.divider()

    _render_financial_summary(conn, data_filtro, df_pagamentos, df_pagamentos_anterior, total, meta)

    st.divider()

    _render_quiosque_ranking(conn, selected_date)

    if user_can_view_all():
        st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if df_pagamentos.empty:
            empty_state("Sem pagamentos no dia selecionado.")
        else:
            resumo_pag = df_pagamentos.groupby("forma_pagamento", as_index=False)["valor"].sum()
            st.plotly_chart(
                pie_chart(resumo_pag, "forma_pagamento", "valor", "Formas de pagamento"),
                width="stretch",
                config=PLOTLY_CONFIG,
            )
    with col2:
        _render_mix_servicos_produtos(servicos, produtos)

    top_itens = _resumo_top_itens(df_dia)
    if not top_itens.empty:
        with st.expander("Itens com maior faturamento", expanded=False):
            st.dataframe(
                top_itens.rename(columns={"descricao": "Descrição", "valor": "Valor", "quantidade": "Qtd"}),
                width="stretch",
                hide_index=True,
                column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
            )

    _render_pagamentos_por_tipo(
        df_pagamentos,
        "Serviço",
        "Formas de Pagamento dos Serviços",
    )

    st.divider()

    _render_pagamentos_por_tipo(
        df_pagamentos,
        "Produto",
        "Formas de Pagamento dos Produtos",
    )

    st.divider()

    _render_tabela_operacional(
        df_dia,
        df_pagamentos,
        "Serviço",
        "Serviços Realizados",
        "#18C29C",
    )

    st.divider()

    _render_tabela_operacional(
        df_dia,
        df_pagamentos,
        "Produto",
        "Produtos Vendidos",
        "#F59E0B",
    )

    st.divider()

    st.subheader("Resumo Final")
    metric_card("Faturamento Total do Dia", _moeda(total), "Serviços + Produtos", "#5B8DEF")
