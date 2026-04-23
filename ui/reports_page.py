from datetime import date, timedelta

import streamlit as st

from services.report_service import ReportService


def _safe_round(value):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def render_reports_page(conn):
    report_service = ReportService(conn)

    st.subheader("Отчёты и аналитика")

    today = date.today()
    first_day_of_month = today.replace(day=1)
    first_day_of_year = today.replace(month=1, day=1)

    preset = st.selectbox(
        "Период",
        [
            "Текущий месяц",
            "Текущий год",
            "Последние 30 дней",
            "Произвольный период",
        ],
    )

    if preset == "Текущий месяц":
        date_from = first_day_of_month
        date_to = today
    elif preset == "Текущий год":
        date_from = first_day_of_year
        date_to = today
    elif preset == "Последние 30 дней":
        date_from = today - timedelta(days=30)
        date_to = today
    else:
        c1, c2 = st.columns(2)
        with c1:
            date_from = st.date_input(
                "Дата от",
                value=first_day_of_month,
                format="YYYY-MM-DD",
            )
        with c2:
            date_to = st.date_input(
                "Дата до",
                value=today,
                format="YYYY-MM-DD",
            )

    if date_to < date_from:
        st.error("Дата окончания не может быть раньше даты начала.")
        return

    try:
        report = report_service.build_period_report(
            date_from=date_from.strftime("%Y-%m-%d"),
            date_to=date_to.strftime("%Y-%m-%d"),
        )
    except Exception as e:
        st.error(f"Ошибка построения отчёта: {e}")
        return

    summary = report.get("summary", {})
    apartments = report.get("apartments", [])
    owners = report.get("owners", [])
    bookings = report.get("bookings", [])

    st.markdown(f"### Период: {summary.get('date_from')} → {summary.get('date_to')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Бронирований", summary.get("bookings_count", 0))
    c2.metric("Доход от гостей", _safe_round(summary.get("total_guest_income")))
    c3.metric("Начислено собственникам", _safe_round(summary.get("total_owner_accrual")))
    c4.metric("Расходы компании", _safe_round(summary.get("total_company_expenses")))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Выплаты менеджерам", _safe_round(summary.get("total_manager_payout")))
    c6.metric("Чистая прибыль", _safe_round(summary.get("total_net_profit")))
    c7.metric("Долг гостей", _safe_round(summary.get("total_guest_debt")))
    c8.metric("Долг собственникам", _safe_round(summary.get("total_owner_debt")))

    st.markdown("---")
    st.markdown("### По квартирам")
    if apartments:
        st.dataframe(apartments, use_container_width=True)
    else:
        st.info("Нет данных по квартирам.")

    st.markdown("---")
    st.markdown("### По собственникам")
    if owners:
        st.dataframe(owners, use_container_width=True)
    else:
        st.info("Нет данных по собственникам.")

    st.markdown("---")
    st.markdown("### Брони за период")
    if bookings:
        booking_rows = []
        for booking in bookings:
            booking_rows.append({
                "ID": booking.get("booking_id"),
                "Гость": booking.get("guest_name"),
                "Квартира": booking.get("apartment_name"),
                "Собственник": booking.get("owner_name"),
                "Заезд": booking.get("check_in"),
                "Выезд": booking.get("check_out"),
                "Доход от гостя": _safe_round(booking.get("guest_income")),
                "Начислено собственнику": _safe_round(booking.get("owner_accrual")),
                "Расходы компании": _safe_round(booking.get("company_expenses")),
                "Выплаты менеджерам": _safe_round(booking.get("manager_payout")),
                "Чистая прибыль": _safe_round(booking.get("net_profit")),
                "Долг гостя": _safe_round(booking.get("guest_debt")),
                "Долг собственнику": _safe_round(booking.get("owner_debt")),
            })

        st.dataframe(booking_rows, use_container_width=True)
    else:
        st.info("Нет броней за этот период.")