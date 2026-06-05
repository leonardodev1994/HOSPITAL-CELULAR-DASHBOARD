from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import execute_insert_returning_id
from utils.audit import log_action
from utils.auth import current_user
from utils.dashboard_ui import moeda, page_banner
from utils.estoque import load_stock, produto_label, reduce_stock, restore_stock
from utils.quiosques import current_quiosque_id, load_quiosques, scope_clause, user_can_view_all
from utils.sales_authorization import can_directly_change_sale, validate_sale_authorization
from utils.servicos import load_services, servico_label
from utils.text import search_matches


def _load_lancamentos(conn, data_inicio=None, data_fim=None, limit=100):
    scope, params = scope_clause("l", prefix="AND")
    filters = ["COALESCE(l.status, 'Ativo') <> 'Cancelado'"]
    query_params = []

    if data_inicio:
        filters.append("l.data >= ?")
        query_params.append(str(data_inicio))
    if data_fim:
        filters.append("l.data <= ?")
        query_params.append(str(data_fim))

    where_sql = " WHERE " + " AND ".join(filters) + scope
    return pd.read_sql_query("""
    SELECT
        l.id,
        l.data,
        l.tipo,
        l.descricao,
        l.valor,
        l.produto_id,
        l.quantidade,
        l.venda_id,
        l.venda_item_id,
        l.preco_original,
        l.preco_vendido,
        l.diferenca_preco,
        l.observacao_alteracao_preco,
        l.usuario_responsavel_preco,
        l.data_hora_alteracao_preco,
        l.status,
        l.quiosque_id,
        q.nome AS quiosque_nome,
        v.usuario_nome AS usuario_responsavel
    FROM lancamentos l
    LEFT JOIN quiosques q ON q.id = l.quiosque_id
    LEFT JOIN vendas v ON v.id = l.venda_id
    """ + where_sql + """
    ORDER BY l.data DESC, l.id DESC
    LIMIT ?
    """, conn, params=tuple(query_params) + params + (int(limit),))


def _update_venda_status(conn, venda_id, sale_quiosque_id, authorizer=None, motivo=""):
    if not venda_id:
        return

    cursor = conn.cursor()
    total_ativo = cursor.execute("""
    SELECT COALESCE(SUM(valor), 0)
    FROM lancamentos
    WHERE venda_id = ? AND quiosque_id = ? AND COALESCE(status, 'Ativo') <> 'Cancelado'
    """, (int(venda_id), int(sale_quiosque_id))).fetchone()[0]

    if float(total_ativo or 0) <= 0:
        cursor.execute("""
        UPDATE vendas
        SET total = 0,
            status = 'Cancelada',
            cancelado_em = COALESCE(cancelado_em, CURRENT_TIMESTAMP),
            cancelado_por_id = COALESCE(cancelado_por_id, ?),
            cancelado_por_nome = COALESCE(cancelado_por_nome, ?),
            cancelado_por_perfil = COALESCE(cancelado_por_perfil, ?),
            cancelado_motivo = COALESCE(cancelado_motivo, ?)
        WHERE id = ? AND quiosque_id = ?
        """, (
            None if not authorizer else authorizer.get("id"),
            None if not authorizer else authorizer.get("nome"),
            None if not authorizer else authorizer.get("perfil"),
            motivo,
            int(venda_id),
            int(sale_quiosque_id),
        ))
    else:
        cursor.execute("""
        UPDATE vendas
        SET total = ?, status = 'Ativa'
        WHERE id = ? AND quiosque_id = ?
        """, (float(total_ativo), int(venda_id), int(sale_quiosque_id)))


