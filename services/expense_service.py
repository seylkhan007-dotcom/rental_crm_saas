from datetime import datetime

from repositories.expense_repository import ExpenseRepository
from repositories.booking_repository import BookingRepository
from repositories.actor_repository import ActorRepository
from repositories.contract_repository import ContractRepository


class ExpenseService:
    """Сервис расходов.

    Логика:
    - расход привязан к существующей брони
    - сумма > 0
    - тип расхода не пустой
    - по умолчанию применяется правило расхода из контракта
    - можно вручную override-ить распределение owner/company/guest
    """

    ALLOWED_STATUSES = {"draft", "approved", "paid", "cancelled"}

    def __init__(self, conn):
        self.expense_repo = ExpenseRepository(conn)
        self.booking_repo = BookingRepository(conn)
        self.actor_repo = ActorRepository(conn)
        self.contract_repo = ContractRepository(conn)

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create_expense(
        self,
        booking_id: int,
        expense_type: str,
        amount: float,
        responsibility_mode_snapshot: str | None = None,
        owner_share_gel: float | None = None,
        company_share_gel: float | None = None,
        guest_share_gel: float | None = None,
        status: str = "draft",
        created_by_actor_id: int | None = None,
        use_manual_override: bool = False,
    ) -> int:
        """Создать расход.

        Если use_manual_override=False:
        - система сама пытается применить правило расхода из контракта

        Если use_manual_override=True:
        - используются переданные owner/company/guest shares
        """

        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")

        normalized_expense_type = (expense_type or "").strip()
        if not normalized_expense_type:
            raise ValueError("Тип расхода не может быть пустым.")

        amount = float(amount or 0)
        if amount <= 0:
            raise ValueError("Сумма расхода должна быть больше нуля.")

        if status not in self.ALLOWED_STATUSES:
            raise ValueError("Некорректный статус расхода.")

        if created_by_actor_id is not None:
            actor = self.actor_repo.get_by_id(created_by_actor_id)
            if not actor:
                raise ValueError("Создатель расхода не найден.")

        if use_manual_override:
            resolved = self._resolve_manual_shares(
                amount=amount,
                owner_share_gel=owner_share_gel,
                company_share_gel=company_share_gel,
                guest_share_gel=guest_share_gel,
                responsibility_mode_snapshot=responsibility_mode_snapshot,
            )
        else:
            resolved = self._resolve_expense_from_contract_rule(
                booking=booking,
                expense_type=normalized_expense_type,
                amount=amount,
            )

        return self.expense_repo.create(
            booking_id=booking_id,
            expense_type=normalized_expense_type,
            amount=amount,
            responsibility_mode_snapshot=resolved["responsibility_mode_snapshot"],
            owner_share_gel=resolved["owner_share_gel"],
            company_share_gel=resolved["company_share_gel"],
            guest_share_gel=resolved["guest_share_gel"],
            status=status,
            created_by_actor_id=created_by_actor_id,
        )

    # ---------------------------------------------------------
    # READ
    # ---------------------------------------------------------

    def get_all_expenses(self):
        return self.expense_repo.get_all()

    def get_expense_by_id(self, expense_id: int):
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            raise ValueError("Расход не найден.")
        return expense

    def get_expenses_by_booking_id(self, booking_id: int):
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")
        return self.expense_repo.get_by_booking_id(booking_id)

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update_expense(
        self,
        expense_id: int,
        booking_id: int,
        expense_type: str,
        amount: float,
        responsibility_mode_snapshot: str | None = None,
        owner_share_gel: float | None = None,
        company_share_gel: float | None = None,
        guest_share_gel: float | None = None,
        status: str = "draft",
        created_by_actor_id: int | None = None,
        approved_by_actor_id: int | None = None,
        approved_at: str | None = None,
        use_manual_override: bool = False,
    ) -> None:
        """Обновить расход."""

        existing_expense = self.expense_repo.get_by_id(expense_id)
        if not existing_expense:
            raise ValueError("Расход не найден.")

        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")

        normalized_expense_type = (expense_type or "").strip()
        if not normalized_expense_type:
            raise ValueError("Тип расхода не может быть пустым.")

        amount = float(amount or 0)
        if amount <= 0:
            raise ValueError("Сумма расхода должна быть больше нуля.")

        if status not in self.ALLOWED_STATUSES:
            raise ValueError("Некорректный статус расхода.")

        if created_by_actor_id is not None:
            actor = self.actor_repo.get_by_id(created_by_actor_id)
            if not actor:
                raise ValueError("Создатель расхода не найден.")

        if approved_by_actor_id is not None:
            actor = self.actor_repo.get_by_id(approved_by_actor_id)
            if not actor:
                raise ValueError("Подтверждающий расход не найден.")

        if use_manual_override:
            resolved = self._resolve_manual_shares(
                amount=amount,
                owner_share_gel=owner_share_gel,
                company_share_gel=company_share_gel,
                guest_share_gel=guest_share_gel,
                responsibility_mode_snapshot=responsibility_mode_snapshot,
            )
        else:
            resolved = self._resolve_expense_from_contract_rule(
                booking=booking,
                expense_type=normalized_expense_type,
                amount=amount,
            )

        self.expense_repo.update(
            expense_id=expense_id,
            booking_id=booking_id,
            expense_type=normalized_expense_type,
            amount=amount,
            responsibility_mode_snapshot=resolved["responsibility_mode_snapshot"],
            owner_share_gel=resolved["owner_share_gel"],
            company_share_gel=resolved["company_share_gel"],
            guest_share_gel=resolved["guest_share_gel"],
            status=status,
            created_by_actor_id=created_by_actor_id,
            approved_by_actor_id=approved_by_actor_id,
            approved_at=approved_at,
        )

    # ---------------------------------------------------------
    # STATUS FLOW
    # ---------------------------------------------------------

    def approve_expense(self, expense_id: int, approved_by_actor_id: int | None = None) -> None:
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            raise ValueError("Расход не найден.")

        if approved_by_actor_id is not None:
            actor = self.actor_repo.get_by_id(approved_by_actor_id)
            if not actor:
                raise ValueError("Подтверждающий расход не найден.")

        self.expense_repo.set_status(
            expense_id=expense_id,
            status="approved",
            approved_by_actor_id=approved_by_actor_id,
            approved_at=datetime.utcnow().isoformat(),
        )

    def mark_expense_as_paid(self, expense_id: int, approved_by_actor_id: int | None = None) -> None:
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            raise ValueError("Расход не найден.")

        if approved_by_actor_id is not None:
            actor = self.actor_repo.get_by_id(approved_by_actor_id)
            if not actor:
                raise ValueError("Подтверждающий расход не найден.")

        self.expense_repo.set_status(
            expense_id=expense_id,
            status="paid",
            approved_by_actor_id=approved_by_actor_id,
            approved_at=datetime.utcnow().isoformat(),
        )

    def cancel_expense(self, expense_id: int) -> None:
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            raise ValueError("Расход не найден.")

        self.expense_repo.set_status(
            expense_id=expense_id,
            status="cancelled",
            approved_by_actor_id=None,
            approved_at=None,
        )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete_expense(self, expense_id: int) -> None:
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            raise ValueError("Расход не найден.")

        self.expense_repo.delete(expense_id)

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _resolve_expense_from_contract_rule(
        self,
        booking: dict,
        expense_type: str,
        amount: float,
    ) -> dict:
        """Автоматически определить распределение расхода по контракту.

        Приоритет:
        1. contract_expense_rules
        2. fallback company 100%
        """

        contract_profile_id = booking.get("contract_profile_id")
        if not contract_profile_id:
            return {
                "responsibility_mode_snapshot": "company",
                "owner_share_gel": 0.0,
                "company_share_gel": amount,
                "guest_share_gel": 0.0,
            }

        rule = self.contract_repo.get_expense_rule_by_profile_and_type(
            contract_profile_id=contract_profile_id,
            expense_type_code=expense_type,
        )

        if not rule:
            # безопасный fallback
            return {
                "responsibility_mode_snapshot": "company",
                "owner_share_gel": 0.0,
                "company_share_gel": amount,
                "guest_share_gel": 0.0,
            }

        responsibility_mode = (rule.get("responsibility_mode") or "company").strip()

        if responsibility_mode == "company":
            return {
                "responsibility_mode_snapshot": "company",
                "owner_share_gel": 0.0,
                "company_share_gel": amount,
                "guest_share_gel": 0.0,
            }

        if responsibility_mode == "owner":
            return {
                "responsibility_mode_snapshot": "owner",
                "owner_share_gel": amount,
                "company_share_gel": 0.0,
                "guest_share_gel": 0.0,
            }

        if responsibility_mode == "guest":
            return {
                "responsibility_mode_snapshot": "guest",
                "owner_share_gel": 0.0,
                "company_share_gel": 0.0,
                "guest_share_gel": amount,
            }

        if responsibility_mode == "split":
            owner_pct = float(rule.get("owner_pct") or 0)
            company_pct = float(rule.get("company_pct") or 0)
            guest_pct = float(rule.get("guest_pct") or 0)

            total_pct = round(owner_pct + company_pct + guest_pct, 2)
            if total_pct != 100.0:
                raise ValueError(
                    f"Некорректное правило расхода '{expense_type}': сумма процентов должна быть 100."
                )

            owner_share = amount * owner_pct / 100
            company_share = amount * company_pct / 100
            guest_share = amount * guest_pct / 100

            return {
                "responsibility_mode_snapshot": "split",
                "owner_share_gel": owner_share,
                "company_share_gel": company_share,
                "guest_share_gel": guest_share,
            }

        raise ValueError(f"Неизвестный responsibility_mode у правила расхода: {responsibility_mode}")

    def _resolve_manual_shares(
        self,
        amount: float,
        owner_share_gel: float | None,
        company_share_gel: float | None,
        guest_share_gel: float | None,
        responsibility_mode_snapshot: str | None = None,
    ) -> dict:
        """Ручной override распределения расхода."""

        owner_share = float(owner_share_gel or 0)
        company_share = float(company_share_gel or 0)
        guest_share = float(guest_share_gel or 0)

        if owner_share < 0 or company_share < 0 or guest_share < 0:
            raise ValueError("Доли расхода не могут быть отрицательными.")

        total_shares = round(owner_share + company_share + guest_share, 2)
        expected_amount = round(float(amount), 2)

        if total_shares != expected_amount:
            raise ValueError(
                "При ручном override сумма owner/company/guest shares "
                "должна быть равна сумме расхода."
            )

        mode = (responsibility_mode_snapshot or "manual").strip()

        return {
            "responsibility_mode_snapshot": mode,
            "owner_share_gel": owner_share,
            "company_share_gel": company_share,
            "guest_share_gel": guest_share,
        }