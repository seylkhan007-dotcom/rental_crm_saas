from services.owner_service import OwnerService
from services.booking_service import BookingService
from services.finance_service import FinanceService


class OwnerStatementService:
    """Сервис отчёта по собственнику.

    Возвращает:
    - сводку по собственнику
    - список броней собственника
    - начислено / выплачено / долг
    """

    def __init__(self, conn):
        self.conn = conn
        self.owner_service = OwnerService(conn)
        self.booking_service = BookingService(conn)
        self.finance_service = FinanceService(conn)

    def get_owner_statement(self, owner_id: int) -> dict:
        owner = self.owner_service.get_owner_by_id(owner_id)
        bookings = self.booking_service.get_all_bookings()

        total_accrued = 0.0
        total_paid = 0.0
        total_debt = 0.0
        booking_rows = []

        for booking in bookings:
            apartment = self.booking_service.get_apartment_by_booking(booking["id"])
            if not apartment:
                continue

            if apartment.get("owner_id") != owner_id:
                continue

            finance = self.finance_service.calculate_booking_finances(
                booking["id"],
                persist_snapshot=False,
            )

            accrued = float(finance.get("owner_amount") or 0)
            debt = float(finance.get("owner_balance_gel") or 0)
            paid = accrued - debt

            total_accrued += accrued
            total_paid += paid
            total_debt += debt

            booking_rows.append({
                "booking_id": booking["id"],
                "guest_name": booking.get("guest_name"),
                "apartment_name": apartment.get("name"),
                "check_in": booking.get("check_in"),
                "check_out": booking.get("check_out"),
                "accrued": round(accrued, 2),
                "paid": round(paid, 2),
                "debt": round(debt, 2),
            })

        booking_rows.sort(key=lambda x: (x["check_in"] or "", x["booking_id"]), reverse=True)

        return {
            "owner": owner,
            "summary": {
                "total_accrued": round(total_accrued, 2),
                "total_paid": round(total_paid, 2),
                "total_debt": round(total_debt, 2),
                "bookings_count": len(booking_rows),
            },
            "bookings": booking_rows,
        }