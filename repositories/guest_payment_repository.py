from repositories.base_repository import BaseRepository


class GuestPaymentRepository(BaseRepository):
    def get_all(self):
        self.cursor.execute(
            """
            SELECT *
            FROM guest_payments
            ORDER BY id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_total_received_by_booking_id(self, booking_id: int) -> float:
        self.cursor.execute(
            """
            SELECT COALESCE(SUM(amount_gel), 0) AS total
            FROM guest_payments
            WHERE booking_id = ?
              AND status IN ('received', 'approved', 'paid')
            """,
            (booking_id,),
        )
        row = self.cursor.fetchone()
        return float(dict(row).get("total") or 0.0) if row else 0.0

    def create(
        self,
        booking_id: int,
        payment_date: str,
        payment_method: str,
        amount_original: float,
        currency_code: str,
        fx_rate_to_gel: float,
        amount_gel: float,
        status: str,
        notes: str | None = None,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO guest_payments (
                booking_id,
                payment_date,
                payment_method,
                amount_original,
                currency_code,
                fx_rate_to_gel,
                amount_gel,
                status,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                booking_id,
                payment_date,
                payment_method,
                amount_original,
                currency_code,
                fx_rate_to_gel,
                amount_gel,
                status,
                notes,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid
