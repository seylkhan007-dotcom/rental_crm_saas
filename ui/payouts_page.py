import streamlit as st

from services.booking_service import BookingService
from services.finance_service import FinanceService
from services.owner_payout_service import OwnerPayoutService
from services.owner_service import OwnerService


PAYOUT_STATUS_LABELS = {
    "pending": "Ожидает выплаты",
    "partial": "Частично выплачен",
    "paid": "Выплачен",
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


def render_payouts_page(conn):
    booking_service = BookingService(conn)
    finance_service = FinanceService(conn)
    owner_service = OwnerService(conn)
    owner_payout_service = OwnerPayoutService(conn)

    st.subheader("Выплаты собственникам")
    st.caption(
        "Здесь видно, сколько начислено по броням, сколько уже выплачено и какой остаток долга."
    )

    try:
        bookings = booking_service.get_all_bookings()
        owners = owner_service.get_all_owners()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    owner_map = {owner["id"]: owner["name"] for owner in owners}

    st.markdown("### Начисления и остатки по броням")

    rows = []

    for booking in bookings:
        try:
            finance = finance_service.calculate_booking_finances(
                booking["id"],
                persist_snapshot=False,
            )

            apartment = booking_service.get_apartment_by_booking(booking["id"])
            owner_id = apartment.get("owner_id") if apartment else None
            owner_name = owner_map.get(owner_id, "-")

            owner_accrued = _safe_round(finance.get("owner_amount_due"))
            owner_paid = _safe_round(
                owner_payout_service.get_total_paid_by_booking_id(booking["id"])
            )
            owner_balance = _safe_round(owner_accrued - owner_paid)

            rows.append(
                {
                    "Бронь": booking["id"],
                    "Гость": booking.get("guest_name") or "-",
                    "Собственник": owner_name,
                    "Сумма гостя": _safe_round(finance.get("guest_price")),
                    "Начислено собственнику": owner_accrued,
                    "Уже выплачено": owner_paid,
                    "Остаток долга": owner_balance,
                    "Стратегия": finance.get("strategy_type") or "-",
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
        total_accrued = _safe_round(
            sum(
                row.get("Начислено собственнику", 0)
                for row in rows
                if "Начислено собственнику" in row
            )
        )
        total_paid = _safe_round(
            sum(
                row.get("Уже выплачено", 0)
                for row in rows
                if "Уже выплачено" in row
            )
        )
        total_balance = _safe_round(
            sum(
                row.get("Остаток долга", 0)
                for row in rows
                if "Остаток долга" in row
            )
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Всего начислено", total_accrued)
        c2.metric("Всего выплачено", total_paid)
        c3.metric("Общий остаток долга", total_balance)
    else:
        st.info("Пока нет данных для итогов.")

    st.markdown("---")
    st.markdown("### Зафиксировать выплату")

    if not bookings:
        st.warning("Нет бронирований.")
        return

    booking_options = {
        f"{booking['id']} - {booking.get('guest_name') or 'Без имени'} - {booking.get('check_in')} → {booking.get('check_out')}": booking["id"]
        for booking in bookings
    }

    with st.form("create_owner_payout_form"):
        selected_booking_label = st.selectbox("Бронь", list(booking_options.keys()))
        payout_amount_text = st.text_input(
            "Сумма выплаты",
            value="",
            placeholder="Например: 300",
        )
        submitted = st.form_submit_button("Добавить выплату")

        if submitted:
            try:
                booking_id = booking_options[selected_booking_label]
                payout_amount = _parse_money_input(
                    payout_amount_text,
                    "Сумма выплаты",
                    allow_zero=False,
                )

                owner_payout_service.create_manual_payout(
                    booking_id=booking_id,
                    amount_paid_gel=payout_amount,
                )

                st.success("Выплата сохранена.")
                st.rerun()

            except Exception as e:
                st.error(f"Ошибка создания выплаты: {e}")

    st.markdown("---")
    st.markdown("### Все выплаты")

    payout_rows_raw = owner_payout_service.get_all_payouts()

    if payout_rows_raw:
        booking_map = {booking["id"]: booking for booking in bookings}
        payout_rows = []

        for payout in payout_rows_raw:
            booking = booking_map.get(payout.get("booking_id"))
            owner_name = owner_map.get(payout.get("owner_id"), "-")

            payout_rows.append(
                {
                    "ID": payout.get("id"),
                    "Бронь": payout.get("booking_id"),
                    "Гость": booking.get("guest_name") if booking else "-",
                    "Собственник": owner_name,
                    "Начислено": _safe_round(
                        payout.get("amount_due_gel") or payout.get("amount")
                    ),
                    "Выплачено": _safe_round(payout.get("amount_paid_gel")),
                    "Валюта": payout.get("currency_code") or "GEL",
                    "Статус": _label(
                        payout.get("status"),
                        PAYOUT_STATUS_LABELS,
                    ),
                    "Создано": payout.get("created_at"),
                }
            )

        st.dataframe(payout_rows, use_container_width=True)
    else:
        st.info("Пока нет выплат собственникам.")

    st.markdown("---")
    st.markdown("### Проверка одной брони")

    selected_check_booking_label = st.selectbox(
        "Выбери бронь для проверки",
        list(booking_options.keys()),
        key="owner_payout_check_booking",
    )
    selected_check_booking_id = booking_options[selected_check_booking_label]

    try:
        finance = finance_service.calculate_booking_finances(
            selected_check_booking_id,
            persist_snapshot=False,
        )

        apartment = booking_service.get_apartment_by_booking(selected_check_booking_id)
        owner_id = apartment.get("owner_id") if apartment else None
        owner_name = owner_map.get(owner_id, "-")

        total_due = _safe_round(finance.get("owner_amount_due"))
        already_paid = _safe_round(
            owner_payout_service.get_total_paid_by_booking_id(
                selected_check_booking_id
            )
        )
        remaining_due = _safe_round(total_due - already_paid)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Собственник", owner_name)
            st.metric("Начислено", total_due)
        with c2:
            st.metric("Уже выплачено", already_paid)
            st.metric("Остаток долга", remaining_due)

        st.markdown("#### Финансовый breakdown")
        st.json(finance)

    except Exception as e:
        st.error(f"Ошибка проверки брони: {e}")
