import os

from database.db import get_connection
from database.schema import create_all
from database.seed import seed_all

from repositories.owner_repository import OwnerRepository
from repositories.booking_repository import BookingRepository
from repositories.apartment_repository import ApartmentRepository
from repositories.expense_rule_repository import ExpenseRuleRepository

from services.booking_service import BookingService
from services.finance_service import FinanceService
from services.expense_service import ExpenseService
from services.owner_payout_service import OwnerPayoutService
from services.debt_service import DebtService


def main():
    if os.path.exists("app.db"):
        os.remove("app.db")

    conn = get_connection("app.db")

    print("Создаем полную schema...")
    create_all(conn)

    print("Запускаем seed...")
    seed_all(conn, tenant_id=1)

    owner_repo = OwnerRepository(conn)
    booking_repo = BookingRepository(conn)
    apartment_repo = ApartmentRepository(conn)
    expense_rule_repo = ExpenseRuleRepository(conn)

    booking_service = BookingService(conn)
    finance_service = FinanceService(conn)
    expense_service = ExpenseService(conn)
    owner_payout_service = OwnerPayoutService(conn)
    debt_service = DebtService(conn)

    print("\n--- СОЗДАЕМ БРОНИРОВАНИЕ ЧЕРЕЗ SERVICE ---")
    booking_id = booking_service.create_booking(
        apartment_id=1,
        guest_name="Alice Smith",
        check_in="2026-05-01",
        check_out="2026-05-03",
        total_amount=300,
    )
    print(f"Создано бронирование ID: {booking_id}")

    print("\n--- ДОБАВЛЯЕМ НОВЫЙ РАСХОД ДЛЯ BOOKING ID = 2 ---")
    expense_id = expense_service.create_expense(
        booking_id=2,
        expense_type="cleaning",
        amount=25,
    )
    print(f"Создан расход ID: {expense_id}")

    print("\n--- ПРОБУЕМ СОЗДАТЬ НЕВАЛИДНЫЙ РАСХОД ---")
    try:
        expense_service.create_expense(
            booking_id=999,
            expense_type="",
            amount=-10,
        )
    except ValueError as e:
        print(f"Ошибка расхода: {e}")

    print("\n--- ПРОБУЕМ НЕВАЛИДНОЕ БРОНИРОВАНИЕ ---")
    try:
        booking_service.create_booking(
            apartment_id=1,
            guest_name="",
            check_in="2026-06-10",
            check_out="2026-06-08",
            total_amount=-50,
        )
    except ValueError as e:
        print(f"Ошибка: {e}")

    print("\n--- ПРОБУЕМ OVERLAP ---")
    try:
        booking_service.create_booking(
            apartment_id=1,
            guest_name="Overlap Guest",
            check_in="2026-04-02",
            check_out="2026-04-04",
            total_amount=200,
        )
    except ValueError as e:
        print(f"Ошибка: {e}")

    print("\n--- СОЗДАЕМ OWNER PAYOUT ДЛЯ BOOKING 1 ---")
    payout_1_id = owner_payout_service.create_payout_for_booking(1)
    print(f"Создан owner payout ID: {payout_1_id}")

    print("\n--- СОЗДАЕМ OWNER PAYOUT ДЛЯ BOOKING 2 ---")
    payout_2_id = owner_payout_service.create_payout_for_booking(2)
    print(f"Создан owner payout ID: {payout_2_id}")

    print("\n--- СОЗДАЕМ DEBT ИЗ PAYOUT 1 ---")
    debt_1_id = debt_service.create_owner_debt_from_payout(1)
    print(f"Создан debt ID: {debt_1_id}")

    print("\n--- СОЗДАЕМ DEBT ИЗ PAYOUT 2 ---")
    debt_2_id = debt_service.create_owner_debt_from_payout(2)
    print(f"Создан debt ID: {debt_2_id}")

    print("\n--- MARK PAYOUT 1 AS PAID ---")
    owner_payout_service.mark_payout_as_paid(1)
    print("Payout 1 marked as paid")

    print("\n--- MARK DEBT 1 AS SETTLED ---")
    debt_service.mark_debt_as_settled(1)
    print("Debt 1 marked as settled")

    print("\n--- ПРОВЕРКА ---")

    print("\nOWNERS:")
    owners = owner_repo.get_all()
    for owner in owners:
        print(owner)

    print("\nAPARTMENTS:")
    apartments = apartment_repo.get_all()
    for apartment in apartments:
        print(apartment)

    print("\nBOOKINGS:")
    bookings = booking_repo.get_all()
    for booking in bookings:
        print(booking)

    print("\nEXPENSE RULES:")
    for rule in expense_rule_repo.get_all():
        print(rule)

    print("\nEXPENSES:")
    for expense in expense_service.get_all_expenses():
        print(expense)

    print("\nAVAILABLE APARTMENTS (2026-04-02 → 2026-04-04):")
    for a in apartment_repo.get_available_between("2026-04-02", "2026-04-04"):
        print(a)

    print("\nAVAILABLE APARTMENTS (2026-06-10 → 2026-06-12):")
    for a in apartment_repo.get_available_between("2026-06-10", "2026-06-12"):
        print(a)

    print("\n--- ФИНАНСОВЫЙ РАСЧЕТ С RESPONSIBILITY RULES ---")
    apartments_by_id = {a["id"]: a for a in apartments}

    for booking in bookings:
        apartment = apartments_by_id[booking["apartment_id"]]
        result = finance_service.calculate_split(booking, apartment)
        print(result)

    print("\n--- OWNER PAYOUTS ---")
    for payout in owner_payout_service.get_all_payouts():
        print(payout)

    print("\n--- DEBTS ---")
    for debt in debt_service.get_all_debts():
        print(debt)

    print("\n--- OWNER BALANCE SUMMARY FOR OWNER ID = 1 ---")
    balance_summary = debt_service.get_owner_balance_summary(1)
    print(balance_summary)

    conn.close()

    print("\nГотово.")


if __name__ == "__main__":
    main()