import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.auth import current_user
from utils.dashboard_ui import light_page_header, moeda
from utils.permissions import has_permission, require_permission
from utils.quiosques import current_quiosque_id, load_quiosques, user_can_view_all
from utils.seminovos import (
    ANEXO_TIPOS,
    CHECKLIST_ITEMS,
    CHECKLIST_OPTIONS,
    STATUS_COMPRA,
    STATUS_SEMINOVO,
    can_view_internal_costs,
    checklist_comparison,
    checklist_dict,
    create_device_purchase,
    ensure_exit_checklist_from_entry,
    ensure_preowned_stock,
    get_device_purchase,
    load_attachments,
    load_device_purchases,
    load_history,
    load_preowned_stock,
    save_attachment,
    save_checklist,
    save_purchase_term,
    update_device_status,
    update_preowned_stock,
)
from utils.tx_components import tx_card


def _money_input(label, value=0.0, key=None):
    return st.number_input(label, min_value=0.0, value=float(value or 0), step=10.0, key=key)


def _quiosque_selector(conn, user, key):
    if not user_can_view_all(user):
        return current_quiosque_id(user)
    df = load_quiosques(conn)
    options = {int(row.id): row.nome for row in df.itertuples()}
    return st.selectbox(
        "Loja/quiosque",
        list(options.keys()),
        format_func=lambda value: options[value],
        key=key,
    )


def _status_badge(status):
    colors = {
        "Em avaliação": "#2563EB",
        "Aguardando aprovação": "#F59E0B",
        "Aprovado para compra": "#16A34A",
        "Compra concluída": "#16A34A",
        "Recusado": "#E63946",
        "Em estoque": "#111827",
        "Vendido": "#64748B",
    }
    color = colors.get(status, "#64748B")
    st.markdown(
        f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;background:{color}14;color:{color};font-weight:800;'>{status}</span>",
        unsafe_allow_html=True,
    )


def _render_nova_avaliacao(conn, user):
    st.subheader("Nova Avaliação")
    with st.form("form_nova_avaliacao_aparelho"):
        c1, c2, c3 = st.columns(3)
        with c1:
            cliente = st.text_input("Cliente / vendedor")
            cpf = st.text_input("CPF")
            telefone = st.text_input("Telefone")
            documento = st.text_input("Documento")
        with c2:
            imei = st.text_input("IMEI")
            marca = st.text_input("Marca")
            modelo = st.text_input("Modelo")
            cor = st.text_input("Cor")
        with c3:
            capacidade = st.text_input("Capacidade")
            estado_fisico = st.selectbox("Estado físico", ["Excelente", "Bom", "Regular", "Ruim", "Sucata"])
            data_entrada = st.date_input("Data de entrada", value=datetime.today())
            quiosque_id = _quiosque_selector(conn, user, "seminovo_nova_quiosque")

        observacoes = st.text_area("Observações")
        c1, c2, c3 = st.columns(3)
        with c1:
            valor_sugerido = _money_input("Valor sugerido")
        with c2:
            valor_final = _money_input("Valor final")
        with c3:
            forma_pagamento = st.selectbox("Forma de pagamento", ["Dinheiro", "Pix", "Débito", "Crédito", "Transferência", "Outro"])
            status = st.selectbox("Status", STATUS_COMPRA, index=0)

        submitted = st.form_submit_button("Salvar avaliação", width="stretch")

    if submitted:
        if not cliente.strip():
            st.error("Informe o cliente/vendedor.")
            return
        aparelho_id = create_device_purchase(
            conn,
            {
                "cliente": cliente.strip(),
                "cpf": cpf.strip(),
                "telefone": telefone.strip(),
                "documento": documento.strip(),
                "imei": imei.strip(),
                "marca": marca.strip(),
                "modelo": modelo.strip(),
                "cor": cor.strip(),
                "capacidade": capacidade.strip(),
                "estado_fisico": estado_fisico,
                "observacoes": observacoes.strip(),
                "data_entrada": data_entrada,
                "valor_sugerido": valor_sugerido,
                "valor_final": valor_final,
                "forma_pagamento": forma_pagamento,
                "status": status,
                "quiosque_id": quiosque_id,
            },
            user,
        )
        st.success(f"Avaliação #{aparelho_id} criada. Agora preencha o checklist de entrada.")
        st.session_state["seminovo_aparelho_aberto"] = aparelho_id


