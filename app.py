import streamlit as st
from PIL import Image
from pathlib import Path

from database.database import init_db
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
)

apply_style()

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

if "menu_atual" not in st.session_state or st.session_state["menu_atual"] not in MENU_ITEMS:
    st.session_state["menu_atual"] = "Dashboard Geral"

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
            st.session_state["menu_atual"] = menu_label
            st.rerun()

menu = st.session_state["menu_atual"]

st.sidebar.divider()

if st.sidebar.button("Sair", width="stretch", icon=":material/logout:"):
    logout()

MENU_ITEMS[menu](conn)
