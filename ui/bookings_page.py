from datetime import date, datetime, timedelta

import streamlit as st

from services.apartment_service import ApartmentService
from services.booking_service import BookingService
from services.finance_service import FinanceService


STAY_TYPE_LABELS = {
    "short_term": "Краткосрок",
    "long_term": "Долгосрок",
}

SOURCE_CHANNEL_LABELS = {
    "direct": "Прямой",
    "booking_com": "Booking.com",
    "whatsapp": "WhatsApp",
    "owner_direct": "От собственника",
}

OTA_MODE_LABELS = {
    "company_only": "Компания",
    "owner_only": "Собственник",
    "shared": "Делится",
}


def _safe_round(value):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _parse_date(value: str | None, fallback: date | None = None) -> date:
    if not value:
        return fallback or date.today()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return fallback or date.today()


def _to_iso(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def _label(code: str | None, mapping: dict, default: str = "-") -> str:
    if not code:
        return default
    return mapping.get(code, code)


def _get_booking_by_id(bookings: list[dict], booking_id: int):
    for booking in bookings:
        if booking["id"] == booking_id:
            return booking
    return None


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


def render_bookings_page(conn):
    booking_service = BookingService(conn)
    apartment_service = ApartmentService(conn)
    finance_service = FinanceService(conn)

    st.subheader("Бронирования и финансы")
    st.caption("Быстро создаём бронь и сразу видим финансы, OTA и прибыль.")

    try:
        bookings = booking_service.get_all_bookings()
        apartments = apartment_service.get_all_apartments()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    apartment_map = {apartment["id"]: apartment for apartment in apartments}

    # ---------------------------------------------------------
    # БЫСТРОЕ СОЗДАНИЕ БРОНИ
    # ---------------------------------------------------------
    st.markdown("### Быстрое создание бронирования")

    if not apartments:
        st.warning("Сначала создай хотя бы одну квартиру.")
    else:
        apartment_options = {
            f"{apartment['id']} - {apartment['name']}": apartment["id"]
            for apartment in apartments
        }

        with st.form("quick_create_booking_form"):
            selected_apartment = st.selectbox("Квартира", list(apartment_options.keys()))
            guest_name = st.text_input("Имя гостя")

            today = date.today()
            check_in_date = st.date_input(
                "Дата заезда",
                value=today,
                format="YYYY-MM-DD",
            )
            check_out_date = st.date_input(
                "Дата выезда",
                value=today + timedelta(days=1),
                format="YYYY-MM-DD",
            )

            c1, c2 = st.columns(2)
            with c1:
                guest_price_text = st.text_input(
                    "Сколько платит гость",
                    value="",
                    placeholder="Например: 1000",
                )
            with c2:
                settlement_base_text = st.text_input(
                    "Settlement base / база для собственника",
                    value="",
                    placeholder="Например: 700",
                )

            c3, c4 = st.columns(2)
            with c3:
                stay_type = st.selectbox(
                    "Тип аренды",
                    list(STAY_TYPE_LABELS.keys()),
                    format_func=lambda x: STAY_TYPE_LABELS[x],
                )
            with c4:
                source_channel = st.selectbox(
                    "Источник брони",
                    list(SOURCE_CHANNEL_LABELS.keys()),
                    format_func=lambda x: SOURCE_CHANNEL_LABELS[x],
                )

            st.markdown("#### OTA")
            c5, c6, c7, c8 = st.columns(4)
            with c5:
                ota_account_name = st.text_input(
                    "OTA аккаунт",
                    value="",
                    placeholder="Например: booking main",
                )
            with c6:
                ota_commission_pct_text = st.text_input(
                    "Комиссия OTA (%)",
                    value="0",
                    placeholder="Например: 15",
                )
            with c7:
                ota_vat_pct_text = st.text_input(
                    "НДС на комиссию OTA (%)",
                    value="0",
                    placeholder="Например: 18",
                )
            with c8:
                ota_cost_mode_snapshot = st.selectbox(
                    "Кто платит OTA",
                    list(OTA_MODE_LABELS.keys()),
                    format_func=lambda x: OTA_MODE_LABELS[x],
                )

            submitted_create = st.form_submit_button("Создать бронирование")

            if submitted_create:
                try:
                    if not guest_name.strip():
                        raise ValueError("Имя гостя обязательно.")

                    if check_out_date <= check_in_date:
                        raise ValueError("Дата выезда должна быть позже даты заезда.")

                    guest_price = _parse_money_input(
                        guest_price_text,
                        "Сколько платит гость",
                        allow_zero=False,
                    )

                    settlement_base_amount = _parse_money_input(
                        settlement_base_text,
                        "Settlement base / база для собственника",
                        allow_zero=True,
                    )

                    ota_commission_pct = _parse_money_input(
                        ota_commission_pct_text,
                        "Комиссия OTA (%)",
                        allow_zero=True,
                    )

                    ota_vat_pct = _parse_money_input(
                        ota_vat_pct_text,
                        "НДС на комиссию OTA (%)",
                        allow_zero=True,
                    )

                    booking_id = booking_service.create_booking(
                        apartment_id=apartment_options[selected_apartment],
                        guest_name=guest_name.strip(),
                        check_in=_to_iso(check_in_date),
                        check_out=_to_iso(check_out_date),
                        total_amount=guest_price,
                        guest_price=guest_price,
                        settlement_base_amount=settlement_base_amount if settlement_base_amount > 0 else None,
                        source_channel=source_channel,
                        stay_type=stay_type,
                        ota_account_name=ota_account_name.strip() if ota_account_name.strip() else None,
                        ota_commission_pct=ota_commission_pct,
                        ota_vat_pct=ota_vat_pct,
                        ota_cost_mode_snapshot=ota_cost_mode_snapshot,
                    )

                    finance_service.calculate_booking_finances(
                        booking_id=booking_id,
                        persist_snapshot=True,
                    )

                    st.success(f"Бронирование создано. ID = {booking_id}")
                    st.rerun()

                except Exception as e:
                    st.error(f"Ошибка создания бронирования: {e}")

    # ---------------------------------------------------------
    # СПИСОК БРОНИРОВАНИЙ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Список бронирований")

    booking_rows = []

    for booking in bookings:
        apartment = apartment_map.get(booking["apartment_id"])

        try:
            finance = finance_service.calculate_booking_finances(
                booking["id"],
                persist_snapshot=False,
            )

            booking_rows.append({
                "ID": booking["id"],
                "Гость": booking.get("guest_name") or "-",
                "Квартира": apartment["name"] if apartment else "-",
                "Заезд": booking.get("check_in") or "-",
                "Выезд": booking.get("check_out") or "-",
                "Источник": _label(booking.get("source_channel"), SOURCE_CHANNEL_LABELS),
                "Сумма гостя": _safe_round(finance.get("guest_price")),
                "Settlement base": _safe_round(finance.get("settlement_base_amount")),
                "OTA": _safe_round(finance.get("ota_total_amount")),
                "OTA mode": _label(finance.get("ota_cost_mode"), OTA_MODE_LABELS),
                "Выплата собственнику": _safe_round(finance.get("owner_amount_due")),
                "Чистая прибыль компании": _safe_round(finance.get("distributable_profit_amount")),
            })
        except Exception as e:
            booking_rows.append({
                "ID": booking["id"],
                "Гость": booking.get("guest_name") or "-",
                "Квартира": apartment["name"] if apartment else "-",
                "Ошибка расчёта": str(e),
            })

    if booking_rows:
        st.dataframe(booking_rows, use_container_width=True)
    else:
        st.info("Пока нет бронирований.")

    # ---------------------------------------------------------
    # КРАТКИЕ ИТОГИ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Краткие итоги")

    if booking_rows:
        total_guest_income = _safe_round(
            sum(row.get("Сумма гостя", 0) for row in booking_rows if "Сумма гостя" in row)
        )
        total_ota = _safe_round(
            sum(row.get("OTA", 0) for row in booking_rows if "OTA" in row)
        )
        total_owner_payout = _safe_round(
            sum(row.get("Выплата собственнику", 0) for row in booking_rows if "Выплата собственнику" in row)
        )
        total_company_profit = _safe_round(
            sum(row.get("Чистая прибыль компании", 0) for row in booking_rows if "Чистая прибыль компании" in row)
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Доход от гостей", total_guest_income)
        c2.metric("OTA", total_ota)
        c3.metric("Выплаты собственникам", total_owner_payout)
        c4.metric("Чистая прибыль компании", total_company_profit)
    else:
        st.info("Пока нет данных для итогов.")

    # ---------------------------------------------------------
    # ДЕТАЛИ ОДНОЙ БРОНИ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Детали бронирования")

    if bookings:
        booking_options = {
            f"{booking['id']} - {booking['guest_name']} - {booking['check_in']} → {booking['check_out']}": booking["id"]
            for booking in bookings
        }

        selected_booking_label = st.selectbox(
            "Выбери бронирование",
            list(booking_options.keys()),
        )
        selected_booking_id = booking_options[selected_booking_label]

        try:
            booking = _get_booking_by_id(bookings, selected_booking_id)
            apartment = apartment_map.get(booking["apartment_id"]) if booking else None
            finance = finance_service.get_booking_finance_breakdown(selected_booking_id)

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Сумма гостя", _safe_round(finance.get("guest_price")))
                st.metric("Settlement base", _safe_round(finance.get("settlement_base_amount")))
                st.metric("Extra margin", _safe_round(finance.get("extra_margin_amount")))
                st.metric("Выплата собственнику", _safe_round(finance.get("owner_amount_due")))

            with c2:
                st.metric("OTA комиссия", _safe_round(finance.get("ota_commission_amount")))
                st.metric("OTA НДС", _safe_round(finance.get("ota_vat_amount")))
                st.metric("OTA total", _safe_round(finance.get("ota_total_amount")))
                st.metric("Чистая прибыль компании", _safe_round(finance.get("distributable_profit_amount")))

            st.markdown("#### Основная информация")
            st.json({
                "ID брони": selected_booking_id,
                "Гость": booking.get("guest_name") if booking else "-",
                "Квартира": apartment["name"] if apartment else "-",
                "Дата заезда": booking.get("check_in") if booking else "-",
                "Дата выезда": booking.get("check_out") if booking else "-",
                "Источник": _label(booking.get("source_channel") if booking else None, SOURCE_CHANNEL_LABELS),
                "Тип аренды": _label(booking.get("stay_type") if booking else None, STAY_TYPE_LABELS),
                "OTA аккаунт": booking.get("ota_account_name") if booking else "-",
                "OTA комиссия %": booking.get("ota_commission_pct") if booking else 0,
                "OTA VAT %": booking.get("ota_vat_pct") if booking else 0,
                "OTA mode": _label(finance.get("ota_cost_mode"), OTA_MODE_LABELS),
                "OTA owner burden": _safe_round(finance.get("ota_owner_amount")),
                "OTA company burden": _safe_round(finance.get("ota_company_amount")),
                "OTA shared amount": _safe_round(finance.get("ota_shared_amount")),
                "Стратегия расчёта": finance.get("strategy_type") or "-",
            })

            st.markdown("#### Финансовый breakdown")
            st.json(finance)

        except Exception as e:
            st.error(f"Ошибка загрузки деталей: {e}")
    else:
        st.info("Пока нет бронирований.")