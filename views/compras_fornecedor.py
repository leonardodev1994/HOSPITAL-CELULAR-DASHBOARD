from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import ensure_supplier_purchase_schema
from utils.auth import current_user
from utils.dashboard_ui import light_page_header, moeda
from utils.fornecedor_compras import (
    DEFAULT_ARO_OPTIONS,
    DEFAULT_TECH_OPTIONS,
    DEFAULT_TYPE_OPTIONS,
    PAYMENT_STATUSES,
    SUPPLIER_PURCHASE_COLUMNS,
    csv_preview,
    dataframe_from_rows,
    export_purchases_csv,
    import_supplier_purchases,
    load_supplier_dictionary,
    load_supplier_history,
    load_supplier_purchases,
    load_supplier_summary,
    preview_from_images,
    preview_from_text,
    spreadsheet_preview,
    ai_ocr_available,
    update_purchase_payment,
    update_supplier_dictionary,
)
from utils.permissions import require_permission


SIMPLE_PREVIEW_COLUMNS = [
    "data_compra",
    "tipo",
    "descricao_original",
    "valor",
    "observacao",
    "status_pagamento",
]


def _column_config():
    return {
        "data_compra": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
        "fornecedor": st.column_config.TextColumn("Fornecedor", width="medium"),
        "tipo": st.column_config.SelectboxColumn("Tipo", options=DEFAULT_TYPE_OPTIONS),
        "descricao_original": st.column_config.TextColumn("Descrição original", width="large"),
        "modelo": st.column_config.TextColumn("Modelo", width="large"),
        "aro": st.column_config.SelectboxColumn("Aro", options=DEFAULT_ARO_OPTIONS),
        "tecnologia": st.column_config.SelectboxColumn("Tecnologia", options=DEFAULT_TECH_OPTIONS),
        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        "observacao": st.column_config.TextColumn("Observação", width="large"),
        "status_pagamento": st.column_config.SelectboxColumn("Status", options=PAYMENT_STATUSES),
        "valor_pago": st.column_config.NumberColumn("Valor pago", format="R$ %.2f"),
        "data_pagamento": st.column_config.DateColumn("Data pagamento", format="DD/MM/YYYY"),
    }


def _dictionary_editor(conn, user):
    st.subheader("Dicionário de siglas")
    dictionary_df = load_supplier_dictionary(conn)
    if dictionary_df.empty:
        dictionary_df = pd.DataFrame(columns=["sigla", "categoria", "valor_expandido", "ativo"])
    else:
        dictionary_df = dictionary_df[["sigla", "categoria", "valor_expandido", "ativo"]]

    edited = st.data_editor(
        dictionary_df,
        width="stretch",
        num_rows="dynamic",
        hide_index=True,
        key="supplier_dictionary_editor",
        column_config={
            "sigla": st.column_config.TextColumn("Sigla"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["tipo", "aro", "tecnologia"]),
            "valor_expandido": st.column_config.TextColumn("Valor expandido", width="large"),
            "ativo": st.column_config.CheckboxColumn("Ativo"),
        },
    )
    if st.button("Salvar dicionário", key="save_supplier_dictionary", width="stretch"):
        saved = update_supplier_dictionary(conn, edited.to_dict("records"), user)
        st.success(f"{saved} sigla(s) salvas.")
        st.rerun()


def _preview_editor(conn, df):
    if df is None or df.empty:
        st.info("Nenhum item pronto para conferência ainda.")
        return None
    base_df = df.copy()
    visible_df = base_df[SIMPLE_PREVIEW_COLUMNS].copy()
    edited = st.data_editor(
        visible_df,
        width="stretch",
        num_rows="dynamic",
        hide_index=True,
        key="supplier_purchase_preview_editor",
        column_config={key: value for key, value in _column_config().items() if key in SIMPLE_PREVIEW_COLUMNS},
    )
    for column in SIMPLE_PREVIEW_COLUMNS:
        base_df[column] = edited[column]
    return base_df[SUPPLIER_PURCHASE_COLUMNS]


