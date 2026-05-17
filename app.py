from pathlib import Path

import streamlit as st
from PIL import Image

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


st.set_page_config(
    page_title="Hospital do Celular",
    layout="wide",
)

apply_style()

conn = init_db()

if not require_login(conn):
    st.stop()

user = current_user()
auto_backup = run_daily_auto_backup()

MENU_ITEMS = {
    "📊 Dashboard Geral": render_dashboard_geral,
    "📅 Dashboard Diário": render_dashboard_diario,
    "🗓️ Dashboard Mensal": render_dashboard_mensal,
    "👤 Clientes": render_clientes,
    "📦 Estoque": render_estoque,
    "➕ Novo Lançamento": render_novo_lancamento,
    "💰 Caixa Diário": render_caixa_diario,
    "💸 Despesas": render_despesas,
    "📋 Ordem de Serviço": render_ordem_servico,
    "👥 Usuários/Funcionários": render_usuarios,
    "🛡️ Backup": render_backup,
}

if "menu_atual" not in st.session_state:
    st.session_state["menu_atual"] = "📊 Dashboard Geral"

logo_path = Path("assets/logo.png")
if logo_path.exists():
    logo = Image.open(logo_path)
    st.sidebar.image(logo, width=220)

st.sidebar.title("Hospital do Celular")
st.sidebar.caption(f"Logado como: {user['nome']} ({user['perfil']})")

if auto_backup:
    st.sidebar.success(f"Backup automático criado: {auto_backup.name}")

menu = st.sidebar.radio(
    "Navegação",
    list(MENU_ITEMS.keys()),
    index=list(MENU_ITEMS.keys()).index(st.session_state["menu_atual"]),
    label_visibility="collapsed",
)

st.session_state["menu_atual"] = menu

st.sidebar.divider()

if st.sidebar.button("Sair", width="stretch"):
    logout()

MENU_ITEMS[menu](conn)
