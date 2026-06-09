from repositories.base_repository import BaseRepository


class BreakfastOrderRepository(BaseRepository):
    """Репозиторий заказов завтраков.

    Работает с таблицей breakfast_orders.
    """

    def create(self, data: dict) -> dict:
        """Создать заказ завтрака и вернуть его с id."""
        self.cursor.execute(
            """
            INSERT INTO breakfast_orders (
                service_date,
                apartment_id,
                manager_checkin_report_id,
                booking_id,
                adults_count,
                children_count,
                breakfast_count,
                price_per_breakfast,
                total_amount,
                status,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                data.get("service_date"),
                data.get("apartment_id"),
                data.get("manager_checkin_report_id"),
                data.get("booking_id"),
                data.get("adults_count", 0),
                data.get("children_count", 0),
                data.get("breakfast_count", 0),
                data.get("price_per_breakfast", 7.5),
                data.get("total_amount", 0),
                data.get("status", "planned"),
                data.get("notes"),
            ),
        )
        self.conn.commit()
        order_id = self.cursor.lastrowid
        return self.get_by_id(order_id)

    def get_by_id(self, order_id: int) -> dict | None:
        """Получить заказ завтрака по ID."""
        self.cursor.execute(
            """
            SELECT *
            FROM breakfast_orders
            WHERE id = ?
            """,
            (order_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_all(self) -> list:
        """Получить все заказы завтраков, новые сверху."""
        self.cursor.execute(
            """
            SELECT *
            FROM breakfast_orders
            ORDER BY service_date DESC, id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_date(self, service_date: str) -> list:
        """Получить заказы завтраков на конкретную дату."""
        self.cursor.execute(
            """
            SELECT *
            FROM breakfast_orders
            WHERE service_date = ?
            ORDER BY id ASC
            """,
            (service_date,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_date_range(self, start_date: str, end_date: str) -> list:
        """Получить заказы завтраков за период."""
        self.cursor.execute(
            """
            SELECT *
            FROM breakfast_orders
            WHERE service_date BETWEEN ? AND ?
            ORDER BY service_date ASC, id ASC
            """,
            (start_date, end_date),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def update_status(self, order_id: int, status: str) -> dict | None:
        """Обновить статус заказа завтрака."""
        self.cursor.execute(
            """
            UPDATE breakfast_orders
            SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                status,
                order_id,
            ),
        )
        self.conn.commit()
        return self.get_by_id(order_id)

    def update_counts(
        self,
        order_id: int,
        adults_count: int,
        children_count: int,
        breakfast_count: int,
        total_amount: float,
    ) -> dict | None:
        """Обновить количество завтраков и итоговую сумму."""
        self.cursor.execute(
            """
            UPDATE breakfast_orders
            SET
                adults_count = ?,
                children_count = ?,
                breakfast_count = ?,
                total_amount = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                adults_count,
                children_count,
                breakfast_count,
                total_amount,
                order_id,
            ),
        )
        self.conn.commit()
        return self.get_by_id(order_id)
