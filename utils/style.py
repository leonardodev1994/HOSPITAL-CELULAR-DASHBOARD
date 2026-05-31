import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"


def _logo_data_uri():
    if not LOGO_PATH.exists():
        return ""
    return f"data:image/png;base64,{base64.b64encode(LOGO_PATH.read_bytes()).decode('utf-8')}"


def apply_style():
    logo_uri = _logo_data_uri()
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

            function upsertLink(rel, href, extra) {
                let el = head.querySelector(`link[rel="${rel}"][href="${href}"]`);
                if (!el) {
                    el = doc.createElement("link");
                    el.setAttribute("rel", rel);
                    el.setAttribute("href", href);
                    head.appendChild(el);
                }
                Object.entries(extra || {}).forEach(([key, value]) => el.setAttribute(key, value));
            }

            upsertMeta("viewport", "width=device-width, initial-scale=1, viewport-fit=cover");
            upsertMeta("theme-color", "#37F29A");
            upsertMeta("apple-mobile-web-app-capable", "yes");
            upsertMeta("apple-mobile-web-app-status-bar-style", "default");
            upsertMeta("apple-mobile-web-app-title", "Hospital do Celular");

            upsertLink("manifest", "/app/static/manifest.json");
            upsertLink("apple-touch-icon", "/app/static/icon-192.png", { sizes: "192x192" });

            if ("serviceWorker" in window.parent.navigator) {
                window.parent.navigator.serviceWorker.register("/app/static/service-worker.js").catch(function () {});
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )
