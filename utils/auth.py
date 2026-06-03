import hashlib
import hmac
import os
import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from database.database import recover_connection


DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
BRANDING_DIR = Path(__file__).resolve().parents[1] / "assets" / "branding"
LOGIN_BANNER_PATH = BRANDING_DIR / "tx_login_banner.webp"
LOGIN_LOGO_PATH = BRANDING_DIR / "tx_logo_icon.png"


@st.cache_data(show_spinner=False)
def _image_data_uri_cached(path_str, mtime_ns):
    path = Path(path_str)
    if not path.exists():
        return ""

    image_bytes = path.read_bytes()
    suffix = path.suffix.lower()
    mime_type = "image/png"
    if image_bytes.startswith(b"\x89PNG"):
        mime_type = "image/png"
    elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        mime_type = "image/webp"
    elif image_bytes.startswith(b"\xff\xd8"):
        mime_type = "image/jpeg"
    elif suffix in {".jpg", ".jpeg"}:
        mime_type = "image/jpeg"

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _image_data_uri(path):
    if not path.exists():
        return ""
    return _image_data_uri_cached(str(path), path.stat().st_mtime_ns)


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
    recover_connection(conn)
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
        ativo,
        quiosque_id,
        acesso_todos_quiosques
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Administrador",
        DEFAULT_ADMIN_USER,
        password_hash,
        salt,
        "Admin",
        1,
        1,
        1,
    ))
    conn.commit()


def get_user_by_username(conn, username):
    users = pd.read_sql_query("""
    SELECT
        id,
        nome,
        usuario,
        senha_hash,
        senha_salt,
        perfil,
        ativo,
        quiosque_id,
        acesso_todos_quiosques
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
        "quiosque_id": int(user.get("quiosque_id") or 1),
        "acesso_todos_quiosques": int(user.get("acesso_todos_quiosques") or 0),
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

    banner_uri = _image_data_uri(LOGIN_BANNER_PATH)
    logo_uri = _image_data_uri(LOGIN_LOGO_PATH)

    st.markdown('<div class="tx-login-page"></div>', unsafe_allow_html=True)

    art_col, form_col = st.columns([1.08, 0.92], gap="large")

    with art_col:
        if banner_uri:
            st.markdown(
                f"""
                <div class="tx-login-art">
                    <img src="{banner_uri}" alt="Tecnologia urbana para gestao inteligente" loading="eager" decoding="async">
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="tx-login-art tx-login-art-fallback">
                    <strong>TX</strong>
                    <span>Tecnologia urbana para gestao inteligente.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with form_col:
        st.markdown(
            f"""
            <div class="tx-login-brand">
                {'<img src="' + logo_uri + '" alt="TX System" loading="eager" decoding="async">' if logo_uri else '<strong>TX</strong>'}
                <div>
                    <h1>TX System</h1>
                    <p>Gestao inteligente, resultado previsivel.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)

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
