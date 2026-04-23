from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from repositories.booking_repository import BookingRepository
from repositories.contract_repository import ContractRepository
from repositories.expense_repository import ExpenseRepository


@dataclass
class FinanceValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class FinanceCalculationContext:
    booking: dict[str, Any]
    contract: dict[str, Any]
    split_rule: dict[str, Any] | None
    expense_rules_map: dict[str, dict[str, Any]]

    booking_id: int
    contract_profile_id: int
    pricing_model: str
    profit_mode: str
    stay_type: str

    guest_price: float
    settlement_base_amount: float
    extra_margin_amount: float
    tax_base_price: float

    ota_commission_pct: float
    ota_vat_pct: float
    ota_cost_mode: str

    owner_percent: float
    company_percent: float

    fixed_rent_type: str | None
    fixed_rent_value: float
    fixed_rent_currency: str

    manager_actor_id: int | None
    manager_commission_pct: float

    currency_code: str = "GEL"
    nights: int = 1


class FinanceService:
    """
    Централизованный финансовый движок бронирования.

    Ключевые правила:
    - owner считается от settlement_base_amount
    - extra_margin = guest_price - settlement_base_amount
    - extra_margin всегда 100% компании
    - snapshot брони = источник истины
    """

    def __init__(self, conn):
        self.conn = conn
        self.contract_repo = ContractRepository(conn)
        self.booking_repo = BookingRepository(conn)
        self.expense_repo = ExpenseRepository(conn)

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------

    def calculate_booking_finances(
        self,
        booking_id: int,
        persist_snapshot: bool = False,
    ) -> dict[str, Any]:
        context = self._build_context(booking_id)
        validation = self._validate_context(context)
        if validation.has_errors:
            raise ValueError(" | ".join(validation.errors))

        result = self._calculate_result(context)
        result["warnings"] = validation.warnings
        result["validation_errors"] = validation.errors

        if persist_snapshot:
            snapshot_id = self._save_snapshot(context, result)
            result["snapshot_id"] = snapshot_id

        return result

    def calculate_booking_finance(
        self,
        booking_id: int,
        persist_snapshot: bool = False,
    ) -> dict[str, Any]:
        """
        Алиас под новое имя.
        """
        return self.calculate_booking_finances(
            booking_id=booking_id,
            persist_snapshot=persist_snapshot,
        )

    def recalculate_booking_finance(
        self,
        booking_id: int,
        persist_snapshot: bool = True,
    ) -> dict[str, Any]:
        """
        Пересчёт брони.
        Всё равно считается по snapshot-полям самой брони.
        """
        return self.calculate_booking_finances(
            booking_id=booking_id,
            persist_snapshot=persist_snapshot,
        )

    def get_booking_finance_breakdown(self, booking_id: int) -> dict[str, Any]:
        """
        Сначала пытаемся взять последний snapshot.
        Если его нет — считаем на лету без сохранения.
        """
        snapshot = self._get_latest_snapshot(booking_id)
        if snapshot:
            return self._map_snapshot_to_breakdown(snapshot)

        return self.calculate_booking_finances(
            booking_id=booking_id,
            persist_snapshot=False,
        )

    def finalize_booking_finance(
        self,
        booking_id: int,
        locked_by_actor_id: int | None = None,
        lock_reason: str = "finalized",
    ) -> dict[str, Any]:
        """
        Создаёт финальный snapshot и помечает его locked/final.
        """
        result = self.calculate_booking_finances(
            booking_id=booking_id,
            persist_snapshot=True,
        )

        snapshot_id = result.get("snapshot_id")
        if snapshot_id:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE booking_finance_snapshots
                SET
                    snapshot_status = 'final',
                    lock_reason = ?,
                    locked_at = CURRENT_TIMESTAMP,
                    locked_by = ?
                WHERE id = ?
                """,
                (lock_reason, locked_by_actor_id, snapshot_id),
            )
            self.conn.commit()

        return result

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    def _build_context(self, booking_id: int) -> FinanceCalculationContext:
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Бронирование не найдено.")

        contract_profile_id = self._to_int(booking.get("contract_profile_id"))
        if not contract_profile_id:
            raise ValueError("У бронирования не указан контракт.")

        contract = self.contract_repo.get_profile_by_id(contract_profile_id)
        if not contract:
            raise ValueError("Контракт не найден.")

        pricing_model = self._str_or_default(
            booking.get("pricing_model") or contract.get("pricing_model"),
            "management",
        )
        profit_mode = self._normalize_profit_mode(
            booking.get("profit_mode_snapshot") or contract.get("profit_mode")
        )
        stay_type = self._str_or_default(booking.get("stay_type"), "short_term")

        guest_price = self._to_float(booking.get("guest_price"))
        settlement_base_amount = self._to_float(booking.get("settlement_base_amount"))
        tax_base_price = self._to_float(booking.get("tax_base_price"))
        extra_margin_amount = guest_price - settlement_base_amount

        ota_commission_pct = self._to_float(booking.get("ota_commission_pct"))
        ota_vat_pct = self._to_float(booking.get("ota_vat_pct"))
        ota_cost_mode = self._str_or_default(
            booking.get("ota_cost_mode_snapshot") or contract.get("ota_cost_mode"),
            "company_only",
        )

        split_rule = self._resolve_split_rule(contract_profile_id, stay_type)

        owner_percent = self._to_float(
            booking.get("owner_percent_snapshot")
            if booking.get("owner_percent_snapshot") is not None
            else (split_rule or {}).get("owner_percent")
            if split_rule
            else contract.get("owner_percent")
        )
        company_percent = self._to_float(
            booking.get("company_percent_snapshot")
            if booking.get("company_percent_snapshot") is not None
            else (split_rule or {}).get("company_percent")
            if split_rule
            else contract.get("company_percent")
        )

        fixed_rent_type = (
            booking.get("fixed_rent_type_snapshot")
            or booking.get("fixed_rent_type")
            or contract.get("fixed_rent_type")
        )
        fixed_rent_value = self._to_float(
            booking.get("fixed_rent_value_snapshot")
            if booking.get("fixed_rent_value_snapshot") is not None
            else booking.get("fixed_rent_value")
            if booking.get("fixed_rent_value") is not None
            else contract.get("fixed_rent_value")
        )
        fixed_rent_currency = self._str_or_default(
            booking.get("fixed_rent_currency_snapshot")
            or contract.get("fixed_rent_currency"),
            "GEL",
        )

        manager_actor_id = self._to_int(booking.get("manager_commission_actor_id"))
        manager_commission_pct = self._to_float(
            booking.get("manager_commission_pct_snapshot")
        )

        expense_rules = self.contract_repo.get_expense_rules_by_profile_id(
            contract_profile_id
        )
        expense_rules_map = {
            str(rule.get("expense_type_code") or "").strip(): rule
            for rule in expense_rules
            if str(rule.get("expense_type_code") or "").strip()
        }

        nights = self._calculate_nights(
            str(booking.get("check_in") or "").strip(),
            str(booking.get("check_out") or "").strip(),
        )

        return FinanceCalculationContext(
            booking=booking,
            contract=contract,
            split_rule=split_rule,
            expense_rules_map=expense_rules_map,
            booking_id=booking_id,
            contract_profile_id=contract_profile_id,
            pricing_model=pricing_model,
            profit_mode=profit_mode,
            stay_type=stay_type,
            guest_price=guest_price,
            settlement_base_amount=settlement_base_amount,
            extra_margin_amount=extra_margin_amount,
            tax_base_price=tax_base_price,
            ota_commission_pct=ota_commission_pct,
            ota_vat_pct=ota_vat_pct,
            ota_cost_mode=ota_cost_mode,
            owner_percent=owner_percent,
            company_percent=company_percent,
            fixed_rent_type=fixed_rent_type,
            fixed_rent_value=fixed_rent_value,
            fixed_rent_currency=fixed_rent_currency,
            manager_actor_id=manager_actor_id,
            manager_commission_pct=manager_commission_pct,
            nights=nights,
        )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def _validate_context(self, context: FinanceCalculationContext) -> FinanceValidationResult:
        result = FinanceValidationResult()

        if context.guest_price <= 0:
            result.errors.append("Сумма гостя должна быть больше нуля.")

        if context.settlement_base_amount <= 0:
            result.errors.append("Settlement base должна быть больше нуля.")

        if context.settlement_base_amount > context.guest_price:
            result.errors.append(
                "Settlement base не может быть больше guest price."
            )

        if context.extra_margin_amount < 0:
            result.errors.append(
                "Extra margin не может быть отрицательной."
            )

        if context.nights <= 0:
            result.errors.append("Количество ночей должно быть больше нуля.")

        if context.pricing_model not in {"management", "sublease"}:
            result.errors.append("Неизвестная модель договора.")

        if context.pricing_model == "management":
            if context.owner_percent < 0 or context.company_percent < 0:
                result.errors.append("Проценты owner/company не могут быть отрицательными.")

            total_pct = context.owner_percent + context.company_percent
            if total_pct <= 0:
                result.errors.append(
                    "Для management должна быть задана сумма процентов больше нуля."
                )

            if abs(total_pct - 100.0) > 0.0001:
                result.errors.append(
                    "Для management owner_percent + company_percent должны давать 100."
                )

            if context.profit_mode not in {"gross_split", "net_split"}:
                result.errors.append(
                    "Для management profit_mode должен быть gross_split или net_split."
                )

        if context.pricing_model == "sublease":
            if context.fixed_rent_value <= 0:
                result.errors.append(
                    "Для sublease должен быть задан fixed rent."
                )

            if context.fixed_rent_type not in {"daily", "monthly"}:
                result.errors.append(
                    "Для sublease fixed_rent_type должен быть daily или monthly."
                )

        if context.ota_cost_mode not in {"company_only", "owner_only", "shared"}:
            result.errors.append("Некорректный OTA mode.")

        if context.ota_commission_pct < 0 or context.ota_vat_pct < 0:
            result.errors.append("OTA проценты не могут быть отрицательными.")

        if context.manager_commission_pct < 0:
            result.errors.append("Комиссия менеджера не может быть отрицательной.")

        if context.manager_commission_pct > 100:
            result.errors.append("Комиссия менеджера не может быть больше 100%.")

        if context.booking.get("owner_price") not in (None, ""):
            result.warnings.append(
                "В брони есть legacy поле owner_price. В новой логике оно игнорируется."
            )

        return result

    # ---------------------------------------------------------
    # CALC MAIN
    # ---------------------------------------------------------

    def _calculate_result(self, context: FinanceCalculationContext) -> dict[str, Any]:
        ota_breakdown = self._calculate_ota(context)
        expense_breakdown = self._calculate_expense_breakdown(context)

        if context.pricing_model == "management":
            if context.profit_mode == "gross_split":
                strategy_result = self._calculate_management_gross(
                    context=context,
                    ota_breakdown=ota_breakdown,
                    expense_breakdown=expense_breakdown,
                )
                strategy_type = "management_gross"
            else:
                strategy_result = self._calculate_management_net(
                    context=context,
                    ota_breakdown=ota_breakdown,
                    expense_breakdown=expense_breakdown,
                )
                strategy_type = "management_net"
        else:
            if context.fixed_rent_type == "daily":
                strategy_result = self._calculate_sublease_daily(
                    context=context,
                    ota_breakdown=ota_breakdown,
                    expense_breakdown=expense_breakdown,
                )
                strategy_type = "sublease_daily"
            else:
                strategy_result = self._calculate_sublease_monthly(
                    context=context,
                    ota_breakdown=ota_breakdown,
                    expense_breakdown=expense_breakdown,
                )
                strategy_type = "sublease_monthly"

        guest_payments_received = self._sum_guest_payments(context.booking_id)
        owner_paid_amount = self._sum_owner_payouts_paid(context.booking_id)

        guest_balance = context.guest_price - guest_payments_received
        owner_payout_due = max(strategy_result["owner_net_amount"] - owner_paid_amount, 0.0)
        owner_debt_total = max(strategy_result["owner_net_amount"] - owner_paid_amount, 0.0)

        result = {
            "booking_id": context.booking_id,
            "contract_profile_id": context.contract_profile_id,
            "strategy_type": strategy_type,
            "pricing_model": context.pricing_model,
            "profit_mode": context.profit_mode,
            "stay_type": context.stay_type,
            "currency_code": context.currency_code,
            "nights": context.nights,

            "guest_price": self._round2(context.guest_price),
            "settlement_base_amount": self._round2(context.settlement_base_amount),
            "extra_margin_amount": self._round2(context.extra_margin_amount),
            "tax_base_price": self._round2(context.tax_base_price),

            "ota_commission_pct": self._round4(context.ota_commission_pct),
            "ota_vat_pct": self._round4(context.ota_vat_pct),
            "ota_cost_mode": context.ota_cost_mode,

            "ota_commission_amount": self._round2(ota_breakdown["ota_commission_amount"]),
            "ota_vat_amount": self._round2(ota_breakdown["ota_vat_amount"]),
            "ota_total_amount": self._round2(ota_breakdown["ota_total_amount"]),
            "ota_owner_amount": self._round2(ota_breakdown["ota_owner_amount"]),
            "ota_company_amount": self._round2(ota_breakdown["ota_company_amount"]),
            "ota_shared_amount": self._round2(ota_breakdown["ota_shared_amount"]),

            "pre_split_expenses_total": self._round2(expense_breakdown["pre_split_expenses_total"]),
            "owner_expenses_total": self._round2(expense_breakdown["owner_expenses_total"]),
            "company_expenses_total": self._round2(expense_breakdown["company_expenses_total"]),
            "guest_expenses_total": self._round2(expense_breakdown["guest_expenses_total"]),
            "split_pool_expenses_total": self._round2(expense_breakdown["split_pool_expenses_total"]),

            "base_pool_amount": self._round2(strategy_result["base_pool_amount"]),
            "net_pool_amount": self._round2(strategy_result["net_pool_amount"]),
            "owner_gross_amount": self._round2(strategy_result["owner_gross_amount"]),
            "company_gross_amount": self._round2(strategy_result["company_gross_amount"]),
            "owner_net_amount": self._round2(strategy_result["owner_net_amount"]),
            "company_net_amount": self._round2(strategy_result["company_net_amount"]),
            "company_gross_before_ota": self._round2(strategy_result["company_gross_before_ota"]),
            "company_after_ota": self._round2(strategy_result["company_after_ota"]),
            "company_before_manager": self._round2(strategy_result["company_before_manager"]),

            "manager_commission_amount": self._round2(strategy_result["manager_commission_amount"]),
            "distributable_profit_amount": self._round2(strategy_result["distributable_profit_amount"]),

            "owner_amount": self._round2(strategy_result["owner_net_amount"]),
            "owner_amount_due": self._round2(strategy_result["owner_net_amount"]),
            "owner_payout_due_amount": self._round2(owner_payout_due),

            "guest_payments_received_gel": self._round2(guest_payments_received),
            "owner_paid_amount_gel": self._round2(owner_paid_amount),
            "guest_balance_gel": self._round2(guest_balance),
            "owner_balance_gel": self._round2(strategy_result["owner_net_amount"] - owner_paid_amount),

            "debt_total_owner_gel": self._round2(owner_debt_total),
            "payout_due_owner_gel": self._round2(owner_payout_due),

            "expense_lines": expense_breakdown["expense_lines"],
        }

        return result

    # ---------------------------------------------------------
    # OTA
    # ---------------------------------------------------------

    def _calculate_ota(self, context: FinanceCalculationContext) -> dict[str, float]:
        ota_commission_amount = context.guest_price * context.ota_commission_pct / 100.0
        ota_vat_amount = ota_commission_amount * context.ota_vat_pct / 100.0
        ota_total_amount = ota_commission_amount + ota_vat_amount

        owner_burden = 0.0
        company_burden = 0.0
        shared_amount = 0.0

        if context.ota_cost_mode == "company_only":
            company_burden = ota_total_amount
        elif context.ota_cost_mode == "owner_only":
            owner_burden = ota_total_amount
        elif context.ota_cost_mode == "shared":
            shared_amount = ota_total_amount
            owner_burden = ota_total_amount * (context.owner_percent / 100.0)
            company_burden = ota_total_amount * (context.company_percent / 100.0)

        return {
            "ota_commission_amount": ota_commission_amount,
            "ota_vat_amount": ota_vat_amount,
            "ota_total_amount": ota_total_amount,
            "ota_owner_amount": owner_burden,
            "ota_company_amount": company_burden,
            "ota_shared_amount": shared_amount,
        }

    # ---------------------------------------------------------
    # EXPENSES
    # ---------------------------------------------------------

    def _calculate_expense_breakdown(self, context: FinanceCalculationContext) -> dict[str, Any]:
        expenses = self.expense_repo.get_by_booking_id(context.booking_id)

        pre_split_total = 0.0
        owner_total = 0.0
        company_total = 0.0
        guest_total = 0.0
        split_pool_total = 0.0
        expense_lines: list[dict[str, Any]] = []

        for expense in expenses:
            status = self._str_or_default(expense.get("status"), "draft")
            if status == "cancelled":
                continue

            expense_type = str(expense.get("expense_type") or "").strip()

            owner_share = self._to_float(expense.get("owner_share_gel"))
            company_share = self._to_float(expense.get("company_share_gel"))
            guest_share = self._to_float(expense.get("guest_share_gel"))
            total_amount = self._to_float(expense.get("amount"))

            rule = context.expense_rules_map.get(expense_type, {})
            responsibility_mode = self._str_or_default(
                expense.get("responsibility_mode_snapshot") or rule.get("responsibility_mode"),
                "company",
            )

            application_stage = self._resolve_expense_application_stage(
                responsibility_mode=responsibility_mode
            )

            owner_total += owner_share
            company_total += company_share
            guest_total += guest_share

            if application_stage == "pre_split":
                pre_split_total += owner_share + company_share
                split_pool_total += owner_share + company_share

            expense_lines.append(
                {
                    "expense_id": expense.get("id"),
                    "expense_type": expense_type,
                    "status": status,
                    "amount": self._round2(total_amount),
                    "owner_share_gel": self._round2(owner_share),
                    "company_share_gel": self._round2(company_share),
                    "guest_share_gel": self._round2(guest_share),
                    "responsibility_mode": responsibility_mode,
                    "application_stage": application_stage,
                }
            )

        return {
            "pre_split_expenses_total": pre_split_total,
            "owner_expenses_total": owner_total,
            "company_expenses_total": company_total,
            "guest_expenses_total": guest_total,
            "split_pool_expenses_total": split_pool_total,
            "expense_lines": expense_lines,
        }

    def _resolve_expense_application_stage(self, responsibility_mode: str) -> str:
        """
        Пока stage выводим из responsibility_mode.
        Правило переходное, но уже централизованное.

        pre_split:
        - split
        - net_pool
        - shared

        outside_split:
        - guest

        post_split:
        - owner
        - company
        - всё остальное по умолчанию
        """
        normalized = self._str_or_default(responsibility_mode, "company")

        if normalized in {"split", "shared", "net_pool"}:
            return "pre_split"

        if normalized == "guest":
            return "outside_split"

        return "post_split"

    # ---------------------------------------------------------
    # STRATEGIES
    # ---------------------------------------------------------

    def _calculate_management_gross(
        self,
        context: FinanceCalculationContext,
        ota_breakdown: dict[str, float],
        expense_breakdown: dict[str, Any],
    ) -> dict[str, float]:
        base_pool = context.settlement_base_amount

        owner_gross = base_pool * context.owner_percent / 100.0
        company_base_gross = base_pool * context.company_percent / 100.0
        company_extra_margin = context.extra_margin_amount

        company_gross = company_base_gross + company_extra_margin

        company_after_ota = company_gross - ota_breakdown["ota_company_amount"]
        company_before_manager = company_after_ota - expense_breakdown["company_expenses_total"]

        owner_net = owner_gross - ota_breakdown["ota_owner_amount"] - expense_breakdown["owner_expenses_total"]
        company_net_before_manager = company_before_manager

        manager_amount = self._calculate_manager_amount(
            company_amount_before_manager=company_net_before_manager,
            context=context,
        )
        distributable_profit = company_net_before_manager - manager_amount

        return {
            "base_pool_amount": base_pool,
            "net_pool_amount": 0.0,
            "owner_gross_amount": owner_gross,
            "company_gross_amount": company_gross,
            "owner_net_amount": owner_net,
            "company_net_amount": distributable_profit,
            "company_gross_before_ota": company_gross,
            "company_after_ota": company_after_ota,
            "company_before_manager": company_before_manager,
            "manager_commission_amount": manager_amount,
            "distributable_profit_amount": distributable_profit,
        }

    def _calculate_management_net(
        self,
        context: FinanceCalculationContext,
        ota_breakdown: dict[str, float],
        expense_breakdown: dict[str, Any],
    ) -> dict[str, float]:
        """
        КЛЮЧЕВОЕ ПРАВИЛО:
        extra_margin НЕ входит в net pool.
        Net pool считается только от settlement_base_amount.
        """
        base_pool = context.settlement_base_amount

        pre_split_ota = self._resolve_pre_split_ota_amount(context, ota_breakdown)
        pre_split_expenses = expense_breakdown["pre_split_expenses_total"]

        net_pool = base_pool - pre_split_ota - pre_split_expenses
        if net_pool < 0:
            net_pool = 0.0

        owner_gross = net_pool * context.owner_percent / 100.0
        company_base_gross = net_pool * context.company_percent / 100.0
        company_extra_margin = context.extra_margin_amount

        company_gross = company_base_gross + company_extra_margin

        owner_post_split_ota = self._resolve_post_split_owner_ota_amount(context, ota_breakdown)
        company_post_split_ota = self._resolve_post_split_company_ota_amount(context, ota_breakdown)

        owner_net = owner_gross - owner_post_split_ota - expense_breakdown["owner_expenses_total"]
        company_after_ota = company_gross - company_post_split_ota
        company_before_manager = company_after_ota - expense_breakdown["company_expenses_total"]

        manager_amount = self._calculate_manager_amount(
            company_amount_before_manager=company_before_manager,
            context=context,
        )
        distributable_profit = company_before_manager - manager_amount

        return {
            "base_pool_amount": base_pool,
            "net_pool_amount": net_pool,
            "owner_gross_amount": owner_gross,
            "company_gross_amount": company_gross,
            "owner_net_amount": owner_net,
            "company_net_amount": distributable_profit,
            "company_gross_before_ota": company_gross,
            "company_after_ota": company_after_ota,
            "company_before_manager": company_before_manager,
            "manager_commission_amount": manager_amount,
            "distributable_profit_amount": distributable_profit,
        }

    def _calculate_sublease_daily(
        self,
        context: FinanceCalculationContext,
        ota_breakdown: dict[str, float],
        expense_breakdown: dict[str, Any],
    ) -> dict[str, float]:
        owner_gross = context.fixed_rent_value * context.nights
        owner_net = owner_gross - ota_breakdown["ota_owner_amount"] - expense_breakdown["owner_expenses_total"]

        company_gross = context.guest_price - owner_gross
        company_after_ota = company_gross - ota_breakdown["ota_company_amount"]
        company_before_manager = company_after_ota - expense_breakdown["company_expenses_total"]

        manager_amount = self._calculate_manager_amount(
            company_amount_before_manager=company_before_manager,
            context=context,
        )
        distributable_profit = company_before_manager - manager_amount

        return {
            "base_pool_amount": context.settlement_base_amount,
            "net_pool_amount": 0.0,
            "owner_gross_amount": owner_gross,
            "company_gross_amount": company_gross,
            "owner_net_amount": owner_net,
            "company_net_amount": distributable_profit,
            "company_gross_before_ota": company_gross,
            "company_after_ota": company_after_ota,
            "company_before_manager": company_before_manager,
            "manager_commission_amount": manager_amount,
            "distributable_profit_amount": distributable_profit,
        }

    def _calculate_sublease_monthly(
        self,
        context: FinanceCalculationContext,
        ota_breakdown: dict[str, float],
        expense_breakdown: dict[str, Any],
    ) -> dict[str, float]:
        allocated_rent = self._allocate_monthly_rent_to_booking(
            monthly_rent=context.fixed_rent_value,
            check_in=str(context.booking.get("check_in") or "").strip(),
            check_out=str(context.booking.get("check_out") or "").strip(),
        )

        owner_gross = allocated_rent
        owner_net = owner_gross - ota_breakdown["ota_owner_amount"] - expense_breakdown["owner_expenses_total"]

        company_gross = context.guest_price - owner_gross
        company_after_ota = company_gross - ota_breakdown["ota_company_amount"]
        company_before_manager = company_after_ota - expense_breakdown["company_expenses_total"]

        manager_amount = self._calculate_manager_amount(
            company_amount_before_manager=company_before_manager,
            context=context,
        )
        distributable_profit = company_before_manager - manager_amount

        return {
            "base_pool_amount": context.settlement_base_amount,
            "net_pool_amount": 0.0,
            "owner_gross_amount": owner_gross,
            "company_gross_amount": company_gross,
            "owner_net_amount": owner_net,
            "company_net_amount": distributable_profit,
            "company_gross_before_ota": company_gross,
            "company_after_ota": company_after_ota,
            "company_before_manager": company_before_manager,
            "manager_commission_amount": manager_amount,
            "distributable_profit_amount": distributable_profit,
        }

    # ---------------------------------------------------------
    # SNAPSHOT
    # ---------------------------------------------------------

    def _save_snapshot(
        self,
        context: FinanceCalculationContext,
        result: dict[str, Any],
    ) -> int:
        cursor = self.conn.cursor()
        version_no = self._get_next_snapshot_version(context.booking_id)

        cursor.execute(
            """
            INSERT INTO booking_finance_snapshots (
                booking_id,
                version_no,
                snapshot_status,

                pricing_model_snapshot,
                stay_type_snapshot,

                contract_profile_id_snapshot,
                settlement_base_mode_snapshot,
                profit_mode_snapshot,
                owner_percent_snapshot,
                company_percent_snapshot,
                ota_cost_mode_snapshot,
                expense_mode_snapshot,

                guest_price_snapshot,
                settlement_base_amount_snapshot,
                tax_base_price_snapshot,

                ota_commission_pct_snapshot,
                ota_vat_pct_snapshot,
                ota_commission_amount,
                ota_vat_amount,
                ota_total_amount,

                fixed_rent_type_snapshot,
                fixed_rent_value_snapshot,
                fixed_rent_currency_snapshot,
                fixed_rent_amount_gel,

                owner_amount_due,
                company_gross_before_ota,
                company_after_ota,
                company_expenses_total,
                company_before_manager,
                manager_commission_amount,
                distributable_profit_amount,

                currency_code,
                fx_rate_to_gel,
                gel_total_amount,

                created_at
            )
            VALUES (
                ?, ?, 'draft',
                ?, ?,
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                CURRENT_TIMESTAMP
            )
            """,
            (
                context.booking_id,
                version_no,
                context.pricing_model,
                context.stay_type,
                context.contract_profile_id,
                context.booking.get("settlement_base_mode_snapshot")
                or context.contract.get("settlement_base_mode"),
                context.profit_mode,
                context.owner_percent,
                context.company_percent,
                context.ota_cost_mode,
                context.booking.get("expense_mode_snapshot")
                or context.contract.get("expense_mode"),
                result["guest_price"],
                result["settlement_base_amount"],
                result["tax_base_price"],
                result["ota_commission_pct"],
                result["ota_vat_pct"],
                result["ota_commission_amount"],
                result["ota_vat_amount"],
                result["ota_total_amount"],
                context.fixed_rent_type,
                context.fixed_rent_value,
                context.fixed_rent_currency,
                result["owner_gross_amount"] if context.pricing_model == "sublease" else 0.0,
                result["owner_amount_due"],
                result["company_gross_before_ota"],
                result["company_after_ota"],
                result["company_expenses_total"],
                result["company_before_manager"],
                result["manager_commission_amount"],
                result["distributable_profit_amount"],
                context.currency_code,
                1.0,
                result["guest_price"],
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def _get_latest_snapshot(self, booking_id: int) -> dict[str, Any] | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM booking_finance_snapshots
            WHERE booking_id = ?
            ORDER BY version_no DESC, id DESC
            LIMIT 1
            """,
            (booking_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def _get_next_snapshot_version(self, booking_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(MAX(version_no), 0) AS max_version
            FROM booking_finance_snapshots
            WHERE booking_id = ?
            """,
            (booking_id,),
        )
        row = cursor.fetchone()
        if not row:
            return 1
        return int(dict(row).get("max_version") or 0) + 1

    def _map_snapshot_to_breakdown(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "booking_id": snapshot.get("booking_id"),
            "strategy_type": self._build_strategy_type_from_snapshot(snapshot),
            "pricing_model": snapshot.get("pricing_model_snapshot"),
            "profit_mode": snapshot.get("profit_mode_snapshot"),
            "stay_type": snapshot.get("stay_type_snapshot"),
            "currency_code": snapshot.get("currency_code") or "GEL",

            "guest_price": self._to_float(snapshot.get("guest_price_snapshot")),
            "settlement_base_amount": self._to_float(snapshot.get("settlement_base_amount_snapshot")),
            "extra_margin_amount": self._round2(
                self._to_float(snapshot.get("guest_price_snapshot"))
                - self._to_float(snapshot.get("settlement_base_amount_snapshot"))
            ),
            "tax_base_price": self._to_float(snapshot.get("tax_base_price_snapshot")),

            "ota_commission_amount": self._to_float(snapshot.get("ota_commission_amount")),
            "ota_vat_amount": self._to_float(snapshot.get("ota_vat_amount")),
            "ota_total_amount": self._to_float(snapshot.get("ota_total_amount")),

            "owner_amount_due": self._to_float(snapshot.get("owner_amount_due")),
            "company_gross_before_ota": self._to_float(snapshot.get("company_gross_before_ota")),
            "company_after_ota": self._to_float(snapshot.get("company_after_ota")),
            "company_expenses_total": self._to_float(snapshot.get("company_expenses_total")),
            "company_before_manager": self._to_float(snapshot.get("company_before_manager")),
            "manager_commission_amount": self._to_float(snapshot.get("manager_commission_amount")),
            "distributable_profit_amount": self._to_float(snapshot.get("distributable_profit_amount")),

            "snapshot_id": snapshot.get("id"),
            "snapshot_version": snapshot.get("version_no"),
            "snapshot_status": snapshot.get("snapshot_status"),
        }

    def _build_strategy_type_from_snapshot(self, snapshot: dict[str, Any]) -> str:
        pricing_model = self._str_or_default(snapshot.get("pricing_model_snapshot"), "management")
        profit_mode = self._normalize_profit_mode(snapshot.get("profit_mode_snapshot"))
        fixed_rent_type = self._str_or_default(snapshot.get("fixed_rent_type_snapshot"), "")

        if pricing_model == "management":
            return "management_net" if profit_mode == "net_split" else "management_gross"

        if fixed_rent_type == "monthly":
            return "sublease_monthly"

        return "sublease_daily"

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    def _resolve_split_rule(
        self,
        contract_profile_id: int,
        stay_type: str,
    ) -> dict[str, Any] | None:
        exact_rule = self.contract_repo.get_split_rule_by_profile_and_stay_type(
            contract_profile_id,
            stay_type,
        )
        if exact_rule:
            return exact_rule

        common_rule = self.contract_repo.get_split_rule_by_profile_and_stay_type(
            contract_profile_id,
            "all",
        )
        if common_rule:
            return common_rule

        return None

    def _resolve_pre_split_ota_amount(
        self,
        context: FinanceCalculationContext,
        ota_breakdown: dict[str, float],
    ) -> float:
        """
        Для management_net:
        - owner_only / company_only / shared влияют на net pool,
          если модель net_split.
        """
        if context.pricing_model == "management" and context.profit_mode == "net_split":
            return ota_breakdown["ota_total_amount"]

        return 0.0

    def _resolve_post_split_owner_ota_amount(
        self,
        context: FinanceCalculationContext,
        ota_breakdown: dict[str, float],
    ) -> float:
        if context.pricing_model == "management" and context.profit_mode == "net_split":
            return 0.0
        return ota_breakdown["ota_owner_amount"]

    def _resolve_post_split_company_ota_amount(
        self,
        context: FinanceCalculationContext,
        ota_breakdown: dict[str, float],
    ) -> float:
        if context.pricing_model == "management" and context.profit_mode == "net_split":
            return 0.0
        return ota_breakdown["ota_company_amount"]

    def _calculate_manager_amount(
        self,
        company_amount_before_manager: float,
        context: FinanceCalculationContext,
    ) -> float:
        if not context.manager_actor_id or context.manager_commission_pct <= 0:
            return 0.0

        base_amount = max(company_amount_before_manager, 0.0)
        return base_amount * context.manager_commission_pct / 100.0

    def _sum_guest_payments(self, booking_id: int) -> float:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount_gel), 0) AS total
            FROM guest_payments
            WHERE booking_id = ?
              AND status IN ('received', 'paid', 'approved')
            """,
            (booking_id,),
        )
        row = cursor.fetchone()
        return float(dict(row).get("total") or 0.0) if row else 0.0

    def _sum_owner_payouts_paid(self, booking_id: int) -> float:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount_paid_gel), 0) AS total
            FROM owner_payouts
            WHERE booking_id = ?
              AND status IN ('partial', 'paid')
            """,
            (booking_id,),
        )
        row = cursor.fetchone()
        return float(dict(row).get("total") or 0.0) if row else 0.0

    def _allocate_monthly_rent_to_booking(
        self,
        monthly_rent: float,
        check_in: str,
        check_out: str,
    ) -> float:
        """
        Упрощённое, но уже корректное распределение:
        бронь получает долю месячной аренды пропорционально дням.
        Если бронь переходит через месяцы — считаем по каждому месяцу отдельно.
        """
        start = self._parse_date(check_in)
        end = self._parse_date(check_out)

        if end <= start:
            return 0.0

        total_allocated = 0.0
        cursor_day = start

        while cursor_day < end:
            month_start = date(cursor_day.year, cursor_day.month, 1)
            next_month_start = self._first_day_of_next_month(cursor_day)
            period_end = min(end, next_month_start)
            days_in_period = (period_end - cursor_day).days
            days_in_month = (next_month_start - month_start).days

            if days_in_month > 0 and days_in_period > 0:
                total_allocated += monthly_rent * (days_in_period / days_in_month)

            cursor_day = period_end

        return total_allocated

    def _calculate_nights(self, check_in: str, check_out: str) -> int:
        start = self._parse_date(check_in)
        end = self._parse_date(check_out)
        return max((end - start).days, 0)

    def _parse_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Некорректная дата: {value}") from exc

    def _first_day_of_next_month(self, current_date: date) -> date:
        if current_date.month == 12:
            return date(current_date.year + 1, 1, 1)
        return date(current_date.year, current_date.month + 1, 1)

    def _to_float(self, value: Any) -> float:
        if value in (None, ""):
            return 0.0
        return float(value)

    def _to_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

    def _str_or_default(self, value: Any, default: str) -> str:
        text = str(value).strip() if value not in (None, "") else ""
        return text or default

    def _normalize_profit_mode(self, value: Any) -> str:
        normalized_profit_mode = self._str_or_default(value, "gross_split")
        if normalized_profit_mode == "net_profit_split":
            return "net_split"
        return normalized_profit_mode

    def _round2(self, value: float) -> float:
        return round(float(value or 0.0), 2)

    def _round4(self, value: float) -> float:
        return round(float(value or 0.0), 4)
