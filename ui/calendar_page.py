from datetime import date, timedelta

import streamlit as st
import streamlit.components.v1 as components

from services.calendar_service import CalendarService


CELL_STYLES = {
    "free": {
        "bg": "#ffffff",
        "border": "#e5e7eb",
        "text": "#9ca3af",
        "short": "",
    },
    "check_in": {
        "bg": "#dcfce7",
        "border": "#16a34a",
        "text": "#166534",
        "short": "Заезд",
    },
    "occupied": {
        "bg": "#dbeafe",
        "border": "#2563eb",
        "text": "#1d4ed8",
        "short": "Занято",
    },
    "check_out": {
        "bg": "#fef3c7",
        "border": "#d97706",
        "text": "#92400e",
        "short": "Выезд",
    },
}


def _day_header(iso_date: str) -> tuple[str, str]:
    dt = date.fromisoformat(iso_date)
    weekday_map = {
        0: "Пн",
        1: "Вт",
        2: "Ср",
        3: "Чт",
        4: "Пт",
        5: "Сб",
        6: "Вс",
    }
    return f"{dt.day:02d}.{dt.month:02d}", weekday_map[dt.weekday()]


def _escape_html(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _build_calendar_html(rows: list[dict], days: list[str]) -> str:
    header_days = []
    for day in days:
        d_top, d_bottom = _day_header(day)
        header_days.append(
            f"""
            <div class="crm-cal-header-day">
                <div class="crm-cal-header-day-top">{d_top}</div>
                <div class="crm-cal-header-day-bottom">{d_bottom}</div>
            </div>
            """
        )

    rows_html = []

    for row in rows:
        apartment_name = _escape_html(row.get("apartment_name") or "-")
        owner_name = _escape_html(row.get("owner_name") or "-")

        cells_html = []
        for cell in row["days"]:
            status = cell.get("status", "free")
            style = CELL_STYLES.get(status, CELL_STYLES["free"])
            label = _escape_html(cell.get("label") or style["short"] or "")

            if status == "free":
                label = "&nbsp;"

            cells_html.append(
                f"""
                <div class="crm-cal-cell"
                     title="{_escape_html(cell.get('label') or '')}"
                     style="background:{style['bg']}; border:1px solid {style['border']}; color:{style['text']};">
                    {label}
                </div>
                """
            )

        bookings_line = ""
        if row.get("bookings"):
            booking_labels = []
            for booking in row["bookings"]:
                booking_labels.append(
                    f"#{booking['booking_id']} — {_escape_html(booking.get('guest_name') or '-')}"
                    f" ({_escape_html(booking.get('check_in') or '')} → {_escape_html(booking.get('check_out') or '')})"
                )
            bookings_line = f"""
            <div class="crm-cal-bookings-line">
                {' | '.join(booking_labels)}
            </div>
            """

        rows_html.append(
            f"""
            <div class="crm-cal-row-wrap">
                <div class="crm-cal-row">
                    <div class="crm-cal-apartment">{apartment_name}</div>
                    <div class="crm-cal-owner">{owner_name}</div>
                    {''.join(cells_html)}
                </div>
                {bookings_line}
            </div>
            """
        )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                color: #111827;
                background: #ffffff;
            }}

            .crm-wrap {{
                padding: 8px 2px 12px 2px;
            }}

            .crm-cal-legend {{
                display: grid;
                grid-template-columns: repeat(4, minmax(140px, 1fr));
                gap: 10px;
                margin-bottom: 14px;
            }}

            .crm-cal-legend-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 10px;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                background: #ffffff;
                font-size: 13px;
                color: #111827;
                box-sizing: border-box;
            }}

            .crm-cal-legend-dot {{
                width: 18px;
                height: 18px;
                border-radius: 6px;
                flex-shrink: 0;
                box-sizing: border-box;
            }}

            .crm-cal-scroll {{
                overflow-x: auto;
                overflow-y: hidden;
                padding-bottom: 10px;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                background: #ffffff;
                box-sizing: border-box;
            }}

            .crm-cal-grid {{
                min-width: {360 + len(days) * 86}px;
                padding: 12px;
                box-sizing: border-box;
            }}

            .crm-cal-header,
            .crm-cal-row {{
                display: grid;
                grid-template-columns: 180px 180px repeat({len(days)}, 78px);
                gap: 8px;
                align-items: stretch;
                box-sizing: border-box;
            }}

            .crm-cal-header {{
                padding-bottom: 8px;
                border-bottom: 1px solid #e5e7eb;
                margin-bottom: 10px;
            }}

            .crm-cal-header-fixed {{
                font-weight: 700;
                color: #111827;
                font-size: 14px;
                display: flex;
                align-items: center;
                min-height: 48px;
                padding: 8px 10px;
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                box-sizing: border-box;
            }}

            .crm-cal-header-day {{
                min-height: 48px;
                padding: 6px 4px;
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                text-align: center;
                box-sizing: border-box;
            }}

            .crm-cal-header-day-top {{
                font-size: 13px;
                font-weight: 700;
                color: #111827;
                line-height: 1.1;
            }}

            .crm-cal-header-day-bottom {{
                font-size: 11px;
                color: #6b7280;
                margin-top: 4px;
                line-height: 1.1;
            }}

            .crm-cal-row-wrap {{
                margin-bottom: 12px;
            }}

            .crm-cal-apartment,
            .crm-cal-owner {{
                min-height: 58px;
                padding: 10px;
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                display: flex;
                align-items: center;
                font-size: 14px;
                color: #111827;
                word-break: break-word;
                box-sizing: border-box;
            }}

            .crm-cal-apartment {{
                font-weight: 700;
            }}

            .crm-cal-owner {{
                color: #374151;
            }}

            .crm-cal-cell {{
                min-height: 58px;
                padding: 6px;
                border-radius: 12px;
                font-size: 11px;
                line-height: 1.2;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                overflow: hidden;
                word-break: break-word;
                box-sizing: border-box;
            }}

            .crm-cal-bookings-line {{
                margin-top: 6px;
                padding-left: 4px;
                font-size: 12px;
                color: #6b7280;
            }}
        </style>
    </head>
    <body>
        <div class="crm-wrap">
            <div class="crm-cal-legend">
                <div class="crm-cal-legend-item">
                    <div class="crm-cal-legend-dot" style="background:#dcfce7;border:1px solid #16a34a;"></div>
                    <span>Заезд</span>
                </div>
                <div class="crm-cal-legend-item">
                    <div class="crm-cal-legend-dot" style="background:#dbeafe;border:1px solid #2563eb;"></div>
                    <span>Занято</span>
                </div>
                <div class="crm-cal-legend-item">
                    <div class="crm-cal-legend-dot" style="background:#fef3c7;border:1px solid #d97706;"></div>
                    <span>Выезд</span>
                </div>
                <div class="crm-cal-legend-item">
                    <div class="crm-cal-legend-dot" style="background:#ffffff;border:1px solid #e5e7eb;"></div>
                    <span>Свободно</span>
                </div>
            </div>

            <div class="crm-cal-scroll">
                <div class="crm-cal-grid">
                    <div class="crm-cal-header">
                        <div class="crm-cal-header-fixed">Квартира</div>
                        <div class="crm-cal-header-fixed">Собственник</div>
                        {''.join(header_days)}
                    </div>

                    {''.join(rows_html)}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def render_calendar_page(conn):
    """Страница календаря бронирований."""

    calendar_service = CalendarService(conn)

    st.subheader("Календарь бронирований")
    st.caption("Здесь видно загрузку квартир по дням: заезды, выезды и занятые даты.")

    today = date.today()
    default_from = today
    default_to = today + timedelta(days=13)

    c1, c2 = st.columns(2)
    with c1:
        date_from = st.date_input(
            "Дата от",
            value=default_from,
            format="YYYY-MM-DD",
            key="calendar_date_from",
        )
    with c2:
        date_to = st.date_input(
            "Дата до",
            value=default_to,
            format="YYYY-MM-DD",
            key="calendar_date_to",
        )

    if date_to < date_from:
        st.error("Дата окончания не может быть раньше даты начала.")
        return

    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")

    try:
        calendar_data = calendar_service.build_calendar_view(
            date_from=date_from_str,
            date_to=date_to_str,
        )
    except Exception as e:
        st.error(f"Ошибка построения календаря: {e}")
        return

    days = calendar_data["days"]
    rows = calendar_data["rows"]

    st.markdown("---")
    st.markdown(f"### Период: {calendar_data['date_from']} → {calendar_data['date_to']}")

    if not rows:
        st.info("Нет квартир для отображения.")
        return

    html = _build_calendar_html(rows=rows, days=days)
    components.html(html, height=900, scrolling=True)