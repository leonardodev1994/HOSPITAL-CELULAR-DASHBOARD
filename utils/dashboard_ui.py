import base64
from pathlib import Path

import plotly.express as px
import streamlit as st


CHART_COLORS = ["#E63946", "#16A34A", "#2563EB", "#F59E0B", "#64748B", "#0EA5E9"]
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"


def moeda(valor):
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def page_header(title, subtitle):
    logo_html = ""
    if LOGO_PATH.exists():
        logo_base64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        logo_html = f'<img class="dash-hero-logo" src="data:image/png;base64,{logo_base64}" alt="Hospital do Celular" />'

    st.markdown(
        f"""
        <div class="dash-hero">
            <div class="dash-hero-mark">TX</div>
            {logo_html}
            <div>
                <span class="dash-hero-kicker">Tecnologia urbana para gestão inteligente</span>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, detail="", accent="#E11D2E"):
    st.markdown(
        f"""
        <div class="dash-card" style="--card-accent:{accent};">
            <div class="dash-card-top">
                <span>{label}</span>
                <i></i>
            </div>
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


def _is_money_field(field):
    field = str(field or "").lower()
    return any(term in field for term in ["valor", "faturamento", "receita", "lucro", "total"])


def _format_chart_value(value, money=False):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return value or "-"

    if money:
        return moeda(number)

    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")

    return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def apply_plot_style(fig, height=360):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#111827",
        margin=dict(l=20, r=20, t=55, b=20),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#4B5563"),
        ),
        title=dict(font=dict(size=18, color="#111827")),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#E5E7EB",
            font=dict(color="#111827", size=13, family="Inter, sans-serif"),
            align="left",
        ),
    )
    fig.update_xaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB", tickfont=dict(color="#6B7280"))
    fig.update_yaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB", tickfont=dict(color="#6B7280"))
    fig.update_traces(marker_line_width=0, hoverlabel_namelength=-1)
    return fig


def bar_chart(df, x, y, title, color=None):
    df_plot = df.copy()
    value_axis = x if _is_money_field(x) else y
    category_axis = y if value_axis == x else x
    is_money = _is_money_field(value_axis)
    df_plot["_hover_value"] = df_plot[value_axis].map(lambda value: _format_chart_value(value, is_money))

    fig = px.bar(
        df_plot,
        x=x,
        y=y,
        color=color,
        template="plotly_white",
        title=title,
        color_discrete_sequence=CHART_COLORS,
        custom_data=["_hover_value"],
    )
    if value_axis == y:
        fig.update_traces(
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"{value_axis.title()}: <b>%{{customdata[0]}}</b>"
                "<extra></extra>"
            )
        )
    else:
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{value_axis.title()}: <b>%{{customdata[0]}}</b>"
                "<extra></extra>"
            )
        )
    return apply_plot_style(fig)


def pie_chart(df, names, values, title):
    df_plot = df.copy()
    is_money = _is_money_field(values)
    df_plot["_hover_value"] = df_plot[values].map(lambda value: _format_chart_value(value, is_money))

    fig = px.pie(
        df_plot,
        names=names,
        values=values,
        hole=0.58,
        template="plotly_white",
        title=title,
        color_discrete_sequence=CHART_COLORS,
        custom_data=["_hover_value"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Valor: <b>%{customdata[0]}</b><br>"
            "Participação: <b>%{percent}</b>"
            "<extra></extra>"
        ),
        textinfo="percent+label",
        textposition="inside",
    )
    return apply_plot_style(fig)
