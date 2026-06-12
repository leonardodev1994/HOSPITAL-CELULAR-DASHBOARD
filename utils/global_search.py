import pandas as pd
import streamlit as st

from utils.quiosques import scope_clause
from utils.text import normalize_search_text


SEARCH_LIMIT_PER_MODULE = 5


def _like_param(term):
    return f"%{term.lower()}%"


def _run_query(conn, query, params):
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return pd.DataFrame(columns=["modulo", "titulo", "detalhe", "menu"])


def _search_clientes(conn, term):
    scope, scope_params = scope_clause("c", prefix="AND")
    like = _like_param(term)
    return _run_query(
        conn,
        f"""
        SELECT 'Clientes' AS modulo, c.nome AS titulo,
               COALESCE(c.telefone, c.cpf, c.email, '') AS detalhe,
               'Clientes' AS menu
        FROM clientes c
        WHERE COALESCE(c.ativo, 1) = 1
          AND LOWER(COALESCE(c.nome, '') || ' ' || COALESCE(c.cpf, '') || ' ' ||
                    COALESCE(c.telefone, '') || ' ' || COALESCE(c.email, '')) LIKE ?
          {scope}
        ORDER BY c.nome
        LIMIT ?
        """,
        (like,) + scope_params + (SEARCH_LIMIT_PER_MODULE,),
    )


def _search_ordens(conn, term):
    scope, scope_params = scope_clause("os", prefix="AND")
    like = _like_param(term)
    return _run_query(
        conn,
        f"""
        SELECT 'Ordem de Serviço' AS modulo,
               COALESCE(os.cliente, 'OS #' || CAST(os.id AS TEXT)) AS titulo,
               COALESCE(os.status, '') || ' • ' || COALESCE(os.marca, '') || ' ' ||
               COALESCE(os.modelo, '') || ' • ' || COALESCE(os.servico, '') AS detalhe,
               'Ordem de Serviço' AS menu
        FROM ordens_servico os
        WHERE LOWER(COALESCE(os.cliente, '') || ' ' || COALESCE(os.telefone, '') || ' ' ||
                    COALESCE(os.cpf, '') || ' ' || COALESCE(os.marca, '') || ' ' ||
                    COALESCE(os.modelo, '') || ' ' || COALESCE(os.servico, '') || ' ' ||
                    COALESCE(os.status, '')) LIKE ?
          {scope}
        ORDER BY os.id DESC
        LIMIT ?
        """,
        (like,) + scope_params + (SEARCH_LIMIT_PER_MODULE,),
    )


def _search_estoque(conn, term):
    scope, scope_params = scope_clause("e", prefix="AND")
    like = _like_param(term)
    return _run_query(
        conn,
        f"""
        SELECT 'Estoque' AS modulo,
               COALESCE(e.produto, e.codigo, 'Produto') AS titulo,
               COALESCE(e.marca, '') || ' ' || COALESCE(e.modelo, '') || ' • Qtd ' ||
               COALESCE(CAST(e.quantidade AS TEXT), '0') AS detalhe,
               'Estoque' AS menu
        FROM estoque e
        WHERE COALESCE(e.ativo, 1) = 1
          AND LOWER(COALESCE(e.produto, '') || ' ' || COALESCE(e.codigo, '') || ' ' ||
                    COALESCE(e.categoria, '') || ' ' || COALESCE(e.marca, '') || ' ' ||
                    COALESCE(e.modelo, '')) LIKE ?
          {scope}
        ORDER BY e.produto
        LIMIT ?
        """,
        (like,) + scope_params + (SEARCH_LIMIT_PER_MODULE,),
    )


def _search_catalogo(conn, term):
    like = _like_param(term)
    return _run_query(
        conn,
        """
        SELECT 'Catálogo' AS modulo,
               COALESCE(c.marca, '') || ' • ' || COALESCE(c.modelo, '') AS titulo,
               COALESCE(c.qualidade, '') || ' • S/A ' ||
               COALESCE(CAST(c.venda_sem_aro AS TEXT), '0') || ' • C/A ' ||
               COALESCE(CAST(c.venda_com_aro AS TEXT), '0') AS detalhe,
               'Catálogo' AS menu
        FROM catalogo_pecas c
        WHERE COALESCE(c.ativo, 1) = 1
          AND LOWER(COALESCE(c.marca, '') || ' ' || COALESCE(c.modelo, '') || ' ' ||
                    COALESCE(c.qualidade, '')) LIKE ?
        ORDER BY c.marca, c.modelo
        LIMIT ?
        """,
        (like, SEARCH_LIMIT_PER_MODULE),
    )


def _search_servicos(conn, term):
    scope, scope_params = scope_clause("s", prefix="AND")
    like = _like_param(term)
    return _run_query(
        conn,
        f"""
        SELECT 'Serviços' AS modulo, s.nome AS titulo,
               COALESCE(s.categoria, '') || ' • ' || COALESCE(s.modelo, '') AS detalhe,
               'Serviços' AS menu
        FROM servicos s
        WHERE COALESCE(s.ativo, 1) = 1
          AND LOWER(COALESCE(s.nome, '') || ' ' || COALESCE(s.categoria, '') || ' ' ||
                    COALESCE(s.modelo, '')) LIKE ?
          {scope}
        ORDER BY s.nome
        LIMIT ?
        """,
        (like,) + scope_params + (SEARCH_LIMIT_PER_MODULE,),
    )