def _stock_return_for_cancel(conn, lancamento, authorizer):
    produto_id = lancamento.get("produto_id")
    quantidade = lancamento.get("quantidade")
    if lancamento.get("tipo") != "Produto" or not produto_id or not quantidade:
        return

    cursor = conn.cursor()
    sale_quiosque_id = int(lancamento.get("quiosque_id") or current_quiosque_id())
    cursor.execute("""
    UPDATE estoque
    SET quantidade = COALESCE(quantidade, 0) + ?,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ? AND quiosque_id = ?
    """, (float(quantidade), int(produto_id), sale_quiosque_id))
    cursor.execute("""
    INSERT INTO estoque_movimentacoes (
        produto_id,
        data,
        tipo,
        quantidade,
        motivo,
        lancamento_id,
        responsavel,
        quiosque_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        int(produto_id),
        datetime.today().strftime("%Y-%m-%d"),
        "Entrada",
        float(quantidade),
        "Cancelamento de venda",
        int(lancamento["id"]),
        None if not authorizer else authorizer.get("nome"),
        sale_quiosque_id,
    ))


def _sync_pagamentos_valor(conn, lancamento_id, novo_valor):
    cursor = conn.cursor()
    pagamentos = cursor.execute("""
    SELECT id, valor
    FROM pagamentos
    WHERE lancamento_id = ?
    ORDER BY id
    """, (int(lancamento_id),)).fetchall()

    if not pagamentos:
        return

    total_atual = sum(float(row[1] or 0) for row in pagamentos)
    restante = round(float(novo_valor), 2)

    for index, row in enumerate(pagamentos):
        pagamento_id = int(row[0])
        if index == len(pagamentos) - 1:
            novo_pagamento = restante
        else:
            novo_pagamento = round(float(novo_valor) * (float(row[1] or 0) / total_atual), 2) if total_atual else 0
            restante = round(restante - novo_pagamento, 2)
        cursor.execute("UPDATE pagamentos SET valor = ? WHERE id = ?", (novo_pagamento, pagamento_id))


def _sync_lancamento_quiosque(conn, lancamento, old_quiosque_id, new_quiosque_id):
    if int(old_quiosque_id) == int(new_quiosque_id):
        return

    cursor = conn.cursor()
    lancamento_id = int(lancamento["id"])
    venda_id = lancamento.get("venda_id")
    venda_item_id = lancamento.get("venda_item_id")

    cursor.execute(
        "UPDATE pagamentos SET quiosque_id = ? WHERE lancamento_id = ?",
        (int(new_quiosque_id), lancamento_id),
    )
    cursor.execute(
        "UPDATE estoque_movimentacoes SET quiosque_id = ? WHERE lancamento_id = ?",
        (int(new_quiosque_id), lancamento_id),
    )

    if venda_item_id:
        cursor.execute(
            "UPDATE venda_itens SET quiosque_id = ? WHERE id = ?",
            (int(new_quiosque_id), int(venda_item_id)),
        )

    if not venda_id:
        return

    other_quiosques = cursor.execute("""
    SELECT DISTINCT quiosque_id
    FROM lancamentos
    WHERE venda_id = ?
      AND id <> ?
      AND COALESCE(status, 'Ativo') <> 'Cancelado'
    """, (int(venda_id), lancamento_id)).fetchall()
    other_quiosque_ids = {int(row[0] or 0) for row in other_quiosques}

    if not other_quiosque_ids or other_quiosque_ids == {int(new_quiosque_id)}:
        cursor.execute(
            "UPDATE vendas SET quiosque_id = ? WHERE id = ?",
            (int(new_quiosque_id), int(venda_id)),
        )


def _edit_lancamento(conn, lancamento, data, descricao, valor, motivo, logged_user, authorizer, quiosque_id=None):
    old = {
        "data": lancamento.get("data"),
        "descricao": lancamento.get("descricao"),
        "valor": lancamento.get("valor"),
        "quiosque_id": lancamento.get("quiosque_id"),
    }
    sale_quiosque_id = int(lancamento.get("quiosque_id") or current_quiosque_id())
    new_quiosque_id = int(quiosque_id or sale_quiosque_id)
    new = {
        "data": str(data),
        "descricao": str(descricao or "").strip(),
        "valor": float(valor or 0),
        "quiosque_id": new_quiosque_id,
    }

    if not new["descricao"]:
        raise ValueError("Informe a descrição.")
    if new["valor"] <= 0:
        raise ValueError("Informe um valor maior que zero.")
    if not str(motivo or "").strip():
        raise ValueError("Informe o motivo da alteração.")

    cursor = conn.cursor()
    cursor.execute("""
    UPDATE lancamentos
    SET data = ?,
        descricao = ?,
        valor = ?,
        quiosque_id = ?,
        alterado_em = CURRENT_TIMESTAMP,
        alterado_por_id = ?,
        alterado_por_nome = ?,
        alterado_por_perfil = ?,
        alterado_motivo = ?
    WHERE id = ? AND quiosque_id = ? AND COALESCE(status, 'Ativo') <> 'Cancelado'
    """, (
        new["data"],
        new["descricao"],
        new["valor"],
        new_quiosque_id,
        authorizer.get("id"),
        authorizer.get("nome"),
        authorizer.get("perfil"),
        motivo.strip(),
        int(lancamento["id"]),
        sale_quiosque_id,
    ))
    _sync_lancamento_quiosque(conn, lancamento, sale_quiosque_id, new_quiosque_id)
    _sync_pagamentos_valor(conn, int(lancamento["id"]), new["valor"])
    _update_venda_status(conn, lancamento.get("venda_id"), sale_quiosque_id)
    _update_venda_status(conn, lancamento.get("venda_id"), new_quiosque_id)
    conn.commit()

    log_action(conn, logged_user, "editou_lancamento", "lancamentos", int(lancamento["id"]), {
        "usuario_logado": logged_user,
        "autorizado_por": authorizer,
        "motivo": motivo.strip(),
        "dados_antigos": old,
        "dados_novos": new,
        "venda_id": lancamento.get("venda_id"),
    })


def _cancel_lancamento(conn, lancamento, motivo, logged_user, authorizer):
    if not str(motivo or "").strip():
        raise ValueError("Informe o motivo do cancelamento.")

    sale_quiosque_id = int(lancamento.get("quiosque_id") or current_quiosque_id())
    _stock_return_for_cancel(conn, lancamento, authorizer)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE lancamentos
    SET status = 'Cancelado',
        cancelado_em = CURRENT_TIMESTAMP,
        cancelado_por_id = ?,
        cancelado_por_nome = ?,
        cancelado_por_perfil = ?,
        cancelado_motivo = ?
    WHERE id = ? AND quiosque_id = ? AND COALESCE(status, 'Ativo') <> 'Cancelado'
    """, (
        authorizer.get("id"),
        authorizer.get("nome"),
        authorizer.get("perfil"),
        motivo.strip(),
        int(lancamento["id"]),
        sale_quiosque_id,
    ))
    cursor.execute("""
    UPDATE venda_itens
    SET status = 'Cancelado'
    WHERE lancamento_id = ? AND quiosque_id = ?
    """, (int(lancamento["id"]), sale_quiosque_id))
    _update_venda_status(conn, lancamento.get("venda_id"), sale_quiosque_id, authorizer, motivo.strip())
    conn.commit()

    log_action(conn, logged_user, "cancelou_lancamento", "lancamentos", int(lancamento["id"]), {
        "usuario_logado": logged_user,
        "autorizado_por": authorizer,
        "motivo": motivo.strip(),
        "dados_antigos": {
            "data": lancamento.get("data"),
            "tipo": lancamento.get("tipo"),
            "descricao": lancamento.get("descricao"),
            "valor": lancamento.get("valor"),
            "venda_id": lancamento.get("venda_id"),
            "quiosque_id": sale_quiosque_id,
        },
        "dados_novos": {"status": "Cancelado"},
    })


