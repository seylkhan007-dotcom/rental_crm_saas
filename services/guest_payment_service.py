from datetime import date

from repositories.booking_repository import BookingRepository
from repositories.guest_payment_repository import GuestPaymentRepository
from services.finance_service import FinanceService


class GuestPaymentService:
    ALLOWED_STATUSES = {"pending", "received", "approved", "paid"}

    def __init__(self, conn):
        self.guest_payment_repo = GuestPaymentRepository(conn)
        self.booking_repo = BookingRepository(conn)
        self.finance_service = FinanceService(conn)

    def create_payment(
        self,
        booking_id: int,
        amount_original: float,
        currency_code: str,
        fx_rate_to_gel: float,
        payment_method: str,
        notes: str | None = None,
        payment_date: str | None = None,
        status: str = "received",
    ) -> int:
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")

        amount_original = float(amount_original or 0)
        if amount_original <= 0:
            raise ValueError("Сумма платежа должна быть больше нуля.")

        fx_rate_to_gel = float(fx_rate_to_gel or 0)
        if fx_rate_to_gel <= 0:
            raise ValueError("Курс к GEL должен быть больше нуля.")

        normalized_currency_code = (currency_code or "").strip().upper()
        if not normalized_currency_code:
            raise ValueError("Валюта платежа обязательна.")

        normalized_payment_method = (payment_method or "").strip()
        if not normalized_payment_method:
            raise ValueError("Способ оплаты обязателен.")

        normalized_status = (status or "received").strip()
        if normalized_status not in self.ALLOWED_STATUSES:
            raise ValueError("Некорректный статус платежа гостя.")

        normalized_notes = (notes or "").strip() or None
        normalized_payment_date = (payment_date or date.today().isoformat()).strip()

        amount_gel = round(amount_original * fx_rate_to_gel, 2)

        finance = self.finance_service.calculate_booking_finances(
            booking_id=booking_id,
            persist_snapshot=False,
        )
        total_due = round(float(finance.get("guest_price") or 0), 2)
        already_received = round(
            self.guest_payment_repo.get_total_received_by_booking_id(booking_id),
            2,
        )
        remaining_due = round(total_due - already_received, 2)

        if remaining_due <= 0:
            raise ValueError("По этой брони больше нет долга гостя.")

        if amount_gel > remaining_due:
            raise ValueError(
                f"Сумма платежа больше остатка долга. Остаток: {remaining_due}"
            )

        payment_id = self.guest_payment_repo.create(
            booking_id=booking_id,
            payment_date=normalized_payment_date,
            payment_method=normalized_payment_method,
            amount_original=amount_original,
            currency_code=normalized_currency_code,
            fx_rate_to_gel=fx_rate_to_gel,
            amount_gel=amount_gel,
            status=normalized_status,
            notes=normalized_notes,
        )

        self.finance_service.calculate_booking_finances(
            booking_id=booking_id,
            persist_snapshot=True,
        )

        return payment_id

    def get_all_guest_payments(self):
        return self.guest_payment_repo.get_all()

    def get_total_received_by_booking_id(self, booking_id: int) -> float:
        return self.guest_payment_repo.get_total_received_by_booking_id(booking_id)
