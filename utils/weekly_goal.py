from datetime import date, timedelta
from html import escape
from textwrap import dedent

import pandas as pd
import streamlit as st

from utils.dashboard_ui import moeda
from utils.quiosques import selected_quiosque_id


WEEKLY_GOAL_SETTINGS = {
    "daily_goal": 1000.0,
    "daily_bonus": 25.0,
    "working_days": (0, 1, 2, 3, 4, 5),
}

DAY_LABELS = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
}

STATUS_META = {
    "hit": {
        "badge": "✅ Bateu",
        "class": "is-hit",
        "accent": "#16A34A",
    },
    "miss": {
        "badge": "❌ Não bateu",
        "class": "is-miss",
        "accent": "#E63946",
    },
    "open": {
        "badge": "⚪ Ainda não fechou",
        "class": "is-open",
        "accent": "#94A3B8",
    },
}


def _week_bounds(reference_day):
    start = reference_day - timedelta(days=reference_day.weekday())
    end = start + timedelta(days=6)
    return start, end


@st.cache_data(ttl=120, show_spinner=False)
def _weekly_revenue_rows(_conn, week_start_iso, week_end_iso, quiosque_id):
    query = """
    SELECT
        l.data AS data,
        COALESCE(SUM(l.valor), 0) AS faturamento
    FROM lancamentos l
    WHERE l.data >= ?
      AND l.data <= ?
      AND COALESCE(l.status, 'Ativo') <> 'Cancelado'
    """
    params = [week_start_iso, week_end_iso]

    if int(quiosque_id) > 0:
        query += " AND l.quiosque_id = ?"
        params.append(int(quiosque_id))

    query += """
    GROUP BY l.data
    ORDER BY l.data ASC
    """
    return pd.read_sql_query(query, _conn, params=tuple(params))


def get_weekly_goal_snapshot(conn, reference_day=None, settings=None):
    config = dict(WEEKLY_GOAL_SETTINGS)
    if settings:
        config.update(settings)

    today = date.today()
    reference_day = reference_day or today
    week_start, _week_end = _week_bounds(reference_day)
    week_end = week_start + timedelta(days=max(config["working_days"]))
    quiosque_id = int(selected_quiosque_id())

    df = _weekly_revenue_rows(conn, week_start.isoformat(), week_end.isoformat(), quiosque_id)
    revenue_map = {str(row.data): float(row.faturamento or 0) for row in df.itertuples()}

    rows = []
    completed_days = 0
    hit_days = 0
    miss_days = 0

    for weekday in config["working_days"]:
        current_day = week_start + timedelta(days=weekday)
        faturamento = float(revenue_map.get(current_day.isoformat(), 0) or 0)

        if current_day >= today:
            status_key = "open"
        elif faturamento >= float(config["daily_goal"]):
            status_key = "hit"
            completed_days += 1
            hit_days += 1
        else:
            status_key = "miss"
            completed_days += 1
            miss_days += 1

        status_meta = STATUS_META[status_key]
        rows.append(
            {
                "date": current_day,
                "label": DAY_LABELS.get(current_day.weekday(), current_day.strftime("%A")),
                "faturamento": faturamento,
                "meta": float(config["daily_goal"]),
                "status_key": status_key,
                "status_label": status_meta["badge"],
                "status_class": status_meta["class"],
                "accent": status_meta["accent"],
            }
        )

    total_days = len(config["working_days"])
    open_days = total_days - completed_days
    bonus_total = hit_days * float(config["daily_bonus"])
    remaining_hit_days = max(0, total_days - hit_days)
    progress_pct = int(round((hit_days / total_days) * 100)) if total_days else 0

    return {
        "rows": rows,
        "total_days": total_days,
        "completed_days": completed_days,
        "open_days": open_days,
        "hit_days": hit_days,
        "miss_days": miss_days,
        "bonus_total": bonus_total,
        "remaining_hit_days": remaining_hit_days,
        "remaining_bonus": remaining_hit_days * float(config["daily_bonus"]),
        "progress_pct": progress_pct,
        "week_start": week_start,
        "week_end": week_end,
        "daily_goal": float(config["daily_goal"]),
        "daily_bonus": float(config["daily_bonus"]),
        "quiosque_id": quiosque_id,
    }


def render_weekly_goal_block(conn, title="🏆 Meta Semanal", settings=None):
    snapshot = get_weekly_goal_snapshot(conn, settings=settings)
    cards = []

    for row in snapshot["rows"]:
        cards.append(
            dedent(f"""
            <div class="weekly-goal-day-card {row['status_class']}">
                <div class="weekly-goal-day-top">
                    <strong>{escape(row['label'])}</strong>
                    <span>{escape(row['status_label'])}</span>
                </div>
                <div class="weekly-goal-day-value">{moeda(row['faturamento'])}</div>
                <small>Meta do dia: {moeda(row['meta'])}</small>
            </div>
            """).strip()
        )

    summary_items = [
        ("Dias trabalhados", f"{snapshot['completed_days']}/{snapshot['total_days']}"),
        ("Meta batida", f"{snapshot['hit_days']}/{snapshot['total_days']}"),
        ("Nao bateram", str(snapshot["miss_days"])),
        ("Bonus acumulado", moeda(snapshot["bonus_total"])),
    ]
    summary_html = "".join(
        dedent(f"""
        <div class="weekly-goal-summary-item">
            <span>{escape(label)}</span>
            <strong>{escape(value)}</strong>
        </div>
        """).strip()
        for label, value in summary_items
    )

    perfect_week_text = f"Semana perfeita: faltam {snapshot['remaining_hit_days']} dia(s) de meta batida"
    if snapshot["remaining_hit_days"] == 0:
        perfect_week_text = "Semana perfeita concluida"

    st.markdown(
        dedent(f"""
        <div class="weekly-goal-card">
            <div class="weekly-goal-header">
                <div>
                    <span>{escape(title)}</span>
                    <strong>Semana atual de {snapshot['week_start'].strftime('%d/%m')} a {snapshot['week_end'].strftime('%d/%m')}</strong>
                </div>
                <em>Bonus por dia: {moeda(snapshot['daily_bonus'])}</em>
            </div>
            <div class="weekly-goal-progress">
                <div class="weekly-goal-progress-head">
                    <span>Dias com meta batida: {snapshot['hit_days']}/{snapshot['total_days']}</span>
                    <strong>{snapshot['progress_pct']}%</strong>
                </div>
                <div class="weekly-goal-track"><i style="width:{snapshot['progress_pct']}%;"></i></div>
                <p>{escape(perfect_week_text)}{f" • Bonus restante: {moeda(snapshot['remaining_bonus'])}" if snapshot['remaining_hit_days'] else ''}</p>
            </div>
            <div class="weekly-goal-days">{''.join(cards)}</div>
            <div class="weekly-goal-summary">{summary_html}</div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )
