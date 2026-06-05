import pandas as pd
import streamlit as st

from database.database import execute_insert_returning_id
from utils.dashboard_ui import page_banner
from utils.quiosques import current_quiosque_id, scope_clause
from utils.text import search_matches


def load_clientes(conn, somente_ativos=False):
    scope, params = scope_clause()
    query = """
    SELECT
        id,
        nome,
        cpf,
        telefone,
        endereco,
        email,
        observacoes,
        ativo,
        criado_em,
        quiosque_id
    FROM clientes
    """

    if somente_ativos:
        query += " WHERE ativo = 1"
        if scope:
            query += scope.replace(" WHERE ", " AND ")
    else:
        query += scope

    query += " ORDER BY nome"

    return pd.read_sql_query(query, conn, params=params)


def create_cliente(conn, nome, cpf, telefone, endereco, email="", observacoes="", ativo=True):
    cursor = conn.cursor()
    return execute_insert_returning_id(conn, cursor, """
    INSERT INTO clientes (
        nome,
        cpf,
        telefone,
        endereco,
        email,
        observacoes,
        ativo,
        quiosque_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nome.strip(),
        cpf.strip(),
        telefone.strip(),
        endereco.strip(),
        email.strip(),
        observacoes.strip(),
        1 if ativo else 0,
        current_quiosque_id(),
    ))


def update_cliente(conn, cliente_id, nome, cpf, telefone, endereco, email, observacoes, ativo):
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE clientes
    SET
        nome = ?,
        cpf = ?,
        telefone = ?,
        endereco = ?,
        email = ?,
        observacoes = ?,
        ativo = ?
    WHERE id = ? AND quiosque_id = ?
    """, (
        nome.strip(),
        cpf.strip(),
        telefone.strip(),
        endereco.strip(),
        email.strip(),
        observacoes.strip(),
        1 if ativo else 0,
        cliente_id,
        current_quiosque_id(),
    ))
    conn.commit()


def _clientes_table(df_clientes):
    if df_clientes.empty:
        return df_clientes

    tabela = df_clientes.copy()
    tabela["Status"] = tabela["ativo"].map({1: "Ativo", 0: "Inativo"})
    tabela = tabela.rename(columns={
        "id": "ID",
        "nome": "Nome",
        "cpf": "CPF",
        "telefone": "Telefone",
        "endereco": "Endereço",
        "email": "E-mail",
        "observacoes": "Observações",
        "criado_em": "Criado em",
    })

    return tabela[[
        "ID",
        "Nome",
        "CPF",
        "Telefone",
        "Endereço",
        "E-mail",
        "Status",
        "Criado em",
    ]]


def _reset_new_cliente_form():
    for key in [
        "cliente_novo_nome",
        "cliente_novo_cpf",
        "cliente_novo_telefone",
        "cliente_novo_email",
        "cliente_novo_endereco",
        "cliente_novo_observacoes",
    ]:
        st.session_state.pop(key, None)
    st.session_state.pop("cliente_novo_ativo", None)


def _status_cliente(value):
    return "Ativo" if int(value or 0) == 1 else "Inativo"


def _render_cliente_details(row):
    col1, col2 = st.columns(2)
    with col1:
        st.caption("CPF/CNPJ")
        st.write(row.cpf or "Não informado")
        st.caption("E-mail")
        st.write(row.email or "Não informado")
    with col2:
        st.caption("Endereço")
        st.write(row.endereco or "Não informado")
        st.caption("Criado em")
        st.write(row.criado_em or "Não informado")

    if row.observacoes:
        st.caption("Observações")
        st.write(row.observacoes)


