import pandas as pd
import streamlit as st

from utils.auth import current_user, hash_password
from utils.permissions import PERFIS
from utils.quiosques import load_quiosques


def _load_users(conn):
    return pd.read_sql_query("""
    SELECT
        usuarios.id,
        usuarios.nome,
        usuarios.usuario,
        usuarios.perfil,
        usuarios.ativo,
        usuarios.criado_em,
        usuarios.quiosque_id,
        usuarios.acesso_todos_quiosques,
        quiosques.nome AS quiosque_nome
    FROM usuarios
    LEFT JOIN quiosques ON quiosques.id = usuarios.quiosque_id
    ORDER BY usuarios.ativo DESC, usuarios.nome
    """, conn)


def _create_user(conn, nome, usuario, senha, perfil, ativo, quiosque_id, acesso_todos_quiosques):
    cursor = conn.cursor()
    salt, password_hash = hash_password(senha)

    cursor.execute("""
    INSERT INTO usuarios (
        nome,
        usuario,
        senha_hash,
        senha_salt,
        perfil,
        ativo,
        quiosque_id,
        acesso_todos_quiosques
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nome.strip(),
        usuario.strip(),
        password_hash,
        salt,
        perfil,
        1 if ativo else 0,
        quiosque_id,
        1 if acesso_todos_quiosques else 0,
    ))
    conn.commit()


def _update_user(conn, user_id, nome, perfil, ativo, quiosque_id, acesso_todos_quiosques):
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE usuarios
    SET nome = ?, perfil = ?, ativo = ?, quiosque_id = ?, acesso_todos_quiosques = ?
    WHERE id = ?
    """, (
        nome.strip(),
        perfil,
        1 if ativo else 0,
        quiosque_id,
        1 if acesso_todos_quiosques else 0,
        user_id,
    ))
    conn.commit()


def _update_password(conn, user_id, senha):
    cursor = conn.cursor()
    salt, password_hash = hash_password(senha)
    cursor.execute("""
    UPDATE usuarios
    SET senha_hash = ?, senha_salt = ?
    WHERE id = ?
    """, (password_hash, salt, user_id))
    conn.commit()


def render_usuarios(conn):
    user = current_user()

    if user["perfil"] != "Admin":
        st.warning("Apenas administradores podem acessar usuários e funcionários.")
        return

    st.subheader("👥 Usuários e Funcionários")
    df_quiosques = load_quiosques(conn)
    quiosque_options = {int(row.id): row.nome for row in df_quiosques.itertuples()}

    with st.expander("➕ Cadastrar novo usuário", expanded=False):
        with st.form("novo_usuario_form"):
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input("Nome completo")
                usuario = st.text_input("Usuário de acesso")

            with col2:
                senha = st.text_input("Senha", type="password")
                perfil = st.selectbox("Perfil", PERFIS, index=1)
                ativo = st.checkbox("Ativo", value=True)
                acesso_todos = st.checkbox("Acesso a todos os quiosques", value=perfil == "Admin")
                quiosque_id = st.selectbox(
                    "Quiosque",
                    list(quiosque_options.keys()),
                    format_func=lambda value: quiosque_options[value],
                )

            submitted = st.form_submit_button("Salvar usuário")

        if submitted:
            if not nome.strip() or not usuario.strip() or not senha:
                st.error("Preencha nome, usuário e senha.")
            elif len(senha) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                try:
                    _create_user(conn, nome, usuario, senha, perfil, ativo, quiosque_id, acesso_todos)
                    st.success("✅ Usuário cadastrado!")
                    st.rerun()
                except Exception as error:
                    if "UNIQUE" in str(error).upper():
                        st.error("Já existe um usuário com esse login.")
                    else:
                        st.error(f"Erro ao cadastrar usuário: {error}")

    df_users = _load_users(conn)

    if df_users.empty:
        st.info("Nenhum usuário cadastrado.")
        return

    tabela = df_users.copy()
    tabela["Status"] = tabela["ativo"].map({1: "Ativo", 0: "Inativo"})
    tabela = tabela.rename(columns={
        "id": "ID",
        "nome": "Nome",
        "usuario": "Usuário",
        "perfil": "Perfil",
        "quiosque_nome": "Quiosque",
        "criado_em": "Criado em",
    })
    tabela["Acesso"] = tabela["acesso_todos_quiosques"].map({1: "Todos", 0: "Quiosque"})
    tabela = tabela[["ID", "Nome", "Usuário", "Perfil", "Quiosque", "Acesso", "Status", "Criado em"]]

    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
    )

    st.divider()
    st.subheader("✏️ Editar usuário")

    options = {
        f"{row.nome} ({row.usuario})": row.id
        for row in df_users.itertuples()
    }

    selected_label = st.selectbox("Selecione", list(options.keys()))
    selected_id = options[selected_label]
    selected_user = df_users[df_users["id"] == selected_id].iloc[0]

    with st.form("editar_usuario_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            nome_edit = st.text_input("Nome", value=selected_user["nome"])

        with col2:
            perfil_edit = st.selectbox(
                "Perfil",
                PERFIS,
                index=PERFIS.index(selected_user["perfil"])
                if selected_user["perfil"] in PERFIS
                else 1,
            )

        with col3:
            ativo_edit = st.checkbox("Ativo", value=bool(selected_user["ativo"]))
            acesso_todos_edit = st.checkbox("Acesso a todos", value=bool(selected_user["acesso_todos_quiosques"]))
            selected_quiosque = int(selected_user["quiosque_id"] or 1)
            quiosque_edit = st.selectbox(
                "Quiosque",
                list(quiosque_options.keys()),
                format_func=lambda value: quiosque_options[value],
                index=list(quiosque_options.keys()).index(selected_quiosque)
                if selected_quiosque in quiosque_options
                else 0,
            )

        salvar_edicao = st.form_submit_button("Salvar alterações")

    if salvar_edicao:
        _update_user(conn, selected_id, nome_edit, perfil_edit, ativo_edit, quiosque_edit, acesso_todos_edit)
        st.success("✅ Usuário atualizado!")
        st.rerun()

    with st.form("alterar_senha_form"):
        nova_senha = st.text_input("Nova senha", type="password")
        salvar_senha = st.form_submit_button("Alterar senha")

    if salvar_senha:
        if len(nova_senha) < 6:
            st.error("A senha deve ter pelo menos 6 caracteres.")
        else:
            _update_password(conn, selected_id, nova_senha)
            st.success("✅ Senha atualizada!")
