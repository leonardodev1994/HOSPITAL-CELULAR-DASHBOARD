import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

from database.database import execute_insert_returning_id
from utils.dashboard_ui import page_header
from utils.pdf_os import generate_os_pdf
from views.clientes import create_cliente, load_clientes


STATUS_OS = [
    "Em análise",
    "Em reparo",
    "Aguardando peça",
    "Finalizado",
    "Entregue",
    "Cancelado",
]

STATUS_COLORS = {
    "Finalizado": ("#16A34A", "#052E16"),
    "Entregue": ("#06B6D4", "#083344"),
    "Cancelado": ("#DC2626", "#450A0A"),
    "Aguardando peça": ("#EAB308", "#422006"),
    "Em reparo": ("#6366F1", "#1E1B4B"),
    "Em análise": ("#94A3B8", "#111827"),
}

TEST_OPTIONS = ["Ok", "Defeito", "Não Testado"]
YES_NO = ["Sim", "Não"]
FORMAS_PAGAMENTO = ["Dinheiro", "Pix", "Crédito", "Débito", "Misto"]

CHECKLIST_ENTRADA = [
    "Tela",
    "Carregamento",
    "Botões",
    "Câmera traseira",
    "Câmera frontal",
    "Sensor de proximidade",
    "Alto-falante",
    "Auricular",
    "Microfone",
    "Carcaça",
]

CHECKLIST_SAIDA = [
    "Power button",
    "LCD",
    "Home button",
    "Touch ID ou Face ID",
    "3D Touch",
    "Botão de vibração",
    "Botão de volume",
    "Câmera frontal",
    "Câmera traseira",
    "Microfone",
    "Alto-falante",
    "Auricular",
    "Sensor de proximidade",
    "Porta do fone",
    "Carcaça",
]


def _json_load(value):
    if not value:
        return {}

    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _json_dump(value):
    return json.dumps(value, ensure_ascii=False)


def _cliente_options(df_clientes):
    options = {"Novo cliente": None}

    for row in df_clientes.itertuples():
        telefone = row.telefone or "sem telefone"
        options[f"{row.nome} | {telefone}"] = row.id

    return options


def _cliente_selecionado(df_clientes, cliente_id):
    if cliente_id is None:
        return None

    filtro = df_clientes[df_clientes["id"] == cliente_id]
    return None if filtro.empty else filtro.iloc[0]


def _digits(value):
    return "".join(char for char in str(value or "") if char.isdigit())


def _row_value(row, field, default=""):
    if isinstance(row, pd.Series):
        value = row.get(field, default)
    else:
        value = getattr(row, field, default)

    return default if pd.isna(value) else value


def _search_clientes(df_clientes, termo, limit=8):
    termo = str(termo or "").strip()
    if len(termo) < 2 or df_clientes.empty:
        return df_clientes.head(0)

    termo_lower = termo.lower()
    termo_digits = _digits(termo)
    mask = (
        df_clientes["nome"].fillna("").str.lower().str.contains(termo_lower, regex=False)
        | df_clientes["cpf"].fillna("").str.lower().str.contains(termo_lower, regex=False)
        | df_clientes["telefone"].fillna("").str.lower().str.contains(termo_lower, regex=False)
    )

    if termo_digits:
        cpf_digits = df_clientes["cpf"].fillna("").map(_digits)
        telefone_digits = df_clientes["telefone"].fillna("").map(_digits)
        mask = mask | cpf_digits.str.contains(termo_digits, regex=False) | telefone_digits.str.contains(termo_digits, regex=False)

    return df_clientes[mask].head(limit)