def _render_checklist_form(conn, aparelho_id, etapa, user):
    title = "Checklist de Entrada" if etapa == "entrada" else "Checklist de Saída"
    if etapa == "saida":
        ensure_exit_checklist_from_entry(conn, aparelho_id, user)
        st.caption("A saída é iniciada copiando automaticamente o checklist de entrada. Ajuste apenas o que mudou.")

    data = checklist_dict(conn, aparelho_id, etapa)
    with st.form(f"checklist_{etapa}_{aparelho_id}"):
        st.markdown(f"**{title}**")
        updated = {}
        for item in CHECKLIST_ITEMS:
            c1, c2 = st.columns([0.42, 0.58])
            with c1:
                valor = st.selectbox(
                    item,
                    CHECKLIST_OPTIONS,
                    index=CHECKLIST_OPTIONS.index(data[item]["valor"]) if data[item]["valor"] in CHECKLIST_OPTIONS else 2,
                    key=f"{etapa}_{aparelho_id}_{item}_valor",
                )
            with c2:
                obs = st.text_input(
                    "Observação",
                    value=data[item].get("observacao", ""),
                    key=f"{etapa}_{aparelho_id}_{item}_obs",
                    label_visibility="collapsed",
                )
            updated[item] = {"valor": valor, "observacao": obs}
        if st.form_submit_button(f"Salvar {title.lower()}", width="stretch"):
            save_checklist(conn, aparelho_id, etapa, updated, user)
            st.success("Checklist salvo.")
            st.rerun()