def _delete_lancamento(conn, lancamento, user=None):
    cursor = conn.cursor()
    scope, params = scope_clause(prefix="AND")
    produto_id = lancamento.get("produto_id")
    quantidade = lancamento.get("quantidade")

    if lancamento.get("tipo") == "Produto" and produto_id and quantidade:
        restore_stock(
            conn,
            int(produto_id),
            float(quantidade),
            lancamento_id=int(lancamento["id"]),
            motivo="Venda removida",
        )

    cursor.execute(
        "DELETE FROM pagamentos WHERE lancamento_id = ?" + scope,
        (int(lancamento["id"]),) + params,
    )
    cursor.execute(
        "DELETE FROM lancamentos WHERE id = ?" + scope,
        (int(lancamento["id"]),) + params,
    )
    conn.commit()
    log_action(
        conn,
        user,
        "removeu_lancamento",
        "lancamentos",
        int(lancamento["id"]),
        {
            "tipo": lancamento.get("tipo"),
            "descricao": lancamento.get("descricao"),
            "valor": lancamento.get("valor"),
            "venda_id": lancamento.get("venda_id"),
        },
    )


def _cart_items():
    if "novo_lancamento_itens" not in st.session_state:
        st.session_state["novo_lancamento_itens"] = []

    return st.session_state["novo_lancamento_itens"]


def _item_total(item):
    return float(item.get("quantidade") or 0) * float(item.get("valor_unitario") or 0)


def _parse_money_input(value):
    text = str(value or "").strip()
    if not text:
        return 0.0
    text = text.replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _cart_total(items):
    return sum(_item_total(item) for item in items)


def _add_cart_item(item):
    items = _cart_items()
    items.append(item)
    st.session_state["novo_lancamento_itens"] = items


def _cart_has_same_product(product_id):
    return any(
        item.get("tipo") == "Produto" and int(item.get("produto_id") or 0) == int(product_id)
        for item in _cart_items()
    )


def _remove_cart_item(index):
    items = _cart_items()
    if 0 <= index < len(items):
        items.pop(index)
    st.session_state["novo_lancamento_itens"] = items


def _clear_cart():
    st.session_state["novo_lancamento_itens"] = []


