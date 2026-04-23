import streamlit as st

from services.booking_service import BookingService
from services.finance_service import FinanceService
from services.expense_service import ExpenseService
from services.owner_service import OwnerService


FINANCE_STATUS_LABELS = {
    "draft": "Черновик",
    "calculated": "Рассчитан",
    "finalized": "Зафиксирован",
}


def _safe_round(value):
    try:
        return round(float(value or 0), 2)
    except:
        return 0.0


def _label(code: str | None, mapping: dict, default: str = "-") -> str:
    if not code:
        return default
    return mapping.get(code, code)


def render_dashboard_page(conn):
    booking_service = BookingService(conn)
    finance_service = FinanceService(conn)
    expense_service = ExpenseService(conn)
    owner_service = OwnerService(conn)

    st.subheader("Дашборд")
    st.caption("Общий контроль по бронированиям, прибыли, долгам и расходам.")

    # ---------------------------------------------------------
    # ЗАГРУЗКА ДАННЫХ
    # ---------------------------------------------------------
    try:
        bookings = booking_service.get_all_bookings()
        expenses = expense_service.get_all_expenses()
        owners = owner_service.get_all_owners()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    # ---------------------------------------------------------
    # СВОДНЫЕ ФИНАНСОВЫЕ ПОКАЗАТЕЛИ
    # ---------------------------------------------------------
    total_guest_income = 0.0
    total_owner_accrual = 0.0
    total_company_before_manager = 0.0
    total_manager_payout = 0.0
    total_net_profit = 0.0
    total_guest_debt = 0.0
    total_owner_debt = 0.0
    bookings_with_errors = 0

    booking_rows = []

    for booking in bookings:
        try:
            finance = finance_service.calculate_booking_finances(
                booking["id"],
                persist_snapshot=False,
            )

            total_guest_income += float(finance.get("guest_price") or 0)
            total_owner_accrual += float(finance.get("owner_amount") or 0)
            total_company_before_manager += float(finance.get("company_before_manager") or 0)
            total_manager_payout += float(finance.get("manager_commission_amount") or 0)
            total_net_profit += float(finance.get("distributable_profit_amount") or 0)
            total_guest_debt += float(finance.get("guest_balance_gel") or 0)
            total_owner_debt += float(finance.get("owner_balance_gel") or 0)

            booking_rows.append({
                "ID": booking["id"],
                "Гость": booking.get("guest_name"),
                "Доход от гостя": _safe_round(finance.get("guest_price")),
                "Выплата собственнику": _safe_round(finance.get("owner_amount")),
                "Расходы компании": _safe_round(finance.get("company_expenses_total")),
                "Доход компании до менеджера": _safe_round(finance.get("company_before_manager")),
                "Выплата менеджеру": _safe_round(finance.get("manager_commission_amount")),
                "Чистая прибыль": _safe_round(finance.get("distributable_profit_amount")),
                "Долг гостя": _safe_round(finance.get("guest_balance_gel")),
                "Долг собственнику": _safe_round(finance.get("owner_balance_gel")),
                "Статус финансов": _label(booking.get("finance_status"), FINANCE_STATUS_LABELS),
            })

        except Exception as e:
            bookings_with_errors += 1
            booking_rows.append({
                "ID": booking["id"],
                "Гость": booking.get("guest_name"),
                "Ошибка": str(e),
            })

    # ---------------------------------------------------------
    # KPI
    # ---------------------------------------------------------
    st.markdown("### Ключевые показатели")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Бронирований", len(bookings))
    k2.metric("Собственников", len(owners))
    k3.metric("Расходов", len(expenses))
    k4.metric("Ошибок в расчётах", bookings_with_errors)

    k5, k6, k7 = st.columns(3)
    k5.metric("Доход от гостей", _safe_round(total_guest_income))
    k6.metric("Выплаты собственникам", _safe_round(total_owner_accrual))
    k7.metric("Доход компании до менеджера", _safe_round(total_company_before_manager))

    k8, k9, k10 = st.columns(3)
    k8.metric("Выплаты менеджерам", _safe_round(total_manager_payout))
    k9.metric("Чистая прибыль компании", _safe_round(total_net_profit))
    k10.metric(
        "Общие расходы компании",
        _safe_round(
            sum(
                float(expense.get("company_share_gel") or 0)
                for expense in expenses
                if expense.get("status") != "cancelled"
            )
        ),
    )

    k11, k12 = st.columns(2)
    k11.metric("Долг гостей", _safe_round(total_guest_debt))
    k12.metric("Долг собственникам", _safe_round(total_owner_debt))

    # ---------------------------------------------------------
    # СТРУКТУРА РАСХОДОВ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Структура расходов")

    expense_type_summary = {}
    total_owner_expenses = 0.0
    total_company_expenses = 0.0
    total_guest_expenses = 0.0

    for expense in expenses:
        if expense.get("status") == "cancelled":
            continue

        expense_type = expense.get("expense_type") or "unknown"
        amount = float(expense.get("amount") or 0)

        if expense_type not in expense_type_summary:
            expense_type_summary[expense_type] = 0.0
        expense_type_summary[expense_type] += amount

        total_owner_expenses += float(expense.get("owner_share_gel") or 0)
        total_company_expenses += float(expense.get("company_share_gel") or 0)
        total_guest_expenses += float(expense.get("guest_share_gel") or 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Расходы собственников", _safe_round(total_owner_expenses))
    c2.metric("Расходы компании", _safe_round(total_company_expenses))
    c3.metric("Расходы гостей", _safe_round(total_guest_expenses))

    if expense_type_summary:
        expense_rows = []
        for expense_type, total_amount in sorted(
            expense_type_summary.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            expense_rows.append({
                "Тип расхода": expense_type,
                "Сумма": _safe_round(total_amount),
            })
        st.dataframe(expense_rows, use_container_width=True)
    else:
        st.info("Пока нет расходов для анализа.")

    # ---------------------------------------------------------
    # БРОНИРОВАНИЯ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Бронирования")

    if booking_rows:
        st.dataframe(booking_rows, use_container_width=True)
    else:
        st.info("Пока нет бронирований.")

    # ---------------------------------------------------------
    # ДОЛГИ ПО СОБСТВЕННИКАМ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Сводка по собственникам")

    owner_summary = {}

    for booking in bookings:
        try:
            apartment = booking_service.get_apartment_by_booking(booking["id"])
            if not apartment:
                continue

            owner_id = apartment.get("owner_id")
            if not owner_id:
                continue

            finance = finance_service.calculate_booking_finances(
                booking["id"],
                persist_snapshot=False,
            )

            if owner_id not in owner_summary:
                owner_summary[owner_id] = {
                    "owner_id": owner_id,
                    "owner_name": next(
                        (owner["name"] for owner in owners if owner["id"] == owner_id),
                        f"Собственник {owner_id}",
                    ),
                    "начислено": 0.0,
                    "долг": 0.0,
                }

            owner_summary[owner_id]["начислено"] += float(finance.get("owner_amount") or 0)
            owner_summary[owner_id]["долг"] += float(finance.get("owner_balance_gel") or 0)

        except Exception:
            continue

    if owner_summary:
        owner_rows = []
        for _, data in owner_summary.items():
            owner_rows.append({
                "Собственник": data["owner_name"],
                "Начислено": _safe_round(data["начислено"]),
                "Долг": _safe_round(data["долг"]),
            })
        owner_rows.sort(key=lambda x: x["Долг"], reverse=True)
        st.dataframe(owner_rows, use_container_width=True)
    else:
        st.info("Пока нет данных по собственникам.")