def render_clientes(conn):
    page_banner("tx_clientes_banner.webp", "TX System - Clientes")
    st.subheader("👤 Clientes")

    st.session_state.setdefault("cliente_form_aberto", False)
    st.session_state.setdefault("cliente_salvando", False)
    st.session_state.setdefault("cliente_edit_salvando", False)
    st.session_state.setdefault("cliente_edit_id", None)

    if st.session_state.pop("cliente_sucesso", False):
        st.success("✅ Cliente cadastrado!")

    if not st.session_state["cliente_form_aberto"]:
        if st.button("➕ Cadastrar cliente", width="stretch"):
            st.session_state["cliente_form_aberto"] = True
            st.rerun()

    if st.session_state["cliente_form_aberto"]:
        with st.form("novo_cliente_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                nome = st.text_input("Nome do cliente", key="cliente_novo_nome")
                cpf = st.text_input("CPF", key="cliente_novo_cpf")

            with col2:
                telefone = st.text_input("Telefone", key="cliente_novo_telefone")
                email = st.text_input("E-mail", key="cliente_novo_email")

            with col3:
                ativo = st.checkbox("Ativo", value=True, key="cliente_novo_ativo")

            endereco = st.text_area("Endereço", key="cliente_novo_endereco")
            observacoes = st.text_area("Observações", key="cliente_novo_observacoes")

            col_salvar, col_cancelar = st.columns(2)
            with col_salvar:
                submitted = st.form_submit_button("Salvar cliente", disabled=st.session_state["cliente_salvando"])
            with col_cancelar:
                cancel = st.form_submit_button("Cancelar")

        if cancel:
            _reset_new_cliente_form()
            st.session_state["cliente_form_aberto"] = False
            st.rerun()

        if submitted and not st.session_state["cliente_salvando"]:
            if not nome.strip():
                st.error("Informe o nome do cliente.")
            else:
                try:
                    st.session_state["cliente_salvando"] = True
                    create_cliente(
                        conn,
                        nome,
                        cpf,
                        telefone,
                        endereco,
                        email,
                        observacoes,
                        ativo,
                    )
                    _reset_new_cliente_form()
                    st.session_state["cliente_form_aberto"] = False
                    st.session_state["cliente_sucesso"] = True
                    st.rerun()
                finally:
                    st.session_state["cliente_salvando"] = False

    df_clientes = load_clientes(conn)

    st.subheader("📋 Clientes cadastrados")

    if df_clientes.empty:
        st.info("Nenhum cliente cadastrado ainda.")
        return

    busca = st.text_input("Buscar por nome, CPF ou telefone")

    df_filtrado = df_clientes.copy()
    if busca.strip():
        filtro = (
            df_filtrado["nome"].fillna("").map(lambda value: search_matches(value, busca))
            | df_filtrado["cpf"].fillna("").map(lambda value: search_matches(value, busca))
            | df_filtrado["telefone"].fillna("").map(lambda value: search_matches(value, busca))
            | df_filtrado["email"].fillna("").map(lambda value: search_matches(value, busca))
        )
        df_filtrado = df_filtrado[filtro]

    if df_filtrado.empty:
        st.info("Nenhum cliente encontrado para essa busca.")
        return

    selected_id = st.session_state.get("cliente_edit_id")
    if selected_id and selected_id not in set(df_filtrado["id"].astype(int)):
        st.session_state["cliente_edit_id"] = None

    for row in df_filtrado.itertuples():
        status = _status_cliente(row.ativo)
        telefone = row.telefone or "sem telefone"
        title = f"{row.nome} | {telefone} | {status}"
        expanded = st.session_state.get("cliente_edit_id") == int(row.id)

        with st.expander(title, expanded=expanded):
            _render_cliente_details(row)

            if st.button("✏️ Editar", key=f"editar_cliente_{row.id}", width="stretch"):
                st.session_state["cliente_edit_id"] = int(row.id)
                st.rerun()

            if st.session_state.get("cliente_edit_id") != int(row.id):
                continue

            with st.form(f"editar_cliente_form_{row.id}"):
                st.markdown("#### Editar cliente")
                col1, col2, col3 = st.columns(3)

                with col1:
                    nome_edit = st.text_input("Nome", value=row.nome or "")
                    cpf_edit = st.text_input("CPF", value=row.cpf or "")

                with col2:
                    telefone_edit = st.text_input("Telefone", value=row.telefone or "")
                    email_edit = st.text_input("E-mail", value=row.email or "")

                with col3:
                    ativo_edit = st.checkbox("Ativo", value=bool(row.ativo))

                endereco_edit = st.text_area("Endereço", value=row.endereco or "")
                observacoes_edit = st.text_area("Observações", value=row.observacoes or "")

                col_salvar, col_cancelar = st.columns(2)
                with col_salvar:
                    salvar = st.form_submit_button(
                        "Salvar alterações",
                        disabled=st.session_state["cliente_edit_salvando"],
                    )
                with col_cancelar:
                    cancelar_edicao = st.form_submit_button("Cancelar edição")

            if cancelar_edicao:
                st.session_state["cliente_edit_id"] = None
                st.rerun()

            if salvar and not st.session_state["cliente_edit_salvando"]:
                if not nome_edit.strip():
                    st.error("Informe o nome do cliente.")
                else:
                    try:
                        st.session_state["cliente_edit_salvando"] = True
                        update_cliente(
                            conn,
                            int(row.id),
                            nome_edit,
                            cpf_edit,
                            telefone_edit,
                            endereco_edit,
                            email_edit,
                            observacoes_edit,
                            ativo_edit,
                        )
                        st.success("✅ Cliente atualizado!")
                        st.session_state["cliente_edit_id"] = None
                        st.rerun()
                    finally:
                        st.session_state["cliente_edit_salvando"] = False
