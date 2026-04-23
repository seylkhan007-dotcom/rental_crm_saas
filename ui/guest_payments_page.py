import streamlit as st

from services.booking_service import BookingService
from services.finance_service import FinanceService
from services.guest_payment_service import GuestPaymentService


PAYMENT_STATUS_LABELS = {
    "pending": "Ожидает",
    "received": "Получен",
    "approved": "Подтвержден",
    "paid": "Оплачен",
    "cancelled": "Отменен",
}


def _safe_round(value):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _label(code: str | None, mapping: dict, default: str = "-") -> str:
    if not code:
        return default
    return mapping.get(code, code)


def _parse_money_input(value: str, field_name: str, allow_zero: bool = True) -> float:
    text = str(value or "").strip()

    if text == "":
        if allow_zero:
            return 0.0
        raise ValueError(f"Поле '{field_name}' обязательно.")

    text = text.replace(",", ".").replace(" ", "")

    try:
        amount = float(text)
    except ValueError as exc:
        raise ValueError(f"Поле '{field_name}' должно быть числом.") from exc

    if amount < 0:
        raise ValueError(f"Поле '{field_name}' не может быть отрицательным.")

    if not allow_zero and amount == 0:
        raise ValueError(f"Поле '{field_name}' должно быть больше нуля.")

    return amount


def render_guest_payments_page(conn):
    booking_service = BookingService(conn)
    finance_service = FinanceService(conn)
    guest_payment_service = GuestPaymentService(conn)

    st.subheader("Платежи гостей")
    st.caption(
        "Здесь фиксируются реальные оплаты гостей и считается остаток долга."
    )

    try:
        bookings = booking_service.get_all_bookings()
    except Exception as e:
        st.error(f"Ошибка загрузки бронирований: {e}")
        return

    st.markdown("### Начисления и оплаты по броням")

    rows = []

    for booking in bookings:
        try:
            finance = finance_service.calculate_booking_finances(
                booking["id"],
                persist_snapshot=False,
            )

            guest_due = _safe_round(finance.get("guest_price"))
            guest_paid = _safe_round(
                guest_payment_service.get_total_received_by_booking_id(booking["id"])
            )
            guest_balance = _safe_round(guest_due - guest_paid)

            rows.append(
                {
                    "Бронь": booking["id"],
                    "Гость": booking.get("guest_name") or "-",
                    "Начислено": guest_due,
                    "Оплачено": guest_paid,
                    "Остаток": guest_balance,
                    "Источник": booking.get("source_channel") or "-",
                    "Тип аренды": booking.get("stay_type") or "-",
                }
            )

        except Exception as e:
            rows.append(
                {
                    "Бронь": booking["id"],
                    "Гость": booking.get("guest_name") or "-",
                    "Ошибка": str(e),
                }
            )

    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Пока нет броней.")

    st.markdown("---")
    st.markdown("### Краткие итоги")

    if rows:
        total_due = _safe_round(
            sum(row.get("Начислено", 0) for row in rows if "Начислено" in row)
        )
        total_paid = _safe_round(
            sum(row.get("Оплачено", 0) for row in rows if "Оплачено" in row)
        )
        total_balance = _safe_round(
            sum(row.get("Остаток", 0) for row in rows if "Остаток" in row)
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Всего начислено", total_due)
        c2.metric("Всего оплачено", total_paid)
        c3.metric("Общий долг гостей", total_balance)
    else:
        st.info("Пока нет данных для итогов.")

    st.markdown("---")
    st.markdown("### Добавить платеж")

    if not bookings:
        st.warning("Нет бронирований.")
        return

    booking_options = {
        f"{booking['id']} - {booking.get('guest_name') or 'Без имени'} - {booking.get('check_in')} → {booking.get('check_out')}": booking["id"]
        for booking in bookings
    }

    with st.form("guest_payment_form"):
        selected_booking_label = st.selectbox("Бронь", list(booking_options.keys()))

        amount_text = st.text_input(
            "Сумма платежа",
            value="",
            placeholder="Например: 500",
        )

        currency_code = st.selectbox("Валюта", ["GEL", "USD", "EUR"])

        fx_rate_text = st.text_input(
            "Курс к GEL",
            value="1",
            placeholder="Например: 1",
        )

        payment_method = st.selectbox(
            "Способ оплаты",
            ["cash", "card", "transfer", "booking_com", "other"],
        )

        notes = st.text_area("Комментарий", value="")

        submitted = st.form_submit_button("Добавить платеж")

        if submitted:
            try:
                booking_id = booking_options[selected_booking_label]
                amount_original = _parse_money_input(
                    amount_text,
                    "Сумма платежа",
                    allow_zero=False,
                )
                fx_rate_to_gel = _parse_money_input(
                    fx_rate_text,
                    "Курс к GEL",
                    allow_zero=False,
                )

                guest_payment_service.create_payment(
                    booking_id=booking_id,
                    amount_original=amount_original,
                    currency_code=currency_code,
                    fx_rate_to_gel=fx_rate_to_gel,
                    payment_method=payment_method,
                    notes=notes,
                )

                st.success("Платеж добавлен.")
                st.rerun()

            except Exception as e:
                st.error(f"Ошибка добавления платежа: {e}")

    st.markdown("---")
    st.markdown("### Все платежи гостей")

    payment_rows_raw = guest_payment_service.get_all_guest_payments()

    if payment_rows_raw:
        booking_map = {booking["id"]: booking for booking in bookings}
        payment_rows = []

        for payment in payment_rows_raw:
            booking = booking_map.get(payment.get("booking_id"))

            payment_rows.append(
                {
                    "ID": payment.get("id"),
                    "Бронь": payment.get("booking_id"),
                    "Гость": booking.get("guest_name") if booking else "-",
                    "Сумма": _safe_round(payment.get("amount_original")),
                    "Валюта": payment.get("currency_code") or "GEL",
                    "Курс": _safe_round(payment.get("fx_rate_to_gel")),
                    "Сумма в GEL": _safe_round(payment.get("amount_gel")),
                    "Метод": payment.get("payment_method") or "-",
                    "Статус": _label(
                        payment.get("status"),
                        PAYMENT_STATUS_LABELS,
                    ),
                    "Комментарий": payment.get("notes") or "",
                    "Создано": payment.get("created_at"),
                }
            )

        st.dataframe(payment_rows, use_container_width=True)
    else:
        st.info("Пока нет платежей гостей.")

    st.markdown("---")
    st.markdown("### Проверка одной брони")

    selected_check_booking_label = st.selectbox(
        "Выбери бронь для проверки",
        list(booking_options.keys()),
        key="guest_payment_check_booking",
    )
    selected_check_booking_id = booking_options[selected_check_booking_label]

    try:
        finance = finance_service.calculate_booking_finances(
            selected_check_booking_id,
            persist_snapshot=False,
        )

        total_due = _safe_round(finance.get("guest_price"))
        already_paid = _safe_round(
            guest_payment_service.get_total_received_by_booking_id(
                selected_check_booking_id
            )
        )
        remaining_due = _safe_round(total_due - already_paid)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Начислено гостю", total_due)
            st.metric("Уже оплачено", already_paid)
        with c2:
            st.metric("Остаток долга", remaining_due)
            st.metric(
                "Источник",
                (finance.get("source_channel") or "-")
                if isinstance(finance, dict)
                else "-",
            )

        st.markdown("#### Финансовый breakdown")
        st.json(finance)

    except Exception as e:
        st.error(f"Ошибка проверки брони: {e}")
