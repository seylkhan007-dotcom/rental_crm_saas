from repositories.contract_repository import ContractRepository
from repositories.owner_repository import OwnerRepository
from repositories.apartment_repository import ApartmentRepository


class ContractService:
    """Сервис контрактов и правил контрактов."""

    ALLOWED_PRICING_MODELS = {"management", "sublease"}
    ALLOWED_SETTLEMENT_BASE_MODES = {"from_guest_price", "manual_base"}
    ALLOWED_PROFIT_MODES = {"gross_split", "net_split"}
    ALLOWED_OTA_COST_MODES = {"company_only", "shared", "owner_only"}
    ALLOWED_EXPENSE_MODES = {"rule_based", "company_all", "owner_all", "profit_share_based"}
    ALLOWED_STAY_TYPES = {"all", "short_term", "long_term"}
    ALLOWED_RESPONSIBILITY_MODES = {"company", "owner", "guest", "split"}
    ALLOWED_FIXED_RENT_TYPES = {"daily", "monthly"}
    ALLOWED_CURRENCIES = {"GEL", "USD", "EUR"}
    ALLOWED_EXPENSE_TYPES = {
        "service_fee",
        "utilities",
        "cleaning",
        "laundry",
        "breakfast",
        "consumables",
        "minor_repair",
        "major_repair",
        "guest_damage",
        "ota_commission",
    }

    def __init__(self, conn):
        self.contract_repo = ContractRepository(conn)
        self.owner_repo = OwnerRepository(conn)
        self.apartment_repo = ApartmentRepository(conn)

    # ---------------------------------------------------------
    # CONTRACT PROFILES
    # ---------------------------------------------------------

    def create_profile(
        self,
        owner_id: int,
        profile_name: str,
        pricing_model: str = "management",
        settlement_base_mode: str = "from_guest_price",
        profit_mode: str = "gross_split",
        owner_percent: float = 0.0,
        company_percent: float = 0.0,
        fixed_rent_type: str | None = None,
        fixed_rent_value: float = 0.0,
        fixed_rent_currency: str = "GEL",
        ota_cost_mode: str = "company_only",
        expense_mode: str = "rule_based",
        apartment_ids: list[int] | None = None,
        notes: str | None = None,
        is_active: int = 1,
    ) -> int:
        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")

        normalized_profile_name = (profile_name or "").strip()
        normalized_pricing_model = (pricing_model or "management").strip()
        normalized_settlement_base_mode = (settlement_base_mode or "from_guest_price").strip()
        normalized_profit_mode = self._normalize_profit_mode(profit_mode)
        normalized_ota_cost_mode = (ota_cost_mode or "company_only").strip()
        normalized_expense_mode = (expense_mode or "rule_based").strip()
        normalized_notes = (notes or "").strip() or None
        normalized_fixed_rent_type = (fixed_rent_type or "").strip() or None
        normalized_fixed_rent_currency = (fixed_rent_currency or "GEL").strip().upper()

        apartment_ids = apartment_ids or []

        if not normalized_profile_name:
            raise ValueError("Название контракта не может быть пустым.")

        if normalized_pricing_model not in self.ALLOWED_PRICING_MODELS:
            raise ValueError("Некорректная модель контракта.")

        if normalized_settlement_base_mode not in self.ALLOWED_SETTLEMENT_BASE_MODES:
            raise ValueError("Некорректный режим базы расчёта.")

        if normalized_profit_mode not in self.ALLOWED_PROFIT_MODES:
            raise ValueError("Некорректный режим расчёта прибыли.")

        if normalized_ota_cost_mode not in self.ALLOWED_OTA_COST_MODES:
            raise ValueError("Некорректный режим OTA.")

        if normalized_expense_mode not in self.ALLOWED_EXPENSE_MODES:
            raise ValueError("Некорректный режим расходов.")

        if normalized_fixed_rent_currency not in self.ALLOWED_CURRENCIES:
            raise ValueError("Некорректная валюта фиксированной аренды.")

        if owner_percent < 0 or company_percent < 0:
            raise ValueError("Проценты не могут быть отрицательными.")

        if fixed_rent_value < 0:
            raise ValueError("Фиксированная аренда не может быть отрицательной.")

        unique_apartment_ids = self._validate_apartment_ids(apartment_ids)

        if normalized_pricing_model == "management":
            total_percent = round(float(owner_percent) + float(company_percent), 2)
            if total_percent != 100.0:
                raise ValueError("Сумма процентов собственника и компании должна быть ровно 100.")

            normalized_fixed_rent_type = None
            fixed_rent_value = 0.0
            normalized_fixed_rent_currency = "GEL"

        elif normalized_pricing_model == "sublease":
            if not normalized_fixed_rent_type:
                raise ValueError("Для субаренды нужно указать тип фиксированной аренды.")
            if normalized_fixed_rent_type not in self.ALLOWED_FIXED_RENT_TYPES:
                raise ValueError("Тип фиксированной аренды должен быть daily или monthly.")
            if fixed_rent_value <= 0:
                raise ValueError("Для субаренды фиксированная аренда должна быть больше нуля.")

            owner_percent = 0.0
            company_percent = 0.0
            normalized_settlement_base_mode = "from_guest_price"
            normalized_profit_mode = "gross_split"

        profile_id = self.contract_repo.create_profile(
            owner_id=owner_id,
            profile_name=normalized_profile_name,
            pricing_model=normalized_pricing_model,
            settlement_base_mode=normalized_settlement_base_mode,
            profit_mode=normalized_profit_mode,
            owner_percent=owner_percent,
            company_percent=company_percent,
            fixed_rent_type=normalized_fixed_rent_type,
            fixed_rent_value=fixed_rent_value,
            fixed_rent_currency=normalized_fixed_rent_currency,
            ota_cost_mode=normalized_ota_cost_mode,
            expense_mode=normalized_expense_mode,
            notes=normalized_notes,
            is_active=is_active,
        )

        if unique_apartment_ids:
            self.contract_repo.replace_profile_apartments(profile_id, unique_apartment_ids)

        return profile_id

    def get_all_profiles(self):
        profiles = self.contract_repo.get_all_profiles()
        return self._attach_apartments_to_profiles(profiles)

    def get_active_profiles(self):
        profiles = self.contract_repo.get_active_profiles()
        return self._attach_apartments_to_profiles(profiles)

    def get_profile_by_id(self, contract_profile_id: int):
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        apartments = self.contract_repo.get_apartments_by_profile_id(contract_profile_id)
        profile["apartments"] = apartments
        return profile

    def get_profiles_by_owner_id(self, owner_id: int):
        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")

        profiles = self.contract_repo.get_profiles_by_owner_id(owner_id)
        return self._attach_apartments_to_profiles(profiles)

    def get_active_profile_by_apartment_id(self, apartment_id: int):
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        profile = self.contract_repo.get_active_profile_by_apartment_id(apartment_id)
        if not profile:
            return None

        apartments = self.contract_repo.get_apartments_by_profile_id(profile["id"])
        profile["apartments"] = apartments
        return profile

    def update_profile(
        self,
        contract_profile_id: int,
        owner_id: int,
        profile_name: str,
        pricing_model: str = "management",
        settlement_base_mode: str = "from_guest_price",
        profit_mode: str = "gross_split",
        owner_percent: float = 0.0,
        company_percent: float = 0.0,
        fixed_rent_type: str | None = None,
        fixed_rent_value: float = 0.0,
        fixed_rent_currency: str = "GEL",
        ota_cost_mode: str = "company_only",
        expense_mode: str = "rule_based",
        apartment_ids: list[int] | None = None,
        notes: str | None = None,
        is_active: int = 1,
    ) -> None:
        existing_profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not existing_profile:
            raise ValueError("Контракт не найден.")

        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")

        normalized_profile_name = (profile_name or "").strip()
        normalized_pricing_model = (pricing_model or "management").strip()
        normalized_settlement_base_mode = (settlement_base_mode or "from_guest_price").strip()
        normalized_profit_mode = self._normalize_profit_mode(profit_mode)
        normalized_ota_cost_mode = (ota_cost_mode or "company_only").strip()
        normalized_expense_mode = (expense_mode or "rule_based").strip()
        normalized_notes = (notes or "").strip() or None
        normalized_fixed_rent_type = (fixed_rent_type or "").strip() or None
        normalized_fixed_rent_currency = (fixed_rent_currency or "GEL").strip().upper()

        apartment_ids = apartment_ids or []

        if not normalized_profile_name:
            raise ValueError("Название контракта не может быть пустым.")

        if normalized_pricing_model not in self.ALLOWED_PRICING_MODELS:
            raise ValueError("Некорректная модель контракта.")

        if normalized_settlement_base_mode not in self.ALLOWED_SETTLEMENT_BASE_MODES:
            raise ValueError("Некорректный режим базы расчёта.")

        if normalized_profit_mode not in self.ALLOWED_PROFIT_MODES:
            raise ValueError("Некорректный режим расчёта прибыли.")

        if normalized_ota_cost_mode not in self.ALLOWED_OTA_COST_MODES:
            raise ValueError("Некорректный режим OTA.")

        if normalized_expense_mode not in self.ALLOWED_EXPENSE_MODES:
            raise ValueError("Некорректный режим расходов.")

        if normalized_fixed_rent_currency not in self.ALLOWED_CURRENCIES:
            raise ValueError("Некорректная валюта фиксированной аренды.")

        if owner_percent < 0 or company_percent < 0:
            raise ValueError("Проценты не могут быть отрицательными.")

        if fixed_rent_value < 0:
            raise ValueError("Фиксированная аренда не может быть отрицательной.")

        unique_apartment_ids = self._validate_apartment_ids(apartment_ids)

        if normalized_pricing_model == "management":
            total_percent = round(float(owner_percent) + float(company_percent), 2)
            if total_percent != 100.0:
                raise ValueError("Сумма процентов собственника и компании должна быть ровно 100.")

            normalized_fixed_rent_type = None
            fixed_rent_value = 0.0
            normalized_fixed_rent_currency = "GEL"

        elif normalized_pricing_model == "sublease":
            if not normalized_fixed_rent_type:
                raise ValueError("Для субаренды нужно указать тип фиксированной аренды.")
            if normalized_fixed_rent_type not in self.ALLOWED_FIXED_RENT_TYPES:
                raise ValueError("Тип фиксированной аренды должен быть daily или monthly.")
            if fixed_rent_value <= 0:
                raise ValueError("Для субаренды фиксированная аренда должна быть больше нуля.")

            owner_percent = 0.0
            company_percent = 0.0
            normalized_settlement_base_mode = "from_guest_price"
            normalized_profit_mode = "gross_split"

        self.contract_repo.update_profile(
            contract_profile_id=contract_profile_id,
            owner_id=owner_id,
            profile_name=normalized_profile_name,
            pricing_model=normalized_pricing_model,
            settlement_base_mode=normalized_settlement_base_mode,
            profit_mode=normalized_profit_mode,
            owner_percent=owner_percent,
            company_percent=company_percent,
            fixed_rent_type=normalized_fixed_rent_type,
            fixed_rent_value=fixed_rent_value,
            fixed_rent_currency=normalized_fixed_rent_currency,
            ota_cost_mode=normalized_ota_cost_mode,
            expense_mode=normalized_expense_mode,
            notes=normalized_notes,
            is_active=is_active,
        )

        self.contract_repo.replace_profile_apartments(contract_profile_id, unique_apartment_ids)

    def delete_profile(self, contract_profile_id: int) -> None:
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        self.contract_repo.delete_profile(contract_profile_id)

    # ---------------------------------------------------------
    # CONTRACT ↔ APARTMENTS
    # ---------------------------------------------------------

    def add_apartment_to_profile(self, contract_profile_id: int, apartment_id: int) -> int:
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        return self.contract_repo.add_apartment_to_profile(contract_profile_id, apartment_id)

    def remove_apartment_from_profile(self, contract_profile_id: int, apartment_id: int) -> None:
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        self.contract_repo.remove_apartment_from_profile(contract_profile_id, apartment_id)

    def get_apartments_by_profile_id(self, contract_profile_id: int):
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        return self.contract_repo.get_apartments_by_profile_id(contract_profile_id)

    # ---------------------------------------------------------
    # SPLIT RULES
    # ---------------------------------------------------------

    def create_split_rule(
        self,
        contract_profile_id: int,
        stay_type: str,
        owner_percent: float,
        company_percent: float,
        split_basis: str = "owner_price",
        notes: str | None = None,
    ) -> int:
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        normalized_stay_type = (stay_type or "").strip()
        normalized_split_basis = (split_basis or "owner_price").strip()
        normalized_notes = (notes or "").strip() or None

        if normalized_stay_type not in self.ALLOWED_STAY_TYPES:
            raise ValueError("Некорректный тип аренды.")

        if owner_percent < 0 or company_percent < 0:
            raise ValueError("Проценты не могут быть отрицательными.")

        total_percent = round(float(owner_percent) + float(company_percent), 2)
        if total_percent != 100.0:
            raise ValueError("Сумма процентов собственника и компании должна быть ровно 100.")

        existing_rule = self.contract_repo.get_split_rule_by_profile_and_stay_type(
            contract_profile_id,
            normalized_stay_type,
        )
        if existing_rule:
            raise ValueError("Для этого контракта и типа аренды правило уже существует.")

        return self.contract_repo.create_split_rule(
            contract_profile_id=contract_profile_id,
            stay_type=normalized_stay_type,
            owner_percent=owner_percent,
            company_percent=company_percent,
            split_basis=normalized_split_basis,
            notes=normalized_notes,
        )

    def get_all_split_rules(self):
        return self.contract_repo.get_all_split_rules()

    def get_split_rule_by_id(self, rule_id: int):
        rule = self.contract_repo.get_split_rule_by_id(rule_id)
        if not rule:
            raise ValueError("Правило распределения не найдено.")
        return rule

    def get_split_rules_by_profile_id(self, contract_profile_id: int):
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        return self.contract_repo.get_split_rules_by_profile_id(contract_profile_id)

    def update_split_rule(
        self,
        rule_id: int,
        contract_profile_id: int,
        stay_type: str,
        owner_percent: float,
        company_percent: float,
        split_basis: str = "owner_price",
        notes: str | None = None,
    ) -> None:
        rule = self.contract_repo.get_split_rule_by_id(rule_id)
        if not rule:
            raise ValueError("Правило распределения не найдено.")

        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        normalized_stay_type = (stay_type or "").strip()
        normalized_split_basis = (split_basis or "owner_price").strip()
        normalized_notes = (notes or "").strip() or None

        if normalized_stay_type not in self.ALLOWED_STAY_TYPES:
            raise ValueError("Некорректный тип аренды.")

        if owner_percent < 0 or company_percent < 0:
            raise ValueError("Проценты не могут быть отрицательными.")

        total_percent = round(float(owner_percent) + float(company_percent), 2)
        if total_percent != 100.0:
            raise ValueError("Сумма процентов собственника и компании должна быть ровно 100.")

        existing_rule = self.contract_repo.get_split_rule_by_profile_and_stay_type(
            contract_profile_id,
            normalized_stay_type,
        )
        if existing_rule and existing_rule["id"] != rule_id:
            raise ValueError("Для этого контракта и типа аренды правило уже существует.")

        self.contract_repo.update_split_rule(
            rule_id=rule_id,
            contract_profile_id=contract_profile_id,
            stay_type=normalized_stay_type,
            owner_percent=owner_percent,
            company_percent=company_percent,
            split_basis=normalized_split_basis,
            notes=normalized_notes,
        )

    def delete_split_rule(self, rule_id: int) -> None:
        rule = self.contract_repo.get_split_rule_by_id(rule_id)
        if not rule:
            raise ValueError("Правило распределения не найдено.")

        self.contract_repo.delete_split_rule(rule_id)

    # ---------------------------------------------------------
    # EXPENSE RULES
    # ---------------------------------------------------------

    def create_expense_rule(
        self,
        contract_profile_id: int,
        expense_type_code: str,
        responsibility_mode: str = "company",
        owner_pct: float = 0.0,
        company_pct: float = 0.0,
        guest_pct: float = 0.0,
        notes: str | None = None,
    ) -> int:
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        normalized_expense_type = (expense_type_code or "").strip()
        normalized_responsibility_mode = (responsibility_mode or "company").strip()
        normalized_notes = (notes or "").strip() or None

        if not normalized_expense_type:
            raise ValueError("Тип расхода не может быть пустым.")

        if normalized_expense_type not in self.ALLOWED_EXPENSE_TYPES:
            raise ValueError("Некорректный тип расхода. Выбери один из предложенных вариантов.")

        if normalized_responsibility_mode not in self.ALLOWED_RESPONSIBILITY_MODES:
            raise ValueError("Некорректный режим ответственности за расход.")

        if owner_pct < 0 or company_pct < 0 or guest_pct < 0:
            raise ValueError("Проценты по расходу не могут быть отрицательными.")

        if normalized_responsibility_mode == "split":
            total_percent = round(float(owner_pct) + float(company_pct) + float(guest_pct), 2)
            if total_percent != 100.0:
                raise ValueError("При режиме split сумма процентов owner/company/guest должна быть ровно 100.")
        else:
            # For non-split modes, validate that exactly one party has 100%
            if normalized_responsibility_mode == "company":
                if company_pct != 100.0 or owner_pct != 0.0 or guest_pct != 0.0:
                    raise ValueError("Для режима 'Компания платит' должны быть: компания=100%, остальные=0%.")
            elif normalized_responsibility_mode == "owner":
                if owner_pct != 100.0 or company_pct != 0.0 or guest_pct != 0.0:
                    raise ValueError("Для режима 'Собственник платит' должны быть: собственник=100%, остальные=0%.")
            elif normalized_responsibility_mode == "guest":
                if guest_pct != 100.0 or owner_pct != 0.0 or company_pct != 0.0:
                    raise ValueError("Для режима 'Гость платит' должны быть: гость=100%, остальные=0%.")

        existing_rule = self.contract_repo.get_expense_rule_by_profile_and_type(
            contract_profile_id,
            normalized_expense_type,
        )
        if existing_rule:
            raise ValueError("Для этого контракта и типа расхода правило уже существует.")

        return self.contract_repo.create_expense_rule(
            contract_profile_id=contract_profile_id,
            expense_type_code=normalized_expense_type,
            responsibility_mode=normalized_responsibility_mode,
            owner_pct=owner_pct,
            company_pct=company_pct,
            guest_pct=guest_pct,
            notes=normalized_notes,
        )

    def get_all_expense_rules(self):
        return self.contract_repo.get_all_expense_rules()

    def get_expense_rule_by_id(self, rule_id: int):
        rule = self.contract_repo.get_expense_rule_by_id(rule_id)
        if not rule:
            raise ValueError("Правило расходов не найдено.")
        return rule

    def get_expense_rules_by_profile_id(self, contract_profile_id: int):
        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        return self.contract_repo.get_expense_rules_by_profile_id(contract_profile_id)

    def update_expense_rule(
        self,
        rule_id: int,
        contract_profile_id: int,
        expense_type_code: str,
        responsibility_mode: str = "company",
        owner_pct: float = 0.0,
        company_pct: float = 0.0,
        guest_pct: float = 0.0,
        notes: str | None = None,
    ) -> None:
        rule = self.contract_repo.get_expense_rule_by_id(rule_id)
        if not rule:
            raise ValueError("Правило расходов не найдено.")

        profile = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not profile:
            raise ValueError("Контракт не найден.")

        normalized_expense_type = (expense_type_code or "").strip()
        normalized_responsibility_mode = (responsibility_mode or "company").strip()
        normalized_notes = (notes or "").strip() or None

        if not normalized_expense_type:
            raise ValueError("Тип расхода не может быть пустым.")

        if normalized_expense_type not in self.ALLOWED_EXPENSE_TYPES:
            raise ValueError("Некорректный тип расхода. Выбери один из предложенных вариантов.")

        if normalized_responsibility_mode not in self.ALLOWED_RESPONSIBILITY_MODES:
            raise ValueError("Некорректный режим ответственности за расход.")

        if owner_pct < 0 or company_pct < 0 or guest_pct < 0:
            raise ValueError("Проценты по расходу не могут быть отрицательными.")

        if normalized_responsibility_mode == "split":
            total_percent = round(float(owner_pct) + float(company_pct) + float(guest_pct), 2)
            if total_percent != 100.0:
                raise ValueError("При режиме split сумма процентов owner/company/guest должна быть ровно 100.")
        else:
            # For non-split modes, validate that exactly one party has 100%
            if normalized_responsibility_mode == "company":
                if company_pct != 100.0 or owner_pct != 0.0 or guest_pct != 0.0:
                    raise ValueError("Для режима 'Компания платит' должны быть: компания=100%, остальные=0%.")
            elif normalized_responsibility_mode == "owner":
                if owner_pct != 100.0 or company_pct != 0.0 or guest_pct != 0.0:
                    raise ValueError("Для режима 'Собственник платит' должны быть: собственник=100%, остальные=0%.")
            elif normalized_responsibility_mode == "guest":
                if guest_pct != 100.0 or owner_pct != 0.0 or company_pct != 0.0:
                    raise ValueError("Для режима 'Гость платит' должны быть: гость=100%, остальные=0%.")

        existing_rule = self.contract_repo.get_expense_rule_by_profile_and_type(
            contract_profile_id,
            normalized_expense_type,
        )
        if existing_rule and existing_rule["id"] != rule_id:
            raise ValueError("Для этого контракта и типа расхода правило уже существует.")

        self.contract_repo.update_expense_rule(
            rule_id=rule_id,
            contract_profile_id=contract_profile_id,
            expense_type_code=normalized_expense_type,
            responsibility_mode=normalized_responsibility_mode,
            owner_pct=owner_pct,
            company_pct=company_pct,
            guest_pct=guest_pct,
            notes=normalized_notes,
        )

    def delete_expense_rule(self, rule_id: int) -> None:
        rule = self.contract_repo.get_expense_rule_by_id(rule_id)
        if not rule:
            raise ValueError("Правило расходов не найдено.")

        self.contract_repo.delete_expense_rule(rule_id)

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _validate_apartment_ids(self, apartment_ids: list[int]) -> list[int]:
        unique_ids = []
        seen = set()

        for apartment_id in apartment_ids:
            if apartment_id in seen:
                continue

            apartment = self.apartment_repo.get_by_id(apartment_id)
            if not apartment:
                raise ValueError(f"Квартира с ID {apartment_id} не найдена.")

            unique_ids.append(apartment_id)
            seen.add(apartment_id)

        return unique_ids

    def _attach_apartments_to_profiles(self, profiles: list[dict]) -> list[dict]:
        for profile in profiles:
            profile["profit_mode"] = self._normalize_profit_mode(
                profile.get("profit_mode")
            )
            profile["apartments"] = self.contract_repo.get_apartments_by_profile_id(profile["id"])
        return profiles

    def _normalize_profit_mode(self, profit_mode: str | None) -> str:
        normalized_profit_mode = (profit_mode or "gross_split").strip()
        if normalized_profit_mode == "net_profit_split":
            return "net_split"
        return normalized_profit_mode or "gross_split"
