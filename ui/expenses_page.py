import streamlit as st

from services.actor_service import ActorService
from services.booking_service import BookingService
from services.expense_service import ExpenseService
from services.finance_service import FinanceService


EXPENSE_STATUS_LABELS = {
    "draft": "Черновик",
    "approved": "Подтверждён",
    "paid": "Оплачен",
    "cancelled": "Отменён",
}

RESPONSIBILITY_MODE_LABELS = {
    "company": "Компания",
    "owner": "Собственник",
    "guest": "Гость",
    "split": "Разделить",
    "manual_override": "Ручное распределение",
    "net_pool": "Общий pool",
}

EXPENSE_TYPE_PRESETS = {
    "cleaning": "Уборка",
    "laundry": "Стирка",
    "breakfast": "Завтрак",
    "consumables": "Расходники",
    "transfer": "Трансфер",
    "maintenance": "Мелкий ремонт",
    "guest_damage": "Ущерб от гостя",
    "utilities": "Коммунальные",
    "refund": "Возврат",
    "other": "Другое",
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


def render_expenses_page(conn):
    expense_service = ExpenseService(conn)
    booking_service = BookingService(conn)
    actor_service = ActorService(conn)
    finance_service = FinanceService(conn)

    st.subheader("Расходы")
    st.caption("Быстро добавляем расход и сразу смотрим, как он влияет на бронь.")

    try:
        expenses = expense_service.get_all_expenses()
        bookings = booking_service.get_all_bookings()
        actors = actor_service.get_active_actors()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    booking_map = {booking["id"]: booking for booking in bookings}

    # ---------------------------------------------------------
    # БЫСТРОЕ ДОБАВЛЕНИЕ РАСХОДА
    # ---------------------------------------------------------
    st.markdown("### Быстро добавить расход")

    if not bookings:
        st.warning("Сначала создай хотя бы одну бронь.")
    else:
        booking_options = {
            f"{booking['id']} - {booking.get('guest_name') or 'Без имени'} - {booking.get('check_in')} → {booking.get('check_out')}": booking["id"]
            for booking in bookings
        }

        actor_options = {"— не выбран —": None}
        for actor in actors:
            actor_name = actor.get("display_name") or actor.get("full_name") or f"Actor {actor['id']}"
            actor_options[f"{actor['id']} - {actor_name}"] = actor["id"]

        with st.form("quick_create_expense_form"):
            selected_booking_label = st.selectbox("Бронирование", list(booking_options.keys()))
            expense_type_code = st.selectbox(
                "Тип расхода",
                list(EXPENSE_TYPE_PRESETS.keys()),
                format_func=lambda x: EXPENSE_TYPE_PRESETS[x],
            )

            amount_text = st.text_input(
                "Сумма расхода",
                value="",
                placeholder="Например: 20",
            )

            responsibility_mode = st.selectbox(
                "Кто платит",
                ["company", "owner", "guest", "split", "net_pool", "manual_override"],
                format_func=lambda x: RESPONSIBILITY_MODE_LABELS.get(x, x),
            )

            owner_share_text = ""
            company_share_text = ""
            guest_share_text = ""

            if responsibility_mode == "manual_override":
                st.caption("Заполни вручную. Сумма долей должна совпасть с суммой расхода.")
                c1, c2, c3 = st.columns(3)
                with c1:
                    owner_share_text = st.text_input(
                        "Доля собственника",
                        value="",
                        placeholder="Например: 10",
                    )
                with c2:
                    company_share_text = st.text_input(
                        "Доля компании",
                        value="",
                        placeholder="Например: 10",
                    )
                with c3:
                    guest_share_text = st.text_input(
                        "Доля гостя",
                        value="",
                        placeholder="Например: 0",
                    )

            elif responsibility_mode == "split":
                st.caption("Расход делится между собственником и компанией.")
                c1, c2 = st.columns(2)
                with c1:
                    owner_share_text = st.text_input(
                        "Собственник",
                        value="",
                        placeholder="Например: 5",
                    )
                with c2:
                    company_share_text = st.text_input(
                        "Компания",
                        value="",
                        placeholder="Например: 15",
                    )

            created_by_label = st.selectbox("Кто создал расход", list(actor_options.keys()))
            submitted = st.form_submit_button("Добавить расход")

            if submitted:
                try:
                    booking_id = booking_options[selected_booking_label]
                    created_by_actor_id = actor_options[created_by_label]

                    amount = _parse_money_input(
                        amount_text,
                        "Сумма расхода",
                        allow_zero=False,
                    )

                    owner_share_gel = 0.0
                    company_share_gel = 0.0
                    guest_share_gel = 0.0

                    if responsibility_mode == "company":
                        company_share_gel = amount

                    elif responsibility_mode == "owner":
                        owner_share_gel = amount

                    elif responsibility_mode == "guest":
                        guest_share_gel = amount

                    elif responsibility_mode == "net_pool":
                        company_share_gel = amount

                    elif responsibility_mode == "split":
                        owner_share_gel = _parse_money_input(
                            owner_share_text,
                            "Доля собственника",
                            allow_zero=True,
                        )
                        company_share_gel = _parse_money_input(
                            company_share_text,
                            "Доля компании",
                            allow_zero=True,
                        )

                        total_shares = round(owner_share_gel + company_share_gel, 2)
                        if round(amount, 2) != total_shares:
                            raise ValueError("Сумма долей собственника и компании должна быть равна сумме расхода.")

                    elif responsibility_mode == "manual_override":
                        owner_share_gel = _parse_money_input(
                            owner_share_text,
                            "Доля собственника",
                            allow_zero=True,
                        )
                        company_share_gel = _parse_money_input(
                            company_share_text,
                            "Доля компании",
                            allow_zero=True,
                        )
                        guest_share_gel = _parse_money_input(
                            guest_share_text,
                            "Доля гостя",
                            allow_zero=True,
                        )

                        total_shares = round(owner_share_gel + company_share_gel + guest_share_gel, 2)
                        if round(amount, 2) != total_shares:
                            raise ValueError("Сумма долей должна быть равна сумме расхода.")

                    expense_id = expense_service.create_expense(
                        booking_id=booking_id,
                        expense_type=expense_type_code,
                        amount=amount,
                        responsibility_mode_snapshot=responsibility_mode,
                        owner_share_gel=owner_share_gel if responsibility_mode in {"manual_override", "split", "owner"} else None,
                        company_share_gel=company_share_gel if responsibility_mode in {"manual_override", "split", "company", "net_pool"} else None,
                        guest_share_gel=guest_share_gel if responsibility_mode in {"manual_override", "guest"} else None,
                        created_by_actor_id=created_by_actor_id,
                        use_manual_override=responsibility_mode in {"manual_override", "split", "owner", "company", "guest", "net_pool"},
                    )

                    finance_service.calculate_booking_finances(
                        booking_id=booking_id,
                        persist_snapshot=True,
                    )

                    st.success(f"Расход создан. ID = {expense_id}")
                    st.rerun()

                except Exception as e:
                    st.error(f"Ошибка создания расхода: {e}")

    # ---------------------------------------------------------
    # СПИСОК РАСХОДОВ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Список расходов")

    rows = []
    for expense in expenses:
        booking = booking_map.get(expense["booking_id"])

        rows.append({
            "ID": expense["id"],
            "Бронь": expense["booking_id"],
            "Гость": booking.get("guest_name") if booking else "-",
            "Тип": _label(expense.get("expense_type"), EXPENSE_TYPE_PRESETS, expense.get("expense_type") or "-"),
            "Сумма": _safe_round(expense.get("amount")),
            "Режим": _label(expense.get("responsibility_mode_snapshot"), RESPONSIBILITY_MODE_LABELS),
            "Компания": _safe_round(expense.get("company_share_gel")),
            "Собственник": _safe_round(expense.get("owner_share_gel")),
            "Гость": _safe_round(expense.get("guest_share_gel")),
            "Статус": _label(expense.get("status"), EXPENSE_STATUS_LABELS),
        })

    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Пока нет расходов.")

    # ---------------------------------------------------------
    # УПРАВЛЕНИЕ СТАТУСОМ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Управление статусом расхода")

    if expenses:
        expense_options = {
            f"{expense['id']} - {expense.get('expense_type') or '-'} - {expense.get('amount') or 0}": expense["id"]
            for expense in expenses
        }

        selected_expense_label = st.selectbox("Выбери расход", list(expense_options.keys()))
        selected_expense_id = expense_options[selected_expense_label]

        selected_expense = None
        for expense in expenses:
            if expense["id"] == selected_expense_id:
                selected_expense = expense
                break

        c1, c2, c3 = st.columns(3)

        if c1.button("Подтвердить расход"):
            try:
                expense_service.approve_expense(selected_expense_id)

                if selected_expense:
                    finance_service.calculate_booking_finances(
                        booking_id=selected_expense["booking_id"],
                        persist_snapshot=True,
                    )

                st.success("Расход подтверждён.")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка подтверждения: {e}")

        if c2.button("Отметить как оплаченный"):
            try:
                expense_service.mark_expense_as_paid(selected_expense_id)

                if selected_expense:
                    finance_service.calculate_booking_finances(
                        booking_id=selected_expense["booking_id"],
                        persist_snapshot=True,
                    )

                st.success("Расход отмечен как оплаченный.")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка оплаты: {e}")

        if c3.button("Отменить расход"):
            try:
                expense_service.cancel_expense(selected_expense_id)

                if selected_expense:
                    finance_service.calculate_booking_finances(
                        booking_id=selected_expense["booking_id"],
                        persist_snapshot=True,
                    )

                st.success("Расход отменён.")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка отмены: {e}")

    else:
        st.info("Нет расходов для управления статусом.")

    # ---------------------------------------------------------
    # ПРОВЕРКА ВЛИЯНИЯ НА ФИНАНСЫ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Проверка влияния расхода на бронь")

    if bookings:
        booking_options_for_check = {
            f"{booking['id']} - {booking.get('guest_name') or 'Без имени'} - {booking.get('check_in')} → {booking.get('check_out')}": booking["id"]
            for booking in bookings
        }

        selected_booking_check_label = st.selectbox(
            "Выбери бронь",
            list(booking_options_for_check.keys()),
            key="expense_finance_check",
        )
        booking_id_for_check = booking_options_for_check[selected_booking_check_label]
        booking = _get_booking_by_id(bookings, booking_id_for_check)

        try:
            finance = finance_service.calculate_booking_finances(
                booking_id_for_check,
                persist_snapshot=False,
            )

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Сумма гостя", _safe_round(finance.get("guest_price")))
                st.metric("Settlement base", _safe_round(finance.get("settlement_base_amount")))
                st.metric("Выплата собственнику", _safe_round(finance.get("owner_amount_due")))
                st.metric("Расходы собственника", _safe_round(finance.get("owner_expenses_total")))

            with c2:
                st.metric("OTA total", _safe_round(finance.get("ota_total_amount")))
                st.metric("Расходы компании", _safe_round(finance.get("company_expenses_total")))
                st.metric("Доход компании до менеджера", _safe_round(finance.get("company_before_manager")))
                st.metric("Чистая прибыль компании", _safe_round(finance.get("distributable_profit_amount")))

            st.markdown("#### Информация по брони")
            st.json({
                "ID брони": booking_id_for_check,
                "Гость": booking.get("guest_name") if booking else "-",
                "Источник": booking.get("source_channel") if booking else "-",
                "Тип аренды": booking.get("stay_type") if booking else "-",
                "Стратегия": finance.get("strategy_type") or "-",
            })

            st.markdown("#### Детализация расходов")
            expense_lines = finance.get("expense_lines") or []
            if expense_lines:
                st.dataframe(expense_lines, use_container_width=True)
            else:
                st.info("По этой брони пока нет расходов.")

        except Exception as e:
            st.error(f"Ошибка расчёта влияния на бронь: {e}")
    else:
        st.info("Пока нет бронирований.")