def _cart_table(items):
    rows = []
    for index, item in enumerate(items, start=1):
        diferenca = float(item.get("diferenca_preco") or 0)
        if item["tipo"] in {"Produto", "Serviço"} and item.get("preco_original") is not None:
            status_preco = "Acima do preço" if diferenca > 0.01 else "Com desconto" if diferenca < -0.01 else "Preço normal"
        else:
            status_preco = "-"
        rows.append({
            "#": index,
            "Tipo": item["tipo"],
            "Descrição": item["descricao"],
            "Qtd": item["quantidade"],
            "Preço cadastrado": item.get("preco_original"),
            "Valor unitário": item["valor_unitario"],
            "Diferença unit.": item.get("diferenca_preco"),
            "Status preço": status_preco,
            "Motivo": item.get("observacao_alteracao_preco") or "",
            "Total": _item_total(item),
        })

    return pd.DataFrame(rows)


def _validate_stock(items, df_estoque):
    produtos = {}
    for item in items:
        if item["tipo"] != "Produto":
            continue
        produto_id = int(item["produto_id"])
        produtos[produto_id] = produtos.get(produto_id, 0) + float(item["quantidade"])

    for produto_id, quantidade in produtos.items():
        produto = df_estoque[df_estoque["id"] == produto_id]
        if produto.empty:
            return False, "Produto não encontrado no estoque."

        estoque_atual = float(produto.iloc[0]["quantidade"] or 0)
        if quantidade > estoque_atual:
            descricao = produto_label(produto.iloc[0])
            return False, f"Estoque insuficiente para {descricao}. Disponível: {estoque_atual:g}."

    return True, ""


def _split_payment(valor, item_totals, total):
    if valor <= 0:
        return [0 for _ in item_totals]

    valores = []
    restante = round(float(valor), 2)

    for item_total in item_totals[:-1]:
        parcela = round(float(valor) * (item_total / total), 2) if total else 0
        valores.append(parcela)
        restante = round(restante - parcela, 2)

    valores.append(restante)
    return valores


