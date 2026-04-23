from services.booking_service import BookingService
from services.finance_service import FinanceService
from services.owner_service import OwnerService
from services.apartment_service import ApartmentService


class ReportService:
    """Сервис отчётов и аналитики по периоду.

    Возвращает:
    - общие KPI за период
    - разбивку по квартирам
    - разбивку по собственникам
    - список броней за период
    """

    def __init__(self, conn):
        self.conn = conn
        self.booking_service = BookingService(conn)
        self.finance_service = FinanceService(conn)
        self.owner_service = OwnerService(conn)
        self.apartment_service = ApartmentService(conn)

    def build_period_report(self, date_from: str, date_to: str) -> dict:
        """Собрать отчёт за период по датам заезда.

        Логика периода сейчас простая:
        - берём брони, у которых check_in попадает в диапазон
        """

        all_bookings = self.booking_service.get_all_bookings()
        owners = self.owner_service.get_all_owners()
        apartments = self.apartment_service.get_all_apartments()

        owner_map = {owner["id"]: owner for owner in owners}
        apartment_map = {apartment["id"]: apartment for apartment in apartments}

        filtered_bookings = []
        for booking in all_bookings:
            check_in = booking.get("check_in")
            if not check_in:
                continue

            if date_from <= check_in <= date_to:
                filtered_bookings.append(booking)

        total_guest_income = 0.0
        total_owner_accrual = 0.0
        total_company_expenses = 0.0
        total_manager_payout = 0.0
        total_net_profit = 0.0
        total_guest_debt = 0.0
        total_owner_debt = 0.0

        bookings_rows = []
        apartments_summary = {}
        owners_summary = {}

        for booking in filtered_bookings:
            finance = self.finance_service.calculate_booking_finances(
                booking["id"],
                persist_snapshot=False,
            )

            apartment = apartment_map.get(booking["apartment_id"])
            apartment_name = apartment.get("name") if apartment else "-"
            owner_id = apartment.get("owner_id") if apartment else None
            owner_name = owner_map.get(owner_id, {}).get("name", "-") if owner_id else "-"

            guest_income = float(finance.get("guest_price") or 0)
            owner_accrual = float(finance.get("owner_amount") or 0)
            company_expenses = float(finance.get("company_expenses_total") or 0)
            manager_payout = float(finance.get("manager_commission_amount") or 0)
            net_profit = float(finance.get("distributable_profit_amount") or 0)
            guest_debt = float(finance.get("guest_balance_gel") or 0)
            owner_debt = float(finance.get("owner_balance_gel") or 0)

            total_guest_income += guest_income
            total_owner_accrual += owner_accrual
            total_company_expenses += company_expenses
            total_manager_payout += manager_payout
            total_net_profit += net_profit
            total_guest_debt += guest_debt
            total_owner_debt += owner_debt

            bookings_rows.append({
                "booking_id": booking["id"],
                "guest_name": booking.get("guest_name"),
                "apartment_name": apartment_name,
                "owner_name": owner_name,
                "check_in": booking.get("check_in"),
                "check_out": booking.get("check_out"),
                "guest_income": round(guest_income, 2),
                "owner_accrual": round(owner_accrual, 2),
                "company_expenses": round(company_expenses, 2),
                "manager_payout": round(manager_payout, 2),
                "net_profit": round(net_profit, 2),
                "guest_debt": round(guest_debt, 2),
                "owner_debt": round(owner_debt, 2),
            })

            if apartment:
                apartment_id = apartment["id"]
                if apartment_id not in apartments_summary:
                    apartments_summary[apartment_id] = {
                        "apartment_id": apartment_id,
                        "apartment_name": apartment_name,
                        "bookings_count": 0,
                        "guest_income": 0.0,
                        "owner_accrual": 0.0,
                        "company_expenses": 0.0,
                        "manager_payout": 0.0,
                        "net_profit": 0.0,
                    }

                apartments_summary[apartment_id]["bookings_count"] += 1
                apartments_summary[apartment_id]["guest_income"] += guest_income
                apartments_summary[apartment_id]["owner_accrual"] += owner_accrual
                apartments_summary[apartment_id]["company_expenses"] += company_expenses
                apartments_summary[apartment_id]["manager_payout"] += manager_payout
                apartments_summary[apartment_id]["net_profit"] += net_profit

            if owner_id:
                if owner_id not in owners_summary:
                    owners_summary[owner_id] = {
                        "owner_id": owner_id,
                        "owner_name": owner_name,
                        "bookings_count": 0,
                        "owner_accrual": 0.0,
                        "owner_debt": 0.0,
                    }

                owners_summary[owner_id]["bookings_count"] += 1
                owners_summary[owner_id]["owner_accrual"] += owner_accrual
                owners_summary[owner_id]["owner_debt"] += owner_debt

        apartments_rows = []
        for _, row in apartments_summary.items():
            apartments_rows.append({
                "Квартира": row["apartment_name"],
                "Броней": row["bookings_count"],
                "Доход от гостей": round(row["guest_income"], 2),
                "Начислено собственнику": round(row["owner_accrual"], 2),
                "Расходы компании": round(row["company_expenses"], 2),
                "Выплаты менеджерам": round(row["manager_payout"], 2),
                "Чистая прибыль": round(row["net_profit"], 2),
            })

        apartments_rows.sort(key=lambda x: x["Чистая прибыль"], reverse=True)

        owners_rows = []
        for _, row in owners_summary.items():
            owners_rows.append({
                "Собственник": row["owner_name"],
                "Броней": row["bookings_count"],
                "Начислено": round(row["owner_accrual"], 2),
                "Долг": round(row["owner_debt"], 2),
            })

        owners_rows.sort(key=lambda x: x["Начислено"], reverse=True)

        bookings_rows.sort(key=lambda x: (x["check_in"] or "", x["booking_id"]), reverse=True)

        return {
            "summary": {
                "date_from": date_from,
                "date_to": date_to,
                "bookings_count": len(filtered_bookings),
                "total_guest_income": round(total_guest_income, 2),
                "total_owner_accrual": round(total_owner_accrual, 2),
                "total_company_expenses": round(total_company_expenses, 2),
                "total_manager_payout": round(total_manager_payout, 2),
                "total_net_profit": round(total_net_profit, 2),
                "total_guest_debt": round(total_guest_debt, 2),
                "total_owner_debt": round(total_owner_debt, 2),
            },
            "apartments": apartments_rows,
            "owners": owners_rows,
            "bookings": bookings_rows,
        }