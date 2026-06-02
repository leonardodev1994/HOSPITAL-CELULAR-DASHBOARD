import streamlit as st

from utils.audit import log_action
from utils.auth import current_user
from utils.catalogo import (
    MARCAS_PADRAO,
    create_catalog_item,
    enrich_catalog_df,
    load_catalog_items,
)
from utils.dashboard_ui import moeda, page_banner, page_header
from utils.permissions import has_permission


def _item_descricao(row, tipo_aro):
    aro = "com aro" if tipo_aro == "com" else "sem aro"
    return f"Tela {row.modelo} {row.qualidade or ''} {aro}".strip()


def _item_valor(row, tipo_aro):
    return float(row.venda_com_aro if tipo_aro == "com" else row.venda_sem_aro or 0)


def _render_catalog_results(conn, df):
    if df.empty:
        st.info("Nenhum item encontrado.")
        return

    for row in enrich_catalog_df(df).itertuples():
        with st.container(border=True):
            st.markdown(f"**{row.marca or 'Sem marca'} · {row.modelo} · {row.qualidade or '-'}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("S/A", moeda(row.venda_sem_aro), f"Custo {moeda(row.custo_sem_aro)}")
            c2.metric("C/A", moeda(row.venda_com_aro), f"Custo {moeda(row.custo_com_aro)}")
            c3.metric("Lucro melhor", moeda(max(row.lucro_sem_aro, row.lucro_com_aro)))

            tipo_aro = st.segmented_control(
                "Opção",
                ["sem", "com"],
                default="sem" if float(row.venda_sem_aro or 0) > 0 else "com",
                format_func=lambda value: "Sem aro" if value == "sem" else "Com aro",
                key=f"catalogo_aro_{row.id}",
            )
            valor = _item_valor(row, tipo_aro)
            descricao = _item_descricao(row, tipo_aro)

            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("Criar orçamento", key=f"orcamento_{row.id}", width="stretch"):
                    st.session_state["catalogo_orcamento"] = {
                        "descricao": descricao,
                        "marca": row.marca,
                        "modelo": row.modelo,
                        "qualidade": row.qualidade,
                        "valor": valor,
                    }
                    st.rerun()
            with a2:
                if st.button("Abrir OS", key=f"abrir_os_catalogo_{row.id}", width="stretch"):
                    st.session_state["catalogo_os_prefill"] = {
                        "servico": descricao,
                        "marca": row.marca,
                        "modelo": row.modelo,
                        "valor": valor,
                        "observacao": f"Orçamento gerado pelo catálogo. Qualidade: {row.qualidade or '-'}",
                    }
                    st.session_state["menu_atual"] = "Ordem de Serviço"
                    st.rerun()
            with a3:
                if st.button("Lançar venda", key=f"venda_catalogo_{row.id}", width="stretch"):
                    st.session_state["catalogo_venda_prefill"] = {
                        "descricao": descricao,
                        "valor": valor,
                    }
                    st.session_state["menu_atual"] = "Novo Lançamento"
                    st.rerun()


def render_catalogo(conn):
    user = current_user()
    can_manage = has_permission("manage_stock", user)

    page_banner("tx_estoque_banner.webp", "TX System - Catálogo")
    page_header("Catálogo Inteligente", "Busca rápida de telas e peças com preço sugerido automático.")

    orcamento = st.session_state.get("catalogo_orcamento")
    if orcamento:
        with st.expander("Orçamento criado", expanded=True):
            st.write(orcamento["descricao"])
            st.metric("Valor sugerido", moeda(orcamento["valor"]))
            if st.button("Fechar orçamento", width="stretch"):
                st.session_state.pop("catalogo_orcamento", None)
                st.rerun()

    search = st.text_input("🔎 Pesquisar modelo, marca ou qualidade", placeholder="Ex.: iPhone 11, A10, Redmi Note...")
    if search.strip():
        _render_catalog_results(conn, load_catalog_items(conn, search=search, limit=40))
    else:
        st.caption("Digite acima para busca rápida ou abra uma marca abaixo.")

    if can_manage:
        with st.expander("Cadastrar tela/peça", expanded=False):
            with st.form("catalogo_item_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    marca = st.selectbox("Marca", MARCAS_PADRAO)
                    modelo = st.text_input("Modelo")
                    qualidade = st.text_input("Qualidade", placeholder="INCELL, OLED, PREMIUM...")
                with c2:
                    custo_sem_aro = st.number_input("Custo S/A", min_value=0.0, value=0.0, step=1.0)
                    custo_com_aro = st.number_input("Custo C/A", min_value=0.0, value=0.0, step=1.0)
                with c3:
                    observacao = st.text_area("Observação")
                salvar = st.form_submit_button("Salvar no catálogo")

            if salvar:
                try:
                    create_catalog_item(conn, marca, modelo, qualidade, custo_sem_aro, custo_com_aro, observacao)
                    log_action(conn, user, "criou_item_catalogo", "catalogo_pecas", None, {"modelo": modelo, "marca": marca})
                    st.success("Item cadastrado.")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))

    st.divider()
    st.subheader("Marcas")
    for marca in MARCAS_PADRAO:
        with st.expander(marca, expanded=False):
            _render_catalog_results(conn, load_catalog_items(conn, marca=marca, limit=60))