def _process_inputs(conn):
    st.subheader("Importar planilha de despesas")
    st.caption("Envie a planilha, confira as linhas e importe. Cada linha vira uma despesa com o valor correspondente.")
    files = st.file_uploader(
        "Foto da folha do fornecedor",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="supplier_purchase_upload",
    )
    raw_text = st.text_area(
        "Texto OCR/manual (opcional)",
        placeholder="Cole aqui o texto bruto ou resumos como: Compra de peças - 02/06 - 8 itens - 555",
        height=140,
        key="supplier_purchase_raw_text",
    )
    csv_file = st.file_uploader(
        "Ou importar planilha/CSV",
        type=["csv", "xlsx", "xlsm"],
        accept_multiple_files=False,
        key="supplier_purchase_csv",
        help="Aceita o modelo simplificado por dia ou a planilha detalhada/CSV TX.",
    )

    cols = st.columns(3)
    with cols[0]:
        use_ai = st.button("Ler fotos com IA", width="stretch", disabled=not files)
    with cols[1]:
        parse_text = st.button("Converter texto em tabela", width="stretch", disabled=not raw_text.strip())
    with cols[2]:
        parse_csv = st.button("Pré-visualizar CSV", width="stretch", disabled=csv_file is None)

    if use_ai:
        if not ai_ocr_available():
            st.error("OCR com IA indisponível: configure `OPENAI_API_KEY` no ambiente.")
        else:
            with st.spinner("Lendo imagens e estruturando compras..."):
                try:
                    preview_df, extracted_meta, ocr_text = preview_from_images(files, conn=conn)
                except Exception as error:
                    st.error(str(error))
                else:
                    st.session_state["supplier_purchase_preview_df"] = preview_df
                    st.session_state["supplier_purchase_extracted_meta"] = extracted_meta
                    if ocr_text:
                        st.session_state["supplier_purchase_raw_text"] = ocr_text
                    st.success(f"{len(preview_df)} item(ns) extraído(s) da(s) foto(s).")

    if parse_text:
        preview_df = preview_from_text(raw_text, conn=conn)
        st.session_state["supplier_purchase_preview_df"] = preview_df
        st.session_state["supplier_purchase_extracted_meta"] = []
        st.success(f"{len(preview_df)} item(ns) convertido(s) do texto.")

    if parse_csv:
        if str(csv_file.name or "").lower().endswith((".xlsx", ".xlsm")):
            preview_df = spreadsheet_preview(csv_file, conn=conn)
        else:
            preview_df = csv_preview(csv_file, conn=conn)
        st.session_state["supplier_purchase_preview_df"] = preview_df
        st.session_state["supplier_purchase_extracted_meta"] = []
        st.success(f"{len(preview_df)} item(ns) carregado(s) do arquivo.")


def _import_actions(conn, user):
    preview_df = st.session_state.get("supplier_purchase_preview_df")
    edited_df = _preview_editor(conn, preview_df)
    if edited_df is None:
        return

    total_preview = float(edited_df["valor"].sum()) if not edited_df.empty else 0.0
    st.info(f"Prévia pronta: {len(edited_df)} linha(s) • total {moeda(total_preview)}.")

    col_import, col_clear = st.columns(2)
    with col_import:
        if st.button("Importar e lançar em Despesas", width="stretch", key="import_supplier_purchases"):
            try:
                result = import_supplier_purchases(
                    conn,
                    edited_df,
                    extracted_meta=st.session_state.get("supplier_purchase_extracted_meta") or [],
                    user=user,
                    create_expenses=True,
                )
            except Exception as error:
                st.error(str(error))
            else:
                st.success(
                    f"{result['despesas']} despesa(s) criada(s) com sucesso. Total importado: {moeda(result['total'])}."
                )
                st.session_state["supplier_purchase_preview_df"] = pd.DataFrame(columns=SUPPLIER_PURCHASE_COLUMNS)
                st.session_state["supplier_purchase_extracted_meta"] = []
                st.rerun()
    with col_clear:
        if st.button("Limpar conferência", width="stretch", key="clear_supplier_preview"):
            st.session_state["supplier_purchase_preview_df"] = pd.DataFrame(columns=SUPPLIER_PURCHASE_COLUMNS)
            st.session_state["supplier_purchase_extracted_meta"] = []
            st.rerun()


def _recent_imported_expenses(conn):
    df = pd.read_sql_query(
        """
        SELECT data, descricao, valor
        FROM despesas
        WHERE COALESCE(origem, '') = 'compras_fornecedor'
        ORDER BY id DESC
        LIMIT 20
        """,
        conn,
    )
    if df.empty:
        st.info("Nenhuma despesa importada por este módulo ainda.")
        return
    st.dataframe(
        df.rename(columns={"data": "Data", "descricao": "Descrição", "valor": "Valor"}),
        hide_index=True,
        width="stretch",
        column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
    )


def _summary_and_history(conn):
    st.subheader("Controle financeiro")
    summary = load_supplier_summary(conn)
    total_comprado = float(summary.iloc[0]["total_comprado"] or 0) if not summary.empty else 0.0
    total_pago = float(summary.iloc[0]["total_pago"] or 0) if not summary.empty else 0.0
    saldo_devedor = float(summary.iloc[0]["saldo_devedor"] or 0) if not summary.empty else 0.0
    quantidade = int(summary.iloc[0]["quantidade"] or 0) if not summary.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total comprado", moeda(total_comprado))
    c2.metric("Total pago", moeda(total_pago))
    c3.metric("Saldo devedor", moeda(saldo_devedor))
    c4.metric("Itens lançados", quantidade)

    history = load_supplier_history(conn)
    with st.expander("Histórico por fornecedor", expanded=False):
        if history.empty:
            st.info("Nenhum histórico por fornecedor ainda.")
        else:
            st.dataframe(
                history.rename(
                    columns={
                        "fornecedor": "Fornecedor",
                        "quantidade": "Itens",
                        "total_comprado": "Total comprado",
                        "total_pago": "Total pago",
                        "saldo_devedor": "Saldo devedor",
                        "ultima_compra": "Última compra",
                    }
                ),
                hide_index=True,
                width="stretch",
                column_config={
                    "Total comprado": st.column_config.NumberColumn("Total comprado", format="R$ %.2f"),
                    "Total pago": st.column_config.NumberColumn("Total pago", format="R$ %.2f"),
                    "Saldo devedor": st.column_config.NumberColumn("Saldo devedor", format="R$ %.2f"),
                },
            )


