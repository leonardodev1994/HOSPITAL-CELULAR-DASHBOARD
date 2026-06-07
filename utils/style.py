import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "branding" / "tx_logo_icon.png"


@st.cache_data(show_spinner=False)
def _logo_data_uri_cached(path_str, mtime_ns):
    path = Path(path_str)
    if not path.exists():
        return ""
    return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode('utf-8')}"


def _logo_data_uri():
    if not LOGO_PATH.exists():
        return ""
    return _logo_data_uri_cached(str(LOGO_PATH), LOGO_PATH.stat().st_mtime_ns)


def apply_style():
    logo_uri = _logo_data_uri()
    st.markdown(
        """
        <link rel="manifest" href="/app/static/manifest.json?v=tx-brand-v6">
        <link rel="icon" type="image/png" sizes="64x64" href="/app/static/favicon.png?v=tx-brand-v6">
        <link rel="icon" href="/app/static/favicon.ico?v=tx-brand-v6">
        <link rel="shortcut icon" type="image/png" sizes="64x64" href="/app/static/favicon.png?v=tx-brand-v6">
        <link rel="apple-touch-icon" sizes="180x180" href="/app/static/apple-touch-icon.png?v=tx-brand-v6">
        <link rel="apple-touch-icon-precomposed" sizes="180x180" href="/app/static/apple-touch-icon-precomposed.png?v=tx-brand-v6">
        <meta name="theme-color" content="#ffffff">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="default">
        <meta name="apple-mobile-web-app-title" content="TX System">
        """,
        unsafe_allow_html=True,
    )
    st.markdown("""
    <style>
    :root {
        --bg: #F5F7FA;
        --surface: #FFFFFF;
        --surface-2: #F8FAFC;
        --sidebar: #FFFFFF;
        --sidebar-2: #F8FAFC;
        --text: #101828;
        --muted: #667085;
        --border: #E4E7EC;
        --accent: #E63946;
        --accent-2: #2563EB;
        --success: #16A34A;
        --warning: #D97706;
        --danger: #DC2626;
        --shadow: 0 18px 48px rgba(16, 24, 40, .08);
        --shadow-soft: 0 8px 26px rgba(16, 24, 40, .06);
        --radius: 8px;
    }

    .stApp {
        background: var(--bg);
        color: var(--text);
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .main .block-container {
        max-width: 1500px;
        padding: 1.35rem 1.75rem 3rem;
    }

    #MainMenu,
    footer {
        visibility: hidden;
        height: 0;
    }

    [data-testid="stHeader"] {
        visibility: visible !important;
        height: 3.25rem !important;
        background: rgba(245, 247, 250, .92) !important;
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(228, 231, 236, .8);
        pointer-events: auto !important;
        z-index: 999998 !important;
    }

    [data-testid="stHeader"] *,
    [data-testid="stToolbar"],
    [data-testid="stToolbar"] * {
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    [data-testid="stToolbar"] {
        display: flex !important;
        height: auto !important;
        min-height: 44px !important;
    }

    [data-testid="collapsedControl"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: fixed !important;
        top: .55rem !important;
        left: .65rem !important;
        z-index: 999999 !important;
    }

    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {
        min-width: 42px !important;
        min-height: 42px !important;
        color: var(--text) !important;
        background: #FFFFFF !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-soft) !important;
    }

    button[aria-label*="sidebar"],
    button[aria-label*="Sidebar"],
    button[title*="sidebar"],
    button[title*="Sidebar"],
    [data-testid="stBaseButton-header"],
    [data-testid="stBaseButton-headerNoPadding"] {
        min-width: 42px !important;
        min-height: 42px !important;
        color: var(--text) !important;
        background: #FFFFFF !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-soft) !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    [data-testid="collapsedControl"] button *,
    [data-testid="stSidebarCollapseButton"] button *,
    button[aria-label*="sidebar"] *,
    button[aria-label*="Sidebar"] *,
    button[title*="sidebar"] *,
    button[title*="Sidebar"] *,
    [data-testid="stBaseButton-header"] *,
    [data-testid="stBaseButton-headerNoPadding"] * {
        color: var(--text) !important;
    }

    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    button[aria-label*="sidebar"] svg,
    button[aria-label*="Sidebar"] svg,
    button[title*="sidebar"] svg,
    button[title*="Sidebar"] svg,
    [data-testid="stBaseButton-header"] svg,
    [data-testid="stBaseButton-headerNoPadding"] svg {
        color: var(--text) !important;
        stroke: var(--text) !important;
        fill: var(--text) !important;
    }

    [data-testid="collapsedControl"] svg path,
    [data-testid="stSidebarCollapseButton"] svg path,
    button[aria-label*="sidebar"] svg path,
    button[aria-label*="Sidebar"] svg path,
    button[title*="sidebar"] svg path,
    button[title*="Sidebar"] svg path,
    [data-testid="stBaseButton-header"] svg path,
    [data-testid="stBaseButton-headerNoPadding"] svg path {
        stroke: var(--text) !important;
        fill: var(--text) !important;
    }

    .stApp,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp div {
        color: var(--text);
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--text) !important;
        letter-spacing: 0;
    }

    h1 { font-size: 30px !important; font-weight: 850 !important; }
    h2 { font-size: 22px !important; font-weight: 800 !important; }
    h3 { font-size: 18px !important; font-weight: 780 !important; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar) 0%, var(--sidebar-2) 100%);
        border-right: 1px solid var(--border);
    }

    section[data-testid="stSidebar"] * {
        color: var(--text) !important;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 18px;
    }

    section[data-testid="stSidebar"] img {
        display: block;
        margin: 6px auto 12px;
        border-radius: var(--radius);
        box-shadow: 0 12px 28px rgba(16, 24, 40, .10);
    }

    .sidebar-brand {
        padding: 6px 6px 16px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 12px;
    }

    .sidebar-brand h2 {
        margin: 0 0 5px;
        color: var(--text) !important;
        font-size: 1.18rem !important;
        font-weight: 850 !important;
    }

    .sidebar-brand p {
        margin: 0;
        color: var(--muted) !important;
        font-size: .82rem;
        line-height: 1.35;
    }

    .sidebar-user {
        background: #F9FAFB;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 12px;
        margin: 6px 0 14px;
    }

    .sidebar-user span,
    .sidebar-user small {
        display: block;
        color: var(--muted) !important;
        font-size: .78rem;
    }

    .sidebar-user strong {
        display: block;
        margin-top: 5px;
        color: var(--text) !important;
        font-size: .98rem;
    }

    .st-key-mobile_nav {
        display: none;
    }

    .mobile-user {
        background: #F9FAFB;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 12px;
        margin: 0 0 12px;
    }

    .mobile-user span,
    .mobile-user small {
        display: block;
        color: var(--muted) !important;
        font-size: .78rem;
    }

    .mobile-user strong {
        display: block;
        margin-top: 5px;
        color: var(--text) !important;
        font-size: .98rem;
    }

    .nav-caption {
        margin: 4px 0 12px;
        color: #98A2B3 !important;
        font-size: .74rem;
        font-weight: 850;
        letter-spacing: .08em;
        text-transform: uppercase;
    }

    .nav-group {
        margin: 14px 0 6px;
        color: #667085 !important;
        font-size: .72rem;
        font-weight: 850;
        letter-spacing: .06em;
        text-transform: uppercase;
    }

    section[data-testid="stSidebar"] .stButton {
        margin-bottom: 4px;
    }

    section[data-testid="stSidebar"] .stButton button {
        justify-content: flex-start;
        min-height: 40px;
        padding: 0 12px;
        border-radius: var(--radius) !important;
        border: 1px solid transparent !important;
        background: transparent !important;
        box-shadow: none !important;
        font-weight: 760;
        gap: 10px;
    }

    section[data-testid="stSidebar"] .stButton button [data-testid="stIconMaterial"],
    section[data-testid="stSidebar"] .stButton button .material-symbols-rounded,
    section[data-testid="stSidebar"] .stButton button span[translate="no"] {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        flex: 0 0 24px;
        border-radius: 7px;
        color: #667085 !important;
        font-size: 20px !important;
        line-height: 1 !important;
    }

    section[data-testid="stSidebar"] .stButton button p {
        color: var(--text) !important;
        font-size: .9rem;
        font-weight: 760;
        white-space: nowrap;
        margin: 0;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        background: #F2F4F7 !important;
        border-color: var(--border) !important;
        transform: none;
    }

    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: #FFF1F2 !important;
        border-color: #F5A3AA !important;
        border-left: 4px solid var(--accent) !important;
    }

    section[data-testid="stSidebar"] .stButton button[kind="primary"] p {
        color: #B4232E !important;
        font-weight: 850;
    }

    section[data-testid="stSidebar"] .stButton button[kind="primary"] [data-testid="stIconMaterial"],
    section[data-testid="stSidebar"] .stButton button[kind="primary"] .material-symbols-rounded,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] span[translate="no"] {
        color: #E63946 !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        min-height: 42px;
        background: transparent;
        border: 1px solid transparent;
        border-radius: var(--radius);
        padding: 9px 12px;
        transition: all .15s ease;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
    section[data-testid="stSidebar"] input[type="radio"] {
        display: none !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #F2F4F7;
        border-color: var(--border);
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #FFF1F2;
        border-color: #F5A3AA;
        box-shadow: none;
        border-left: 4px solid var(--accent);
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
        display: grid;
        place-items: center;
        width: 26px;
        height: 26px;
        flex: 0 0 26px;
        border-radius: 7px;
        background: #EEF2F6;
        color: #475467 !important;
        font-size: .74rem;
        font-weight: 850;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before {
        background: var(--accent);
        color: #FFFFFF !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(1)::before { content: "DG"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(2)::before { content: "DD"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(3)::before { content: "DM"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(4)::before { content: "CL"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(5)::before { content: "ES"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(6)::before { content: "NL"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(7)::before { content: "CX"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(8)::before { content: "DS"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(9)::before { content: "OS"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(10)::before { content: "US"; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(11)::before { content: "BK"; }

    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-weight: 760;
        font-size: .9rem;
    }

    .dash-hero {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: center;
        gap: 18px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        border-radius: var(--radius);
        padding: 20px 22px;
        margin-bottom: 18px;
        box-shadow: var(--shadow-soft);
        overflow: hidden;
    }

    .dash-hero-logo {
        width: 58px;
        height: 58px;
        object-fit: cover;
        border-radius: var(--radius);
        box-shadow: 0 10px 24px rgba(16, 24, 40, .12);
    }

    .dash-hero h1 {
        font-size: 1.75rem !important;
        line-height: 1.1;
        margin: 0 0 7px;
        color: var(--text) !important;
        font-weight: 880 !important;
    }

    .dash-hero p {
        color: var(--muted) !important;
        margin: 0;
        font-size: .98rem;
    }

    .dash-card {
        min-height: 130px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 3px solid var(--accent);
        border-radius: var(--radius);
        padding: 17px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: var(--shadow-soft);
    }

    .dash-card span {
        color: var(--muted) !important;
        font-size: .78rem;
        font-weight: 850;
        text-transform: uppercase;
    }

    .dash-card strong {
        color: var(--text) !important;
        font-size: 1.72rem;
        line-height: 1.08;
        font-weight: 880;
        margin-top: 12px;
        overflow-wrap: anywhere;
    }

    .dash-card small {
        color: var(--muted) !important;
        font-size: .86rem;
        margin-top: 6px;
        line-height: 1.35;
    }

    .empty-state {
        background: var(--surface);
        border: 1px dashed #CBD5E1;
        border-radius: var(--radius);
        padding: 22px;
        color: var(--muted) !important;
        text-align: center;
        font-weight: 700;
        box-shadow: var(--shadow-soft);
    }

    .section-panel,
    [data-testid="stForm"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 18px;
        box-shadow: var(--shadow-soft);
    }

    .section-panel {
        border-left: 4px solid var(--accent);
        margin: 10px 0 14px;
    }

    .section-panel h3 {
        margin: 0 0 4px;
        font-size: 1.16rem;
        font-weight: 850;
    }

    .section-panel p {
        margin: 0;
        color: var(--muted) !important;
        font-size: .9rem;
    }

    .client-search-list {
        margin: 8px 0 14px;
    }

    .client-search-title {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 8px 0 10px;
        padding: 12px 14px;
        background: #F8FAFC;
        border: 1px solid var(--border);
        border-radius: var(--radius);
    }

    .client-search-title .material-symbols-rounded {
        color: var(--accent) !important;
        font-size: 24px !important;
    }

    .client-search-title strong {
        display: block;
        color: var(--text) !important;
        font-size: .96rem;
        font-weight: 850;
    }

    .client-search-title small {
        display: block;
        color: var(--muted) !important;
        font-size: .82rem;
        margin-top: 2px;
    }

    .client-search-card {
        min-height: 72px;
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 12px 14px;
        box-shadow: var(--shadow-soft);
    }

    .client-search-card strong {
        display: block;
        color: var(--text) !important;
        font-size: .96rem;
        font-weight: 820;
    }

    .client-search-card span,
    .client-search-card small {
        display: block;
        color: var(--muted) !important;
        font-size: .84rem;
        margin-top: 3px;
    }

    .os-lookup-panel {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: center;
        gap: 16px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        border-radius: var(--radius);
        padding: 18px;
        margin: 0 0 12px;
        box-shadow: var(--shadow-soft);
    }

    .os-lookup-icon {
        width: 46px;
        height: 46px;
        display: grid;
        place-items: center;
        border-radius: var(--radius);
        background: #FFF1F2;
        border: 1px solid #FFE4E6;
        color: var(--accent) !important;
        font-size: .9rem;
        font-weight: 900;
        letter-spacing: 0;
    }

    .os-lookup-eyebrow {
        display: block;
        color: var(--muted) !important;
        font-size: .73rem;
        font-weight: 850;
        letter-spacing: .06em;
        text-transform: uppercase;
        margin-bottom: 3px;
    }

    .os-lookup-panel strong {
        display: block;
        color: var(--text) !important;
        font-size: 1.06rem;
        font-weight: 860;
    }

    .os-lookup-panel small {
        display: block;
        color: var(--muted) !important;
        font-size: .86rem;
        margin-top: 3px;
    }

    .os-lookup-client {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: 12px;
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        border-radius: var(--radius);
        padding: 13px 15px;
        margin: 14px 0 8px;
        box-shadow: var(--shadow-soft);
    }

    .os-lookup-client strong {
        display: block;
        color: var(--text) !important;
        font-size: .98rem;
        font-weight: 850;
    }

    .os-lookup-client span {
        display: block;
        color: var(--muted) !important;
        font-size: .86rem;
        margin-top: 3px;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        overflow: hidden;
        background: var(--surface);
        box-shadow: var(--shadow-soft);
    }

    [data-testid="stDataFrame"] [role="columnheader"] {
        background: #F2F4F7 !important;
        color: var(--text) !important;
        font-weight: 850;
    }

    [data-testid="stDataFrame"] [role="gridcell"] {
        background: #FFFFFF !important;
        color: var(--text) !important;
    }

    .stButton button,
    .stDownloadButton button,
    button[kind="primary"],
    button[kind="secondary"] {
        border-radius: var(--radius) !important;
        border: 1px solid #D0D5DD;
        min-height: 40px;
        font-weight: 780;
        transition: all .15s ease;
    }

    .stButton button:hover,
    .stDownloadButton button:hover {
        border-color: var(--accent);
        box-shadow: 0 10px 24px rgba(225, 29, 46, .12);
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent), #C92F3B) !important;
        border-color: #C92F3B !important;
        color: #FFFFFF !important;
    }

    button[kind="primary"] p {
        color: #FFFFFF !important;
    }

    input,
    textarea,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {
        border-radius: var(--radius) !important;
        border-color: #D0D5DD !important;
        background: #FFFFFF !important;
        color: var(--text) !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #98A2B3 !important;
    }

    .login-shell {
        max-width: 460px;
        margin: 8vh auto 18px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 4px solid var(--accent);
        border-radius: var(--radius);
        padding: 24px;
        box-shadow: var(--shadow);
        text-align: center;
    }

    .login-shell img {
        width: min(230px, 80%);
        border-radius: var(--radius);
        margin-bottom: 14px;
    }

    .login-shell strong {
        display: block;
        color: var(--text) !important;
        font-size: 1.7rem;
        font-weight: 880;
    }

    .login-shell span {
        display: block;
        color: var(--muted) !important;
        margin-top: 6px;
        font-size: .92rem;
    }

    .main .block-container:has(.login-shell) [data-testid="stForm"],
    .main .block-container:has(.login-shell) [data-testid="stExpander"] {
        max-width: 680px;
        margin-left: auto;
        margin-right: auto;
    }

    .os-card {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto auto;
        gap: 16px;
        align-items: center;
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 5px solid #94A3B8;
        border-radius: var(--radius);
        padding: 14px 16px;
        margin-bottom: 14px;
        box-shadow: var(--shadow-soft);
    }

    .os-card span {
        color: var(--muted) !important;
        font-size: .9rem;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        border: 1px solid;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: .8rem;
        font-weight: 850;
        white-space: nowrap;
    }

    .status-badge.muted {
        border-color: #CBD5E1;
        background: #F8FAFC;
        color: #667085 !important;
    }

    hr {
        border-color: var(--border);
    }

    @media (max-width: 900px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 4.25rem;
        }

        [data-testid="stHeader"] {
            height: 3.5rem !important;
        }

        [data-testid="collapsedControl"] {
            top: .6rem !important;
            left: .6rem !important;
        }

        [data-testid="collapsedControl"] button,
        [data-testid="stSidebarCollapseButton"] button {
            min-width: 44px !important;
            min-height: 44px !important;
        }

        .st-key-mobile_nav {
            display: block;
            margin-bottom: 1rem;
        }

        .st-key-mobile_nav details {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-soft);
            overflow: hidden;
        }

        .st-key-mobile_nav summary {
            min-height: 48px;
            padding: 12px 14px !important;
            font-weight: 850;
            color: var(--text) !important;
        }

        .st-key-mobile_nav [data-testid="stExpanderDetails"] {
            border-top: 1px solid var(--border);
            padding: 12px 14px 14px;
        }

        .st-key-mobile_nav div[role="radiogroup"] {
            gap: 7px;
        }

        .st-key-mobile_nav div[role="radiogroup"] label {
            min-height: 42px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: #FFFFFF;
            padding: 9px 11px;
        }

        .st-key-mobile_nav div[role="radiogroup"] label:has(input:checked) {
            border-color: rgba(230, 57, 70, .55);
            background: #FFF1F2;
        }

        .dash-hero,
        .os-card,
        .os-lookup-panel,
        .os-lookup-client {
            grid-template-columns: 1fr;
        }

        .dash-hero-logo {
            width: 62px;
            height: 62px;
        }
    }

    @media (max-width: 768px) {
        :root {
            --bg: #F8FAFC;
            --shadow: 0 10px 26px rgba(16, 24, 40, .06);
            --shadow-soft: 0 5px 16px rgba(16, 24, 40, .05);
        }

        html,
        body,
        .stApp {
            max-width: 100%;
            overflow-x: hidden !important;
        }

        .stApp {
            background:
                linear-gradient(rgba(248, 250, 252, .94), rgba(248, 250, 252, .96)),
                var(--bg);
        }

        .main .block-container {
            max-width: 100%;
            padding: 4.5rem .72rem 2rem !important;
        }

        section[data-testid="stSidebar"] {
            width: min(86vw, 330px) !important;
            min-width: min(86vw, 330px) !important;
            box-shadow: 12px 0 30px rgba(16, 24, 40, .12);
        }

        .st-key-mobile_nav {
            display: block !important;
            position: sticky;
            top: 3.55rem;
            z-index: 9999;
            margin: 0 0 .85rem;
        }

        .dash-hero {
            grid-template-columns: 1fr;
            gap: 10px;
            padding: 14px;
            margin-bottom: 12px;
            border-left-width: 3px;
        }

        .dash-hero h1 {
            font-size: 1.28rem !important;
            line-height: 1.18;
        }

        .dash-hero p {
            font-size: .84rem;
        }

        .dash-hero-logo {
            width: 50px;
            height: 50px;
        }

        .dash-card {
            min-height: auto;
            padding: 13px 14px;
            margin-bottom: 8px;
        }

        .dash-card strong {
            font-size: 1.34rem;
        }

        .section-panel,
        [data-testid="stForm"] {
            padding: 13px;
            box-shadow: var(--shadow-soft);
        }

        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: .5rem !important;
        }

        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 12px;
            box-shadow: var(--shadow-soft);
        }

        [data-testid="stDataFrame"] {
            max-width: 100% !important;
            overflow-x: auto !important;
            box-shadow: none;
        }

        [data-testid="stTable"] {
            max-width: 100% !important;
            overflow-x: auto !important;
        }

        .stButton button,
        .stDownloadButton button,
        button[kind="primary"],
        button[kind="secondary"] {
            width: 100% !important;
            min-height: 48px !important;
            padding: 10px 13px !important;
            font-size: .96rem !important;
        }

        input,
        textarea,
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {
            min-height: 46px;
            font-size: 16px !important;
        }

        textarea {
            min-height: 92px !important;
        }

        [data-testid="stExpander"] details {
            border-radius: var(--radius);
            overflow: hidden;
            background: var(--surface);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-soft);
        }

        [data-testid="stExpander"] summary {
            min-height: 48px;
            padding: 12px 13px !important;
            font-weight: 820;
        }

        [data-testid="stTabs"] button {
            min-height: 44px;
            padding: 8px 10px;
        }

        .os-lookup-panel,
        .os-lookup-client,
        .client-search-title,
        .client-search-card {
            grid-template-columns: 1fr;
            padding: 12px;
            margin-bottom: 9px;
        }

        .os-card {
            display: block;
            padding: 12px;
        }

        .status-badge {
            margin-top: 8px;
            white-space: normal;
        }

        img {
            max-width: 100%;
            height: auto;
        }

        canvas {
            max-width: 100% !important;
        }

        iframe {
            max-width: 100% !important;
        }

        h1 { font-size: 1.42rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.05rem !important; }

        .login-shell {
            margin: 5vh .25rem 1rem;
            padding: 18px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <style>
    :root {{
        --bg: #07110D;
        --bg-2: #0A1711;
        --surface: rgba(12, 24, 18, .78);
        --surface-2: rgba(16, 32, 24, .86);
        --sidebar: rgba(6, 15, 11, .96);
        --sidebar-2: rgba(12, 26, 19, .96);
        --text: #E5F7EF;
        --muted: #9CAFA6;
        --border: rgba(93, 255, 174, .16);
        --accent: #37F29A;
        --accent-2: #15B77A;
        --success: #37F29A;
        --warning: #D7B56D;
        --danger: #FF6B6B;
        --shadow: 0 22px 70px rgba(0, 0, 0, .42);
        --shadow-soft: 0 14px 38px rgba(0, 0, 0, .30);
        --radius: 10px;
    }}

    .stApp {{
        background:
            radial-gradient(circle at 18% 8%, rgba(55, 242, 154, .13), transparent 34rem),
            radial-gradient(circle at 88% 18%, rgba(21, 183, 122, .10), transparent 30rem),
            linear-gradient(135deg, #06100C 0%, #081A12 48%, #040907 100%) !important;
        color: var(--text) !important;
    }}

    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background-image: url("{logo_uri}");
        background-repeat: no-repeat;
        background-position: right 7vw top 13vh;
        background-size: min(48vw, 620px);
        opacity: .045;
        filter: grayscale(1) contrast(1.15);
        z-index: 0;
    }}

    .main .block-container {{
        position: relative;
        z-index: 1;
    }}

    [data-testid="stHeader"] {{
        background: rgba(5, 12, 9, .72) !important;
        border-bottom: 1px solid rgba(55, 242, 154, .10) !important;
        backdrop-filter: blur(16px);
    }}

    section[data-testid="stSidebar"] {{
        background:
            linear-gradient(180deg, var(--sidebar) 0%, var(--sidebar-2) 100%) !important;
        border-right: 1px solid rgba(55, 242, 154, .14) !important;
        box-shadow: 18px 0 48px rgba(0, 0, 0, .24);
    }}

    section[data-testid="stSidebar"] img {{
        box-shadow: 0 18px 36px rgba(0, 0, 0, .42) !important;
        border: 1px solid rgba(55, 242, 154, .18);
        background: rgba(255, 255, 255, .03);
    }}

    .stApp,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp div,
    section[data-testid="stSidebar"] * {{
        color: var(--text) !important;
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: var(--text) !important;
    }}

    .sidebar-brand,
    .sidebar-user,
    .mobile-user,
    .dash-hero,
    .dash-card,
    .section-panel,
    .empty-state,
    .client-search-title,
    .client-search-card,
    .os-lookup-panel,
    .os-lookup-client,
    [data-testid="stForm"],
    [data-testid="stExpander"] details,
    [data-testid="stMetric"],
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: linear-gradient(145deg, rgba(15, 31, 23, .82), rgba(8, 18, 13, .74)) !important;
        border: 1px solid rgba(55, 242, 154, .16) !important;
        box-shadow: var(--shadow-soft) !important;
        backdrop-filter: blur(16px);
    }}

    .dash-hero {{
        border-left: 4px solid var(--accent) !important;
        padding: 22px 24px;
    }}

    .dash-hero-logo {{
        background: rgba(255, 255, 255, .04);
        border: 1px solid rgba(55, 242, 154, .18);
    }}

    .dash-hero p,
    .dash-card span,
    .dash-card small,
    .section-panel p,
    .sidebar-brand p,
    .sidebar-user span,
    .sidebar-user small,
    .mobile-user span,
    .mobile-user small,
    .client-search-title small,
    .client-search-card span,
    .client-search-card small,
    .os-lookup-panel small,
    .os-lookup-client span,
    .nav-caption,
    .nav-group,
    .stCaptionContainer,
    small {{
        color: var(--muted) !important;
    }}

    .dash-card {{
        border-top: 1px solid rgba(55, 242, 154, .18) !important;
        border-left: 3px solid var(--accent) !important;
        min-height: 138px;
    }}

    .dash-card strong {{
        color: #F4FFF9 !important;
        text-shadow: 0 0 22px rgba(55, 242, 154, .10);
    }}

    .section-panel {{
        border-left: 4px solid var(--accent) !important;
    }}

    section[data-testid="stSidebar"] .stButton button,
    .st-key-mobile_nav div[role="radiogroup"] label {{
        background: rgba(255, 255, 255, .03) !important;
        border: 1px solid rgba(55, 242, 154, .10) !important;
    }}

    section[data-testid="stSidebar"] .stButton button:hover,
    .stButton button:hover,
    .stDownloadButton button:hover {{
        background: rgba(55, 242, 154, .08) !important;
        border-color: rgba(55, 242, 154, .42) !important;
        box-shadow: 0 12px 28px rgba(55, 242, 154, .10) !important;
    }}

    section[data-testid="stSidebar"] .stButton button[kind="primary"],
    button[kind="primary"] {{
        background: linear-gradient(135deg, #37F29A, #15B77A) !important;
        border-color: rgba(55, 242, 154, .65) !important;
        color: #04120B !important;
        box-shadow: 0 16px 34px rgba(55, 242, 154, .18) !important;
    }}

    button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] span {{
        color: #04120B !important;
    }}

    .stButton button,
    .stDownloadButton button,
    button[kind="secondary"] {{
        background: rgba(14, 30, 22, .86) !important;
        border: 1px solid rgba(55, 242, 154, .18) !important;
        color: var(--text) !important;
    }}

    input,
    textarea,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {{
        background: rgba(5, 12, 9, .82) !important;
        border-color: rgba(55, 242, 154, .18) !important;
        color: var(--text) !important;
    }}

    input::placeholder,
    textarea::placeholder {{
        color: rgba(229, 247, 239, .42) !important;
    }}

    [data-testid="stDataFrame"] [role="columnheader"] {{
        background: rgba(55, 242, 154, .10) !important;
        color: #F4FFF9 !important;
    }}

    [data-testid="stDataFrame"] [role="gridcell"] {{
        background: rgba(7, 17, 13, .92) !important;
        color: var(--text) !important;
        border-color: rgba(55, 242, 154, .08) !important;
    }}

    [data-testid="stExpander"] summary {{
        background: rgba(55, 242, 154, .04) !important;
    }}

    [data-testid="stTabs"] button {{
        color: var(--muted) !important;
    }}

    [data-testid="stTabs"] button[aria-selected="true"] {{
        color: var(--accent) !important;
        border-color: var(--accent) !important;
    }}

    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button,
    button[aria-label*="sidebar"],
    button[aria-label*="Sidebar"],
    button[title*="sidebar"],
    button[title*="Sidebar"],
    [data-testid="stBaseButton-header"],
    [data-testid="stBaseButton-headerNoPadding"] {{
        background: rgba(8, 18, 13, .92) !important;
        border-color: rgba(55, 242, 154, .22) !important;
        color: var(--text) !important;
    }}

    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    button[aria-label*="sidebar"] svg,
    button[aria-label*="Sidebar"] svg,
    button[title*="sidebar"] svg,
    button[title*="Sidebar"] svg {{
        stroke: var(--accent) !important;
        color: var(--accent) !important;
    }}

    .status-badge {{
        background: rgba(55, 242, 154, .08) !important;
        border-color: rgba(55, 242, 154, .28) !important;
        color: var(--accent) !important;
    }}

    hr {{
        border-color: rgba(55, 242, 154, .12) !important;
    }}

    @media (max-width: 768px) {{
        .stApp::before {{
            background-position: center 6rem;
            background-size: 92vw;
            opacity: .028;
        }}

        .main .block-container {{
            padding: 4.35rem .75rem 2rem !important;
        }}

        .dash-hero,
        .dash-card,
        .section-panel,
        [data-testid="stForm"],
        [data-testid="stExpander"] details {{
            border-radius: 10px !important;
        }}

        .dash-card {{
            min-height: auto;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <style>
    :root {{
        --tx-bg: #030806;
        --tx-panel: rgba(10, 22, 16, .58);
        --tx-panel-strong: rgba(13, 30, 22, .76);
        --tx-line: rgba(82, 255, 169, .18);
        --tx-line-strong: rgba(82, 255, 169, .34);
        --tx-glow: rgba(55, 242, 154, .22);
        --tx-text: #F2FFF8;
        --tx-muted: #9FB7AB;
        --tx-shadow: 0 24px 80px rgba(0, 0, 0, .48);
        --tx-shadow-soft: 0 14px 40px rgba(0, 0, 0, .34);
        --tx-radius: 18px;
    }}

    .stApp {{
        background:
            linear-gradient(115deg, rgba(3, 8, 6, .98), rgba(5, 18, 12, .97) 44%, rgba(1, 5, 4, .99)),
            repeating-linear-gradient(90deg, rgba(82, 255, 169, .035) 0 1px, transparent 1px 92px),
            repeating-linear-gradient(0deg, rgba(82, 255, 169, .026) 0 1px, transparent 1px 92px) !important;
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif !important;
    }}

    .stApp::before {{
        background-image:
            linear-gradient(90deg, rgba(3, 8, 6, .18), rgba(3, 8, 6, .62)),
            url("{logo_uri}");
        background-size: min(58vw, 760px);
        background-position: right -6vw top 6vh;
        opacity: .16;
        filter: saturate(.9) contrast(1.05);
        mask-image: linear-gradient(90deg, transparent 0%, rgba(0, 0, 0, .72) 42%, rgba(0, 0, 0, .18) 100%);
    }}

    .stApp::after {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(180deg, rgba(255,255,255,.028), transparent 22rem),
            repeating-linear-gradient(135deg, rgba(255,255,255,.022) 0 1px, transparent 1px 7px);
        opacity: .36;
        mix-blend-mode: screen;
        z-index: 0;
    }}

    .main .block-container {{
        max-width: 1480px;
        padding-top: 1.65rem;
    }}

    [data-testid="stHeader"] {{
        background: linear-gradient(180deg, rgba(2, 8, 5, .86), rgba(2, 8, 5, .42)) !important;
        border-bottom: 1px solid rgba(82, 255, 169, .08) !important;
    }}

    section[data-testid="stSidebar"] {{
        background:
            linear-gradient(180deg, rgba(3, 10, 7, .98), rgba(5, 18, 12, .96)),
            repeating-linear-gradient(0deg, rgba(82, 255, 169, .035) 0 1px, transparent 1px 48px) !important;
        border-right: 1px solid rgba(82, 255, 169, .16) !important;
        box-shadow: 24px 0 80px rgba(0, 0, 0, .42);
    }}

    section[data-testid="stSidebar"] > div {{
        padding: 20px 14px;
    }}

    section[data-testid="stSidebar"] img {{
        width: 164px !important;
        border-radius: 22px !important;
        padding: 8px;
        background:
            linear-gradient(145deg, rgba(82, 255, 169, .12), rgba(255,255,255,.03)) !important;
        border: 1px solid rgba(82, 255, 169, .22) !important;
        box-shadow: 0 22px 50px rgba(0,0,0,.46), 0 0 42px rgba(55,242,154,.10) !important;
    }}

    .sidebar-brand {{
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        padding: 2px 4px 14px;
    }}

    .sidebar-brand h2 {{
        font-size: 1.06rem !important;
        letter-spacing: .02em;
    }}

    .sidebar-user,
    .mobile-user {{
        border-radius: 16px !important;
        background: linear-gradient(145deg, rgba(14, 33, 24, .72), rgba(8, 18, 13, .52)) !important;
        border: 1px solid rgba(82, 255, 169, .16) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 14px 34px rgba(0,0,0,.28) !important;
    }}

    section[data-testid="stSidebar"] .stButton button {{
        min-height: 46px;
        border-radius: 14px !important;
        background: rgba(255,255,255,.026) !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        transition: transform .18s ease, border-color .18s ease, background .18s ease, box-shadow .18s ease;
    }}

    section[data-testid="stSidebar"] .stButton button:hover {{
        transform: translateX(3px);
        background: rgba(82, 255, 169, .075) !important;
        border-color: rgba(82, 255, 169, .22) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.05), 0 12px 30px rgba(0,0,0,.22) !important;
    }}

    section[data-testid="stSidebar"] .stButton button[kind="primary"] {{
        background:
            linear-gradient(135deg, rgba(55,242,154,.98), rgba(20,183,122,.88)) !important;
        color: #03110B !important;
        border-color: rgba(180,255,218,.44) !important;
        box-shadow: 0 16px 38px rgba(55,242,154,.18), inset 0 1px 0 rgba(255,255,255,.35) !important;
    }}

    .dash-hero {{
        position: relative;
        min-height: 168px;
        align-items: end;
        grid-template-columns: 88px minmax(0, 1fr);
        border-radius: 24px !important;
        border: 1px solid rgba(82, 255, 169, .20) !important;
        background:
            linear-gradient(135deg, rgba(16, 38, 27, .76), rgba(4, 13, 9, .70)),
            linear-gradient(90deg, rgba(82, 255, 169, .10), transparent 48%) !important;
        box-shadow: var(--tx-shadow), inset 0 1px 0 rgba(255,255,255,.08) !important;
        overflow: hidden;
        padding: 24px 28px !important;
    }}

    .dash-hero::before {{
        content: "";
        position: absolute;
        inset: 1px;
        border-radius: 23px;
        background:
            linear-gradient(120deg, rgba(255,255,255,.10), transparent 28%),
            repeating-linear-gradient(90deg, rgba(82,255,169,.038) 0 1px, transparent 1px 54px);
        pointer-events: none;
    }}

    .dash-hero-mark {{
        position: absolute;
        right: 24px;
        top: 10px;
        color: rgba(82, 255, 169, .055) !important;
        font-size: clamp(4rem, 10vw, 8.2rem);
        line-height: 1;
        font-weight: 950;
        letter-spacing: .03em;
        pointer-events: none;
    }}

    .dash-hero-logo {{
        width: 72px;
        height: 72px;
        border-radius: 18px !important;
        padding: 4px;
        background: rgba(255,255,255,.04) !important;
        border: 1px solid rgba(82,255,169,.24) !important;
        box-shadow: 0 20px 44px rgba(0,0,0,.40), 0 0 28px rgba(55,242,154,.10) !important;
        z-index: 1;
    }}

    .dash-hero > div:not(.dash-hero-mark) {{
        z-index: 1;
    }}

    .dash-hero-kicker {{
        display: inline-flex;
        margin-bottom: 8px;
        color: #7DFFC0 !important;
        font-size: .72rem;
        font-weight: 850;
        letter-spacing: .12em;
        text-transform: uppercase;
    }}

    .dash-hero h1 {{
        font-size: clamp(1.8rem, 3vw, 2.6rem) !important;
        line-height: 1.04;
        font-weight: 900 !important;
        letter-spacing: 0;
    }}

    .dash-hero p {{
        max-width: 760px;
        font-size: .98rem;
        color: rgba(229,247,239,.72) !important;
    }}

    .dash-card,
    .section-panel,
    [data-testid="stForm"],
    [data-testid="stExpander"] details,
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        position: relative;
        border-radius: var(--tx-radius) !important;
        background:
            linear-gradient(145deg, rgba(16, 38, 27, .62), rgba(6, 15, 10, .52)) !important;
        border: 1px solid rgba(82, 255, 169, .15) !important;
        box-shadow: var(--tx-shadow-soft), inset 0 1px 0 rgba(255,255,255,.06) !important;
        backdrop-filter: blur(22px) saturate(1.2);
    }}

    .dash-card {{
        min-height: 150px;
        padding: 18px 18px 17px;
        overflow: hidden;
        border-left: 0 !important;
        border-top: 0 !important;
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }}

    .dash-card::before {{
        content: "";
        position: absolute;
        inset: 0;
        border-top: 1px solid color-mix(in srgb, var(--card-accent, #37F29A) 70%, transparent);
        background:
            linear-gradient(110deg, color-mix(in srgb, var(--card-accent, #37F29A) 14%, transparent), transparent 34%),
            linear-gradient(180deg, rgba(255,255,255,.06), transparent 42%);
        opacity: .86;
        pointer-events: none;
    }}

    .dash-card:hover {{
        transform: translateY(-2px);
        border-color: color-mix(in srgb, var(--card-accent, #37F29A) 34%, transparent) !important;
        box-shadow: 0 22px 58px rgba(0,0,0,.42), 0 0 34px color-mix(in srgb, var(--card-accent, #37F29A) 16%, transparent) !important;
    }}

    .dash-card-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: relative;
        z-index: 1;
    }}

    .dash-card-top i {{
        width: 9px;
        height: 9px;
        border-radius: 999px;
        background: var(--card-accent, #37F29A);
        box-shadow: 0 0 18px var(--card-accent, #37F29A);
    }}

    .dash-card span {{
        color: rgba(229,247,239,.62) !important;
        font-size: .72rem;
        letter-spacing: .11em;
    }}

    .dash-card strong {{
        position: relative;
        z-index: 1;
        font-size: clamp(1.58rem, 2.4vw, 2.05rem);
        margin-top: 18px;
    }}

    .dash-card small {{
        position: relative;
        z-index: 1;
        color: rgba(229,247,239,.58) !important;
    }}

    .section-panel {{
        padding: 18px 20px;
        border-left: 1px solid rgba(82,255,169,.16) !important;
    }}

    [data-testid="stPlotlyChart"] {{
        border-radius: 20px;
        overflow: hidden;
        background: linear-gradient(145deg, rgba(16, 38, 27, .38), rgba(4, 13, 9, .34));
        border: 1px solid rgba(82,255,169,.10);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 16px 38px rgba(0,0,0,.28);
        padding: 8px;
    }}

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {{
        border-radius: 18px !important;
        overflow: hidden;
    }}

    [data-testid="stDataFrame"] [role="columnheader"] {{
        background: rgba(82,255,169,.095) !important;
        border-color: rgba(82,255,169,.08) !important;
    }}

    [data-testid="stDataFrame"] [role="gridcell"] {{
        background: rgba(5,13,9,.70) !important;
    }}

    .stButton button,
    .stDownloadButton button,
    button[kind="secondary"] {{
        border-radius: 14px !important;
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
    }}

    .stButton button:hover,
    .stDownloadButton button:hover {{
        transform: translateY(-1px);
    }}

    input,
    textarea,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {{
        border-radius: 14px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
    }}

    [data-testid="stExpander"] summary {{
        border-radius: 17px !important;
        background: linear-gradient(90deg, rgba(82,255,169,.065), rgba(255,255,255,.015)) !important;
        transition: background .18s ease;
    }}

    [data-testid="stExpander"] summary:hover {{
        background: linear-gradient(90deg, rgba(82,255,169,.10), rgba(255,255,255,.025)) !important;
    }}

    @media (max-width: 768px) {{
        .stApp::before {{
            background-size: 135vw;
            background-position: center 5.2rem;
            opacity: .09;
            mask-image: linear-gradient(180deg, rgba(0,0,0,.55), transparent 74%);
        }}

        .stApp::after {{
            opacity: .24;
        }}

        .main .block-container {{
            padding: 4.25rem .78rem 2rem !important;
        }}

        .dash-hero {{
            min-height: 150px;
            grid-template-columns: 56px minmax(0, 1fr);
            padding: 18px !important;
            border-radius: 20px !important;
        }}

        .dash-hero-logo {{
            width: 54px;
            height: 54px;
            border-radius: 15px !important;
        }}

        .dash-hero-mark {{
            font-size: 5rem;
            right: 12px;
            top: 18px;
        }}

        .dash-hero-kicker {{
            font-size: .62rem;
            letter-spacing: .08em;
        }}

        .dash-card {{
            min-height: 126px;
            padding: 16px;
            border-radius: 18px !important;
        }}

        section[data-testid="stSidebar"] {{
            width: min(88vw, 340px) !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <style>
    :root {{
        --bg: #F6F7F9;
        --bg-2: #FFFFFF;
        --surface: #FFFFFF;
        --surface-2: #F9FAFB;
        --sidebar: #FFFFFF;
        --sidebar-2: #F8FAFC;
        --text: #111827;
        --muted: #6B7280;
        --border: #E5E7EB;
        --accent: #E63946;
        --accent-2: #16A34A;
        --success: #16A34A;
        --warning: #D97706;
        --danger: #DC2626;
        --shadow: 0 18px 50px rgba(17, 24, 39, .08);
        --shadow-soft: 0 10px 30px rgba(17, 24, 39, .06);
        --radius: 12px;
    }}

    .stApp {{
        background: linear-gradient(180deg, #FFFFFF 0%, #F6F7F9 45%, #F3F4F6 100%) !important;
        color: var(--text) !important;
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif !important;
    }}

    .stApp::before,
    .stApp::after {{
        display: none !important;
        content: none !important;
    }}

    [data-testid="stHeader"] {{
        background: rgba(255, 255, 255, .92) !important;
        border-bottom: 1px solid #E5E7EB !important;
        backdrop-filter: blur(14px);
    }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
        border-right: 1px solid #E5E7EB !important;
        box-shadow: 12px 0 32px rgba(17, 24, 39, .05) !important;
    }}

    .stApp,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp div,
    section[data-testid="stSidebar"] * {{
        color: var(--text) !important;
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: var(--text) !important;
    }}

    section[data-testid="stSidebar"] img,
    .dash-hero-logo {{
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: 0 14px 30px rgba(17, 24, 39, .10) !important;
    }}

    .sidebar-brand,
    .sidebar-user,
    .mobile-user,
    .dash-hero,
    .dash-card,
    .section-panel,
    .empty-state,
    .client-search-title,
    .client-search-card,
    .os-lookup-panel,
    .os-lookup-client,
    [data-testid="stForm"],
    [data-testid="stExpander"] details,
    [data-testid="stMetric"],
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: var(--shadow-soft) !important;
        backdrop-filter: none !important;
    }}

    .dash-hero {{
        min-height: auto !important;
        grid-template-columns: auto minmax(0, 1fr) !important;
        border-left: 4px solid var(--accent) !important;
        border-radius: 14px !important;
        padding: 20px 22px !important;
        overflow: hidden;
    }}

    .dash-hero::before,
    .dash-hero-mark {{
        display: none !important;
    }}

    .dash-hero-kicker {{
        color: var(--accent-2) !important;
        font-size: .72rem;
        font-weight: 850;
        letter-spacing: .08em;
        text-transform: uppercase;
    }}

    .dash-hero p,
    .dash-card span,
    .dash-card small,
    .section-panel p,
    .sidebar-brand p,
    .sidebar-user span,
    .sidebar-user small,
    .mobile-user span,
    .mobile-user small,
    .client-search-title small,
    .client-search-card span,
    .client-search-card small,
    .os-lookup-panel small,
    .os-lookup-client span,
    .nav-caption,
    .nav-group,
    .stCaptionContainer,
    small {{
        color: var(--muted) !important;
    }}

    .dash-card {{
        border-radius: 14px !important;
        border-top: 3px solid var(--card-accent, var(--accent)) !important;
        border-left: 1px solid #E5E7EB !important;
        min-height: 132px;
        transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    }}

    .dash-card::before {{
        display: none !important;
    }}

    .dash-card:hover {{
        transform: translateY(-1px);
        border-color: #D1D5DB !important;
        box-shadow: 0 16px 36px rgba(17, 24, 39, .10) !important;
    }}

    .dash-card strong {{
        color: #111827 !important;
        text-shadow: none !important;
    }}

    .dash-card-top i {{
        background: var(--card-accent, var(--accent)) !important;
        box-shadow: none !important;
    }}

    .section-panel {{
        border-left: 4px solid var(--accent-2) !important;
    }}

    section[data-testid="stSidebar"] .stButton button,
    .stButton button,
    .stDownloadButton button,
    button[kind="secondary"] {{
        background: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        color: var(--text) !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }}

    section[data-testid="stSidebar"] .stButton button:hover,
    .stButton button:hover,
    .stDownloadButton button:hover {{
        background: #F9FAFB !important;
        border-color: var(--accent) !important;
        box-shadow: 0 10px 24px rgba(230, 57, 70, .10) !important;
        transform: none !important;
    }}

    section[data-testid="stSidebar"] .stButton button[kind="primary"],
    button[kind="primary"] {{
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #FFFFFF !important;
        box-shadow: 0 12px 24px rgba(230, 57, 70, .18) !important;
    }}

    button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] span {{
        color: #FFFFFF !important;
    }}

    input,
    textarea,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {{
        background: #FFFFFF !important;
        border-color: #D1D5DB !important;
        color: var(--text) !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }}

    input::placeholder,
    textarea::placeholder {{
        color: #9CA3AF !important;
    }}

    [data-testid="stPlotlyChart"] {{
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: var(--shadow-soft) !important;
    }}

    [data-testid="stDataFrame"] [role="columnheader"] {{
        background: #F3F4F6 !important;
        color: #111827 !important;
        border-color: #E5E7EB !important;
    }}

    [data-testid="stDataFrame"] [role="gridcell"] {{
        background: #FFFFFF !important;
        color: #111827 !important;
        border-color: #F3F4F6 !important;
    }}

    [data-testid="stExpander"] summary {{
        background: #FFFFFF !important;
        color: #111827 !important;
    }}

    [data-testid="stExpander"] summary:hover {{
        background: #F9FAFB !important;
    }}

    .status-badge {{
        background: #F0FDF4 !important;
        border-color: #BBF7D0 !important;
        color: #166534 !important;
    }}

    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button,
    button[aria-label*="sidebar"],
    button[aria-label*="Sidebar"],
    button[title*="sidebar"],
    button[title*="Sidebar"],
    [data-testid="stBaseButton-header"],
    [data-testid="stBaseButton-headerNoPadding"] {{
        background: #FFFFFF !important;
        border-color: #D1D5DB !important;
        color: #111827 !important;
    }}

    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    button[aria-label*="sidebar"] svg,
    button[aria-label*="Sidebar"] svg,
    button[title*="sidebar"] svg,
    button[title*="Sidebar"] svg {{
        stroke: #111827 !important;
        color: #111827 !important;
    }}

    hr {{
        border-color: #E5E7EB !important;
    }}

    @media (max-width: 768px) {{
        .main .block-container {{
            padding: 4.35rem .75rem 2rem !important;
        }}

        .dash-hero {{
            grid-template-columns: 56px minmax(0, 1fr) !important;
            padding: 16px !important;
        }}

        .dash-card {{
            min-height: auto;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <style>
    :root {{
        --bg: #050607;
        --bg-2: #0B0D0F;
        --surface: rgba(18, 20, 22, .74);
        --surface-2: rgba(24, 27, 30, .82);
        --sidebar: rgba(5, 6, 7, .98);
        --sidebar-2: rgba(13, 15, 17, .96);
        --text: #F4F7F5;
        --muted: #A4AAA7;
        --border: rgba(255, 255, 255, .09);
        --tx-panel: rgba(18, 20, 22, .64);
        --tx-panel-strong: rgba(24, 27, 30, .78);
        --tx-line: rgba(255, 255, 255, .09);
        --tx-line-strong: rgba(55, 242, 154, .16);
        --tx-glow: rgba(55, 242, 154, .08);
    }}

    .stApp {{
        background:
            radial-gradient(circle at 10% 0%, rgba(255, 255, 255, .055), transparent 30rem),
            radial-gradient(circle at 92% 8%, rgba(55, 242, 154, .028), transparent 28rem),
            linear-gradient(115deg, #050607 0%, #0B0D0F 46%, #030404 100%) !important;
    }}

    .stApp::before {{
        background-image:
            linear-gradient(90deg, rgba(5, 6, 7, .24), rgba(5, 6, 7, .80)),
            url("{logo_uri}") !important;
        background-size: min(48vw, 660px) !important;
        background-position: right -8vw top 9vh !important;
        opacity: .048 !important;
        filter: grayscale(.3) saturate(.48) contrast(1.08) !important;
        mask-image: linear-gradient(90deg, transparent 0%, rgba(0, 0, 0, .42) 46%, rgba(0, 0, 0, .07) 100%) !important;
    }}

    .stApp::after {{
        background:
            linear-gradient(180deg, rgba(255,255,255,.03), transparent 17rem),
            repeating-linear-gradient(135deg, rgba(255,255,255,.012) 0 1px, transparent 1px 10px) !important;
        opacity: .22 !important;
    }}

    [data-testid="stHeader"] {{
        background: linear-gradient(180deg, rgba(5, 6, 7, .88), rgba(5, 6, 7, .44)) !important;
        border-bottom-color: rgba(255, 255, 255, .07) !important;
    }}

    section[data-testid="stSidebar"] {{
        background:
            linear-gradient(180deg, rgba(5, 6, 7, .98), rgba(13, 15, 17, .96)),
            repeating-linear-gradient(0deg, rgba(255, 255, 255, .016) 0 1px, transparent 1px 54px) !important;
        border-right-color: rgba(255, 255, 255, .085) !important;
    }}

    section[data-testid="stSidebar"] img {{
        background: linear-gradient(145deg, rgba(255,255,255,.055), rgba(255,255,255,.018)) !important;
        border-color: rgba(255, 255, 255, .12) !important;
        box-shadow: 0 22px 50px rgba(0,0,0,.46), 0 0 18px rgba(55,242,154,.04) !important;
    }}

    .sidebar-user,
    .mobile-user,
    .dash-hero,
    .dash-card,
    .section-panel,
    .empty-state,
    .client-search-title,
    .client-search-card,
    .os-lookup-panel,
    .os-lookup-client,
    [data-testid="stForm"],
    [data-testid="stExpander"] details,
    [data-testid="stMetric"],
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: linear-gradient(145deg, rgba(24, 27, 30, .66), rgba(8, 9, 11, .58)) !important;
        border-color: rgba(255, 255, 255, .09) !important;
        box-shadow: 0 18px 52px rgba(0, 0, 0, .38), inset 0 1px 0 rgba(255,255,255,.055) !important;
    }}

    section[data-testid="stSidebar"] .stButton button:hover {{
        background: rgba(255, 255, 255, .055) !important;
        border-color: rgba(55, 242, 154, .16) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.05), 0 12px 30px rgba(0,0,0,.22) !important;
    }}

    section[data-testid="stSidebar"] .stButton button[kind="primary"],
    button[kind="primary"] {{
        background: linear-gradient(135deg, rgba(55,242,154,.88), rgba(34,197,94,.78)) !important;
        border-color: rgba(180,255,218,.28) !important;
        box-shadow: 0 14px 30px rgba(55,242,154,.10), inset 0 1px 0 rgba(255,255,255,.28) !important;
    }}

    .dash-hero {{
        border-color: rgba(255, 255, 255, .10) !important;
        background:
            linear-gradient(135deg, rgba(24, 27, 30, .74), rgba(7, 8, 10, .72)),
            linear-gradient(90deg, rgba(55, 242, 154, .026), transparent 48%) !important;
    }}

    .dash-hero::before {{
        background:
            linear-gradient(120deg, rgba(255,255,255,.08), transparent 30%),
            repeating-linear-gradient(90deg, rgba(255,255,255,.016) 0 1px, transparent 1px 58px) !important;
    }}

    .dash-hero-mark {{
        color: rgba(255, 255, 255, .04) !important;
    }}

    .dash-hero-logo {{
        border-color: rgba(255,255,255,.12) !important;
        box-shadow: 0 20px 44px rgba(0,0,0,.40), 0 0 16px rgba(55,242,154,.035) !important;
    }}

    .dash-hero-kicker {{
        color: #8FEABD !important;
    }}

    .dash-card::before {{
        border-top-color: color-mix(in srgb, var(--card-accent, #37F29A) 24%, transparent) !important;
        background:
            linear-gradient(110deg, color-mix(in srgb, var(--card-accent, #37F29A) 4%, transparent), transparent 34%),
            linear-gradient(180deg, rgba(255,255,255,.05), transparent 42%) !important;
        opacity: .68 !important;
    }}

    .dash-card:hover {{
        border-color: color-mix(in srgb, var(--card-accent, #37F29A) 18%, rgba(255,255,255,.08)) !important;
        box-shadow: 0 22px 58px rgba(0,0,0,.44), 0 0 18px color-mix(in srgb, var(--card-accent, #37F29A) 5%, transparent) !important;
    }}

    .dash-card-top i {{
        box-shadow: 0 0 9px color-mix(in srgb, var(--card-accent, #37F29A) 42%, transparent) !important;
    }}

    [data-testid="stPlotlyChart"] {{
        background: linear-gradient(145deg, rgba(24, 27, 30, .42), rgba(6, 7, 8, .36)) !important;
        border-color: rgba(255,255,255,.07) !important;
    }}

    [data-testid="stDataFrame"] [role="columnheader"] {{
        background: rgba(255,255,255,.055) !important;
        border-color: rgba(255,255,255,.06) !important;
    }}

    [data-testid="stDataFrame"] [role="gridcell"] {{
        background: rgba(7,8,10,.74) !important;
    }}

    [data-testid="stExpander"] summary {{
        background: linear-gradient(90deg, rgba(255,255,255,.045), rgba(255,255,255,.014)) !important;
    }}

    [data-testid="stExpander"] summary:hover {{
        background: linear-gradient(90deg, rgba(255,255,255,.065), rgba(55,242,154,.025)) !important;
    }}

    @media (max-width: 768px) {{
        .stApp::before {{
            opacity: .034 !important;
            background-size: 130vw !important;
            mask-image: linear-gradient(180deg, rgba(0,0,0,.34), transparent 72%) !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    :root {
        --bg: #F6F7F9;
        --surface: #FFFFFF;
        --surface-2: #F9FAFB;
        --sidebar: #FFFFFF;
        --sidebar-2: #F8FAFC;
        --text: #111827;
        --muted: #6B7280;
        --border: #E5E7EB;
        --accent: #E63946;
        --accent-2: #16A34A;
        --success: #16A34A;
        --shadow: 0 18px 50px rgba(17, 24, 39, .08);
        --shadow-soft: 0 10px 30px rgba(17, 24, 39, .06);
    }

    .stApp {
        background: linear-gradient(180deg, #FFFFFF 0%, #F6F7F9 55%, #F3F4F6 100%) !important;
        color: var(--text) !important;
    }

    .stApp::before,
    .stApp::after,
    .dash-hero::before,
    .dash-hero-mark,
    .dash-card::before {
        display: none !important;
        content: none !important;
    }

    [data-testid="stHeader"] {
        background: rgba(255, 255, 255, .94) !important;
        border-bottom: 1px solid #E5E7EB !important;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
        border-right: 1px solid #E5E7EB !important;
        box-shadow: 12px 0 32px rgba(17, 24, 39, .05) !important;
    }

    .stApp,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp div,
    section[data-testid="stSidebar"] * {
        color: var(--text) !important;
    }

    .dash-hero,
    .dash-card,
    .section-panel,
    .empty-state,
    .client-search-title,
    .client-search-card,
    .os-lookup-panel,
    .os-lookup-client,
    .sidebar-user,
    .mobile-user,
    [data-testid="stForm"],
    [data-testid="stExpander"] details,
    [data-testid="stMetric"],
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: var(--shadow-soft) !important;
        backdrop-filter: none !important;
    }

    section[data-testid="stSidebar"] img,
    .dash-hero-logo {
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: 0 14px 30px rgba(17, 24, 39, .10) !important;
    }

    .dash-hero {
        min-height: auto !important;
        grid-template-columns: auto minmax(0, 1fr) !important;
        border-left: 4px solid var(--accent) !important;
        border-radius: 14px !important;
        padding: 20px 22px !important;
    }

    .dash-hero-kicker {
        color: var(--accent-2) !important;
    }

    .dash-hero p,
    .dash-card span,
    .dash-card small,
    .section-panel p,
    .sidebar-brand p,
    .sidebar-user span,
    .sidebar-user small,
    .mobile-user span,
    .mobile-user small,
    .client-search-title small,
    .client-search-card span,
    .client-search-card small,
    .os-lookup-panel small,
    .os-lookup-client span,
    .nav-caption,
    .nav-group,
    small {
        color: var(--muted) !important;
    }

    .dash-card {
        border-radius: 14px !important;
        border-top: 3px solid var(--card-accent, var(--accent)) !important;
        min-height: 132px;
    }

    .dash-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 16px 36px rgba(17, 24, 39, .10) !important;
    }

    .dash-card strong {
        color: #111827 !important;
        text-shadow: none !important;
    }

    .dash-card-top i {
        background: var(--card-accent, var(--accent)) !important;
        box-shadow: none !important;
    }

    .daily-goal-card {
        width: 100%;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 5px solid var(--goal-accent, var(--accent-2));
        border-radius: 16px;
        padding: 22px 24px;
        box-shadow: var(--shadow-soft);
        margin: 0 0 4px;
    }

    .tx-light-header {
        align-items: center;
        background:
            linear-gradient(135deg, rgba(255, 255, 255, .98), rgba(248, 250, 252, .96)),
            radial-gradient(circle at 100% 0%, rgba(22, 163, 74, .08), transparent 36%);
        border: 1px solid #E5E7EB;
        border-left: 5px solid var(--accent-2);
        border-radius: 16px;
        box-shadow: var(--shadow-soft);
        display: flex;
        gap: 14px;
        margin: 0 0 1rem;
        padding: 18px 20px;
    }

    .tx-light-header-icon {
        align-items: center;
        background: #111827;
        border: 1px solid rgba(22, 163, 74, .32);
        border-radius: 14px;
        box-shadow: 0 10px 24px rgba(17, 24, 39, .12);
        color: #FFFFFF !important;
        display: flex;
        flex: 0 0 52px;
        font-size: 1.55rem;
        height: 52px;
        justify-content: center;
        line-height: 1;
        width: 52px;
    }

    .tx-light-header span {
        color: var(--accent-2) !important;
        display: block;
        font-size: .72rem;
        font-weight: 900;
        letter-spacing: .08em;
        margin-bottom: 3px;
        text-transform: uppercase;
    }

    .tx-light-header h1 {
        color: var(--text) !important;
        font-size: clamp(1.35rem, 3vw, 1.9rem);
        font-weight: 950;
        letter-spacing: 0;
        line-height: 1.08;
        margin: 0 0 4px;
    }

    .tx-light-header p {
        color: var(--muted) !important;
        font-size: .96rem;
        font-weight: 650;
        line-height: 1.35;
        margin: 0;
    }

    .daily-goal-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
    }

    .daily-goal-head span {
        color: var(--muted) !important;
        font-size: .82rem;
        font-weight: 800;
        letter-spacing: .04em;
        text-transform: uppercase;
    }

    .daily-goal-head strong {
        color: var(--goal-accent, var(--accent-2)) !important;
        font-size: .95rem;
        font-weight: 900;
    }

    .daily-goal-value {
        color: var(--text) !important;
        font-size: clamp(1.8rem, 4vw, 2.7rem);
        line-height: 1;
        font-weight: 900;
        letter-spacing: 0;
        margin-bottom: 8px;
    }

    .daily-goal-value small {
        color: var(--muted) !important;
        font-size: clamp(.95rem, 2vw, 1.15rem);
        font-weight: 800;
    }

    .daily-goal-card p {
        color: var(--text) !important;
        font-size: 1rem;
        font-weight: 700;
        margin: 0 0 16px;
    }

    .daily-goal-track {
        height: 13px;
        overflow: hidden;
        border-radius: 999px;
        background: #EEF2F7;
        border: 1px solid #E5E7EB;
    }

    .daily-goal-track i {
        display: block;
        width: var(--goal-progress, 0%);
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--goal-accent, var(--accent-2)), #22C55E);
        box-shadow: 0 0 18px rgba(22, 163, 74, .18);
    }

    .tx-mix-card,
    .manager-alert-card,
    .ranking-card,
    .company-status-card,
    .os-status-grid,
    .sangria-summary-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        box-shadow: var(--shadow-soft);
        padding: 18px;
        width: 100%;
    }

    .tx-mix-card > strong,
    .manager-alert-card span,
    .os-status-grid > strong,
    .sangria-summary-card span {
        color: var(--text) !important;
        display: block;
        font-size: 1rem;
        font-weight: 900;
        margin-bottom: 10px;
    }

    .tx-mix-card p {
        color: var(--text) !important;
        font-size: 1.05rem;
        font-weight: 800;
        margin: 8px 0;
    }

    .tx-mix-row {
        display: grid;
        gap: 8px;
        margin-top: 14px;
    }

    .tx-mix-row div:first-child {
        align-items: center;
        display: flex;
        justify-content: space-between;
        gap: 12px;
    }

    .tx-mix-row strong {
        color: var(--text) !important;
        font-weight: 900;
    }

    .tx-mix-row span {
        color: var(--muted) !important;
        font-size: .9rem;
        font-weight: 800;
    }

    .tx-mix-track {
        background: #EEF2F7;
        border: 1px solid #E5E7EB;
        border-radius: 999px;
        height: 13px;
        overflow: hidden;
    }

    .tx-mix-track i {
        display: block;
        height: 100%;
        border-radius: inherit;
    }

    .manager-alert-card {
        border-left: 5px solid #E63946;
    }

    .company-status-card {
        align-items: stretch;
        border-left: 6px solid var(--status-accent, var(--accent-2));
        display: grid;
        gap: 18px;
        grid-template-columns: minmax(240px, .8fr) 1.2fr;
        margin-bottom: 14px;
    }

    .company-status-card span {
        color: var(--muted) !important;
        display: block;
        font-size: .82rem;
        font-weight: 900;
        letter-spacing: .04em;
        margin-bottom: 8px;
        text-transform: uppercase;
    }

    .company-status-card strong {
        color: var(--text) !important;
        display: block;
        font-size: clamp(1.55rem, 4vw, 2.25rem);
        font-weight: 950;
        letter-spacing: 0;
        line-height: 1.05;
        margin-bottom: 8px;
    }

    .company-status-card p,
    .sangria-summary-card p,
    .sangria-summary-card small {
        color: var(--muted) !important;
        margin: 0;
    }

    .manager-alert-card strong {
        color: var(--muted) !important;
        display: block;
        font-size: .9rem;
        margin-bottom: 12px;
    }

    .manager-alert-card ul,
    .company-status-card ul {
        display: grid;
        gap: 8px;
        list-style: none;
        margin: 0;
        padding: 0;
    }

    .manager-alert-card li,
    .company-status-card li {
        background: #F8FAFC;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        color: var(--text) !important;
        font-weight: 700;
        padding: 10px 12px;
    }

    .ranking-card {
        display: grid;
        gap: 10px;
    }

    .ranking-row {
        align-items: center;
        background: #F8FAFC;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        display: grid;
        gap: 10px;
        grid-template-columns: auto 1fr auto;
        padding: 12px 14px;
    }

    .ranking-row strong {
        color: var(--text) !important;
        font-weight: 900;
    }

    .ranking-row em {
        color: var(--accent-2) !important;
        font-style: normal;
        font-weight: 900;
    }

    .ranking-row span {
        color: var(--muted) !important;
        display: block;
        font-size: .82rem;
        font-weight: 750;
        margin-top: 2px;
    }

    .payment-value-grid {
        display: grid;
        gap: 10px;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-top: 12px;
    }

    .payment-value-grid div {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-top: 3px solid var(--pay-accent, var(--accent-2));
        border-radius: 12px;
        box-shadow: 0 10px 28px rgba(17, 24, 39, .06);
        padding: 12px;
    }

    .payment-value-grid span {
        color: var(--muted) !important;
        display: block;
        font-size: .78rem;
        font-weight: 900;
        text-transform: uppercase;
    }

    .payment-value-grid strong {
        color: var(--text) !important;
        display: block;
        font-size: 1.05rem;
        font-weight: 950;
        margin-top: 4px;
    }

    .os-status-grid {
        display: grid;
        gap: 10px;
    }

    .os-status-grid div {
        align-items: center;
        background: #F8FAFC;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        display: flex;
        justify-content: space-between;
        padding: 12px 14px;
    }

    .os-status-grid span {
        color: var(--muted) !important;
        font-weight: 850;
    }

    .os-status-grid b {
        color: var(--accent-2) !important;
        font-size: 1.15rem;
        font-weight: 950;
    }

    .sangria-summary-card {
        border-left: 5px solid #F59E0B;
        min-height: 100%;
    }

    .sangria-summary-card strong {
        color: var(--text) !important;
        display: block;
        font-size: clamp(1.55rem, 4vw, 2.2rem);
        font-weight: 950;
        line-height: 1;
        margin: 8px 0;
    }

    .sangria-summary-card small {
        display: block;
        font-weight: 800;
        margin-top: 12px;
    }

    .section-panel {
        border-left: 4px solid var(--accent-2) !important;
    }

    .tx-page-banner,
    .tx-dashboard-banner {
        width: 100%;
        margin: 0 0 1rem;
        aspect-ratio: 2.5 / 1;
        overflow: hidden;
        border-radius: 18px;
        border: 1px solid rgba(17, 24, 39, .10);
        background: #050706;
        box-shadow: 0 18px 42px rgba(17, 24, 39, .13);
    }

    .tx-page-banner img,
    .tx-dashboard-banner img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: 50% 50%;
    }

    .stButton button,
    .stDownloadButton button,
    button[kind="secondary"],
    section[data-testid="stSidebar"] .stButton button {
        background: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        color: var(--text) !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }

    .stButton button:hover,
    .stDownloadButton button:hover,
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #F9FAFB !important;
        border-color: var(--accent) !important;
        box-shadow: 0 10px 24px rgba(230, 57, 70, .10) !important;
        transform: none !important;
    }

    button[kind="primary"],
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #FFFFFF !important;
        box-shadow: 0 12px 24px rgba(230, 57, 70, .18) !important;
    }

    button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] span {
        color: #FFFFFF !important;
    }

    input,
    textarea,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {
        background: #FFFFFF !important;
        border-color: #D1D5DB !important;
        color: var(--text) !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }

    [data-testid="stPlotlyChart"] {
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: var(--shadow-soft) !important;
    }

    [data-testid="stDataFrame"] [role="columnheader"] {
        background: #F3F4F6 !important;
        color: #111827 !important;
        border-color: #E5E7EB !important;
    }

    [data-testid="stDataFrame"] [role="gridcell"] {
        background: #FFFFFF !important;
        color: #111827 !important;
        border-color: #F3F4F6 !important;
    }

    [data-testid="stExpander"] summary {
        background: #FFFFFF !important;
        color: #111827 !important;
    }

    [data-testid="stExpander"] summary:hover {
        background: #F9FAFB !important;
    }

    .status-badge {
        background: #F0FDF4 !important;
        border-color: #BBF7D0 !important;
        color: #166534 !important;
    }

    hr {
        border-color: #E5E7EB !important;
    }

    @media (max-width: 768px) {
        .tx-page-banner,
        .tx-dashboard-banner {
            margin-bottom: .9rem;
            aspect-ratio: 2.5 / 1;
            border-radius: 14px;
            box-shadow: 0 14px 30px rgba(17, 24, 39, .13);
        }

        .daily-goal-card {
            padding: 18px;
            border-radius: 14px;
        }

        .tx-light-header {
            align-items: flex-start;
            border-radius: 14px;
            gap: 12px;
            padding: 15px;
        }

        .tx-light-header-icon {
            border-radius: 12px;
            flex-basis: 46px;
            font-size: 1.32rem;
            height: 46px;
            width: 46px;
        }

        .daily-goal-head {
            align-items: flex-start;
            flex-direction: column;
            gap: 6px;
        }

        .tx-mix-card,
        .manager-alert-card,
        .ranking-card,
        .company-status-card,
        .os-status-grid,
        .sangria-summary-card {
            border-radius: 14px;
            padding: 15px;
        }

        .company-status-card {
            grid-template-columns: 1fr;
        }

        .payment-value-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .tx-mix-row div:first-child,
        .ranking-row {
            align-items: flex-start;
        }

        .ranking-row {
            grid-template-columns: auto 1fr;
        }

        .ranking-row em {
            grid-column: 2;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .stApp:has(.tx-login-page) {
        background:
            radial-gradient(circle at 12% 12%, rgba(22, 163, 74, .08), transparent 24rem),
            linear-gradient(135deg, #FFFFFF 0%, #F7F9FC 48%, #EEF2F7 100%) !important;
    }

    .stApp:has(.tx-login-page) [data-testid="stHeader"],
    .stApp:has(.tx-login-page) section[data-testid="stSidebar"],
    .stApp:has(.tx-login-page) [data-testid="collapsedControl"],
    .stApp:has(.tx-login-page) #MainMenu,
    .stApp:has(.tx-login-page) footer {
        display: none !important;
    }

    .main .block-container:has(.tx-login-page) {
        max-width: 1180px !important;
        min-height: 100dvh;
        padding: 2.4rem 1.35rem !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .main .block-container:has(.tx-login-page) [data-testid="stHorizontalBlock"] {
        align-items: stretch;
        gap: clamp(1.2rem, 3vw, 2.4rem);
    }

    .main .block-container:has(.tx-login-page) [data-testid="column"]:has(.tx-login-art),
    .main .block-container:has(.tx-login-page) [data-testid="column"]:has(.tx-login-brand) {
        min-height: min(720px, calc(100dvh - 5rem));
    }

    .tx-login-art {
        position: relative;
        height: auto;
        min-height: 0;
        aspect-ratio: 3 / 2;
        padding: 10px;
        overflow: hidden;
        border-radius: 28px;
        background:
            linear-gradient(145deg, rgba(255, 255, 255, .96), rgba(244, 247, 250, .88)),
            #FFFFFF;
        border: 1px solid rgba(17, 24, 39, .08);
        box-shadow: 0 26px 70px rgba(17, 24, 39, .16);
    }

    .tx-login-art::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        border-radius: inherit;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .52), inset 0 -80px 110px rgba(0, 0, 0, .24);
    }

    .tx-login-art img {
        display: block;
        width: 100%;
        height: 100%;
        min-height: 0;
        object-fit: cover;
        object-position: 50% 50%;
        border-radius: 22px;
        filter: saturate(1.02) contrast(1.02);
    }

    .tx-login-art-fallback {
        display: grid;
        place-items: center;
        text-align: center;
        color: #FFFFFF !important;
        background: linear-gradient(145deg, #101514, #0B0F0D);
    }

    .tx-login-art-fallback strong {
        color: #53D56C !important;
        font-size: clamp(4rem, 12vw, 8rem);
        line-height: 1;
    }

    .tx-login-art-fallback span {
        color: rgba(255, 255, 255, .72) !important;
    }

    .main .block-container:has(.tx-login-page) [data-testid="column"]:has(.tx-login-brand) {
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: clamp(1.2rem, 3vw, 2.35rem);
        border: 1px solid rgba(17, 24, 39, .08);
        border-radius: 28px;
        background: rgba(255, 255, 255, .88) !important;
        box-shadow: 0 24px 70px rgba(17, 24, 39, .12);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
    }

    .tx-login-brand {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: center;
        gap: 16px;
        margin-bottom: 1.15rem;
    }

    .tx-login-brand img {
        width: 76px;
        height: 76px;
        object-fit: cover;
        border-radius: 20px;
        background: #050706;
        box-shadow: 0 16px 32px rgba(17, 24, 39, .18), 0 0 0 1px rgba(22, 163, 74, .16);
    }

    .tx-login-brand strong {
        display: grid;
        place-items: center;
        width: 76px;
        height: 76px;
        border-radius: 20px;
        color: #53D56C !important;
        background: #050706;
        font-size: 1.4rem;
        font-weight: 900;
    }

    .tx-login-brand h1 {
        margin: 0 !important;
        color: #101828 !important;
        font-size: clamp(2rem, 4vw, 2.65rem) !important;
        font-weight: 850 !important;
        line-height: 1.02 !important;
        letter-spacing: 0 !important;
    }

    .tx-login-brand p {
        margin: .42rem 0 0 !important;
        color: #667085 !important;
        font-size: 1rem !important;
        line-height: 1.45 !important;
    }

    .main .block-container:has(.tx-login-page) [data-testid="stForm"] {
        margin-top: .65rem;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    .main .block-container:has(.tx-login-page) label,
    .main .block-container:has(.tx-login-page) label p {
        color: #344054 !important;
        font-weight: 720 !important;
    }

    .main .block-container:has(.tx-login-page) input,
    .main .block-container:has(.tx-login-page) [data-baseweb="input"] > div {
        min-height: 50px !important;
        border-radius: 14px !important;
        border: 1px solid #D0D5DD !important;
        background: #FFFFFF !important;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .04) !important;
    }

    .main .block-container:has(.tx-login-page) input:focus,
    .main .block-container:has(.tx-login-page) [data-baseweb="input"] > div:focus-within {
        border-color: #16A34A !important;
        box-shadow: 0 0 0 4px rgba(22, 163, 74, .10) !important;
    }

    .main .block-container:has(.tx-login-page) .stButton button,
    .main .block-container:has(.tx-login-page) button[kind="primary"] {
        min-height: 52px !important;
        margin-top: .55rem;
        border: 0 !important;
        border-radius: 14px !important;
        background: linear-gradient(135deg, #22C55E, #15803D) !important;
        color: #FFFFFF !important;
        box-shadow: 0 16px 34px rgba(22, 163, 74, .24) !important;
        font-weight: 820 !important;
    }

    .main .block-container:has(.tx-login-page) .stButton button:hover,
    .main .block-container:has(.tx-login-page) button[kind="primary"]:hover {
        filter: brightness(1.02);
        transform: translateY(-1px);
        box-shadow: 0 20px 38px rgba(22, 163, 74, .28) !important;
    }

    .main .block-container:has(.tx-login-page) button[kind="primary"] p {
        color: #FFFFFF !important;
    }

    .main .block-container:has(.tx-login-page) [data-testid="stExpander"] details {
        margin-top: 1rem;
        border: 1px solid #E5E7EB !important;
        border-radius: 14px !important;
        background: #FFFFFF !important;
        box-shadow: none !important;
        overflow: hidden;
    }

    .main .block-container:has(.tx-login-page) [data-testid="stExpander"] summary {
        background: #FFFFFF !important;
        color: #344054 !important;
        font-weight: 720;
    }

    .main .block-container:has(.tx-login-page) [data-testid="stExpander"] summary:hover {
        background: #F9FAFB !important;
    }

    @media (max-width: 768px) {
        .main .block-container:has(.tx-login-page) {
            min-height: 100dvh;
            padding: 1rem .8rem 1.4rem !important;
            justify-content: flex-start;
        }

        .main .block-container:has(.tx-login-page) [data-testid="stHorizontalBlock"] {
            gap: .9rem;
        }

        .main .block-container:has(.tx-login-page) [data-testid="column"]:has(.tx-login-art),
        .main .block-container:has(.tx-login-page) [data-testid="column"]:has(.tx-login-brand) {
            min-height: auto;
            width: 100% !important;
        }

        .tx-login-art {
            min-height: auto;
            height: clamp(172px, 42vw, 230px);
            padding: 6px;
            border-radius: 22px;
            box-shadow: 0 16px 38px rgba(17, 24, 39, .14);
        }

        .tx-login-art img {
            min-height: 0;
            height: 100%;
            border-radius: 17px;
        }

        .main .block-container:has(.tx-login-page) [data-testid="column"]:has(.tx-login-brand) {
            padding: 1.2rem;
            border-radius: 22px;
            box-shadow: 0 16px 38px rgba(17, 24, 39, .11);
        }

        .tx-login-brand {
            grid-template-columns: 58px minmax(0, 1fr);
            gap: 12px;
            margin-bottom: .8rem;
        }

        .tx-login-brand img,
        .tx-login-brand strong {
            width: 58px;
            height: 58px;
            border-radius: 16px;
        }

        .tx-login-brand h1 {
            font-size: 1.8rem !important;
        }

        .tx-login-brand p {
            font-size: .92rem !important;
        }

        .main .block-container:has(.tx-login-page) input,
        .main .block-container:has(.tx-login-page) [data-baseweb="input"] > div,
        .main .block-container:has(.tx-login-page) .stButton button,
        .main .block-container:has(.tx-login-page) button[kind="primary"] {
            min-height: 54px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    components.html(
        """
        <script>
        (function () {
            const doc = window.parent.document;
            const head = doc.head || doc.getElementsByTagName("head")[0];

            function upsertMeta(name, content) {
                let el = head.querySelector(`meta[name="${name}"]`);
                if (!el) {
                    el = doc.createElement("meta");
                    el.setAttribute("name", name);
                    head.appendChild(el);
                }
                el.setAttribute("content", content);
            }

            const version = "tx-brand-v6";
            const staticBase = `${window.parent.location.origin}/app/static`;
            const manifestUrl = `${staticBase}/manifest.json?v=${version}`;
            const faviconUrl = `${staticBase}/favicon.png?v=${version}`;
            const faviconIcoUrl = `${staticBase}/favicon.ico?v=${version}`;
            const appleIconUrl = `${staticBase}/apple-touch-icon.png?v=${version}`;
            const appleIconRawUrl = `${staticBase}/apple-touch-icon.png`;
            const applePrecomposedUrl = `${staticBase}/apple-touch-icon-precomposed.png?v=${version}`;
            const applePrecomposedRawUrl = `${staticBase}/apple-touch-icon-precomposed.png`;

            function removeLinks(selector) {
                head.querySelectorAll(selector).forEach((el) => el.remove());
            }

            function appendLink(rel, href, extra) {
                const el = doc.createElement("link");
                el.setAttribute("rel", rel);
                el.setAttribute("href", href);
                Object.entries(extra || {}).forEach(([key, value]) => el.setAttribute(key, value));
                head.appendChild(el);
            }

            upsertMeta("viewport", "width=device-width, initial-scale=1, viewport-fit=cover");
            upsertMeta("theme-color", "#ffffff");
            upsertMeta("apple-mobile-web-app-capable", "yes");
            upsertMeta("apple-mobile-web-app-status-bar-style", "default");
            upsertMeta("apple-mobile-web-app-title", "TX System");

            doc.title = "TX System";

            removeLinks('link[rel="manifest"]');
            removeLinks('link[rel="icon"]');
            removeLinks('link[rel="shortcut icon"]');
            removeLinks('link[rel="apple-touch-icon"]');
            removeLinks('link[rel="apple-touch-icon-precomposed"]');
            removeLinks('link[href*="favicon"]');
            removeLinks('link[href*="favicon.ico"]');
            removeLinks('link[href*="apple-touch-icon"]');

            appendLink("manifest", manifestUrl);
            appendLink("manifest", `${staticBase}/manifest.json`);
            appendLink("icon", faviconUrl, { type: "image/png", sizes: "64x64" });
            appendLink("icon", `${staticBase}/favicon.png`, { type: "image/png", sizes: "64x64" });
            appendLink("icon", faviconIcoUrl);
            appendLink("icon", `${staticBase}/favicon.ico`);
            appendLink("shortcut icon", faviconUrl, { type: "image/png", sizes: "64x64" });
            appendLink("shortcut icon", `${staticBase}/favicon.png`, { type: "image/png", sizes: "64x64" });
            appendLink("shortcut icon", faviconIcoUrl);
            appendLink("shortcut icon", `${staticBase}/favicon.ico`);
            appendLink("apple-touch-icon", appleIconUrl, { sizes: "180x180" });
            appendLink("apple-touch-icon", appleIconRawUrl, { sizes: "180x180" });
            appendLink("apple-touch-icon-precomposed", applePrecomposedUrl, { sizes: "180x180" });
            appendLink("apple-touch-icon-precomposed", applePrecomposedRawUrl, { sizes: "180x180" });

            if ("serviceWorker" in window.parent.navigator) {
                window.parent.navigator.serviceWorker.getRegistrations().then(function (registrations) {
                    registrations.forEach(function (registration) {
                        if (registration.active && registration.active.scriptURL.includes("/app/static/service-worker.js")) {
                            registration.unregister();
                        }
                    });
                }).finally(function () {
                    window.parent.navigator.serviceWorker.register(`${staticBase}/service-worker.js?v=${version}`).catch(function () {});
                });
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )
