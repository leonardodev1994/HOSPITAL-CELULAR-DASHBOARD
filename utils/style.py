import streamlit as st


def apply_style():
    st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: white;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    section[data-testid="stSidebar"] {
        background-color: #161B22;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 24px;
    }

    [data-testid="metric-container"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        padding: 20px;
        border-radius: 8px;
    }

    .dash-hero {
        background: linear-gradient(135deg, #151B25 0%, #1D2633 55%, #111827 100%);
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 26px 28px;
        margin-bottom: 18px;
    }

    .dash-hero h1 {
        font-size: 2rem;
        line-height: 1.1;
        margin: 0 0 8px 0;
        font-weight: 850;
        letter-spacing: 0;
    }

    .dash-hero p {
        color: #AAB6C5 !important;
        margin: 0;
        font-size: 1rem;
    }

    .dash-card {
        min-height: 132px;
        background-color: #161B22;
        border: 1px solid #30363D;
        border-top: 4px solid #5B8DEF;
        border-radius: 8px;
        padding: 18px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .dash-card span {
        color: #AAB6C5;
        font-size: 0.88rem;
        font-weight: 750;
        text-transform: uppercase;
    }

    .dash-card strong {
        color: #F8FAFC;
        font-size: 1.8rem;
        line-height: 1.05;
        font-weight: 850;
    }

    .dash-card small {
        color: #7D8A9B;
        font-size: 0.86rem;
    }

    .empty-state {
        background-color: #161B22;
        border: 1px dashed #3B4554;
        border-radius: 8px;
        padding: 22px;
        color: #AAB6C5;
        text-align: center;
        font-weight: 650;
    }

    .section-panel {
        background-color: #121821;
        border: 1px solid #30363D;
        border-left: 5px solid #5B8DEF;
        border-radius: 8px;
        padding: 16px 18px;
        margin: 10px 0 14px 0;
    }

    .section-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
    }

    .section-panel h3 {
        margin: 0 0 4px 0;
        font-size: 1.25rem;
        font-weight: 850;
        letter-spacing: 0;
    }

    .section-panel p {
        margin: 0;
        color: #AAB6C5 !important;
        font-size: 0.92rem;
    }

    h1, h2, h3, h4, h5, h6, p, label {
        color: white !important;
    }

    .stButton button {
        background-color: #E63946;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }

    section[data-testid="stSidebar"] .stButton button {
        width: 100%;
        background-color: #E63946;
        border: 1px solid #E63946;
    }

    .stButton button:hover {
        background-color: #f0525f;
        color: white;
        border: none;
    }

    .stTextInput input,
    .stNumberInput input {
        background-color: #1E242D;
        color: white;
        border-radius: 8px;
    }

    div[data-baseweb="select"] > div {
        background-color: #1E242D;
        color: white;
        border-radius: 8px;
    }

    div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    div[role="radiogroup"] label {
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 9px 10px;
        margin: 0;
        transition: background-color 0.15s ease, border-color 0.15s ease;
    }

    div[role="radiogroup"] label:hover {
        background-color: #1E242D;
        border-color: #30363D;
    }

    div[role="radiogroup"] label:has(input:checked) {
        background-color: #2A303A;
        border-color: #E63946;
    }

    div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        font-weight: 700;
        font-size: 0.93rem;
    }

    [data-testid="stForm"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 24px;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #30363D;
        border-radius: 8px;
        overflow: hidden;
    }

    .os-card {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto auto;
        gap: 16px;
        align-items: center;
        background-color: #161B22;
        border: 1px solid #30363D;
        border-left: 6px solid #94A3B8;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 14px;
    }

    .os-card span {
        color: #C9D1D9;
        font-size: 0.9rem;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        border: 1px solid;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 0.82rem;
        font-weight: 800;
        white-space: nowrap;
    }
    </style>
    """, unsafe_allow_html=True)
