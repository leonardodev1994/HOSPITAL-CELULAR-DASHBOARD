import streamlit as st


def apply_style():
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

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    #MainMenu,
    footer {
        visibility: hidden;
        height: 0;
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
    </style>
    """, unsafe_allow_html=True)