def _search_lancamentos(conn, term):
    scope, scope_params = scope_clause("l", prefix="AND")
    like = _like_param(term)
    return _run_query(
        conn,
        f"""
        SELECT 'Vendas' AS modulo,
               COALESCE(l.descricao, 'Lançamento') AS titulo,
               COALESCE(l.tipo, '') || ' • ' || COALESCE(l.data, '') || ' • R$ ' ||
               COALESCE(CAST(l.valor AS TEXT), '0') AS detalhe,
               'Lançamentos' AS menu
        FROM lancamentos l
        WHERE COALESCE(l.status, 'Ativo') <> 'Cancelado'
          AND LOWER(COALESCE(l.descricao, '') || ' ' || COALESCE(l.tipo, '') || ' ' ||
                    COALESCE(l.data, '')) LIKE ?
          {scope}
        ORDER BY l.data DESC, l.id DESC
        LIMIT ?
        """,
        (like,) + scope_params + (SEARCH_LIMIT_PER_MODULE,),
    )


def _search_compra_aparelhos(conn, term):
    scope, scope_params = scope_clause("a", prefix="AND")
    like = _like_param(term)
    return _run_query(
        conn,
        f"""
        SELECT 'Compra de Aparelhos' AS modulo,
               COALESCE(a.marca, '') || ' ' || COALESCE(a.modelo, '') AS titulo,
               COALESCE(a.cliente, '') || ' • ' || COALESCE(a.imei, '') || ' • ' ||
               COALESCE(a.status, '') AS detalhe,
               'Compra de Aparelhos' AS menu
        FROM aparelho_compras a
        WHERE LOWER(COALESCE(a.cliente, '') || ' ' || COALESCE(a.cpf, '') || ' ' ||
                    COALESCE(a.telefone, '') || ' ' || COALESCE(a.imei, '') || ' ' ||
                    COALESCE(a.marca, '') || ' ' || COALESCE(a.modelo, '') || ' ' ||
                    COALESCE(a.status, '')) LIKE ?
          {scope}
        ORDER BY a.id DESC
        LIMIT ?
        """,
        (like,) + scope_params + (SEARCH_LIMIT_PER_MODULE,),
    )


def _search_seminovos(conn, term):
    scope, scope_params = scope_clause("s", prefix="AND")
    like = _like_param(term)
    return _run_query(
        conn,
        f"""
        SELECT 'Seminovos' AS modulo,
               COALESCE(s.codigo_interno, 'Seminovo') || ' • ' || COALESCE(s.modelo, '') AS titulo,
               COALESCE(s.imei, '') || ' • ' || COALESCE(s.status, '') AS detalhe,
               'Compra de Aparelhos' AS menu
        FROM seminovos_estoque s
        WHERE LOWER(COALESCE(s.codigo_interno, '') || ' ' || COALESCE(s.imei, '') || ' ' ||
                    COALESCE(s.modelo, '') || ' ' || COALESCE(s.status, '')) LIKE ?
          {scope}
        ORDER BY s.id DESC
        LIMIT ?
        """,
        (like,) + scope_params + (SEARCH_LIMIT_PER_MODULE,),
    )


def _search_all(conn, raw_term):
    term = normalize_search_text(raw_term)
    if len(term) < 2:
        return pd.DataFrame(columns=["modulo", "titulo", "detalhe", "menu"])

    results = [
        _search_clientes(conn, term),
        _search_ordens(conn, term),
        _search_estoque(conn, term),
        _search_catalogo(conn, term),
        _search_servicos(conn, term),
        _search_lancamentos(conn, term),
        _search_compra_aparelhos(conn, term),
        _search_seminovos(conn, term),
    ]
    return pd.concat(results, ignore_index=True)


def render_global_search(conn, available_menus):
    st.markdown("<div class='tx-global-search-wrap'>", unsafe_allow_html=True)
    query = st.text_input(
        "Pesquisa Global TX",
        placeholder="Buscar cliente, OS, produto, catálogo, serviço ou venda...",
        key="tx_global_search",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if not query or len(normalize_search_text(query)) < 2:
        return

    results = _search_all(conn, query)
    if results.empty:
        st.info("Nenhum resultado encontrado na pesquisa global.")
        return

    with st.container(border=True):
        st.caption(f"Resultados para: {query}")
        for row in results.itertuples():
            c1, c2 = st.columns([1, 0.25])
            with c1:
                st.markdown(f"**{row.modulo}** · {row.titulo}")
                st.caption(row.detalhe or "Sem detalhe")
            with c2:
                if row.menu in available_menus and st.button("Abrir", key=f"global_search_{row.Index}", width="stretch"):
                    st.session_state["menu_atual"] = row.menu
                    st.session_state["tx_global_search"] = ""
                    st.rerun()
