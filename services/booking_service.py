from repositories.booking_repository import BookingRepository
from repositories.apartment_repository import ApartmentRepository
from repositories.contract_repository import ContractRepository
from repositories.actor_repository import ActorRepository


class BookingService:
    """Сервис бронирований.

    Логика:
    - бронь создаётся от квартиры
    - активный договор подтягивается автоматически по квартире
    - условия договора сохраняются в snapshot полях брони
    """

    ALLOWED_SOURCE_CHANNELS = {"direct", "booking_com", "whatsapp", "owner_direct"}
    ALLOWED_PRICING_MODELS = {"management", "sublease"}
    ALLOWED_STAY_TYPES = {"short_term", "long_term"}

    def __init__(self, conn):
        self.conn = conn
        self.booking_repo = BookingRepository(conn)
        self.apartment_repo = ApartmentRepository(conn)
        self.contract_repo = ContractRepository(conn)
        self.actor_repo = ActorRepository(conn)

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create_booking(
        self,
        apartment_id: int,
        guest_name: str,
        check_in: str,
        check_out: str,
        total_amount: float,
        guest_price: float | None = None,
        settlement_base_amount: float | None = None,
        tax_base_price: float | None = None,
        source_channel: str | None = None,
        ota_account_name: str | None = None,
        ota_commission_pct: float | None = None,
        ota_vat_pct: float | None = None,
        stay_type: str = "short_term",
        checkin_actor_id: int | None = None,
        manager_commission_actor_id: int | None = None,
        manager_commission_pct_snapshot: float | None = None,
    ) -> int:
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        normalized_guest_name = (guest_name or "").strip()
        if not normalized_guest_name:
            raise ValueError("Имя гостя не может быть пустым.")

        normalized_check_in = (check_in or "").strip()
        normalized_check_out = (check_out or "").strip()

        if not normalized_check_in or not normalized_check_out:
            raise ValueError("Дата заезда и дата выезда обязательны.")

        total_amount = float(total_amount or 0)
        if total_amount <= 0:
            raise ValueError("Общая сумма бронирования должна быть больше нуля.")

        if guest_price is None:
            guest_price = total_amount
        guest_price = float(guest_price or 0)
        if guest_price <= 0:
            raise ValueError("Сумма от гостя должна быть больше нуля.")

        if settlement_base_amount is None:
            settlement_base_amount = guest_price
        settlement_base_amount = float(settlement_base_amount or 0)
        if settlement_base_amount <= 0:
            raise ValueError("База расчёта с собственником должна быть больше нуля.")

        if settlement_base_amount > guest_price:
            raise ValueError("База расчёта с собственником не может быть больше цены гостя.")

        if tax_base_price is not None:
            tax_base_price = float(tax_base_price or 0)
            if tax_base_price < 0:
                raise ValueError("Налоговая база не может быть отрицательной.")

        normalized_source_channel = (source_channel or "direct").strip()
        if normalized_source_channel not in self.ALLOWED_SOURCE_CHANNELS:
            raise ValueError("Некорректный источник бронирования.")

        normalized_stay_type = (stay_type or "short_term").strip()
        if normalized_stay_type not in self.ALLOWED_STAY_TYPES:
            raise ValueError("Некорректный тип аренды.")

        if checkin_actor_id is not None:
            actor = self.actor_repo.get_by_id(checkin_actor_id)
            if not actor:
                raise ValueError("Кто заселил: участник не найден.")

        if manager_commission_actor_id is not None:
            actor = self.actor_repo.get_by_id(manager_commission_actor_id)
            if not actor:
                raise ValueError("Внешний менеджер не найден.")

        if manager_commission_pct_snapshot is None:
            manager_commission_pct_snapshot = 0.0

        manager_commission_pct_snapshot = float(manager_commission_pct_snapshot or 0)
        if manager_commission_pct_snapshot < 0 or manager_commission_pct_snapshot > 100:
            raise ValueError("Комиссия внешнего менеджера должна быть в диапазоне от 0 до 100.")

        ota_commission_pct = float(ota_commission_pct or 0)
        ota_vat_pct = float(ota_vat_pct or 0)

        if ota_commission_pct < 0 or ota_commission_pct > 100:
            raise ValueError("Комиссия OTA должна быть в диапазоне от 0 до 100.")

        if ota_vat_pct < 0 or ota_vat_pct > 100:
            raise ValueError("НДС на комиссию OTA должен быть в диапазоне от 0 до 100.")

        active_contract = self.contract_repo.get_active_profile_by_apartment_id(apartment_id)
        if not active_contract:
            raise ValueError("Для выбранной квартиры не найден активный договор.")

        contract_snapshot = self._build_contract_snapshot(active_contract)

        booking_id = self.booking_repo.create(
            apartment_id=apartment_id,
            guest_name=normalized_guest_name,
            check_in=normalized_check_in,
            check_out=normalized_check_out,
            total_amount=total_amount,
            guest_price=guest_price,
            settlement_base_amount=settlement_base_amount,
            tax_base_price=tax_base_price,
            source_channel=normalized_source_channel,
            ota_account_name=(ota_account_name or "").strip() or None,
            ota_commission_pct=ota_commission_pct,
            ota_vat_pct=ota_vat_pct,
            pricing_model=contract_snapshot["pricing_model"],
            fixed_rent_type=contract_snapshot["fixed_rent_type"],
            fixed_rent_value=contract_snapshot["fixed_rent_value"],
            contract_profile_id=active_contract["id"],
            stay_type=normalized_stay_type,
            settlement_base_mode_snapshot=contract_snapshot["settlement_base_mode"],
            profit_mode_snapshot=contract_snapshot["profit_mode"],
            owner_percent_snapshot=contract_snapshot["owner_percent"],
            company_percent_snapshot=contract_snapshot["company_percent"],
            fixed_rent_type_snapshot=contract_snapshot["fixed_rent_type"],
            fixed_rent_value_snapshot=contract_snapshot["fixed_rent_value"],
            fixed_rent_currency_snapshot=contract_snapshot["fixed_rent_currency"],
            ota_cost_mode_snapshot=contract_snapshot["ota_cost_mode"],
            expense_mode_snapshot=contract_snapshot["expense_mode"],
            checkin_actor_id=checkin_actor_id,
            manager_commission_actor_id=manager_commission_actor_id,
            manager_commission_pct_snapshot=manager_commission_pct_snapshot,
            finance_status="draft",
            finance_locked_at=None,
            finance_locked_by=None,
        )

        return booking_id

    # ---------------------------------------------------------
    # READ
    # ---------------------------------------------------------

    def get_all_bookings(self):
        return self.booking_repo.get_all()

    def get_booking_by_id(self, booking_id: int):
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")
        return booking

    def get_apartment_by_booking(self, booking_id: int):
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")

        apartment_id = booking.get("apartment_id")
        if not apartment_id:
            return None

        apartment = self.apartment_repo.get_by_id(apartment_id)
        return apartment

    def get_bookings_by_apartment_id(self, apartment_id: int):
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        return self.booking_repo.get_by_apartment_id(apartment_id)

    def get_bookings_by_date_range(self, date_from: str, date_to: str):
        normalized_from = (date_from or "").strip()
        normalized_to = (date_to or "").strip()

        if not normalized_from or not normalized_to:
            raise ValueError("Нужно указать дату начала и дату окончания.")

        return self.booking_repo.get_by_date_range(normalized_from, normalized_to)

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update_booking(
        self,
        booking_id: int,
        apartment_id: int,
        guest_name: str,
        check_in: str,
        check_out: str,
        total_amount: float,
        guest_price: float | None = None,
        settlement_base_amount: float | None = None,
        tax_base_price: float | None = None,
        source_channel: str | None = None,
        ota_account_name: str | None = None,
        ota_commission_pct: float | None = None,
        ota_vat_pct: float | None = None,
        stay_type: str = "short_term",
        checkin_actor_id: int | None = None,
        manager_commission_actor_id: int | None = None,
        manager_commission_pct_snapshot: float | None = None,
    ) -> None:
        existing_booking = self.booking_repo.get_by_id(booking_id)
        if not existing_booking:
            raise ValueError("Бронирование не найдено.")

        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        normalized_guest_name = (guest_name or "").strip()
        if not normalized_guest_name:
            raise ValueError("Имя гостя не может быть пустым.")

        normalized_check_in = (check_in or "").strip()
        normalized_check_out = (check_out or "").strip()

        if not normalized_check_in or not normalized_check_out:
            raise ValueError("Дата заезда и дата выезда обязательны.")

        total_amount = float(total_amount or 0)
        if total_amount <= 0:
            raise ValueError("Общая сумма бронирования должна быть больше нуля.")

        if guest_price is None:
            guest_price = total_amount
        guest_price = float(guest_price or 0)
        if guest_price <= 0:
            raise ValueError("Сумма от гостя должна быть больше нуля.")

        if settlement_base_amount is None:
            settlement_base_amount = guest_price
        settlement_base_amount = float(settlement_base_amount or 0)
        if settlement_base_amount <= 0:
            raise ValueError("База расчёта с собственником должна быть больше нуля.")

        if settlement_base_amount > guest_price:
            raise ValueError("База расчёта с собственником не может быть больше цены гостя.")

        if tax_base_price is not None:
            tax_base_price = float(tax_base_price or 0)
            if tax_base_price < 0:
                raise ValueError("Налоговая база не может быть отрицательной.")

        normalized_source_channel = (source_channel or "direct").strip()
        if normalized_source_channel not in self.ALLOWED_SOURCE_CHANNELS:
            raise ValueError("Некорректный источник бронирования.")

        normalized_stay_type = (stay_type or "short_term").strip()
        if normalized_stay_type not in self.ALLOWED_STAY_TYPES:
            raise ValueError("Некорректный тип аренды.")

        if checkin_actor_id is not None:
            actor = self.actor_repo.get_by_id(checkin_actor_id)
            if not actor:
                raise ValueError("Кто заселил: участник не найден.")

        if manager_commission_actor_id is not None:
            actor = self.actor_repo.get_by_id(manager_commission_actor_id)
            if not actor:
                raise ValueError("Внешний менеджер не найден.")

        if manager_commission_pct_snapshot is None:
            manager_commission_pct_snapshot = 0.0

        manager_commission_pct_snapshot = float(manager_commission_pct_snapshot or 0)
        if manager_commission_pct_snapshot < 0 or manager_commission_pct_snapshot > 100:
            raise ValueError("Комиссия внешнего менеджера должна быть в диапазоне от 0 до 100.")

        ota_commission_pct = float(ota_commission_pct or 0)
        ota_vat_pct = float(ota_vat_pct or 0)

        if ota_commission_pct < 0 or ota_commission_pct > 100:
            raise ValueError("Комиссия OTA должна быть в диапазоне от 0 до 100.")

        if ota_vat_pct < 0 or ota_vat_pct > 100:
            raise ValueError("НДС на комиссию OTA должен быть в диапазоне от 0 до 100.")

        active_contract = self.contract_repo.get_active_profile_by_apartment_id(apartment_id)
        if not active_contract:
            raise ValueError("Для выбранной квартиры не найден активный договор.")

        contract_snapshot = self._build_contract_snapshot(active_contract)

        self.booking_repo.update(
            booking_id=booking_id,
            apartment_id=apartment_id,
            guest_name=normalized_guest_name,
            check_in=normalized_check_in,
            check_out=normalized_check_out,
            total_amount=total_amount,
            guest_price=guest_price,
            settlement_base_amount=settlement_base_amount,
            tax_base_price=tax_base_price,
            source_channel=normalized_source_channel,
            ota_account_name=(ota_account_name or "").strip() or None,
            ota_commission_pct=ota_commission_pct,
            ota_vat_pct=ota_vat_pct,
            pricing_model=contract_snapshot["pricing_model"],
            fixed_rent_type=contract_snapshot["fixed_rent_type"],
            fixed_rent_value=contract_snapshot["fixed_rent_value"],
            contract_profile_id=active_contract["id"],
            stay_type=normalized_stay_type,
            settlement_base_mode_snapshot=contract_snapshot["settlement_base_mode"],
            profit_mode_snapshot=contract_snapshot["profit_mode"],
            owner_percent_snapshot=contract_snapshot["owner_percent"],
            company_percent_snapshot=contract_snapshot["company_percent"],
            fixed_rent_type_snapshot=contract_snapshot["fixed_rent_type"],
            fixed_rent_value_snapshot=contract_snapshot["fixed_rent_value"],
            fixed_rent_currency_snapshot=contract_snapshot["fixed_rent_currency"],
            ota_cost_mode_snapshot=contract_snapshot["ota_cost_mode"],
            expense_mode_snapshot=contract_snapshot["expense_mode"],
            checkin_actor_id=checkin_actor_id,
            manager_commission_actor_id=manager_commission_actor_id,
            manager_commission_pct_snapshot=manager_commission_pct_snapshot,
            finance_status="draft",
            finance_locked_at=None,
            finance_locked_by=None,
        )

    def update_finance_status(
        self,
        booking_id: int,
        finance_status: str,
        finance_locked_at: str | None = None,
        finance_locked_by: int | None = None,
    ) -> None:
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")

        self.booking_repo.update_finance_status(
            booking_id=booking_id,
            finance_status=finance_status,
            finance_locked_at=finance_locked_at,
            finance_locked_by=finance_locked_by,
        )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete_booking(self, booking_id: int) -> None:
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")

        self.booking_repo.delete(booking_id)

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _build_contract_snapshot(self, contract: dict) -> dict:
        pricing_model = (contract.get("pricing_model") or "management").strip()

        if pricing_model not in self.ALLOWED_PRICING_MODELS:
            raise ValueError("У договора некорректная модель.")

        return {
            "pricing_model": pricing_model,
            "settlement_base_mode": (contract.get("settlement_base_mode") or "from_guest_price").strip(),
            "profit_mode": (contract.get("profit_mode") or "gross_split").strip(),
            "owner_percent": float(contract.get("owner_percent") or 0),
            "company_percent": float(contract.get("company_percent") or 0),
            "fixed_rent_type": (contract.get("fixed_rent_type") or "").strip() or None,
            "fixed_rent_value": float(contract.get("fixed_rent_value") or 0),
            "fixed_rent_currency": (contract.get("fixed_rent_currency") or "GEL").strip().upper(),
            "ota_cost_mode": (contract.get("ota_cost_mode") or "company_only").strip(),
            "expense_mode": (contract.get("expense_mode") or "rule_based").strip(),
        }