from datetime import date, datetime, timedelta

import streamlit as st

from services.actor_service import ActorService
from services.apartment_service import ApartmentService
from services.booking_service import BookingService
from services.finance_service import FinanceService
from services.manager_checkin_report_service import ManagerCheckinReportService


PAYMENT_STATUS_LABELS = {
    "paid": "Оплачено",
    "unpaid": "Не оплачено",
    "partial": "Частично",
}

CASH_HANDOVER_STATUS_LABELS = {
    "pending": "Ожидает передачи",
    "received": "Деньги получены",
    "not_required": "Не требуется",
}

CURRENCY_OPTIONS = ["GEL", "USD", "EUR"]
BREAKFAST_OPTIONS = ["Без завтрака", "С завтраком"]

SOURCE_CHANNEL_LABELS = {
    "booking": "Booking.com",
    "airbnb": "Airbnb",
    "whatsapp": "WhatsApp",
    "instagram": "Instagram",
    "direct": "Прямой гость",
    "walk_in": "С улицы",
    "other": "Другое",
}

BOOKING_STATUS_LABELS = {
    "active": "Активна на площадке",
    "cancelled_but_stayed": "Отменена на площадке, гость проживает",
    "not_platform_booking": "Не через площадку",
}

PAYMENT_METHOD_LABELS = {
    "cash": "Наличные",
    "bank_transfer": "Перевод",
    "card": "Карта",
    "booking": "Booking.com",
    "airbnb": "Airbnb",
    "mixed": "Смешанная оплата",
    "other": "Другое",
}

MONEY_RECEIVER_LABELS = {
    "cashbox": "Касса / наличные",
    "bank_transfer": "Банковский перевод",
    "card_account": "Карта",
    "business_account": "Счёт ИП / компании",
    "personal_account": "Личный счёт",
    "other": "Другое",
}

BOOKING_SOURCE_LABELS = {
    "direct": "Прямой",
    "booking_com": "Booking.com",
    "whatsapp": "WhatsApp",
    "owner_direct": "От собственника",
}

STAY_TYPE_LABELS = {
    "short_term": "Посуточно",
    "long_term": "Долгосрок",
}


