from repositories.base_repository import BaseRepository


class DebtRepository(BaseRepository):
    def get_all(self):
        self.cursor.execute("SELECT * FROM debts")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_counterparty(self, counterparty_type: str, counterparty_id: int):
        self.cursor.execute(
            """
            SELECT * FROM debts
            WHERE counterparty_type = ? AND counterparty_id = ?
            """,
            (counterparty_type, counterparty_id),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def create(
        self,
        counterparty_type: str,
        counterparty_id: int,
        booking_id: int,
        related_payout_id: int,
        amount: float,
        status: str,
        description: str,
    ):
        self.cursor.execute(
            """
            INSERT INTO debts (
                counterparty_type,
                counterparty_id,
                booking_id,
                related_payout_id,
                amount,
                status,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                counterparty_type,
                counterparty_id,
                booking_id,
                related_payout_id,
                amount,
                status,
                description,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def mark_as_settled(self, debt_id: int):
        self.cursor.execute(
            """
            UPDATE debts
            SET status = 'settled'
            WHERE id = ?
            """,
            (debt_id,),
        )
        self.conn.commit()