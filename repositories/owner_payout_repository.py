from repositories.base_repository import BaseRepository


class OwnerPayoutRepository(BaseRepository):
    def get_all(self):
        self.cursor.execute(
            """
            SELECT *
            FROM owner_payouts
            ORDER BY id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_owner_id(self, owner_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM owner_payouts
            WHERE owner_id = ?
            ORDER BY id DESC
            """,
            (owner_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_total_paid_by_booking_id(self, booking_id: int) -> float:
        self.cursor.execute(
            """
            SELECT COALESCE(SUM(amount_paid_gel), 0) AS total
            FROM owner_payouts
            WHERE booking_id = ?
              AND status IN ('partial', 'paid')
            """,
            (booking_id,),
        )
        row = self.cursor.fetchone()
        return float(dict(row).get("total") or 0.0) if row else 0.0

    def create(
        self,
        owner_id: int,
        booking_id: int,
        amount: float,
        status: str = "pending",
    ):
        self.cursor.execute(
            """
            INSERT INTO owner_payouts (owner_id, booking_id, amount, status)
            VALUES (?, ?, ?, ?)
            """,
            (owner_id, booking_id, amount, status),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def create_manual_payout(
        self,
        owner_id: int,
        booking_id: int,
        amount_due_gel: float,
        amount_paid_gel: float,
        currency_code: str,
        fx_rate_to_gel: float,
        status: str,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO owner_payouts (
                owner_id,
                booking_id,
                amount_due_gel,
                amount_paid_gel,
                currency_code,
                fx_rate_to_gel,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                owner_id,
                booking_id,
                amount_due_gel,
                amount_paid_gel,
                currency_code,
                fx_rate_to_gel,
                status,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def mark_as_paid(self, payout_id: int):
        self.cursor.execute(
            """
            UPDATE owner_payouts
            SET status = 'paid'
            WHERE id = ?
            """,
            (payout_id,),
        )
        self.conn.commit()
