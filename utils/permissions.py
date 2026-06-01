import streamlit as st


PROFILE_ADMIN = "Admin"
PROFILE_MANAGER = "Gerente de quiosque"
PROFILE_ATTENDANT = "Atendente"


PERFIS = [PROFILE_ADMIN, PROFILE_MANAGER, PROFILE_ATTENDANT]


ROLE_PERMISSIONS = {
    PROFILE_ADMIN: {
        "view_all_quiosques",
        "view_dashboard_general",
        "view_daily_sales",
        "view_dashboard_monthly",
        "view_profit",
        "view_expenses",
        "view_daily_cash",
        "view_financial_reports",
        "view_stock",
        "create_sales",
        "create_os",
        "manage_stock",
        "delete_records",
        "edit_financial_values",
        "manage_users",
        "manage_backup",
        "export_financial_reports",
    },
    PROFILE_MANAGER: {
        "view_dashboard_general",
        "view_daily_sales",
        "view_dashboard_monthly",
        "view_daily_cash",
        "view_sales_period",
        "view_stock",
        "create_sales",
        "create_os",
        "manage_stock",
        "edit_financial_values",
    },
    PROFILE_ATTENDANT: {
        "view_daily_sales",
        "view_daily_cash",
        "view_stock",
        "create_sales",
        "create_os",
        "edit_os_status",
    },
}


MENU_PERMISSIONS = {
    "Dashboard Geral": "view_dashboard_general",
    "Dashboard Diário": "view_daily_sales",
    "Dashboard Mensal": "view_dashboard_monthly",
    "Clientes": None,
    "Estoque": "view_stock",
    "Novo Lançamento": "create_sales",
    "Caixa Diário": "view_daily_cash",
    "Despesas": "view_expenses",
    "Ordem de Serviço": "create_os",
    "Usuários/Funcionários": "manage_users",
    "Backup": "manage_backup",
}


def current_user():
    return st.session_state.get("usuario_logado") or {}


def normalize_profile(profile):
    normalized = str(profile or "").strip().lower()
    if normalized in {"admin", "administrador"}:
        return PROFILE_ADMIN
    if normalized in {"gerente de quiosque", "gerente"}:
        return PROFILE_MANAGER
    if normalized in {"atendente", "técnico", "tecnico"}:
        return PROFILE_ATTENDANT
    if profile == "Técnico":
        return PROFILE_ATTENDANT
    if profile in PERFIS:
        return profile
    return PROFILE_ATTENDANT


def has_permission(permission, user=None):
    if permission is None:
        return True

    user = user or current_user()
    profile = normalize_profile(user.get("perfil"))
    return permission in ROLE_PERMISSIONS.get(profile, set())


def require_permission(permission, message="Você não tem permissão para acessar esta área."):
    if has_permission(permission):
        return True

    st.warning(message)
    return False


def visible_menu_items(menu_items, user=None):
    return [
        item
        for item in menu_items
        if has_permission(MENU_PERMISSIONS.get(item), user)
    ]
