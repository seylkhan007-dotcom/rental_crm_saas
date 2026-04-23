from datetime import datetime, timedelta

from services.apartment_service import ApartmentService
from services.booking_service import BookingService
from services.owner_service import OwnerService


class CalendarService:
    """Сервис календаря бронирований.

    Отдаёт данные для календарного экрана:
    - список дат в диапазоне
    - список квартир
    - бронирования по квартирам
    - занято / свободно по дням
    """

    def __init__(self, conn):
        self.conn = conn
        self.apartment_service = ApartmentService(conn)
        self.booking_service = BookingService(conn)
        self.owner_service = OwnerService(conn)

    def build_calendar_view(self, date_from: str, date_to: str) -> dict:
        """Построить календарное представление по диапазону дат.

        Логика:
        - строки = квартиры
        - колонки = даты
        - ячейка содержит статус:
          free / occupied / check_in / check_out / inside
        """

        start_date = self._parse_date(date_from)
        end_date = self._parse_date(date_to)

        if end_date < start_date:
            raise ValueError("Дата окончания не может быть раньше даты начала.")

        apartments = self.apartment_service.get_all_apartments()
        owners = self.owner_service.get_all_owners()
        bookings = self.booking_service.get_all_bookings()

        owner_map = {owner["id"]: owner["name"] for owner in owners}

        days = self._build_days_range(start_date, end_date)

        apartment_rows = []
        for apartment in apartments:
            apartment_rows.append({
                "apartment_id": apartment["id"],
                "apartment_name": apartment.get("name"),
                "owner_id": apartment.get("owner_id"),
                "owner_name": owner_map.get(apartment.get("owner_id"), "-"),
                "complex_id": apartment.get("complex_id"),
            })

        apartment_rows.sort(key=lambda x: (x["owner_name"] or "", x["apartment_name"] or ""))

        calendar_rows = []

        for apartment in apartment_rows:
            apartment_id = apartment["apartment_id"]

            apartment_bookings = []
            for booking in bookings:
                if booking.get("apartment_id") != apartment_id:
                    continue

                booking_check_in = booking.get("check_in")
                booking_check_out = booking.get("check_out")

                if not booking_check_in or not booking_check_out:
                    continue

                booking_start = self._parse_date(booking_check_in)
                booking_end = self._parse_date(booking_check_out)

                # если бронь вообще не пересекает диапазон календаря — пропускаем
                if booking_end <= start_date or booking_start > end_date:
                    continue

                apartment_bookings.append({
                    "booking_id": booking["id"],
                    "guest_name": booking.get("guest_name"),
                    "check_in": booking_check_in,
                    "check_out": booking_check_out,
                    "pricing_model": booking.get("pricing_model"),
                    "stay_type": booking.get("stay_type"),
                    "source_channel": booking.get("source_channel"),
                })

            day_cells = []
            for day in days:
                cell = self._build_day_cell(
                    target_day=day,
                    bookings=apartment_bookings,
                )
                day_cells.append(cell)

            calendar_rows.append({
                "apartment_id": apartment["apartment_id"],
                "apartment_name": apartment["apartment_name"],
                "owner_name": apartment["owner_name"],
                "bookings": apartment_bookings,
                "days": day_cells,
            })

        return {
            "date_from": date_from,
            "date_to": date_to,
            "days": [d.strftime("%Y-%m-%d") for d in days],
            "rows": calendar_rows,
        }

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _build_days_range(self, start_date, end_date):
        days = []
        current = start_date
        while current <= end_date:
            days.append(current)
            current += timedelta(days=1)
        return days

    def _build_day_cell(self, target_day, bookings: list[dict]) -> dict:
        """Определить, что происходит в конкретной ячейке календаря."""

        for booking in bookings:
            check_in = self._parse_date(booking["check_in"])
            check_out = self._parse_date(booking["check_out"])

            # модель:
            # check_in день заезда
            # check_out день выезда
            # между ними ночи заняты
            if target_day == check_in:
                return {
                    "status": "check_in",
                    "booking_id": booking["booking_id"],
                    "guest_name": booking.get("guest_name"),
                    "label": f"Заезд: {booking.get('guest_name') or '-'}",
                }

            if target_day == check_out:
                return {
                    "status": "check_out",
                    "booking_id": booking["booking_id"],
                    "guest_name": booking.get("guest_name"),
                    "label": f"Выезд: {booking.get('guest_name') or '-'}",
                }

            if check_in < target_day < check_out:
                return {
                    "status": "occupied",
                    "booking_id": booking["booking_id"],
                    "guest_name": booking.get("guest_name"),
                    "label": booking.get("guest_name") or "Занято",
                }

        return {
            "status": "free",
            "booking_id": None,
            "guest_name": None,
            "label": "",
        }

    def _parse_date(self, value: str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            raise ValueError(f"Некорректная дата: {value}")