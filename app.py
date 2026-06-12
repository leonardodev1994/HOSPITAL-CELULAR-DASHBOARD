import streamlit as st
from pathlib import Path

from database.database import init_db, initialize_database, recover_connection
from utils.backup import run_daily_auto_backup
from views.auditoria import render_auditoria
from views.caixa_diario import render_caixa_diario
from views.backup import render_backup
from views.catalogo import render_catalogo
from views.clientes import render_clientes
from views.compra_aparelhos import render_compra_aparelhos
from views.dashboard_diario import render_dashboard_diario
from views.dashboard_geral import render_dashboard_geral
from views.dashboard_mensal import render_dashboard_mensal
from views.despesas import render_despesas
from views.estoque import render_estoque
from views.lancamentos import render_lancamentos
from views.lancamentos_cancelados import render_lancamentos_cancelados
from views.novo_lancamento import render_novo_lancamento
from views.ordem_servico import render_ordem_servico
from views.servicos import render_servicos
from views.usuarios import render_usuarios
from utils.auth import current_user, logout, require_login
from utils.global_search import render_global_search
from utils.permissions import MENU_PERMISSIONS, has_permission, visible_menu_items
from utils.quiosques import render_quiosque_filter
from utils.style import apply_style


LOGO_PATH = Path("assets/branding/tx_logo_icon.png")
ICON_PATH = Path("assets/branding/tx_logo_icon.png")
APP_VERSION = "seminovos-2026-06-12"

st.set_page_config(
    page_title="TX System",
    page_icon=str(ICON_PATH) if ICON_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_style()


@st.cache_resource(show_spinner=False)
def ensure_database_initialized(app_version):
    migration_conn = init_db()
    try:
        initialize_database(migration_conn)
    except Exception:
        st.cache_resource.clear()
        raise
    finally:
        migration_conn.close()
    return True


ensure_database_initialized(APP_VERSION)


def get_app_connection():
    return init_db()


conn = get_app_connection()
recover_connection(conn)

if not require_login(conn):
    st.stop()

user = current_user()
auto_backup = run_daily_auto_backup()

MENU_ITEMS = {
    "Dashboard Geral": render_dashboard_geral,
    "Dashboard Diário": render_dashboard_diario,
    "Dashboard Mensal": render_dashboard_mensal,
    "Clientes": render_clientes,
    "Catálogo": render_catalogo,
    "Estoque": render_estoque,
    "Serviços": render_servicos,
    "Novo Lançamento": render_novo_lancamento,
    "Lançamentos": render_lancamentos,
    "Lançamentos Cancelados": render_lancamentos_cancelados,
    "Caixa Diário": render_caixa_diario,
    "Despesas": render_despesas,
    "Ordem de Serviço": render_ordem_servico,
    "Compra de Aparelhos": render_compra_aparelhos,
    "Usuários/Funcionários": render_usuarios,
    "Auditoria": render_auditoria,
    "Backup": render_backup,
}

MENU_GROUPS = {
    "Análise": ["Dashboard Geral", "Dashboard Diário", "Dashboard Mensal"],
    "Operação": ["Clientes", "Catálogo", "Estoque", "Serviços", "Novo Lançamento", "Lançamentos", "Ordem de Serviço", "Compra de Aparelhos"],
    "Financeiro": ["Caixa Diário", "Lançamentos Cancelados", "Despesas"],
    "Sistema": ["Usuários/Funcionários", "Auditoria", "Backup"],
}

MENU_ICONS = {
    "Dashboard Geral": ":material/dashboard:",
    "Dashboard Diário": ":material/monitoring:",
    "Dashboard Mensal": ":material/calendar_month:",
    "Clientes": ":material/groups:",
    "Catálogo": ":material/search:",
    "Estoque": ":material/inventory_2:",
    "Serviços": ":material/home_repair_service:",
    "Novo Lançamento": ":material/point_of_sale:",
    "Lançamentos": ":material/receipt_long:",
    "Lançamentos Cancelados": ":material/cancel:",
    "Caixa Diário": ":material/account_balance_wallet:",
    "Despesas": ":material/trending_down:",
    "Ordem de Serviço": ":material/build:",
    "Compra de Aparelhos": ":material/phone_iphone:",
    "Usuários/Funcionários": ":material/admin_panel_settings:",
    "Auditoria": ":material/manage_search:",
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
                    <small>Versão: {APP_VERSION}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if auto_backup:
                st.success(f"Backup automático criado: {auto_backup.name}")
            st.radio(
                "Ir para:",
                visible_menu_items(list(MENU_ITEMS.keys()), user),
                key="menu_mobile",
                on_change=_set_menu_from_mobile,
            )
            if st.button("Sair", key="mobile_logout", width="stretch", icon=":material/logout:"):
                logout()


def render_sidebar_navigation(user, auto_backup):
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width=178)

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
            <small>Versão: {APP_VERSION}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if auto_backup:
        st.sidebar.success(f"Backup automático criado: {auto_backup.name}")

    st.sidebar.markdown('<div class="nav-caption">Navegação</div>', unsafe_allow_html=True)
    for group_name, group_items in MENU_GROUPS.items():
        visible_items = visible_menu_items(group_items, user)
        if not visible_items:
            continue

        st.sidebar.markdown(f'<div class="nav-group">{group_name}</div>', unsafe_allow_html=True)
        for menu_label in visible_items:
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


available_menu_items = visible_menu_items(list(MENU_ITEMS.keys()), user)

if (
    "menu_atual" not in st.session_state
    or st.session_state["menu_atual"] not in MENU_ITEMS
    or not has_permission(MENU_PERMISSIONS.get(st.session_state["menu_atual"]), user)
):
    st.session_state["menu_atual"] = available_menu_items[0]

render_sidebar_navigation(user, auto_backup)
render_mobile_navigation(user, auto_backup)
menu = st.session_state["menu_atual"]

render_quiosque_filter(conn, user)
render_global_search(conn, available_menu_items)

MENU_ITEMS[menu](conn)
