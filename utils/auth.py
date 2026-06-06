import hashlib
import hmac
import os
import base64
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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


def get_user_by_id(conn, user_id):
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
    WHERE id = ?
    LIMIT 1
    """, conn, params=(int(user_id),))

    if users.empty:
        return None

    return users.iloc[0].to_dict()


def _public_user(user):
    return {
        "id": user["id"],
        "nome": user["nome"],
        "usuario": user["usuario"],
        "perfil": user["perfil"],
        "quiosque_id": int(user.get("quiosque_id") or 1),
        "acesso_todos_quiosques": int(user.get("acesso_todos_quiosques") or 0),
    }


def authenticate_user(conn, username, password):
    user = get_user_by_username(conn, username)

    if not user or not user["ativo"]:
        return None

    if not verify_password(password, user["senha_salt"], user["senha_hash"]):
        return None

    return _public_user(user)


def _b64_encode(value):
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


def create_remember_token(conn, user, days=30):
    full_user = get_user_by_id(conn, user["id"])
    if not full_user:
        return ""

    payload = {
        "id": int(full_user["id"]),
        "usuario": full_user["usuario"],
        "exp": int(time.time()) + int(days * 86400),
    }
    payload_raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload_b64 = _b64_encode(payload_raw)
    signature = hmac.new(
        str(full_user["senha_hash"]).encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_b64_encode(signature)}"


def authenticate_remember_token(conn, token):
    if not token or "." not in str(token):
        return None

    try:
        payload_b64, signature_b64 = str(token).split(".", 1)
        payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp") or 0) < int(time.time()):
            return None

        full_user = get_user_by_id(conn, payload.get("id"))
        if not full_user or not full_user["ativo"] or full_user["usuario"] != payload.get("usuario"):
            return None

        expected = hmac.new(
            str(full_user["senha_hash"]).encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        received = _b64_decode(signature_b64)
        if not hmac.compare_digest(expected, received):
            return None

        return _public_user(full_user)
    except Exception:
        return None


def is_logged_in():
    return st.session_state.get("usuario_logado") is not None


def current_user():
    return st.session_state.get("usuario_logado")


def logout():
    st.session_state.pop("usuario_logado", None)
    _sync_login_storage("", remember=False, remember_token="")
    st.stop()


def _inject_login_autofill(remember_username=""):
    safe_username = str(remember_username or "").replace("\\", "\\\\").replace("`", "\\`")
    components.html(
        f"""
        <script>
        (function () {{
            const doc = window.parent.document;
            const storageKey = "tx_system_remembered_username";
            const tokenKey = "tx_system_remember_token";

            const savedToken = window.localStorage.getItem(tokenKey);
            const url = new URL(window.parent.location.href);
            if (savedToken && !url.searchParams.get("tx_session")) {{
                url.searchParams.set("tx_session", savedToken);
                window.parent.history.replaceState(null, "", url.toString());
                window.parent.location.reload();
                return;
            }}

            function enhanceLoginFields() {{
                const inputs = Array.from(doc.querySelectorAll('input'));
                const usernameInput = inputs.find((input) => input.type === "text" && !input.dataset.txLoginUsername);
                const passwordInput = inputs.find((input) => input.type === "password" && !input.dataset.txLoginPassword);
                const checkboxes = Array.from(doc.querySelectorAll('input[type="checkbox"]'));
                const rememberInput = checkboxes[0];

                if (usernameInput) {{
                    usernameInput.dataset.txLoginUsername = "1";
                    usernameInput.setAttribute("name", "username");
                    usernameInput.setAttribute("id", "username");
                    usernameInput.setAttribute("autocomplete", "username");
                    usernameInput.setAttribute("autocapitalize", "none");
                    usernameInput.setAttribute("autocorrect", "off");
                    usernameInput.setAttribute("spellcheck", "false");
                    const saved = window.localStorage.getItem(storageKey) || `{safe_username}`;
                    if (saved && !usernameInput.value) {{
                        usernameInput.value = saved;
                        usernameInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                        usernameInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
                    }}
                    usernameInput.addEventListener("input", function () {{
                        if (!rememberInput || rememberInput.checked) {{
                            window.localStorage.setItem(storageKey, usernameInput.value || "");
                        }}
                    }});
                }}

                if (passwordInput) {{
                    passwordInput.dataset.txLoginPassword = "1";
                    passwordInput.setAttribute("name", "password");
                    passwordInput.setAttribute("id", "password");
                    passwordInput.setAttribute("autocomplete", "current-password");
                }}

                if (rememberInput && !rememberInput.dataset.txRememberUsername) {{
                    rememberInput.dataset.txRememberUsername = "1";
                    rememberInput.addEventListener("change", function () {{
                        if (rememberInput.checked && usernameInput && usernameInput.value) {{
                            window.localStorage.setItem(storageKey, usernameInput.value);
                        }} else if (!rememberInput.checked) {{
                            window.localStorage.removeItem(storageKey);
                        }}
                    }});
                }}
            }}

            enhanceLoginFields();
            setTimeout(enhanceLoginFields, 350);
            setTimeout(enhanceLoginFields, 1000);
        }})();
        </script>
        """,
        height=0,
    )


def _sync_login_storage(username="", remember=False, remember_token=""):
    safe_username = str(username or "").replace("\\", "\\\\").replace("`", "\\`")
    safe_token = str(remember_token or "").replace("\\", "\\\\").replace("`", "\\`")
    user_action = "set" if remember and safe_username else "remove"
    token_action = "set" if safe_token else "remove"
    components.html(
        f"""
        <script>
        (function () {{
            const userKey = "tx_system_remembered_username";
            const tokenKey = "tx_system_remember_token";
            if ("{user_action}" === "set") {{
                window.parent.localStorage.setItem(userKey, `{safe_username}`);
            }} else {{
                window.parent.localStorage.removeItem(userKey);
            }}
            if ("{token_action}" === "set") {{
                window.parent.localStorage.setItem(tokenKey, `{safe_token}`);
            }} else {{
                window.parent.localStorage.removeItem(tokenKey);
            }}
            setTimeout(function () {{
                window.parent.location.reload();
            }}, 120);
        }})();
        </script>
        """,
        height=0,
    )


def require_login(conn):
    ensure_default_admin(conn)

    if is_logged_in():
        return True

    token = st.query_params.get("tx_session")
    if token:
        user = authenticate_remember_token(conn, token)
        if user:
            st.session_state["usuario_logado"] = user
            try:
                del st.query_params["tx_session"]
            except Exception:
                pass
            st.rerun()
        else:
            _sync_login_storage("", remember=False, remember_token="")
            try:
                del st.query_params["tx_session"]
            except Exception:
                pass

    banner_uri = _image_data_uri(LOGIN_BANNER_PATH)
    logo_uri = _image_data_uri(LOGIN_LOGO_PATH)

    st.markdown('<div class="tx-login-page"></div>', unsafe_allow_html=True)
    st.session_state.setdefault("login_remember_user", True)
    st.session_state.setdefault("login_stay_connected", False)
    remembered_user = st.session_state.get("login_username", "")
    _inject_login_autofill(remembered_user)

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
            username = st.text_input(
                "Usuário",
                key="login_username",
                placeholder="Digite seu usuário",
            )
            password = st.text_input(
                "Senha",
                type="password",
                key="login_password",
                placeholder="Digite sua senha",
            )
            remember_user = st.checkbox(
                "Lembrar usuário",
                key="login_remember_user",
                help="Salva apenas o usuário neste aparelho. A senha fica por conta do Safari/Chaves do iCloud.",
            )
            stay_connected = st.checkbox(
                "Permanecer conectado por 30 dias",
                key="login_stay_connected",
                help="Mantém a sessão deste navegador aberta por mais tempo. Não salva sua senha.",
            )
            submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if submitted:
            user = authenticate_user(conn, username, password)

            if user:
                st.session_state["usuario_logado"] = user
                remember_token = create_remember_token(conn, user, days=30) if stay_connected else ""
                _sync_login_storage(username, remember_user, remember_token)
                st.success("Login realizado.")
                st.stop()
            else:
                st.error("Usuário ou senha inválidos.")

        with st.expander("Primeiro acesso"):
            st.write(f"Usuário: `{DEFAULT_ADMIN_USER}`")
            st.write(f"Senha: `{DEFAULT_ADMIN_PASSWORD}`")
            st.caption("Depois crie seus funcionários e altere a senha padrão.")

    return False
