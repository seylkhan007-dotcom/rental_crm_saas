from repositories.base_repository import BaseRepository


class ManagerCheckinReportRepository(BaseRepository):
    """Репозиторий отчётов менеджеров о заселении.

    Работает с таблицей manager_checkin_reports.

    Здесь только CRUD и чтение данных.
    Без бизнес-логики.
    """

    def create(self, data: dict) -> dict:
        """Создать отчёт о заселении и вернуть его с id."""
        self.cursor.execute(
            """
            INSERT INTO manager_checkin_reports (
                manager_id,
                room_id,
                guest_name,
                guest_phone,
                source_channel,
                booking_status,
                payment_method,
                money_receiver,
                checkin_date,
                checkout_date,
                booking_price,
                amount_received,
                currency,
                adults_count,
                children_count,
                breakfast_included,
                payment_status,
                cash_handover_status,
                contract_id,
                booking_id,
                ceo_received_by_actor_id,
                ceo_received_at,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                data.get("manager_id"),
                data.get("room_id"),
                data.get("guest_name"),
                data.get("guest_phone"),
                data.get("source_channel", "other"),
                data.get("booking_status", "active"),
                data.get("payment_method", "cash"),
                data.get("money_receiver", "cashbox"),
                data.get("checkin_date"),
                data.get("checkout_date"),
                data.get("booking_price", 0),
                data.get("amount_received", 0),
                data.get("currency", "GEL"),
                data.get("adults_count", 1),
                data.get("children_count", 0),
                data.get("breakfast_included", 0),
                data.get("payment_status", "unpaid"),
                data.get("cash_handover_status", "pending"),
                data.get("contract_id"),
                data.get("booking_id"),
                data.get("ceo_received_by_actor_id"),
                data.get("ceo_received_at"),
                data.get("notes"),
            ),
        )
        self.conn.commit()
        report_id = self.cursor.lastrowid
        return self.get_by_id(report_id)

    def get_by_id(self, report_id: int) -> dict | None:
        """Получить отчёт по ID."""
        self.cursor.execute(
            """
            SELECT *
            FROM manager_checkin_reports
            WHERE id = ?
            """,
            (report_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_all(self) -> list:
        """Получить все отчёты, новые сверху."""
        self.cursor.execute(
            """
            SELECT *
            FROM manager_checkin_reports
            ORDER BY created_at DESC, id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_pending_cash_handover(self) -> list:
        """Получить отчёты, где CEO ещё не подтвердил получение денег."""
        self.cursor.execute(
            """
            SELECT *
            FROM manager_checkin_reports
            WHERE cash_handover_status = 'pending'
            ORDER BY created_at ASC, id ASC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def mark_cash_received(
        self,
        report_id: int,
        ceo_received_by_actor_id: int,
        received_at: str,
    ) -> dict | None:
        """Отметить, что CEO подтвердил получение денег."""
        self.cursor.execute(
            """
            UPDATE manager_checkin_reports
            SET
                cash_handover_status = 'received',
                ceo_received_by_actor_id = ?,
                ceo_received_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                ceo_received_by_actor_id,
                received_at,
                report_id,
            ),
        )
        self.conn.commit()
        return self.get_by_id(report_id)

    def update_booking_link(self, report_id: int, booking_id: int) -> dict | None:
        """Привязать отчёт к бронированию."""
        self.cursor.execute(
            """
            UPDATE manager_checkin_reports
            SET
                booking_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                booking_id,
                report_id,
            ),
        )
        self.conn.commit()
        return self.get_by_id(report_id)
