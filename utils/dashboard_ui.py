import plotly.express as px
import streamlit as st


CHART_COLORS = ["#5B8DEF", "#18C29C", "#F59E0B", "#EF4444", "#A855F7", "#06B6D4"]


def moeda(valor):
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def page_header(title, subtitle):
    st.markdown(
        f"""
        <div class="dash-hero">
            <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, detail="", accent="#5B8DEF"):
    st.markdown(
        f"""
        <div class="dash-card" style="border-top-color:{accent};">
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(message):
    st.markdown(
        f"<div class='empty-state'>{message}</div>",
        unsafe_allow_html=True,
    )


def apply_plot_style(fig, height=360):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#F8FAFC",
        margin=dict(l=20, r=20, t=55, b=20),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E1"),
        ),
        title=dict(font=dict(size=18, color="#F8FAFC")),
    )
    fig.update_xaxes(gridcolor="#243041", zerolinecolor="#243041")
    fig.update_yaxes(gridcolor="#243041", zerolinecolor="#243041")
    return fig


def bar_chart(df, x, y, title, color=None):
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        template="plotly_dark",
        title=title,
        color_discrete_sequence=CHART_COLORS,
    )
    return apply_plot_style(fig)


def pie_chart(df, names, values, title):
    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.58,
        template="plotly_dark",
        title=title,
        color_discrete_sequence=CHART_COLORS,
    )
    return apply_plot_style(fig)
