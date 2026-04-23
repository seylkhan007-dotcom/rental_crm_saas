# services/owner_payout_service.py

from repositories.owner_payout_repository import OwnerPayoutRepository
from repositories.booking_repository import BookingRepository
from repositories.apartment_repository import ApartmentRepository
from services.finance_service import FinanceService


class OwnerPayoutService:
    def __init__(self, conn):
        self.owner_payout_repo = OwnerPayoutRepository(conn)
        self.booking_repo = BookingRepository(conn)
        self.apartment_repo = ApartmentRepository(conn)
        self.finance_service = FinanceService(conn)

    def create_payout(self, owner_id: int, booking_id: int, amount: float):
        """
        Универсальное создание payout.
        Используется новым booking_service.py
        """

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
        """
        Legacy + ручной режим.
        Оставляем для совместимости со старым кодом.
        """

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

    def get_all_payouts(self):
        return self.owner_payout_repo.get_all()

    def get_payouts_by_owner_id(self, owner_id: int):
        return self.owner_payout_repo.get_by_owner_id(owner_id)

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