def _parse_amount(value: str, field_name: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0

    text = text.replace(",", ".").replace(" ", "")

    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Поле '{field_name}' должно быть числом.") from exc


def _safe_round(value):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _label(code: str | None, mapping: dict, default: str = "-") -> str:
    if not code:
        return default
    return mapping.get(code, code)


def _map_report_source_to_booking_source(source_channel: str | None) -> str:
    mapping = {
        "booking": "booking_com",
        "whatsapp": "whatsapp",
        "direct": "direct",
        "walk_in": "direct",
        "instagram": "direct",
        "airbnb": "direct",
        "other": "direct",
    }
    return mapping.get(source_channel or "", "direct")


def _actor_name(actor: dict | None) -> str:
    if not actor:
        return "-"
    return actor.get("display_name") or actor.get("full_name") or f"Actor {actor['id']}"


def _apartment_name(apartment: dict | None) -> str:
    if not apartment:
        return "-"
    return apartment.get("name") or f"Room {apartment['id']}"


def _money(value, currency: str) -> str:
    return f"{_safe_round(value)} {currency}"


def render_manager_checkin_reports_page(conn):
    """Страница контроля отчётов менеджеров о заселении."""

    actor_service = ActorService(conn)
    apartment_service = ApartmentService(conn)
    booking_service = BookingService(conn)
    finance_service = FinanceService(conn)
    report_service = ManagerCheckinReportService(conn)

    st.subheader("Контроль заселений")

    try:
        reports = report_service.get_all_reports()
        actors = actor_service.get_active_actors()
        apartments = apartment_service.get_all_apartments()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    actor_map = {actor["id"]: actor for actor in actors}
    apartment_map = {apartment["id"]: apartment for apartment in apartments}

    if not reports:
        st.info("Пока нет отчётов менеджеров.")
        return

    actor_options = {
        f"{actor['id']} - {_actor_name(actor)}": actor["id"]
        for actor in actors
    }

    for report in reports:
        manager = _actor_name(actor_map.get(report.get("manager_id")))
        room = _apartment_name(apartment_map.get(report.get("room_id")))
        currency = report.get("currency") or "GEL"
        amount_received = _safe_round(report.get("amount_received"))
        can_mark_cash_received = (
            amount_received > 0
            and report.get("cash_handover_status") == "pending"
        )
        can_create_booking = (
            report.get("cash_handover_status") == "received"
            and not report.get("booking_id")
        )

        with st.container(border=True):
            st.markdown(f"**Гость:** {report.get('guest_name') or '-'}")
            st.write(f"**Комната:** {room}")
            st.write(f"**Менеджер:** {manager}")
            st.write(
                f"**Даты:** {report.get('checkin_date') or '-'} "
                f"→ {report.get('checkout_date') or '-'}"
            )
            st.write(
                "**Источник гостя:** "
                f"{_label(report.get('source_channel'), SOURCE_CHANNEL_LABELS)}"
            )
            st.write(
                "**Статус брони на площадке:** "
                f"{_label(report.get('booking_status'), BOOKING_STATUS_LABELS)}"
            )
            st.write(
                "**Как оплатил:** "
                f"{_label(report.get('payment_method'), PAYMENT_METHOD_LABELS)}"
            )
            st.write(
                "**Куда поступили деньги:** "
                f"{_label(report.get('money_receiver'), MONEY_RECEIVER_LABELS)}"
            )
            st.write(f"**Цена:** {_money(report.get('booking_price'), currency)}")
            st.write(f"**Получено:** {_money(amount_received, currency)}")
            st.write(
                "**Оплата:** "
                f"{_label(report.get('payment_status'), PAYMENT_STATUS_LABELS)}"
            )
            st.write(
                "**Передача денег:** "
                f"{_label(report.get('cash_handover_status'), CASH_HANDOVER_STATUS_LABELS)}"
            )
            st.write(
                "**Бронь в CRM:** "
                f"{'Создана' if report.get('booking_id') else 'Не создана'}"
            )
            st.write("**Распределение денег:** Не распределено")

            if report.get("notes"):
                st.write(f"**Запросы гостя:** {report.get('notes')}")

            if can_create_booking and st.button(
                "Открыть создание брони",
                key=f"create_booking_placeholder_{report['id']}",
            ):
                st.session_state[f"show_create_booking_form_{report['id']}"] = True

            if (
                can_create_booking
                and st.session_state.get(f"show_create_booking_form_{report['id']}")
            ):
                default_booking_source = _map_report_source_to_booking_source(
                    report.get("source_channel")
                )
                booking_source_options = list(BOOKING_SOURCE_LABELS.keys())
                booking_source_index = (
                    booking_source_options.index(default_booking_source)
                    if default_booking_source in booking_source_options
                    else 0
                )

                with st.form(f"create_booking_from_report_form_{report['id']}"):
                    st.markdown("**Шаг 2. Проверить данные и создать бронь**")
                    guest_price = st.number_input(
                        "Цена гостя",
                        min_value=0.0,
                        value=float(report.get("booking_price") or 0),
                        step=1.0,
                        key=f"booking_guest_price_{report['id']}",
                    )
                    settlement_base_amount = st.number_input(
                        "Сумма для расчёта с собственником",
                        min_value=0.0,
                        value=float(report.get("booking_price") or 0),
                        step=1.0,
                        key=f"booking_settlement_base_{report['id']}",
                    )
                    stay_type = st.selectbox(
                        "Тип проживания",
                        list(STAY_TYPE_LABELS.keys()),
                        format_func=lambda x: STAY_TYPE_LABELS[x],
                        key=f"booking_stay_type_{report['id']}",
                    )
                    booking_source = st.selectbox(
                        "Источник для брони",
                        booking_source_options,
                        index=booking_source_index,
                        format_func=lambda x: BOOKING_SOURCE_LABELS[x],
                        key=f"booking_source_channel_{report['id']}",
                    )

                    if st.form_submit_button("Подтвердить и создать бронь"):
                        try:
                            booking_id = booking_service.create_booking(
                                apartment_id=report["room_id"],
                                guest_name=report["guest_name"],
                                check_in=report["checkin_date"],
                                check_out=report["checkout_date"],
                                total_amount=guest_price,
                                guest_price=guest_price,
                                settlement_base_amount=settlement_base_amount,
                                source_channel=booking_source,
                                stay_type=stay_type,
                                checkin_actor_id=report["manager_id"],
                            )

                            finance_service.calculate_booking_finances(
                                booking_id=booking_id,
                                persist_snapshot=True,
                            )

                            report_service.link_booking(
                                report_id=report["id"],
                                booking_id=booking_id,
                            )

                            st.success(f"Бронь #{booking_id} создана.")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Ошибка создания брони: {e}")

            if not can_mark_cash_received:
                continue

            if not actor_options:
                st.warning("Нужен активный сотрудник, чтобы указать, кто принял деньги.")
                continue

            selected_actor_label = st.selectbox(
                "Кто подтвердил получение",
                list(actor_options.keys()),
                key=f"cash_received_actor_{report['id']}",
            )
            ceo_received_by_actor_id = actor_options[selected_actor_label]

            if st.button(
                "Деньги получены",
                key=f"mark_cash_received_{report['id']}",
            ):
                try:
                    report_service.mark_cash_received(
                        report_id=report["id"],
                        ceo_received_by_actor_id=ceo_received_by_actor_id,
                        received_at=datetime.now().isoformat(timespec="seconds"),
                    )
                    st.success(f"Получение денег подтверждено по отчёту ID {report['id']}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка подтверждения получения денег: {e}")


def render_manager_checkin_create_page(conn):
    """Страница создания отчёта менеджера о заселении."""

    actor_service = ActorService(conn)
    apartment_service = ApartmentService(conn)
    report_service = ManagerCheckinReportService(conn)

    st.subheader("Заселить гостя")

    try:
        actors = actor_service.get_active_actors()
        apartments = apartment_service.get_all_apartments()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    if not actors:
        st.warning("Сначала создай хотя бы одного сотрудника / участника.")
        return

    if not apartments:
        st.warning("Сначала создай хотя бы одну комнату.")
        return

    manager_options = {
        f"{actor['id']} - {_actor_name(actor)}": actor["id"]
        for actor in actors
    }
    room_options = {
        f"{apartment['id']} - {_apartment_name(apartment)}": apartment["id"]
        for apartment in apartments
    }

    with st.form("create_manager_checkin_report_form", clear_on_submit=True):
        selected_manager = st.selectbox("Менеджер", list(manager_options.keys()))
        selected_room = st.selectbox("Комната", list(room_options.keys()))

        guest_name = st.text_input(
            "Гость",
            placeholder="Имя и фамилия",
        )
        guest_phone = st.text_input(
            "Телефон / WhatsApp",
            placeholder="Номер гостя",
        )

        today = date.today()
        c1, c2 = st.columns(2)
        with c1:
            checkin_date = st.date_input(
                "Дата заезда",
                value=today,
                format="YYYY-MM-DD",
            )
        with c2:
            checkout_date = st.date_input(
                "Дата выезда",
                value=today + timedelta(days=1),
                format="YYYY-MM-DD",
            )

        source_channel = st.selectbox(
            "Канал источника",
            list(SOURCE_CHANNEL_LABELS.keys()),
            format_func=lambda x: SOURCE_CHANNEL_LABELS[x],
        )
        booking_status = st.selectbox(
            "Статус брони на площадке",
            list(BOOKING_STATUS_LABELS.keys()),
            format_func=lambda x: BOOKING_STATUS_LABELS[x],
        )
        payment_method = st.selectbox(
            "Как оплатил",
            list(PAYMENT_METHOD_LABELS.keys()),
            format_func=lambda x: PAYMENT_METHOD_LABELS[x],
        )
        money_receiver = st.selectbox(
            "Куда поступили деньги",
            list(MONEY_RECEIVER_LABELS.keys()),
            format_func=lambda x: MONEY_RECEIVER_LABELS[x],
        )

        c3, c4 = st.columns(2)
        with c3:
            booking_price_text = st.text_input(
                "Цена брони",
                placeholder="0",
            )
        with c4:
            amount_received_text = st.text_input(
                "Получено",
                placeholder="0",
            )

        c5, c6, c7 = st.columns(3)
        with c5:
            currency = st.selectbox("Валюта", CURRENCY_OPTIONS)
        with c6:
            adults_count = st.number_input(
                "Взрослые",
                min_value=0,
                value=1,
                step=1,
            )
        with c7:
            children_count = st.number_input(
                "Дети",
                min_value=0,
                value=0,
                step=1,
            )

        breakfast = st.selectbox("Завтрак", BREAKFAST_OPTIONS)

        payment_status = st.selectbox(
            "Статус оплаты",
            list(PAYMENT_STATUS_LABELS.keys()),
            format_func=lambda x: PAYMENT_STATUS_LABELS[x],
        )

        notes = st.text_area(
            "Запросы гостя / комментарий",
            placeholder=(
                "Доп. бельё, раскладная кровать, поздний выезд, нужна уборка, "
                "проблемы в номере..."
            ),
        )

        submitted = st.form_submit_button("Отправить отчёт")

        if submitted:
            try:
                booking_price = _parse_amount(booking_price_text, "Цена брони")
                amount_received = _parse_amount(amount_received_text, "Получено")

                report_service.create_report(
                    manager_id=manager_options[selected_manager],
                    room_id=room_options[selected_room],
                    guest_name=guest_name,
                    guest_phone=guest_phone,
                    checkin_date=str(checkin_date),
                    checkout_date=str(checkout_date),
                    source_channel=source_channel,
                    booking_status=booking_status,
                    payment_method=payment_method,
                    money_receiver=money_receiver,
                    booking_price=booking_price,
                    amount_received=amount_received,
                    payment_status=payment_status,
                    notes=notes,
                    currency=currency,
                    adults_count=adults_count,
                    children_count=children_count,
                    breakfast_included=1 if breakfast == "С завтраком" else 0,
                )
                st.success("Отчёт отправлен руководителю.")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Ошибка создания отчёта: {e}")
