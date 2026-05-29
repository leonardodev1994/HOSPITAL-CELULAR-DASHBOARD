import streamlit as st
from PIL import Image
from pathlib import Path

from database.database import init_db, initialize_database
from utils.backup import run_daily_auto_backup
from views.caixa_diario import render_caixa_diario
from views.backup import render_backup
from views.clientes import render_clientes
from views.dashboard_diario import render_dashboard_diario
from views.dashboard_geral import render_dashboard_geral
from views.dashboard_mensal import render_dashboard_mensal
from views.despesas import render_despesas
from views.estoque import render_estoque
from views.novo_lancamento import render_novo_lancamento
from views.ordem_servico import render_ordem_servico
from views.usuarios import render_usuarios
from utils.auth import current_user, logout, require_login
from utils.style import apply_style


LOGO_PATH = Path("assets/logo.png")

st.set_page_config(
    page_title="Hospital do Celular",
    page_icon=Image.open(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_style()


@st.cache_resource(show_spinner=False)
def ensure_database_initialized():
    migration_conn = init_db()
    try:
        initialize_database(migration_conn)
    finally:
        migration_conn.close()


ensure_database_initialized()
conn = init_db()

if not require_login(conn):
    st.stop()

user = current_user()
auto_backup = run_daily_auto_backup()

MENU_ITEMS = {
    "Dashboard Geral": render_dashboard_geral,
    "Dashboard Diário": render_dashboard_diario,
    "Dashboard Mensal": render_dashboard_mensal,
    "Clientes": render_clientes,
    "Estoque": render_estoque,
    "Novo Lançamento": render_novo_lancamento,
    "Caixa Diário": render_caixa_diario,
    "Despesas": render_despesas,
    "Ordem de Serviço": render_ordem_servico,
    "Usuários/Funcionários": render_usuarios,
    "Backup": render_backup,
}

MENU_GROUPS = {
    "Análise": ["Dashboard Geral", "Dashboard Diário", "Dashboard Mensal"],
    "Operação": ["Clientes", "Estoque", "Novo Lançamento", "Ordem de Serviço"],
    "Financeiro": ["Caixa Diário", "Despesas"],
    "Sistema": ["Usuários/Funcionários", "Backup"],
}

MENU_ICONS = {
    "Dashboard Geral": ":material/dashboard:",
    "Dashboard Diário": ":material/monitoring:",
    "Dashboard Mensal": ":material/calendar_month:",
    "Clientes": ":material/groups:",
    "Estoque": ":material/inventory_2:",
    "Novo Lançamento": ":material/point_of_sale:",
    "Caixa Diário": ":material/account_balance_wallet:",
    "Despesas": ":material/trending_down:",
    "Ordem de Serviço": ":material/build:",
    "Usuários/Funcionários": ":material/admin_panel_settings:",
    "Backup": ":material/cloud_upload:",
}


def _set_menu(menu_label: str):
    st.session_state["menu_atual"] = menu_label


def _set_menu_from_mobile():
    selected = st.session_state.get("menu_mobile")
    if selected in MENU_ITEMS:
        _set_menu(selected)


def render_mobile_navigation(user, auto_backup):
    current_menu = st.session_state["menu_atual"]
    if st.session_state.get("menu_mobile") != current_menu:
        st.session_state["menu_mobile"] = current_menu

    with st.container(key="mobile_nav"):
        with st.expander("☰ Menu / Categorias", expanded=False):
            st.markdown(
                f"""
                <div class="mobile-user">
                    <span>Usuário ativo</span>
                    <strong>{user['nome']}</strong>
                    <small>{user['perfil']}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if auto_backup:
                st.success(f"Backup automático criado: {auto_backup.name}")
            st.radio(
                "Ir para:",
                list(MENU_ITEMS.keys()),
                key="menu_mobile",
                on_change=_set_menu_from_mobile,
            )
            if st.button("Sair", key="mobile_logout", width="stretch", icon=":material/logout:"):
                logout()


def render_sidebar_navigation(user, auto_backup):
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH)
        st.sidebar.image(logo, width=178)

    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <h2>Hospital do Celular</h2>
            <p>Assistência técnica, estoque e vendas</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"""
        <div class="sidebar-user">
            <span>Usuário ativo</span>
            <strong>{user['nome']}</strong>
            <small>{user['perfil']}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if auto_backup:
        st.sidebar.success(f"Backup automático criado: {auto_backup.name}")

    st.sidebar.markdown('<div class="nav-caption">Navegação</div>', unsafe_allow_html=True)
    for group_name, group_items in MENU_GROUPS.items():
        st.sidebar.markdown(f'<div class="nav-group">{group_name}</div>', unsafe_allow_html=True)
        for menu_label in group_items:
            is_active = st.session_state["menu_atual"] == menu_label
            icon = MENU_ICONS.get(menu_label)
            if st.sidebar.button(
                menu_label,
                key=f"nav_{menu_label}",
                width="stretch",
                type="primary" if is_active else "secondary",
                icon=icon,
            ):
                _set_menu(menu_label)
                st.rerun()

    st.sidebar.divider()

    if st.sidebar.button("Sair", width="stretch", icon=":material/logout:"):
        logout()


if "menu_atual" not in st.session_state or st.session_state["menu_atual"] not in MENU_ITEMS:
    st.session_state["menu_atual"] = "Dashboard Geral"

render_sidebar_navigation(user, auto_backup)
render_mobile_navigation(user, auto_backup)
menu = st.session_state["menu_atual"]

MENU_ITEMS[menu](conn)
