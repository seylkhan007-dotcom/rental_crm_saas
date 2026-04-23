from repositories.apartment_repository import ApartmentRepository
from repositories.booking_repository import BookingRepository
from repositories.owner_payout_repository import OwnerPayoutRepository
from services.finance_service import FinanceService


class OwnerPayoutService:
    def __init__(self, conn):
        self.owner_payout_repo = OwnerPayoutRepository(conn)
        self.booking_repo = BookingRepository(conn)
        self.apartment_repo = ApartmentRepository(conn)
        self.finance_service = FinanceService(conn)

    def create_payout(self, owner_id: int, booking_id: int, amount: float):
        existing_payout = self._find_existing_payout_by_booking_id(booking_id)
        if existing_payout:
            raise ValueError(
                f"Для booking_id={booking_id} owner payout уже существует"
            )

        return self.owner_payout_repo.create(
            owner_id=owner_id,
            booking_id=booking_id,
            amount=amount,
            status="pending",
        )

    def create_payout_for_booking(self, booking_id: int):
        booking = self._get_booking_or_raise(booking_id)
        apartment = self._get_apartment_or_raise(booking["apartment_id"])

        existing_payout = self._find_existing_payout_by_booking_id(booking_id)
        if existing_payout:
            raise ValueError(
                f"Для booking_id={booking_id} owner payout уже существует"
            )

        finance_result = self.finance_service.calculate_booking_finances(booking_id)

        if finance_result.get("pricing_model") == "sublease":
            raise ValueError(
                "Для pricing_model='sublease' booking-based owner payout сейчас не поддерживается. "
                "Нужна отдельная логика fixed rent / daily rent obligations."
            )

        owner_id = apartment["owner_id"]
        owner_amount = finance_result["owner_amount"]

        return self.owner_payout_repo.create(
            owner_id=owner_id,
            booking_id=booking_id,
            amount=owner_amount,
            status="pending",
        )

    def create_manual_payout(
        self,
        booking_id: int,
        amount_paid_gel: float,
        currency_code: str = "GEL",
        fx_rate_to_gel: float = 1.0,
    ) -> int:
        booking = self._get_booking_or_raise(booking_id)
        apartment = self._get_apartment_or_raise(booking["apartment_id"])

        owner_id = apartment.get("owner_id")
        if not owner_id:
            raise ValueError("У квартиры не найден собственник.")

        amount_paid_gel = round(float(amount_paid_gel or 0), 2)
        if amount_paid_gel <= 0:
            raise ValueError("Сумма выплаты должна быть больше нуля.")

        normalized_currency_code = (currency_code or "GEL").strip().upper()
        if not normalized_currency_code:
            raise ValueError("Валюта выплаты обязательна.")

        fx_rate_to_gel = float(fx_rate_to_gel or 0)
        if fx_rate_to_gel <= 0:
            raise ValueError("Курс к GEL должен быть больше нуля.")

        finance = self.finance_service.calculate_booking_finances(
            booking_id=booking_id,
            persist_snapshot=False,
        )

        total_due = round(float(finance.get("owner_amount_due") or 0), 2)
        already_paid = round(
            self.owner_payout_repo.get_total_paid_by_booking_id(booking_id),
            2,
        )
        remaining_due = round(total_due - already_paid, 2)

        if remaining_due <= 0:
            raise ValueError(
                "По этой брони больше нет долга перед собственником."
            )

        if amount_paid_gel > remaining_due:
            raise ValueError(
                f"Сумма выплаты больше остатка долга. Остаток: {remaining_due}"
            )

        new_total_paid = round(already_paid + amount_paid_gel, 2)
        payout_status = "paid" if new_total_paid >= total_due else "partial"

        return self.owner_payout_repo.create_manual_payout(
            owner_id=owner_id,
            booking_id=booking_id,
            amount_due_gel=total_due,
            amount_paid_gel=amount_paid_gel,
            currency_code=normalized_currency_code,
            fx_rate_to_gel=fx_rate_to_gel,
            status=payout_status,
        )

    def get_all_payouts(self):
        return self.owner_payout_repo.get_all()

    def get_payouts_by_owner_id(self, owner_id: int):
        return self.owner_payout_repo.get_by_owner_id(owner_id)

    def get_total_paid_by_booking_id(self, booking_id: int) -> float:
        return self.owner_payout_repo.get_total_paid_by_booking_id(booking_id)

    def mark_payout_as_paid(self, payout_id: int):
        self.owner_payout_repo.mark_as_paid(payout_id)

    def _get_booking_or_raise(self, booking_id: int):
        booking = self.booking_repo.get_by_id(booking_id)
        if booking:
            return booking
        raise ValueError("booking_id не существует")

    def _get_apartment_or_raise(self, apartment_id: int):
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if apartment:
            return apartment
        raise ValueError("apartment для booking не найден")

    def _find_existing_payout_by_booking_id(self, booking_id: int):
        payouts = self.owner_payout_repo.get_all()

        for payout in payouts:
            if payout["booking_id"] == booking_id:
                return payout

        return None
