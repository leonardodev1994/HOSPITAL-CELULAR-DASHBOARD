import hashlib
import hmac
import os

import pandas as pd
import streamlit as st


DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()

    return salt, password_hash


def verify_password(password, salt, password_hash):
    _, candidate_hash = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def ensure_default_admin(conn):
    cursor = conn.cursor()
    total_users = cursor.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    if total_users > 0:
        return

    salt, password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
    cursor.execute("""
    INSERT INTO usuarios (
        nome,
        usuario,
        senha_hash,
        senha_salt,
        perfil,
        ativo
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "Administrador",
        DEFAULT_ADMIN_USER,
        password_hash,
        salt,
        "Admin",
        1,
    ))
    conn.commit()


def get_user_by_username(conn, username):
    users = pd.read_sql_query("""
    SELECT *
    FROM usuarios
    WHERE usuario = ?
    LIMIT 1
    """, conn, params=(username.strip(),))

    if users.empty:
        return None

    return users.iloc[0].to_dict()


def authenticate_user(conn, username, password):
    user = get_user_by_username(conn, username)

    if not user or not user["ativo"]:
        return None

    if not verify_password(password, user["senha_salt"], user["senha_hash"]):
        return None

    return {
        "id": user["id"],
        "nome": user["nome"],
        "usuario": user["usuario"],
        "perfil": user["perfil"],
    }


def is_logged_in():
    return st.session_state.get("usuario_logado") is not None


def current_user():
    return st.session_state.get("usuario_logado")


def logout():
    st.session_state.pop("usuario_logado", None)
    st.rerun()


def require_login(conn):
    ensure_default_admin(conn)

    if is_logged_in():
        return True

    st.markdown("## Hospital do Celular")
    st.caption("Acesse sua conta para continuar")

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        user = authenticate_user(conn, username, password)

        if user:
            st.session_state["usuario_logado"] = user
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")

    with st.expander("Primeiro acesso"):
        st.write(f"Usuário: `{DEFAULT_ADMIN_USER}`")
        st.write(f"Senha: `{DEFAULT_ADMIN_PASSWORD}`")
        st.caption("Depois crie seus funcionários e altere a senha padrão.")

    return False