def _purchase_manager(conn, user):
    st.subheader("Compras importadas")
    col_forn, col_status = st.columns(2)
    with col_forn:
        fornecedor = st.text_input("Filtrar fornecedor", key="supplier_purchase_filter_supplier")
    with col_status:
        status = st.selectbox("Status", ["Todos"] + PAYMENT_STATUSES, key="supplier_purchase_filter_status")

    df = load_supplier_purchases(
        conn,
        fornecedor=fornecedor,
        status_pagamento="" if status == "Todos" else status,
    )
    if df.empty:
        st.info("Nenhuma compra cadastrada.")
        return

    export_df = df[
        ["data_compra", "fornecedor", "tipo", "modelo", "aro", "tecnologia", "valor", "observacao", "status_pagamento", "valor_pago", "data_pagamento"]
    ].copy()
    st.download_button(
        "Exportar CSV",
        data=export_purchases_csv(export_df),
        file_name=f"compras_fornecedor_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        width="stretch",
    )

    st.dataframe(
        df.rename(
            columns={
                "id": "ID",
                "data_compra": "Data",
                "fornecedor": "Fornecedor",
                "tipo": "Tipo",
                "modelo": "Modelo",
                "aro": "Aro",
                "tecnologia": "Tecnologia",
                "valor": "Valor",
                "valor_pago": "Valor pago",
                "data_pagamento": "Data pagamento",
                "observacao": "Observação",
                "status_pagamento": "Status",
                "arquivo_origem": "Arquivo",
            }
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "Valor pago": st.column_config.NumberColumn("Valor pago", format="R$ %.2f"),
        },
    )

    st.markdown("#### Atualizar pagamento")
    selected_id = st.selectbox("Compra", list(df["id"]), format_func=lambda value: f"#{value}", key="supplier_purchase_selected_id")
    selected = df[df["id"] == selected_id].iloc[0]
    with st.form("supplier_purchase_payment_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            status_pagamento = st.selectbox(
                "Status pagamento",
                PAYMENT_STATUSES,
                index=PAYMENT_STATUSES.index(selected["status_pagamento"]) if selected["status_pagamento"] in PAYMENT_STATUSES else 0,
            )
        with c2:
            valor_pago = st.number_input("Valor pago", min_value=0.0, value=float(selected["valor_pago"] or 0), step=10.0)
        with c3:
            pagamento_raw = selected["data_pagamento"] if pd.notna(selected["data_pagamento"]) else ""
            pagamento_date = pd.to_datetime(pagamento_raw, errors="coerce")
            data_pagamento = st.date_input(
                "Data pagamento",
                value=pagamento_date.date() if pd.notna(pagamento_date) else datetime.today().date(),
            )
        observacao = st.text_area("Observação", value=selected["observacao"] or "")
        submitted = st.form_submit_button("Salvar pagamento", width="stretch")

    if submitted:
        try:
            update_purchase_payment(
                conn,
                selected_id,
                status_pagamento,
                valor_pago,
                data_pagamento.isoformat() if data_pagamento else "",
                observacao,
                user=user,
            )
        except Exception as error:
            st.error(str(error))
        else:
            st.success("Pagamento atualizado.")
            st.rerun()


def render_compras_fornecedor(conn):
    if not require_permission("manage_supplier_purchases"):
        return

    ensure_supplier_purchase_schema(conn)
    user = current_user()
    st.session_state.setdefault("supplier_purchase_preview_df", pd.DataFrame(columns=SUPPLIER_PURCHASE_COLUMNS))
    st.session_state.setdefault("supplier_purchase_extracted_meta", [])

    light_page_header(
        "🧾",
        "Compras de Fornecedor",
        "Importe a planilha e registre cada linha como despesa de peça.",
    )

    if ai_ocr_available():
        st.caption("OCR com IA habilitado. A meta e sair no mesmo formato simples da planilha.")
    else:
        st.caption("OCR com IA desabilitado no ambiente atual. Você ainda pode importar planilha, CSV ou colar texto manual.")

    _process_inputs(conn)
    st.divider()
    _import_actions(conn, user)
    st.divider()
    st.subheader("Últimas despesas importadas")
    _recent_imported_expenses(conn)

    with st.expander("Controle financeiro e histórico", expanded=False):
        _summary_and_history(conn)
        st.divider()
        _purchase_manager(conn, user)

    with st.expander("Dicionário de siglas", expanded=False):
        _dictionary_editor(conn, user)