def _save_cart(conn, data, items, pagamentos, user=None):
    cursor = conn.cursor()
    item_totals = [_item_total(item) for item in items]
    total = sum(item_totals)
    lancamento_ids = []

    venda_id = execute_insert_returning_id(conn, cursor, """
    INSERT INTO vendas (data, total, status, usuario_id, usuario_nome, quiosque_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(data),
        total,
        "Ativa",
        None if not user else user.get("id"),
        None if not user else user.get("nome"),
        current_quiosque_id(user),
    ))

    for item in items:
        preco_original = item.get("preco_original")
        preco_vendido = item.get("preco_vendido", item.get("valor_unitario"))
        diferenca_preco = item.get("diferenca_preco")
        observacao_preco = item.get("observacao_alteracao_preco")
        usuario_responsavel = None if not user else user.get("nome")
        has_reference_price = item.get("preco_original") is not None
        data_hora_preco = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if has_reference_price else None

        lancamento_id = execute_insert_returning_id(conn, cursor, """
        INSERT INTO lancamentos (
            data,
            tipo,
            descricao,
            valor,
            produto_id,
            quantidade,
            venda_id,
            quiosque_id,
            preco_original,
            preco_vendido,
            diferenca_preco,
            observacao_alteracao_preco,
            usuario_responsavel_preco,
            data_hora_alteracao_preco
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(data),
            item["tipo"],
            item["descricao"],
            _item_total(item),
            item.get("produto_id"),
            item["quantidade"] if item["tipo"] == "Produto" else None,
            venda_id,
            current_quiosque_id(user),
            preco_original,
            preco_vendido if has_reference_price else None,
            diferenca_preco,
            observacao_preco,
            usuario_responsavel if has_reference_price else None,
            data_hora_preco,
        ))
        lancamento_ids.append(lancamento_id)

        venda_item_id = execute_insert_returning_id(conn, cursor, """
        INSERT INTO venda_itens (
            venda_id,
            lancamento_id,
            tipo,
            descricao,
            produto_id,
            quantidade,
            valor_unitario,
            valor_total,
            preco_original,
            preco_vendido,
            diferenca_preco,
            observacao_alteracao_preco,
            usuario_responsavel_preco,
            data_hora_alteracao_preco,
            quiosque_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            venda_id,
            lancamento_id,
            item["tipo"],
            item["descricao"],
            item.get("produto_id"),
            item["quantidade"],
            item["valor_unitario"],
            _item_total(item),
            preco_original,
            preco_vendido if has_reference_price else None,
            diferenca_preco,
            observacao_preco,
            usuario_responsavel if has_reference_price else None,
            data_hora_preco,
            current_quiosque_id(user),
        ))

        cursor.execute(
            "UPDATE lancamentos SET venda_item_id = ? WHERE id = ? AND quiosque_id = ?",
            (venda_item_id, lancamento_id, current_quiosque_id(user)),
        )
        conn.commit()

        if item["tipo"] == "Produto":
            reduce_stock(conn, item["produto_id"], item["quantidade"], lancamento_id=lancamento_id)

    for forma, valor in pagamentos:
        parcelas = _split_payment(valor, item_totals, total)
        for lancamento_id, parcela in zip(lancamento_ids, parcelas):
            if parcela > 0:
                cursor.execute("""
                INSERT INTO pagamentos (lancamento_id, forma_pagamento, valor, quiosque_id)
                VALUES (?, ?, ?, ?)
                """, (lancamento_id, forma, parcela, current_quiosque_id(user)))

    conn.commit()
    log_action(
        conn,
        user,
        "criou_venda",
        "vendas",
        venda_id,
        {
            "total": total,
            "itens": len(items),
            "pagamentos": {forma: valor for forma, valor in pagamentos if valor > 0},
        },
    )


def _request_lancamento_action(action, lancamento_id):
    st.session_state["lancamento_action"] = {
        "action": action,
        "lancamento_id": int(lancamento_id),
    }


@st.dialog("Autorização da venda")
def _render_lancamento_action_dialog(conn, lancamento, user):
    action_data = st.session_state.get("lancamento_action") or {}
    action = action_data.get("action")
    is_edit = action == "edit"
    sale_quiosque_id = int(lancamento.get("quiosque_id") or current_quiosque_id(user))
    direct = can_directly_change_sale(user, sale_quiosque_id)

    st.caption(f"#{lancamento['id']} | {lancamento['descricao']} | {moeda(lancamento['valor'])}")

    if is_edit:
        nova_data = st.date_input("Data", value=pd.to_datetime(lancamento.get("data")).date())
        nova_descricao = st.text_input("Descrição", value=lancamento.get("descricao") or "")
        novo_valor = st.number_input("Valor", min_value=0.01, value=float(lancamento.get("valor") or 0), step=1.0)
        novo_quiosque_id = sale_quiosque_id
        if user_can_view_all(user):
            quiosques = load_quiosques(conn)
            options = {
                int(row.id): row.nome
                for row in quiosques.itertuples()
            }
            if sale_quiosque_id not in options:
                options[sale_quiosque_id] = f"Quiosque {sale_quiosque_id}"
            novo_quiosque_id = st.selectbox(
                "Quiosque do lançamento",
                list(options.keys()),
                index=list(options.keys()).index(sale_quiosque_id),
                format_func=lambda value: options[value],
                help="Use para corrigir lançamento feito no quiosque errado.",
            )
        motivo_label = "Motivo da alteração"
    else:
        nova_data = None
        nova_descricao = None
        novo_valor = None
        novo_quiosque_id = sale_quiosque_id
        motivo_label = "Motivo do cancelamento"
        st.warning("O lançamento será marcado como cancelado, sem apagar o histórico.")

    if direct:
        st.info("Seu perfil permite esta ação diretamente.")
        auth_user = ""
        auth_password = ""
    else:
        st.warning("Atendente precisa de autorização de gerente do mesmo quiosque ou admin.")
        auth_user = st.text_input("Usuário ou nome do gerente/admin")
        auth_password = st.text_input("Senha do autorizador", type="password")

    motivo = st.text_area(motivo_label)

    col_confirm, col_cancel = st.columns(2)
    with col_cancel:
        if st.button("Fechar", width="stretch"):
            st.session_state.pop("lancamento_action", None)
            st.rerun()

    with col_confirm:
        if st.button("Confirmar", type="primary", width="stretch"):
            try:
                if direct:
                    authorizer = {
                        "id": user.get("id"),
                        "nome": user.get("nome"),
                        "usuario": user.get("usuario"),
                        "perfil": user.get("perfil"),
                        "quiosque_id": user.get("quiosque_id"),
                        "acesso_todos_quiosques": user.get("acesso_todos_quiosques"),
                    }
                else:
                    authorizer, error = validate_sale_authorization(conn, auth_user, auth_password, sale_quiosque_id)
                    if error:
                        st.error(error)
                        return

                if is_edit:
                    _edit_lancamento(
                        conn,
                        lancamento,
                        nova_data,
                        nova_descricao,
                        novo_valor,
                        motivo,
                        user,
                        authorizer,
                        quiosque_id=novo_quiosque_id,
                    )
                    st.success("Lançamento atualizado.")
                else:
                    _cancel_lancamento(conn, lancamento, motivo, user, authorizer)
                    st.success("Lançamento cancelado.")
                st.session_state.pop("lancamento_action", None)
                st.rerun()
            except Exception as error:
                conn.rollback()
                st.error(str(error))


def render_novo_lancamento(conn):
    df_estoque = load_stock(conn)
    df_servicos = load_services(conn, only_active=True)
    items = _cart_items()
    user = current_user()
    st.session_state.setdefault("venda_salvando", False)
    st.session_state.setdefault("produto_adicionando", False)
    st.session_state.setdefault("novo_lancamento_form_version", 0)
    form_version = st.session_state["novo_lancamento_form_version"]

    page_banner("tx_lancamento_banner.webp", "TX System - Novo Lançamento")
    st.subheader("➕ Novo Lançamento")

    catalog_prefill = st.session_state.pop("catalogo_venda_prefill", None)
    if catalog_prefill:
        _add_cart_item({
            "tipo": "Serviço",
            "descricao": catalog_prefill["descricao"],
            "produto_id": None,
            "quantidade": 1.0,
            "valor_unitario": float(catalog_prefill["valor"] or 0),
            "preco_original": float(catalog_prefill["valor"] or 0),
            "preco_vendido": float(catalog_prefill["valor"] or 0),
            "diferenca_preco": 0,
            "observacao_alteracao_preco": "Venda iniciada pelo catálogo",
        })
        st.success("Item do catálogo adicionado à venda.")
        st.rerun()

    data = st.date_input("Data da venda", datetime.today(), key=f"venda_data_{form_version}")

    st.markdown("#### Adicionar itens")
    if st.session_state.pop("produto_adicionado_msg", False):
        st.success("Produto adicionado.")
    tab_produto, tab_servico_cadastrado, tab_servico = st.tabs(["Produto do estoque", "Serviço cadastrado", "Serviço manual"])

    with tab_produto:
        if df_estoque.empty:
            st.warning("Nenhum produto cadastrado no estoque. Cadastre ou importe o estoque primeiro.")
        else:
            produtos_disponiveis = df_estoque[df_estoque["quantidade"] > 0].copy()
            if produtos_disponiveis.empty:
                st.warning("Todos os produtos estão com estoque zerado.")
            else:
                busca_produto = st.text_input(
                    "Buscar produto",
                    placeholder="Ex.: pelicula, cabo tipo c, iphone 11",
                    key=f"cart_produto_busca_{form_version}",
                )
                produtos_filtrados = produtos_disponiveis.copy()
                if busca_produto.strip():
                    produtos_filtrados = produtos_filtrados[
                        produtos_filtrados.apply(
                            lambda row: search_matches(
                                " ".join([
                                    str(row.get("produto") or ""),
                                    str(row.get("modelo") or ""),
                                    str(row.get("categoria") or ""),
                                    str(row.get("marca") or ""),
                                    str(row.get("codigo") or ""),
                                ]),
                                busca_produto,
                            ),
                            axis=1,
                        )
                    ]

                if produtos_filtrados.empty:
                    st.info("Nenhum produto encontrado para essa busca.")
                else:
                    options = {
                        f"{produto_label(row)} | Qtd: {row.quantidade:g} | R$ {row.valor_venda:.2f}": row.id
                        for row in produtos_filtrados.head(30).itertuples()
                    }
                    selected_label = st.selectbox("Produto encontrado", list(options.keys()), key=f"cart_produto_{form_version}")
                    produto_id = options[selected_label]
                    produto = produtos_filtrados[produtos_filtrados["id"] == produto_id].iloc[0]
                    descricao = produto_label(produto)
                    max_qtd = float(produto["quantidade"])
                    preco_cadastrado = float(produto["valor_venda"] or 0)

                    col1, col2 = st.columns(2)
                    with col1:
                        quantidade = st.number_input(
                            "Quantidade",
                            min_value=1.0,
                            max_value=max_qtd,
                            value=1.0,
                            step=1.0,
                            key=f"cart_produto_quantidade_{produto_id}_{form_version}",
                        )
                    with col2:
                        valor_padrao = "" if preco_cadastrado <= 0 else f"{preco_cadastrado:.2f}".replace(".", ",")
                        valor_unitario_text = st.text_input(
                            "Valor da venda",
                            value=valor_padrao,
                            placeholder="Digite o valor",
                            key=f"cart_produto_valor_{produto_id}_{form_version}",
                        )
                        valor_unitario = _parse_money_input(valor_unitario_text)

                    diferenca_preco = float(valor_unitario) - preco_cadastrado
                    if abs(diferenca_preco) <= 0.01:
                        st.caption("Preço normal do cadastro.")
                    elif diferenca_preco > 0:
                        st.info(f"Venda acima do preço cadastrado em {moeda(diferenca_preco)} por unidade.")
                    else:
                        st.warning(f"Desconto de {moeda(abs(diferenca_preco))} por unidade.")

                    observacao_preco = st.text_input(
                        "Motivo da alteração de preço",
                        placeholder="Obrigatório se vender abaixo do preço cadastrado",
                        key=f"cart_produto_motivo_preco_{produto_id}_{form_version}",
                    )

                    if st.button("Adicionar produto", width="stretch", disabled=st.session_state["produto_adicionando"]):
                        if valor_unitario <= 0:
                            st.error("Informe o valor unitário do produto.")
                        elif diferenca_preco < -0.01 and not observacao_preco.strip():
                            st.error("Informe o motivo do desconto.")
                        elif _cart_has_same_product(produto_id):
                            st.warning("Este produto já está na lista de itens adicionados.")
                        else:
                            st.session_state["produto_adicionando"] = True
                            _add_cart_item({
                                "tipo": "Produto",
                                "descricao": descricao,
                                "produto_id": int(produto_id),
                                "quantidade": float(quantidade),
                                "valor_unitario": float(valor_unitario),
                                "preco_original": preco_cadastrado,
                                "preco_vendido": float(valor_unitario),
                                "diferenca_preco": diferenca_preco,
                                "observacao_alteracao_preco": observacao_preco.strip(),
                            })
                            st.session_state["produto_adicionando"] = False
                            st.session_state["produto_adicionado_msg"] = True
                            st.session_state["novo_lancamento_form_version"] += 1
                            st.rerun()

    with tab_servico_cadastrado:
        if df_servicos.empty:
            st.info("Nenhum serviço cadastrado. Use serviço manual ou cadastre em Serviços.")
        else:
            options_servicos = {
                f"{servico_label(row)} | {row.categoria or 'Sem categoria'} | R$ {row.valor_padrao:.2f}": row.id
                for row in df_servicos.itertuples()
            }
            selected_service_label = st.selectbox("Serviço", list(options_servicos.keys()), key=f"cart_servico_cadastrado_{form_version}")
            servico_id = options_servicos[selected_service_label]
            servico_row = df_servicos[df_servicos["id"] == servico_id].iloc[0]
            servico_desc = servico_label(servico_row)
            valor_padrao = float(servico_row["valor_padrao"] or 0)
            valor_padrao_text = "" if valor_padrao <= 0 else f"{valor_padrao:.2f}".replace(".", ",")
            valor_servico_text = st.text_input(
                "Valor da venda",
                value=valor_padrao_text,
                placeholder="Digite o valor",
                key=f"cart_servico_cadastrado_valor_{servico_id}_{form_version}",
            )
            valor_servico = _parse_money_input(valor_servico_text)
            diferenca_servico = valor_servico - valor_padrao
            if abs(diferenca_servico) <= 0.01:
                st.caption("Preço normal do cadastro.")
            elif diferenca_servico > 0:
                st.info(f"Cobrança acima do valor padrão em {moeda(diferenca_servico)}.")
            else:
                st.warning(f"Desconto de {moeda(abs(diferenca_servico))}.")

            motivo_servico = st.text_input(
                "Motivo da alteração de preço",
                placeholder="Obrigatório se cobrar abaixo do valor padrão",
                key=f"cart_servico_cadastrado_motivo_{servico_id}_{form_version}",
            )
            if servico_row.get("garantia"):
                st.caption(f"Garantia: {servico_row['garantia']}")
            if servico_row.get("observacao"):
                st.caption(f"Obs.: {servico_row['observacao']}")

            if st.button("Adicionar serviço cadastrado", width="stretch"):
                if valor_servico <= 0:
                    st.error("Informe o valor do serviço.")
                elif diferenca_servico < -0.01 and not motivo_servico.strip():
                    st.error("Informe o motivo do desconto.")
                else:
                    _add_cart_item({
                        "tipo": "Serviço",
                        "descricao": servico_desc,
                        "produto_id": None,
                        "quantidade": 1.0,
                        "valor_unitario": float(valor_servico),
                        "preco_original": valor_padrao,
                        "preco_vendido": float(valor_servico),
                        "diferenca_preco": diferenca_servico,
                        "observacao_alteracao_preco": motivo_servico.strip() or servico_row.get("observacao") or "",
                    })
                    st.success("Serviço adicionado à venda.")
                    st.rerun()

    with tab_servico:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            servico_descricao = st.text_input("Descrição do serviço", key=f"cart_servico_descricao_{form_version}")
        with col2:
            servico_quantidade = st.number_input("Quantidade", min_value=1.0, value=1.0, step=1.0, key=f"cart_servico_quantidade_{form_version}")
        with col3:
            servico_valor_text = st.text_input(
                "Valor unitário",
                value="",
                placeholder="Digite o valor",
                key=f"cart_servico_valor_{form_version}",
            )
            servico_valor = _parse_money_input(servico_valor_text)

        if st.button("Adicionar serviço", width="stretch"):
            if not servico_descricao.strip():
                st.error("Informe a descrição do serviço.")
            elif servico_valor <= 0:
                st.error("Informe o valor do serviço.")
            else:
                _add_cart_item({
                    "tipo": "Serviço",
                    "descricao": servico_descricao.strip(),
                    "produto_id": None,
                    "quantidade": float(servico_quantidade),
                    "valor_unitario": float(servico_valor),
                    "preco_original": None,
                    "preco_vendido": None,
                    "diferenca_preco": None,
                    "observacao_alteracao_preco": "",
                })
                st.success("Serviço adicionado à venda.")
                st.rerun()

    st.divider()
    st.markdown("#### Itens da venda")

    if not items:
        st.info("Adicione ao menos um produto ou serviço para montar a venda.")
    else:
        tabela_carrinho = _cart_table(items)
        st.dataframe(
            tabela_carrinho,
            width="stretch",
            hide_index=True,
            column_config={
                "Valor unitário": st.column_config.NumberColumn("Valor unitário", format="R$ %.2f"),
                "Preço cadastrado": st.column_config.NumberColumn("Preço cadastrado", format="R$ %.2f"),
                "Diferença unit.": st.column_config.NumberColumn("Diferença unit.", format="R$ %.2f"),
                "Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
            },
        )

        col_actions = st.columns(min(len(items), 4))
        for index, item in enumerate(items):
            coluna = col_actions[index % len(col_actions)]
            with coluna:
                if st.button(f"Remover item {index + 1}", key=f"remove_cart_{index}"):
                    _remove_cart_item(index)
                    st.rerun()

        if st.button("Limpar venda", width="stretch"):
            _clear_cart()
            st.rerun()

    total_itens = _cart_total(items)
    st.metric("Total dos itens", moeda(total_itens))

    st.divider()
    st.subheader("💳 Pagamentos")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        dinheiro = _parse_money_input(st.text_input("Dinheiro", value="", placeholder="0,00", key=f"pag_dinheiro_{form_version}"))
    with c2:
        pix = _parse_money_input(st.text_input("Pix", value="", placeholder="0,00", key=f"pag_pix_{form_version}"))
    with c3:
        credito = _parse_money_input(st.text_input("Crédito", value="", placeholder="0,00", key=f"pag_credito_{form_version}"))
    with c4:
        debito = _parse_money_input(st.text_input("Débito", value="", placeholder="0,00", key=f"pag_debito_{form_version}"))

    pagamentos = [
        ("Dinheiro", dinheiro),
        ("Pix", pix),
        ("Crédito", credito),
        ("Débito", debito),
    ]
    total_pagamentos = sum(valor for _, valor in pagamentos)
    diferenca = total_pagamentos - total_itens

    c1, c2 = st.columns(2)
    c1.metric("Total pago", moeda(total_pagamentos))
    c2.metric("Diferença", moeda(diferenca))

    can_save = bool(items) and total_itens > 0 and total_pagamentos > 0 and abs(total_pagamentos - total_itens) <= 0.01
    if not can_save:
        st.caption("Adicione produto/serviço e informe uma forma de pagamento com total igual ao valor da venda.")

    if st.button(
        "Salvar venda",
        width="stretch",
        type="primary",
        disabled=st.session_state["venda_salvando"] or not can_save,
    ):
        if st.session_state["venda_salvando"]:
            return

        if not items:
            st.error("Adicione ao menos um produto ou serviço.")
            return

        if total_itens <= 0:
            st.error("O total da venda precisa ser maior que zero.")
            return

        if abs(total_pagamentos - total_itens) > 0.01:
            st.error("O total dos pagamentos precisa ser igual ao total dos itens.")
            return

        ok, message = _validate_stock(items, df_estoque)
        if not ok:
            st.error(message)
            return

        for item in items:
            if item["tipo"] in {"Produto", "Serviço"} and float(item.get("diferenca_preco") or 0) < -0.01:
                if not str(item.get("observacao_alteracao_preco") or "").strip():
                    st.error("Informe o motivo do desconto.")
                    return

        try:
            st.session_state["venda_salvando"] = True
            _save_cart(conn, data, items, pagamentos, user=user)
        except Exception as error:
            conn.rollback()
            st.error(f"Erro ao salvar venda: {error}")
            return
        finally:
            st.session_state["venda_salvando"] = False

        _clear_cart()
        st.session_state["novo_lancamento_form_version"] += 1
        st.success("✅ Venda salva com todos os itens!")
        st.rerun()
