import re

import streamlit as st


def _slug(value):
    return re.sub(r"[^a-z0-9_]+", "-", str(value or "").strip().lower()).strip("-") or "card"


def tx_card(
    title,
    value,
    detail="",
    key="tx_card",
    icon="",
    accent="green",
    state_key="tx_open_card",
):
    """Render a clickable TX card and return True when its inline details should load."""
    st.session_state.setdefault(state_key, None)
    is_open = st.session_state.get(state_key) == key
    arrow = "▲" if is_open else "▼"
    accent_slug = _slug(accent)
    key_slug = _slug(key)

    def _toggle():
        st.session_state[state_key] = None if st.session_state.get(state_key) == key else key

    st.markdown(
        (
            f"<span class='tx-click-card-marker tx-card-accent-{accent_slug} "
            f"tx-card-{key_slug}'></span>"
        ),
        unsafe_allow_html=True,
    )
    label_icon = f"{icon} " if icon else ""
    st.button(
        f"{label_icon}{title}  {arrow}\n{value}\n{detail}",
        key=f"{state_key}_{key_slug}",
        on_click=_toggle,
        width="stretch",
    )
    return is_open