def _render_aparelho_detalhes(conn, aparelho_id, user):
    aparelho = get_device_purchase(conn, aparelho_id)
    if not aparelho:
        st.warning("Aparelho não encontrado.")
        return

    st.markdown(f"### #{aparelho_id} · {aparelho.get('marca') or ''} {aparelho.get('modelo') or ''}")
    _status_badge(aparelho.get("status"))

    abas = st.tabs(["Resumo", "Checklist", "Termo", "Anexos", "Histórico"])
    with abas[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Vendedor", aparelho.get("cliente") or "-")
        c2.metric("IMEI", aparelho.get("imei") or "-")
        c3.metric("Valor final", moeda(aparelho.get("valor_final")))
        st.caption(f"Quiosque: {aparelho.get('quiosque_nome') or aparelho.get('quiosque_id') or '-'} | Atendente: {aparelho.get('atendente_nome') or '-'}")
        if has_permission("edit_device_purchase_status", user):
            novo_status = st.selectbox(
                "Alterar status",
                STATUS_COMPRA,
                index=STATUS_COMPRA.index(aparelho.get("status")) if aparelho.get("status") in STATUS_COMPRA else 0,
                key=f"seminovo_status_{aparelho_id}",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Salvar status", width="stretch", key=f"save_status_{aparelho_id}"):
                    update_device_status(conn, aparelho_id, novo_status, user)
                    st.success("Status atualizado.")
                    st.rerun()
            with c2:
                if st.button("Enviar para estoque de seminovos", width="stretch", key=f"estoque_{aparelho_id}"):
                    ensure_preowned_stock(conn, aparelho_id, user)
                    st.success("Aparelho adicionado ao estoque de seminovos.")
                    st.rerun()
        else:
            st.info("Seu perfil pode registrar avaliação, checklist e anexos. Aprovação e conclusão ficam com gerente/admin.")

    with abas[1]:
        c1, c2 = st.columns(2)
        with c1:
            _render_checklist_form(conn, aparelho_id, "entrada", user)
        with c2:
            _render_checklist_form(conn, aparelho_id, "saida", user)
        st.markdown("#### Comparação Entrada | Saída")
        st.dataframe(checklist_comparison(conn, aparelho_id), hide_index=True, width="stretch")

    with abas[2]:
        if st.button("Gerar termo de compra", width="stretch", key=f"termo_{aparelho_id}"):
            save_purchase_term(conn, aparelho_id, user)
            st.success("Termo gerado.")
            st.rerun()
        aparelho = get_device_purchase(conn, aparelho_id)
        termo = aparelho.get("termo_html") if aparelho else ""
        if termo:
            st.download_button(
                "Baixar termo HTML",
                data=termo.encode("utf-8"),
                file_name=f"termo_compra_{aparelho_id}.html",
                mime="text/html",
                width="stretch",
            )
            with st.expander("Pré-visualizar termo", expanded=False):
                components.html(termo, height=520, scrolling=True)
        else:
            st.info("Nenhum termo gerado ainda.")

    with abas[3]:
        tipo = st.selectbox("Tipo de anexo", ANEXO_TIPOS, key=f"tipo_anexo_{aparelho_id}")
        files = st.file_uploader(
            "Adicionar anexos",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            accept_multiple_files=True,
            key=f"anexos_{aparelho_id}",
        )
        if st.button("Salvar anexos", width="stretch", disabled=not files, key=f"save_anexo_{aparelho_id}"):
            for uploaded in files:
                save_attachment(conn, aparelho_id, uploaded, tipo, user)
            st.success("Anexos salvos.")
            st.rerun()
        anexos = load_attachments(conn, aparelho_id)
        if anexos.empty:
            st.info("Nenhum anexo cadastrado.")
        else:
            for row in anexos.itertuples():
                st.markdown(f"**{row.tipo}** · {row.nome_arquivo}")
                path = Path(row.caminho)
                if path.exists() and str(row.mime_type or "").startswith("image"):
                    st.image(str(path), width=220)
                elif path.exists():
                    st.download_button("Baixar arquivo", data=path.read_bytes(), file_name=row.nome_arquivo, key=f"download_anexo_{row.id}")

    with abas[4]:
        hist = load_history(conn, aparelho_id)
        if hist.empty:
            st.info("Nenhum histórico ainda.")
        else:
            hist["detalhes"] = hist["detalhes"].map(lambda value: json.dumps(json.loads(value or "{}"), ensure_ascii=False) if value else "")
            st.dataframe(hist, hide_index=True, width="stretch")


def _render_lista_aparelhos(conn, user):
    status = st.selectbox("Status", ["Todos"] + STATUS_COMPRA, key="seminovo_lista_status")
    search = st.text_input("Buscar por cliente, IMEI, marca ou modelo", key="seminovo_lista_busca")
    df = load_device_purchases(conn, status=status, search=search, limit=200)
    if df.empty:
        st.info("Nenhum aparelho encontrado.")
        return
    for row in df.itertuples():
        title = f"#{row.id} · {row.marca or ''} {row.modelo or ''}".strip()
        detail = f"{row.cliente} • {row.status} • {moeda(row.valor_final)}"
        if tx_card(title, row.imei or "Sem IMEI", detail, key=f"aparelho_{row.id}", icon="📱", accent="green", state_key="seminovo_open_card"):
            _render_aparelho_detalhes(conn, int(row.id), user)


def _render_checklist_saida(conn, user):
    st.caption("Selecione um aparelho e confirme o checklist de saída reaproveitando a entrada.")
    df = load_device_purchases(conn, status=None, search="", limit=200)
    if df.empty:
        st.info("Nenhum aparelho cadastrado.")
        return
    options = {int(row.id): f"#{row.id} · {row.marca or ''} {row.modelo or ''} · {row.cliente}" for row in df.itertuples()}
    aparelho_id = st.selectbox("Aparelho", list(options.keys()), format_func=lambda value: options[value])
    _render_checklist_form(conn, aparelho_id, "saida", user)
    st.dataframe(checklist_comparison(conn, aparelho_id), hide_index=True, width="stretch")


def _render_termos(conn, user):
    df = load_device_purchases(conn, status=None, search="", limit=200)
    df = df[df["termo_html"].fillna("") != ""] if not df.empty else df
    if df.empty:
        st.info("Nenhum termo gerado.")
        return
    for row in df.itertuples():
        with st.container(border=True):
            st.markdown(f"**#{row.id} · {row.cliente} · {row.modelo or '-'}**")
            st.download_button(
                "Baixar termo HTML",
                data=str(row.termo_html or "").encode("utf-8"),
                file_name=f"termo_compra_{row.id}.html",
                mime="text/html",
                key=f"termo_download_{row.id}",
            )


def _render_estoque_seminovos(conn, user):
    status = st.selectbox("Status", ["Todos"] + STATUS_SEMINOVO, key="seminovo_estoque_status")
    df = load_preowned_stock(conn, status=status, limit=200)
    if df.empty:
        st.info("Nenhum seminovo em estoque.")
        return
    show_costs = can_view_internal_costs(user)
    for row in df.itertuples():
        detail = f"{row.status} • Venda {moeda(row.valor_venda)}"
        if show_costs:
            detail += f" • Lucro {moeda(row.lucro_estimado)}"
        if tx_card(row.codigo_interno or f"Seminovo #{row.id}", row.modelo or "-", detail, key=f"seminovo_estoque_{row.id}", icon="📦", accent="amber", state_key="seminovo_estoque_open"):
            c1, c2, c3 = st.columns(3)
            c1.metric("IMEI", row.imei or "-")
            c2.metric("Cor", row.cor or "-")
            c3.metric("Capacidade", row.capacidade or "-")
            if show_costs:
                c1, c2, c3 = st.columns(3)
                c1.metric("Custo compra", moeda(row.custo_compra))
                c2.metric("Custo reparo", moeda(row.custo_reparo))
                c3.metric("Lucro estimado", moeda(row.lucro_estimado))
            if has_permission("edit_financial_values", user):
                with st.form(f"edit_seminovo_{row.id}"):
                    c1, c2, c3 = st.columns(3)
                    custo_reparo = c1.number_input("Custo de reparo", min_value=0.0, value=float(row.custo_reparo or 0), step=10.0)
                    valor_venda = c2.number_input("Valor de venda", min_value=0.0, value=float(row.valor_venda or 0), step=10.0)
                    novo_status = c3.selectbox("Status", STATUS_SEMINOVO, index=STATUS_SEMINOVO.index(row.status) if row.status in STATUS_SEMINOVO else 0)
                    comprador = st.text_input("Comprador", value=row.comprador or "")
                    if st.form_submit_button("Atualizar seminovo", width="stretch"):
                        update_preowned_stock(conn, row.id, custo_reparo, valor_venda, novo_status, comprador, user)
                        st.success("Seminovo atualizado.")
                        st.rerun()


def _render_relatorios(conn, user):
    df = load_device_purchases(conn, status=None, search="", limit=1000)
    estoque = load_preowned_stock(conn, status=None, limit=1000)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avaliações", len(df))
    c2.metric("Compras concluídas", len(df[df["status"].isin(["Compra concluída", "Em estoque", "Vendido"])]) if not df.empty else 0)
    c3.metric("Em estoque", len(estoque[estoque["status"] == "Disponível"]) if not estoque.empty else 0)
    c4.metric("Vendidos", len(estoque[estoque["status"] == "Vendido"]) if not estoque.empty else 0)
    if can_view_internal_costs(user) and not estoque.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Custo total", moeda(estoque["custo_total"].sum()))
        c2.metric("Valor de venda", moeda(estoque["valor_venda"].sum()))
        c3.metric("Lucro estimado", moeda(estoque["lucro_estimado"].sum()))
    if not df.empty:
        resumo = df.groupby("status", as_index=False).agg(total=("id", "count"), valor=("valor_final", "sum"))
        st.dataframe(resumo.rename(columns={"status": "Status", "total": "Total", "valor": "Valor final"}), hide_index=True, width="stretch")


def render_compra_aparelhos(conn):
    if not require_permission("manage_device_purchases"):
        return

    user = current_user()
    light_page_header("📱", "Compra de Aparelhos", "Avaliação, checklist, termos e estoque de seminovos em um registro único.")
    menu = st.segmented_control(
        "Área",
        [
            "Nova Avaliação",
            "Aparelhos Comprados",
            "Checklist Entrada/Saída",
            "Termos Assinados",
            "Estoque de Seminovos",
            "Relatórios",
        ],
        default="Nova Avaliação",
        key="seminovos_menu",
    )

    if menu == "Nova Avaliação":
        _render_nova_avaliacao(conn, user)
    elif menu == "Aparelhos Comprados":
        _render_lista_aparelhos(conn, user)
    elif menu == "Checklist Entrada/Saída":
        _render_checklist_saida(conn, user)
    elif menu == "Termos Assinados":
        _render_termos(conn, user)
    elif menu == "Estoque de Seminovos":
        _render_estoque_seminovos(conn, user)
    else:
        _render_relatorios(conn, user)