def _cliente_card(cliente):
    documento = cliente.cpf or "Sem CPF/CNPJ"
    telefone = cliente.telefone or "Sem telefone"
    endereco = cliente.endereco or "Endereço não informado"
    st.markdown(
        f"""
        <div class="client-search-card">
            <div>
                <strong>{cliente.nome}</strong>
                <span>{telefone} • {documento}</span>
                <small>{endereco}</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_cliente_to_new_os(cliente):
    st.session_state["nova_os_cliente_id"] = int(_row_value(cliente, "id", 0))
    st.session_state["nova_os_nome"] = _row_value(cliente, "nome", "") or ""
    st.session_state["nova_os_cpf"] = _row_value(cliente, "cpf", "") or ""
    st.session_state["nova_os_tel"] = _row_value(cliente, "telefone", "") or ""
    st.session_state["nova_os_end"] = _row_value(cliente, "endereco", "") or ""


def _apply_cliente_to_edit_os(cliente, os_id):
    st.session_state[f"edit_cliente_id_{os_id}"] = int(_row_value(cliente, "id", 0))
    st.session_state[f"edit_cliente_{os_id}"] = _row_value(cliente, "nome", "") or ""
    st.session_state[f"edit_cpf_{os_id}"] = _row_value(cliente, "cpf", "") or ""
    st.session_state[f"edit_telefone_{os_id}"] = _row_value(cliente, "telefone", "") or ""
    st.session_state[f"edit_endereco_{os_id}"] = _row_value(cliente, "endereco", "") or ""


def _render_cliente_search(df_clientes, key_prefix, on_select, selected_id=None):
    st.markdown(
        """
        <div class="client-search-title">
            <span class="material-symbols-rounded">search</span>
            <div>
                <strong>Pesquisar cliente</strong>
                <small>Busque por nome, CPF/CNPJ ou telefone/WhatsApp</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    termo = st.text_input(
        "Buscar cliente",
        placeholder="Digite parte do nome, CPF/CNPJ ou telefone...",
        key=f"{key_prefix}_busca_cliente",
        label_visibility="collapsed",
    )

    if selected_id:
        cliente_atual = _cliente_selecionado(df_clientes, selected_id)
        if cliente_atual is not None:
            st.caption(f"Cliente selecionado: {cliente_atual['nome']} • {cliente_atual['telefone'] or 'sem telefone'}")

    encontrados = _search_clientes(df_clientes, termo)
    if termo.strip() and len(termo.strip()) < 2:
        st.caption("Digite pelo menos 2 caracteres para pesquisar.")
    elif termo.strip() and encontrados.empty:
        st.info("Nenhum cliente encontrado. Preencha os dados abaixo para cadastrar/usar um novo cliente.")
    elif not encontrados.empty:
        st.markdown('<div class="client-search-list">', unsafe_allow_html=True)
        for cliente in encontrados.itertuples():
            col_info, col_action = st.columns([.78, .22])
            with col_info:
                _cliente_card(cliente)
            with col_action:
                if st.button("Usar cliente", key=f"{key_prefix}_usar_cliente_{cliente.id}", width="stretch"):
                    on_select(cliente)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def _load_ordens_servico(conn):
    return pd.read_sql_query("""
    SELECT
        id,
        data,
        cliente,
        telefone,
        marca,
        modelo,
        servico,
        valor,
        garantia,
        status
    FROM ordens_servico
    ORDER BY id DESC
    """, conn)


def _load_ordens_por_cliente(conn, cliente):
    cliente_id = int(cliente.id) if getattr(cliente, "id", None) is not None else None
    nome = getattr(cliente, "nome", "") or ""
    cpf = getattr(cliente, "cpf", "") or ""
    telefone = getattr(cliente, "telefone", "") or ""

    return pd.read_sql_query("""
    SELECT
        id,
        data,
        cliente,
        cpf,
        telefone,
        marca,
        modelo,
        servico,
        valor,
        garantia,
        status
    FROM ordens_servico
    WHERE cliente_id = ?
       OR cpf = ?
       OR telefone = ?
       OR cliente LIKE ?
    ORDER BY id DESC
    """, conn, params=(cliente_id, cpf, telefone, f"%{nome}%"))


def _search_ordens_texto(conn, termo, limit=10):
    termo = str(termo or "").strip()
    termo_digits = _digits(termo)
    like_term = f"%{termo}%"
    digit_like = f"%{termo_digits}%"

    if len(termo) < 2:
        return pd.DataFrame()

    if termo_digits:
        return pd.read_sql_query("""
        SELECT
            id,
            data,
            cliente,
            cpf,
            telefone,
            marca,
            modelo,
            servico,
            valor,
            garantia,
            status
        FROM ordens_servico
        WHERE cliente LIKE ?
           OR cpf LIKE ?
           OR telefone LIKE ?
        ORDER BY id DESC
        LIMIT ?
        """, conn, params=(like_term, digit_like, digit_like, limit))

    return pd.read_sql_query("""
    SELECT
        id,
        data,
        cliente,
        cpf,
        telefone,
        marca,
        modelo,
        servico,
        valor,
        garantia,
        status
    FROM ordens_servico
    WHERE cliente LIKE ?
    ORDER BY id DESC
    LIMIT ?
    """, conn, params=(like_term, limit))


def _load_ordem_detalhe(conn, os_id):
    df = pd.read_sql_query("""
    SELECT *
    FROM ordens_servico
    WHERE id = ?
    LIMIT 1
    """, conn, params=(os_id,))

    if df.empty:
        return None

    return df.iloc[0].to_dict()


def _money(value):
    try:
        return f"R$ {float(value):.2f}"
    except (TypeError, ValueError):
        return "R$ 0.00"


def _date_value(value):
    try:
        return pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return datetime.today().date()


def _status_badge(status):
    color, bg = STATUS_COLORS.get(status, ("#94A3B8", "#111827"))
    return (
        f"<span class='status-badge' "
        f"style='border-color:{color};background:{bg};color:{color};'>"
        f"{status}</span>"
    )


def _pdf_button(os_id, os_data):
    nome_arquivo = f"OS_{str(os_id).zfill(5)}_{os_data.get('cliente') or 'cliente'}.pdf"
    nome_arquivo = nome_arquivo.replace(" ", "_").replace("/", "-").replace("\\", "-")
    st.download_button(
        "Baixar PDF",
        data=generate_os_pdf(os_data),
        file_name=nome_arquivo,
        mime="application/pdf",
        key=f"pdf_{os_id}",
    )


def _save_upload(uploaded_file, os_id, field):
    if uploaded_file is None:
        return None

    upload_dir = Path("uploads") / "ordens_servico" / str(os_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = uploaded_file.name.replace("/", "-").replace("\\", "-")
    file_path = upload_dir / f"{field}_{safe_name}"
    file_path.write_bytes(uploaded_file.getbuffer())
    return str(file_path)


def _existing_file_label(path):
    if not path:
        return

    st.caption(f"Arquivo atual: {Path(path).name}")


def _is_existing_file(path):
    return bool(path) and Path(str(path)).exists()


def _is_image_file(path):
    return Path(str(path)).suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]


def _render_file_preview(label, path):
    if not path:
        return

    if not _is_existing_file(path):
        st.caption(f"{label}: {path}")
        return

    file_path = Path(path)
    with st.expander(f"Visualizar {label}", expanded=False):
        if _is_image_file(file_path):
            st.image(str(file_path), caption=file_path.name, width=320)
        else:
            st.caption(file_path.name)

        st.download_button(
            "Baixar arquivo",
            data=file_path.read_bytes(),
            file_name=file_path.name,
            key=f"download_{abs(hash(str(file_path)))}",
        )


def _radio_value(label, options, current, key, horizontal=True):
    if current not in options:
        current = options[0]

    return st.radio(
        label,
        options,
        index=options.index(current),
        key=key,
        horizontal=horizontal,
    )


def _select_value(label, options, current, key):
    if current not in options:
        current = options[0]

    return st.selectbox(label, options, index=options.index(current), key=key)


def _render_checklist(prefix, items, current):
    values = {}

    for item in items:
        field_key = item.lower().replace(" ", "_").replace("-", "_")
        values[field_key] = _radio_value(
            item,
            TEST_OPTIONS,
            current.get(field_key, "Não Testado"),
            f"{prefix}_{field_key}",
        )

    return values


def _render_upload(label, current, os_id, field_key, scope):
    current_path = current.get(field_key)
    edit_key = f"edit_file_{os_id}_{scope}_{field_key}"
    delete_key = f"delete_file_{os_id}_{scope}_{field_key}"

    if not current_path:
        st.session_state.pop(delete_key, None)

    if current_path and not st.session_state.get(delete_key):
        _existing_file_label(current_path)
        _render_file_preview(label, current_path)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Trocar arquivo", key=f"trocar_{os_id}_{scope}_{field_key}"):
                st.session_state[edit_key] = True
                st.rerun()
        with col2:
            if st.button("Apagar arquivo", key=f"apagar_{os_id}_{scope}_{field_key}"):
                st.session_state[delete_key] = True
                st.session_state[edit_key] = False
                st.rerun()

    if st.session_state.get(delete_key):
        st.warning("Arquivo marcado para apagar. Clique em Salvar edição da OS para confirmar.")
        return ""

    if current_path and not st.session_state.get(edit_key):
        return current_path

    uploaded = st.file_uploader(
        label,
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key=f"upload_{os_id}_{scope}_{field_key}",
    )
    saved = _save_upload(uploaded, os_id, f"{scope}_{field_key}")
    if saved:
        st.session_state[edit_key] = False
        st.session_state[delete_key] = False
        return saved

    return current_path or ""


def _signature_has_trace(image_data):
    if image_data is None:
        return False

    rgb = image_data[:, :, :3]
    alpha = image_data[:, :, 3]
    drawn_pixels = ((rgb < 245).any(axis=2)) & (alpha > 0)
    return bool(drawn_pixels.sum() > 30)


def _save_signature(canvas_result, os_id, field, current_value):
    if canvas_result is None or canvas_result.image_data is None:
        return current_value or ""

    if not _signature_has_trace(canvas_result.image_data):
        return current_value or ""

    upload_dir = Path("uploads") / "ordens_servico" / str(os_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{field}.png"
    image = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
    image.save(file_path)
    return str(file_path)


def _render_signature(label, current_value, os_id, field):
    edit_key = f"edit_signature_{os_id}_{field}"
    delete_key = f"delete_signature_{os_id}_{field}"

    if not current_value:
        st.session_state.pop(delete_key, None)

    if current_value and not st.session_state.get(delete_key):
        if _is_existing_file(current_value) and _is_image_file(current_value):
            st.image(str(current_value), caption=f"{label} atual", width=320)
        else:
            st.caption(f"Assinatura atual: {current_value}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Editar assinatura", key=f"editar_{os_id}_{field}"):
                st.session_state[edit_key] = True
                st.rerun()
        with col2:
            if st.button("Apagar assinatura", key=f"apagar_{os_id}_{field}"):
                st.session_state[delete_key] = True
                st.session_state[edit_key] = False
                st.rerun()
    elif not st.session_state.get(edit_key):
        if st.button("Criar assinatura", key=f"criar_{os_id}_{field}"):
            st.session_state[edit_key] = True
            st.rerun()

    if st.session_state.get(delete_key):
        st.warning("Assinatura marcada para apagar. Clique em Salvar edição da OS para confirmar.")
        return None

    if not st.session_state.get(edit_key):
        return None

    st.caption("Assine no quadro abaixo usando touch, mouse ou caneta.")
    return st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=3,
        stroke_color="#111827",
        background_color="#FFFFFF",
        height=180,
        width=520,
        drawing_mode="freedraw",
        key=f"canvas_{os_id}_{field}",
    )


def _signature_value_after_save(canvas_result, os_id, field, current_value):
    edit_key = f"edit_signature_{os_id}_{field}"
    delete_key = f"delete_signature_{os_id}_{field}"

    if st.session_state.get(delete_key):
        st.session_state.pop(delete_key, None)
        st.session_state.pop(edit_key, None)
        return ""

    if st.session_state.get(edit_key):
        value = _save_signature(canvas_result, os_id, field, current_value)
        st.session_state.pop(edit_key, None)
        return value

    return current_value or ""


def _render_ordens_table(df_os):
    if df_os.empty:
        st.info("Nenhuma OS cadastrada.")
        return

    rows = []
    for row in df_os.itertuples():
        rows.append({
            "OS": row.id,
            "Cliente": row.cliente,
            "Aparelho": f"{row.marca or ''} {row.modelo or ''}".strip(),
            "Serviço": row.servico,
            "Valor": row.valor,
            "Status": row.status,
        })

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )


