from repositories.manager_checkin_report_repository import ManagerCheckinReportRepository


class ManagerCheckinReportService:
    """Сервис отчётов менеджеров о заселении."""

    ALLOWED_PAYMENT_STATUSES = {"paid", "unpaid", "partial"}
    ALLOWED_CURRENCIES = {"GEL", "USD", "EUR"}
    ALLOWED_SOURCE_CHANNELS = {
        "booking",
        "airbnb",
        "whatsapp",
        "instagram",
        "direct",
        "walk_in",
        "other",
    }
    ALLOWED_BOOKING_STATUSES = {
        "active",
        "cancelled_but_stayed",
        "not_platform_booking",
    }
    ALLOWED_PAYMENT_METHODS = {
        "cash",
        "bank_transfer",
        "card",
        "booking",
        "airbnb",
        "mixed",
        "other",
    }
    ALLOWED_MONEY_RECEIVERS = {
        "cashbox",
        "bank_transfer",
        "card_account",
        "business_account",
        "personal_account",
        "other",
    }

    def __init__(self, conn):
        self.report_repo = ManagerCheckinReportRepository(conn)

    def create_report(
        self,
        manager_id: int,
        room_id: int,
        guest_name: str,
        guest_phone: str | None,
        checkin_date: str,
        checkout_date: str,
        source_channel: str,
        booking_status: str,
        payment_method: str,
        money_receiver: str,
        booking_price: float,
        amount_received: float,
        payment_status: str,
        notes: str | None = None,
        contract_id: int | None = None,
        currency: str = "GEL",
        adults_count: int = 1,
        children_count: int = 0,
        breakfast_included: int = 0,
    ) -> dict:
        """Создать отчёт менеджера о заселении."""
        if not manager_id:
            raise ValueError("manager_id обязателен.")
        if not room_id:
            raise ValueError("room_id обязателен.")

        normalized_guest_name = (guest_name or "").strip()
        if not normalized_guest_name:
            raise ValueError("Имя гостя обязательно.")

        normalized_checkin_date = (checkin_date or "").strip()
        normalized_checkout_date = (checkout_date or "").strip()
        if not normalized_checkin_date:
            raise ValueError("Дата заезда обязательна.")
        if not normalized_checkout_date:
            raise ValueError("Дата выезда обязательна.")

        normalized_source_channel = (source_channel or "").strip()
        if normalized_source_channel not in self.ALLOWED_SOURCE_CHANNELS:
            raise ValueError("Некорректный канал источника.")

        normalized_booking_status = (booking_status or "").strip()
        if normalized_booking_status not in self.ALLOWED_BOOKING_STATUSES:
            raise ValueError("Некорректный статус брони.")

        normalized_payment_method = (payment_method or "").strip()
        if normalized_payment_method not in self.ALLOWED_PAYMENT_METHODS:
            raise ValueError("Некорректный способ оплаты.")

        normalized_money_receiver = (money_receiver or "").strip()
        if normalized_money_receiver not in self.ALLOWED_MONEY_RECEIVERS:
            raise ValueError("Некорректное место поступления денег.")

        booking_price = float(booking_price or 0)
        if booking_price < 0:
            raise ValueError("Цена бронирования не может быть отрицательной.")

        amount_received = float(amount_received or 0)
        if amount_received < 0:
            raise ValueError("Полученная сумма не может быть отрицательной.")

        normalized_currency = (currency or "GEL").strip().upper()
        if normalized_currency not in self.ALLOWED_CURRENCIES:
            raise ValueError("Некорректная валюта.")

        adults_count = int(adults_count or 0)
        if adults_count < 1:
            raise ValueError("Количество взрослых должно быть минимум 1.")

        children_count = int(children_count or 0)
        if children_count < 0:
            raise ValueError("Количество детей не может быть отрицательным.")

        breakfast_included = 1 if breakfast_included else 0

        normalized_payment_status = (payment_status or "").strip()
        if normalized_payment_status not in self.ALLOWED_PAYMENT_STATUSES:
            raise ValueError("Некорректный статус оплаты.")

        if normalized_payment_status == "unpaid" and amount_received != 0:
            raise ValueError("Для статуса unpaid полученная сумма должна быть 0.")

        if normalized_payment_status == "paid" and amount_received <= 0:
            raise ValueError("Для статуса paid полученная сумма должна быть больше 0.")

        cash_handover_status = (
            "pending"
            if amount_received > 0
            else "not_required"
        )

        data = {
            "manager_id": manager_id,
            "room_id": room_id,
            "guest_name": normalized_guest_name,
            "guest_phone": (guest_phone or "").strip() or None,
            "checkin_date": normalized_checkin_date,
            "checkout_date": normalized_checkout_date,
            "source_channel": normalized_source_channel,
            "booking_status": normalized_booking_status,
            "payment_method": normalized_payment_method,
            "money_receiver": normalized_money_receiver,
            "booking_price": booking_price,
            "amount_received": amount_received,
            "currency": normalized_currency,
            "adults_count": adults_count,
            "children_count": children_count,
            "breakfast_included": breakfast_included,
            "payment_status": normalized_payment_status,
            "cash_handover_status": cash_handover_status,
            "contract_id": contract_id,
            "notes": (notes or "").strip() or None,
        }

        return self.report_repo.create(data)

    def get_all_reports(self) -> list:
        """Получить все отчёты."""
        return self.report_repo.get_all()

    def get_pending_cash_handover(self) -> list:
        """Получить отчёты, ожидающие передачи денег CEO."""
        return self.report_repo.get_pending_cash_handover()

    def mark_cash_received(
        self,
        report_id: int,
        ceo_received_by_actor_id: int,
        received_at: str,
    ) -> dict | None:
        """Подтвердить получение денег CEO."""
        if not report_id:
            raise ValueError("report_id обязателен.")
        if not ceo_received_by_actor_id:
            raise ValueError("ceo_received_by_actor_id обязателен.")

        normalized_received_at = (received_at or "").strip()
        if not normalized_received_at:
            raise ValueError("Дата подтверждения получения денег обязательна.")

        return self.report_repo.mark_cash_received(
            report_id=report_id,
            ceo_received_by_actor_id=ceo_received_by_actor_id,
            received_at=normalized_received_at,
        )

    def link_booking(self, report_id: int, booking_id: int) -> dict | None:
        """Привязать отчёт к созданному бронированию."""
        if not report_id:
            raise ValueError("report_id обязателен.")
        if not booking_id:
            raise ValueError("booking_id обязателен.")

        return self.report_repo.update_booking_link(
            report_id=report_id,
            booking_id=booking_id,
        )
