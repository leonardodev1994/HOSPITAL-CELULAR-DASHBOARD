import pandas as pd
import streamlit as st

from database.database import execute_insert_returning_id


def load_clientes(conn, somente_ativos=False):
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
        criado_em
    FROM clientes
    """

    if somente_ativos:
        query += " WHERE ativo = 1"

    query += " ORDER BY nome"

    return pd.read_sql_query(query, conn)


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
        ativo
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        nome.strip(),
        cpf.strip(),
        telefone.strip(),
        endereco.strip(),
        email.strip(),
        observacoes.strip(),
        1 if ativo else 0,
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
    WHERE id = ?
    """, (
        nome.strip(),
        cpf.strip(),
        telefone.strip(),
        endereco.strip(),
        email.strip(),
        observacoes.strip(),
        1 if ativo else 0,
        cliente_id,
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


def render_clientes(conn):
    st.subheader("👤 Clientes")

    with st.expander("➕ Cadastrar novo cliente", expanded=False):
        with st.form("novo_cliente_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                nome = st.text_input("Nome do cliente")
                cpf = st.text_input("CPF")

            with col2:
                telefone = st.text_input("Telefone")
                email = st.text_input("E-mail")

            with col3:
                ativo = st.checkbox("Ativo", value=True)

            endereco = st.text_area("Endereço")
            observacoes = st.text_area("Observações")

            submitted = st.form_submit_button("Salvar cliente")

        if submitted:
            if not nome.strip():
                st.error("Informe o nome do cliente.")
            else:
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
                st.success("✅ Cliente cadastrado!")
                st.rerun()

    df_clientes = load_clientes(conn)

    st.subheader("📋 Clientes cadastrados")

    if df_clientes.empty:
        st.info("Nenhum cliente cadastrado ainda.")
        return

    busca = st.text_input("Buscar por nome, CPF ou telefone")

    df_filtrado = df_clientes.copy()
    if busca.strip():
        termo = busca.strip().lower()
        filtro = (
            df_filtrado["nome"].fillna("").str.lower().str.contains(termo)
            | df_filtrado["cpf"].fillna("").str.lower().str.contains(termo)
            | df_filtrado["telefone"].fillna("").str.lower().str.contains(termo)
        )
        df_filtrado = df_filtrado[filtro]

    st.dataframe(
        _clientes_table(df_filtrado),
        width="stretch",
        hide_index=True,
    )

    if df_filtrado.empty:
        return

    st.divider()
    st.subheader("✏️ Editar cliente")

    options = {
        f"{row.nome} | {row.telefone or 'sem telefone'}": row.id
        for row in df_filtrado.itertuples()
    }

    selected_label = st.selectbox("Selecione", list(options.keys()))
    selected_id = options[selected_label]
    selected = df_clientes[df_clientes["id"] == selected_id].iloc[0]

    with st.form("editar_cliente_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            nome_edit = st.text_input("Nome", value=selected["nome"] or "")
            cpf_edit = st.text_input("CPF", value=selected["cpf"] or "")

        with col2:
            telefone_edit = st.text_input("Telefone", value=selected["telefone"] or "")
            email_edit = st.text_input("E-mail", value=selected["email"] or "")

        with col3:
            ativo_edit = st.checkbox("Ativo", value=bool(selected["ativo"]))

        endereco_edit = st.text_area("Endereço", value=selected["endereco"] or "")
        observacoes_edit = st.text_area("Observações", value=selected["observacoes"] or "")

        salvar = st.form_submit_button("Salvar alterações")

    if salvar:
        if not nome_edit.strip():
            st.error("Informe o nome do cliente.")
        else:
            update_cliente(
                conn,
                selected_id,
                nome_edit,
                cpf_edit,
                telefone_edit,
                endereco_edit,
                email_edit,
                observacoes_edit,
                ativo_edit,
            )
            st.success("✅ Cliente atualizado!")
            st.rerun()