def _render_os_result_table(df_os):
    rows = []
    for row in df_os.itertuples():
        rows.append({
            "OS": f"#{str(row.id).zfill(5)}",
            "Data": row.data,
            "Cliente": row.cliente,
            "Aparelho": f"{row.marca or ''} {row.modelo or ''}".strip() or "-",
            "Serviço": row.servico or "-",
            "Status": row.status or "-",
            "Valor": row.valor or 0,
        })

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )


def _render_os_lookup(conn):
    df_clientes = load_clientes(conn, somente_ativos=True)

    st.markdown(
        """
        <div class="os-lookup-panel">
            <div class="os-lookup-icon">
                OS
            </div>
            <div>
                <span class="os-lookup-eyebrow">Consulta rápida</span>
                <strong>Cliente e andamento da OS</strong>
                <small>Pesquise por nome, CPF/CNPJ ou telefone/WhatsApp para acompanhar serviços.</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    termo = st.text_input(
        "Pesquisar cliente ou ordem de serviço",
        placeholder="Digite nome, CPF/CNPJ ou WhatsApp...",
        key="os_lookup_cliente_status",
        label_visibility="collapsed",
    )
    termo_limpo = termo.strip()

    if not termo_limpo:
        st.caption("Use a busca acima para acompanhar serviços de um cliente antes de abrir uma nova OS.")
        return

    if len(termo_limpo) < 2:
        st.caption("Digite pelo menos 2 caracteres para pesquisar.")
        return

    clientes = _search_clientes(df_clientes, termo_limpo, limit=6)
    if clientes.empty:
        st.info("Nenhum cliente cadastrado encontrado. Vou procurar em ordens antigas pelo texto digitado.")
        ordens = _search_ordens_texto(conn, termo_limpo)
        if ordens.empty:
            st.warning("Nenhuma ordem de serviço encontrada para essa pesquisa.")
        else:
            _render_os_result_table(ordens)
        return

    for cliente in clientes.itertuples():
        ordens_cliente = _load_ordens_por_cliente(conn, cliente)
        ultima_os = ordens_cliente.iloc[0] if not ordens_cliente.empty else None
        status_html = _status_badge(ultima_os["status"]) if ultima_os is not None else "<span class='status-badge muted'>Sem OS</span>"

        st.markdown(
            f"""
            <div class="os-lookup-client">
                <div>
                    <strong>{cliente.nome}</strong>
                    <span>{cliente.telefone or 'Sem telefone'} • {cliente.cpf or 'Sem CPF/CNPJ'}</span>
                </div>
                <div>{status_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if ordens_cliente.empty:
            st.caption("Este cliente ainda não possui ordem de serviço cadastrada.")
        else:
            _render_os_result_table(ordens_cliente)


def _render_status_board(df_os):
    if df_os.empty:
        return

    st.markdown("#### Painel por status")
    cols = st.columns(3)

    for index, status in enumerate(STATUS_OS):
        coluna = cols[index % 3]
        df_status = df_os[df_os["status"] == status]
        color, bg = STATUS_COLORS.get(status, ("#94A3B8", "#111827"))

        with coluna:
            st.markdown(
                f"""
                <div class="section-panel" style="border-left-color:{color};background:{bg};">
                    <div class="section-panel-header">
                        <div>
                            <h3>{status}</h3>
                            <p>{len(df_status)} ordem(ns)</p>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if df_status.empty:
                st.caption("Sem OS neste status.")
            else:
                for row in df_status.head(4).itertuples():
                    aparelho = f"{row.marca or ''} {row.modelo or ''}".strip()
                    st.caption(f"#{str(row.id).zfill(5)} • {row.cliente or 'Sem cliente'} • {aparelho}")


def _create_ordem(conn, data):
    cursor = conn.cursor()
    return execute_insert_returning_id(conn, cursor, """
    INSERT INTO ordens_servico (
        data,
        cliente_id,
        atendente,
        loja,
        cliente,
        cpf,
        telefone,
        endereco,
        marca,
        modelo,
        imei,
        senha,
        defeito,
        servico,
        valor,
        garantia,
        status,
        observacoes,
        checklist_entrada,
        checklist_reparo,
        checklist_saida,
        pagamento_os,
        assinatura_entrada,
        assinatura_saida
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)


def _update_ordem(conn, os_id, data):
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE ordens_servico
    SET
        data = ?,
        cliente_id = ?,
        cliente = ?,
        cpf = ?,
        telefone = ?,
        endereco = ?,
        atendente = ?,
        loja = ?,
        marca = ?,
        modelo = ?,
        imei = ?,
        senha = ?,
        defeito = ?,
        servico = ?,
        valor = ?,
        garantia = ?,
        status = ?,
        observacoes = ?,
        checklist_entrada = ?,
        checklist_reparo = ?,
        checklist_saida = ?,
        pagamento_os = ?,
        assinatura_entrada = ?,
        assinatura_saida = ?
    WHERE id = ?
    """, (*data, os_id))
    conn.commit()


def _render_nova_os(conn):
    df_clientes = load_clientes(conn, somente_ativos=True)

    with st.expander("➕ Nova Ordem de Serviço", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            data_os = st.date_input("Data", datetime.today(), key="nova_os_data")
        with col2:
            atendente = st.text_input("Atendente", key="nova_os_atendente")
        with col3:
            loja = st.text_input("Loja", key="nova_os_loja")

        st.markdown("#### Cliente")
        if "nova_os_cliente_id" not in st.session_state:
            st.session_state["nova_os_cliente_id"] = None
        for field in ["nova_os_nome", "nova_os_cpf", "nova_os_tel", "nova_os_end"]:
            st.session_state.setdefault(field, "")

        options = _cliente_options(df_clientes)
        cliente_opcao = st.selectbox(
            "Cliente cadastrado (opcional)",
            list(options.keys()),
            key="nova_os_cliente_select",
        )
        cliente_opcao_id = options[cliente_opcao]

        col_preencher, col_limpar = st.columns([1, 1])
        with col_preencher:
            if cliente_opcao_id and st.button("Preencher dados do cliente", key="nova_os_preencher_cliente"):
                cliente_row = _cliente_selecionado(df_clientes, cliente_opcao_id)
                if cliente_row is not None:
                    _apply_cliente_to_new_os(cliente_row)
                    st.rerun()
        with col_limpar:
            if st.button("Usar cliente novo/manual", key="nova_os_cliente_manual"):
                st.session_state["nova_os_cliente_id"] = None
                st.session_state["nova_os_nome"] = ""
                st.session_state["nova_os_cpf"] = ""
                st.session_state["nova_os_tel"] = ""
                st.session_state["nova_os_end"] = ""
                st.rerun()

        cliente_id = st.session_state.get("nova_os_cliente_id")

        col1, col2, col3 = st.columns(3)
        with col1:
            cliente = st.text_input("Nome do Cliente", key="nova_os_nome")
        with col2:
            cpf = st.text_input("CPF/CNPJ", key="nova_os_cpf")
        with col3:
            telefone = st.text_input("Telefone/WhatsApp", key="nova_os_tel")

        endereco = st.text_area("Endereço", key="nova_os_end")
        salvar_cliente = cliente_id is None and st.checkbox("Salvar este cliente no cadastro", value=True)

        st.markdown("#### Aparelho e serviço")
        col1, col2, col3 = st.columns(3)
        with col1:
            marca = st.text_input("Marca")
            valor = st.number_input("Valor", min_value=0.0)
        with col2:
            modelo = st.text_input("Modelo")
            garantia = st.selectbox("Garantia", ["30 dias", "60 dias", "90 dias"])
        with col3:
            imei = st.text_input("IMEI")
            status = st.selectbox("Status", STATUS_OS)

        senha = st.text_input("Senha")
        defeito = st.text_area("Defeito Relatado")
        servico = st.text_area("Serviço Realizado")
        observacoes = st.text_area("Observações")

        if st.button("Salvar Ordem de Serviço", width="stretch"):
            if not cliente.strip():
                st.error("Informe o nome do cliente para salvar a OS.")
                return

            if cliente_id is None and salvar_cliente:
                cliente_id = create_cliente(conn, cliente, cpf, telefone, endereco)

            os_id = _create_ordem(conn, (
                str(data_os),
                cliente_id,
                atendente,
                loja,
                cliente,
                cpf,
                telefone,
                endereco,
                marca,
                modelo,
                imei,
                senha,
                defeito,
                servico,
                valor,
                garantia,
                status,
                observacoes,
                _json_dump({}),
                _json_dump({}),
                _json_dump({}),
                _json_dump({}),
                "",
                "",
            ))
            st.success(f"✅ OS #{str(os_id).zfill(5)} salva!")
            st.rerun()


def _render_edit_form(conn, os_id):
    os_data = _load_ordem_detalhe(conn, os_id)

    if not os_data:
        st.warning("OS não encontrada.")
        return

    entrada = _json_load(os_data.get("checklist_entrada"))
    reparo = _json_load(os_data.get("checklist_reparo"))
    saida = _json_load(os_data.get("checklist_saida"))
    pagamento = _json_load(os_data.get("pagamento_os"))
    assinatura_entrada_atual = os_data.get("assinatura_entrada") or ""
    assinatura_saida_atual = os_data.get("assinatura_saida") or ""

    tab_dados, tab_entrada, tab_reparo, tab_saida, tab_pagamento = st.tabs([
        "Dados",
        "Entrada",
        "Reparo",
        "Saída",
        "Pagamento",
    ])

    with tab_dados:
        df_clientes = load_clientes(conn, somente_ativos=True)
        st.markdown("#### Cliente da OS")
        st.session_state.setdefault(f"edit_cliente_id_{os_id}", os_data.get("cliente_id"))
        st.session_state.setdefault(f"edit_cliente_{os_id}", os_data.get("cliente") or "")
        st.session_state.setdefault(f"edit_cpf_{os_id}", os_data.get("cpf") or "")
        st.session_state.setdefault(f"edit_telefone_{os_id}", os_data.get("telefone") or "")
        st.session_state.setdefault(f"edit_endereco_{os_id}", os_data.get("endereco") or "")
        _render_cliente_search(
            df_clientes,
            f"edit_{os_id}",
            lambda cliente_row: _apply_cliente_to_edit_os(cliente_row, os_id),
            st.session_state.get(f"edit_cliente_id_{os_id}"),
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            data_os = st.date_input("Data", _date_value(os_data.get("data")), key=f"edit_data_{os_id}")
            cliente = st.text_input("Cliente", key=f"edit_cliente_{os_id}")
            telefone = st.text_input("Telefone/WhatsApp", key=f"edit_telefone_{os_id}")
        with col2:
            atendente = st.text_input("Atendente", value=os_data.get("atendente") or "", key=f"edit_atendente_{os_id}")
            cpf = st.text_input("CPF/CNPJ", key=f"edit_cpf_{os_id}")
            loja = st.text_input("Loja", value=os_data.get("loja") or "", key=f"edit_loja_{os_id}")
        with col3:
            status = _select_value("Status", STATUS_OS, os_data.get("status") or "Em análise", f"edit_status_{os_id}")
            garantia = st.selectbox(
                "Garantia",
                ["30 dias", "60 dias", "90 dias"],
                index=["30 dias", "60 dias", "90 dias"].index(os_data.get("garantia"))
                if os_data.get("garantia") in ["30 dias", "60 dias", "90 dias"]
                else 0,
                key=f"edit_garantia_{os_id}",
            )
            valor = st.number_input("Valor", min_value=0.0, value=float(os_data.get("valor") or 0), key=f"edit_valor_{os_id}")

        endereco = st.text_area("Endereço", key=f"edit_endereco_{os_id}")

        col1, col2, col3 = st.columns(3)
        with col1:
            marca = st.text_input("Marca", value=os_data.get("marca") or "", key=f"edit_marca_{os_id}")
        with col2:
            modelo = st.text_input("Modelo", value=os_data.get("modelo") or "", key=f"edit_modelo_{os_id}")
        with col3:
            imei = st.text_input("IMEI", value=os_data.get("imei") or "", key=f"edit_imei_{os_id}")

        senha = st.text_input("Senha", value=os_data.get("senha") or "", key=f"edit_senha_{os_id}")
        defeito = st.text_area("Defeito Relatado", value=os_data.get("defeito") or "", key=f"edit_defeito_{os_id}")
        servico = st.text_area("Serviço Realizado", value=os_data.get("servico") or "", key=f"edit_servico_{os_id}")
        observacoes = st.text_area("Observações gerais", value=os_data.get("observacoes") or "", key=f"edit_obs_{os_id}")

    with tab_entrada:
        st.markdown("#### Testes de entrada")
        entrada["possui_backup"] = _radio_value("Possui backup?", YES_NO, entrada.get("possui_backup", "Não"), f"entrada_backup_{os_id}")
        entrada["ja_reparou"] = _radio_value("Já fez algum reparo neste aparelho?", ["Sim", "Não", "Não sabe"], entrada.get("ja_reparou", "Não sabe"), f"entrada_reparo_anterior_{os_id}")
        entrada["tests"] = _render_checklist(f"entrada_tests_{os_id}", CHECKLIST_ENTRADA, entrada.get("tests", {}))
        entrada["foto_frente"] = _render_upload("Foto frontal de entrada", entrada, os_id, "foto_frente", "entrada")
        entrada["foto_tras"] = _render_upload("Foto traseira de entrada", entrada, os_id, "foto_tras", "entrada")
        entrada["foto_extra"] = _render_upload("Foto extra de entrada", entrada, os_id, "foto_extra", "entrada")
        entrada["observacoes"] = st.text_area("Observações sobre entrada", value=entrada.get("observacoes", ""), key=f"entrada_obs_{os_id}")
        st.markdown("#### Assinatura de entrada")
        assinatura_entrada_canvas = _render_signature(
            "Assinatura de entrada",
            assinatura_entrada_atual,
            os_id,
            "assinatura_entrada",
        )

    with tab_reparo:
        st.markdown("#### Abertura e reparo")
        reparo["tecnico"] = st.text_input("Técnico do reparo", value=reparo.get("tecnico", ""), key=f"reparo_tecnico_{os_id}")
        reparo["aparelho_molhou"] = _radio_value("Aparelho já molhou?", YES_NO, reparo.get("aparelho_molhou", "Não"), f"reparo_molhou_{os_id}")
        reparo["falta_componentes"] = _radio_value("Possui falta de componentes internos?", YES_NO, reparo.get("falta_componentes", "Não"), f"reparo_componentes_{os_id}")
        reparo["foto_interna"] = _render_upload("Foto interna do aparelho", reparo, os_id, "foto_interna", "reparo")
        reparo["foto_interna_extra"] = _render_upload("Foto interna extra", reparo, os_id, "foto_interna_extra", "reparo")
        reparo["servico_realizado"] = st.text_area("Serviço realizado no reparo", value=reparo.get("servico_realizado", ""), key=f"reparo_servico_{os_id}")
        reparo["fornecedor"] = st.text_input("Fornecedor", value=reparo.get("fornecedor", ""), key=f"reparo_fornecedor_{os_id}")
        reparo["foto_peca"] = _render_upload("Foto da peça", reparo, os_id, "foto_peca", "reparo")
        reparo["observacoes"] = st.text_area("Observações do reparo", value=reparo.get("observacoes", ""), key=f"reparo_obs_{os_id}")

    with tab_saida:
        st.markdown("#### Testes de saída")
        saida["tests"] = _render_checklist(f"saida_tests_{os_id}", CHECKLIST_SAIDA, saida.get("tests", {}))
        saida["foto_frente"] = _render_upload("Foto frontal de saída", saida, os_id, "foto_frente", "saida")
        saida["foto_tras"] = _render_upload("Foto traseira de saída", saida, os_id, "foto_tras", "saida")
        saida["foto_extra"] = _render_upload("Foto extra de saída", saida, os_id, "foto_extra", "saida")
        saida["observacoes"] = st.text_area("Observações de saída", value=saida.get("observacoes", ""), key=f"saida_obs_{os_id}")
        saida["cliente_levou_tela"] = _radio_value("Cliente levou a tela?", YES_NO, saida.get("cliente_levou_tela", "Não"), f"saida_tela_{os_id}")
        st.markdown("#### Assinatura de saída")
        assinatura_saida_canvas = _render_signature(
            "Assinatura de saída",
            assinatura_saida_atual,
            os_id,
            "assinatura_saida",
        )

    with tab_pagamento:
        st.markdown("#### Pagamento da OS")
        pagamento["valor"] = st.number_input(
            "Valor pago",
            min_value=0.0,
            value=float(pagamento.get("valor") or os_data.get("valor") or 0),
            key=f"pagamento_valor_{os_id}",
        )
        pagamento["forma"] = _select_value("Forma de pagamento", FORMAS_PAGAMENTO, pagamento.get("forma", "Dinheiro"), f"pagamento_forma_{os_id}")
        pagamento["numero_nf"] = st.text_input("Número da NF", value=pagamento.get("numero_nf", ""), key=f"pagamento_nf_{os_id}")
        pagamento["observacoes"] = st.text_area("Observações do pagamento", value=pagamento.get("observacoes", ""), key=f"pagamento_obs_{os_id}")

        if pagamento["forma"] in ["Pix", "Crédito", "Débito", "Misto"]:
            st.caption("Comprovante recomendado para Pix ou cartão.")
            pagamento["foto_comprovante"] = _render_upload("Foto do comprovante", pagamento, os_id, "foto_comprovante", "pagamento")

    if st.button("Salvar edição da OS", key=f"salvar_edicao_{os_id}", width="stretch"):
        if not cliente.strip():
            st.error("Informe o nome do cliente.")
            return

        assinatura_entrada = _signature_value_after_save(
            assinatura_entrada_canvas,
            os_id,
            "assinatura_entrada",
            assinatura_entrada_atual,
        )
        assinatura_saida = _signature_value_after_save(
            assinatura_saida_canvas,
            os_id,
            "assinatura_saida",
            assinatura_saida_atual,
        )

        _update_ordem(conn, os_id, (
            str(data_os),
            st.session_state.get(f"edit_cliente_id_{os_id}"),
            cliente,
            cpf,
            telefone,
            endereco,
            atendente,
            loja,
            marca,
            modelo,
            imei,
            senha,
            defeito,
            servico,
            valor,
            garantia,
            status,
            observacoes,
            _json_dump(entrada),
            _json_dump(reparo),
            _json_dump(saida),
            _json_dump(pagamento),
            assinatura_entrada,
            assinatura_saida,
        ))
        st.success("✅ OS atualizada!")
        st.rerun()


def _render_lista_ordens(conn):
    df_os = _load_ordens_servico(conn)

    st.subheader("📋 Ordens cadastradas")
    _render_status_board(df_os)
    st.divider()
    _render_ordens_table(df_os)

    if df_os.empty:
        return

    st.divider()
    st.markdown("#### Editar ou imprimir")

    for row in df_os.itertuples():
        os_data = _load_ordem_detalhe(conn, row.id)
        title = f"OS #{str(row.id).zfill(5)} - {row.cliente or 'Sem cliente'} - {row.marca or ''} {row.modelo or ''}"

        with st.expander(title, expanded=False):
            color, _ = STATUS_COLORS.get(row.status, ("#94A3B8", "#111827"))
            st.markdown(
                f"""
                <div class="os-card" style="border-left-color:{color};">
                    <div>
                        <strong>{row.cliente or 'Sem cliente'}</strong><br>
                        <span>{row.telefone or ''}</span><br>
                        <span>{row.servico or ''}</span>
                    </div>
                    <div>{_status_badge(row.status)}</div>
                    <div><strong>{_money(row.valor)}</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns([1, 3])
            with col1:
                _pdf_button(row.id, os_data)
            with col2:
                st.caption("Use as abas abaixo para corrigir dados, atualizar status, anexar fotos e completar o checklist.")

            _render_edit_form(conn, row.id)


def render_ordem_servico(conn):
    page_header(
        "Ordem de Serviço",
        "Consulte clientes, acompanhe status, abra novas OS e imprima documentos técnicos.",
    )

    _render_os_lookup(conn)
    st.divider()
    _render_nova_os(conn)
    st.divider()
    _render_lista_ordens(conn)
