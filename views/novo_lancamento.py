from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import execute_insert_returning_id
from utils.audit import log_action
from utils.auth import current_user
from utils.dashboard_ui import moeda
from utils.estoque import load_stock, produto_label, reduce_stock, restore_stock


def _load_lancamentos(conn):
    return pd.read_sql_query("""
    SELECT
        id,
        data,
        tipo,
        descricao,
        valor,
        produto_id,
        quantidade,
        venda_id,
        venda_item_id
    FROM lancamentos
    ORDER BY data DESC, id DESC
    """, conn)


def _delete_lancamento(conn, lancamento, user=None):
    cursor = conn.cursor()
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

    cursor.execute("DELETE FROM pagamentos WHERE lancamento_id = ?", (int(lancamento["id"]),))
    cursor.execute("DELETE FROM lancamentos WHERE id = ?", (int(lancamento["id"]),))
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


def _cart_total(items):
    return sum(_item_total(item) for item in items)


def _add_cart_item(item):
    items = _cart_items()
    items.append(item)
    st.session_state["novo_lancamento_itens"] = items


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
        rows.append({
            "#": index,
            "Tipo": item["tipo"],
            "Descrição": item["descricao"],
            "Qtd": item["quantidade"],
            "Valor unitário": item["valor_unitario"],
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
    INSERT INTO vendas (data, total, status, usuario_id, usuario_nome)
    VALUES (?, ?, ?, ?, ?)
    """, (
        str(data),
        total,
        "Ativa",
        None if not user else user.get("id"),
        None if not user else user.get("nome"),
    ))

    for item in items:
        lancamento_id = execute_insert_returning_id(conn, cursor, """
        INSERT INTO lancamentos (data, tipo, descricao, valor, produto_id, quantidade, venda_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(data),
            item["tipo"],
            item["descricao"],
            _item_total(item),
            item.get("produto_id"),
            item["quantidade"] if item["tipo"] == "Produto" else None,
            venda_id,
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
            valor_total
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            venda_id,
            lancamento_id,
            item["tipo"],
            item["descricao"],
            item.get("produto_id"),
            item["quantidade"],
            item["valor_unitario"],
            _item_total(item),
        ))

        cursor.execute(
            "UPDATE lancamentos SET venda_item_id = ? WHERE id = ?",
            (venda_item_id, lancamento_id),
        )
        conn.commit()

        if item["tipo"] == "Produto":
            reduce_stock(conn, item["produto_id"], item["quantidade"], lancamento_id=lancamento_id)

    for forma, valor in pagamentos:
        parcelas = _split_payment(valor, item_totals, total)
        for lancamento_id, parcela in zip(lancamento_ids, parcelas):
            if parcela > 0:
                cursor.execute("""
                INSERT INTO pagamentos (lancamento_id, forma_pagamento, valor)
                VALUES (?, ?, ?)
                """, (lancamento_id, forma, parcela))

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


def render_novo_lancamento(conn):
    df_estoque = load_stock(conn)
    items = _cart_items()
    user = current_user()

    st.subheader("➕ Novo Lançamento")
    data = st.date_input("Data da venda", datetime.today())

    st.markdown("#### Adicionar itens")
    tab_produto, tab_servico = st.tabs(["Produto do estoque", "Serviço manual"])

    with tab_produto:
        if df_estoque.empty:
            st.warning("Nenhum produto cadastrado no estoque. Cadastre ou importe o estoque primeiro.")
        else:
            produtos_disponiveis = df_estoque[df_estoque["quantidade"] > 0].copy()
            if produtos_disponiveis.empty:
                st.warning("Todos os produtos estão com estoque zerado.")
            else:
                options = {
                    f"{produto_label(row)} | Qtd: {row.quantidade:g} | R$ {row.valor_venda:.2f}": row.id
                    for row in produtos_disponiveis.itertuples()
                }
                selected_label = st.selectbox("Produto", list(options.keys()), key="cart_produto")
                produto_id = options[selected_label]
                produto = produtos_disponiveis[produtos_disponiveis["id"] == produto_id].iloc[0]
                descricao = produto_label(produto)
                max_qtd = float(produto["quantidade"])

                col1, col2 = st.columns(2)
                with col1:
                    quantidade = st.number_input(
                        "Quantidade",
                        min_value=1.0,
                        max_value=max_qtd,
                        value=1.0,
                        step=1.0,
                        key="cart_produto_quantidade",
                    )
                with col2:
                    valor_unitario = st.number_input(
                        "Valor unitário",
                        min_value=0.0,
                        value=float(produto["valor_venda"] or 0),
                        step=1.0,
                        key="cart_produto_valor",
                    )

                if st.button("Adicionar produto", width="stretch"):
                    if valor_unitario <= 0:
                        st.error("Informe o valor unitário do produto.")
                    else:
                        _add_cart_item({
                            "tipo": "Produto",
                            "descricao": descricao,
                            "produto_id": int(produto_id),
                            "quantidade": float(quantidade),
                            "valor_unitario": float(valor_unitario),
                        })
                        st.success("Produto adicionado à venda.")
                        st.rerun()

    with tab_servico:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            servico_descricao = st.text_input("Descrição do serviço", key="cart_servico_descricao")
        with col2:
            servico_quantidade = st.number_input("Quantidade", min_value=1.0, value=1.0, step=1.0, key="cart_servico_quantidade")
        with col3:
            servico_valor = st.number_input("Valor unitário", min_value=0.0, value=0.0, step=1.0, key="cart_servico_valor")

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
        dinheiro = st.number_input("Dinheiro", min_value=0.0, value=0.0, step=1.0)
    with c2:
        pix = st.number_input("Pix", min_value=0.0, value=0.0, step=1.0)
    with c3:
        credito = st.number_input("Crédito", min_value=0.0, value=0.0, step=1.0)
    with c4:
        debito = st.number_input("Débito", min_value=0.0, value=0.0, step=1.0)

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

    if st.button("Salvar venda", width="stretch", type="primary"):
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

        try:
            _save_cart(conn, data, items, pagamentos, user=user)
        except Exception as error:
            conn.rollback()
            st.error(f"Erro ao salvar venda: {error}")
            return

        _clear_cart()
        st.success("✅ Venda salva com todos os itens!")
        st.rerun()

    st.divider()
    st.subheader("🧾 Lançamentos recentes")

    df_lancamentos = _load_lancamentos(conn)
    if df_lancamentos.empty:
        st.caption("Nenhum lançamento cadastrado.")
        return

    tabela = df_lancamentos.head(30).copy()
    tabela = tabela.rename(columns={
        "id": "ID",
        "data": "Data",
        "tipo": "Tipo",
        "descricao": "Descrição",
        "valor": "Valor",
        "quantidade": "Qtd",
    })

    st.dataframe(
        tabela[["ID", "Data", "Tipo", "Descrição", "Qtd", "Valor"]],
        width="stretch",
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )

    with st.expander("Remover lançamento errado", expanded=False):
        options = {
            f"#{row.id} | {row.data} | {row.tipo} | {row.descricao} | {moeda(row.valor)}": row.id
            for row in df_lancamentos.head(100).itertuples()
        }
        selected_label = st.selectbox("Selecione o lançamento", list(options.keys()))
        selected_id = options[selected_label]
        selected = df_lancamentos[df_lancamentos["id"] == selected_id].iloc[0].to_dict()

        st.warning(
            "Ao remover uma venda de produto, o sistema devolve a quantidade ao estoque "
            "e apaga as formas de pagamento desse lançamento."
        )
        confirmar = st.checkbox("Confirmo que este lançamento foi feito errado e deve ser removido")

        if st.button("Remover lançamento", type="primary", disabled=not confirmar):
            _delete_lancamento(conn, selected, user=user)
            st.success("✅ Lançamento removido.")
            st.rerun()
