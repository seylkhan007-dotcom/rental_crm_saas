from repositories.base_repository import BaseRepository


class OwnerPayoutRepository(BaseRepository):
    def get_all(self):
        self.cursor.execute("SELECT * FROM owner_payouts")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_owner_id(self, owner_id: int):
        self.cursor.execute(
            "SELECT * FROM owner_payouts WHERE owner_id = ?",
            (owner_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def create(self, owner_id: int, booking_id: int, amount: float, status: str = "pending"):
        self.cursor.execute(
            """
            INSERT INTO owner_payouts (owner_id, booking_id, amount, status)
            VALUES (?, ?, ?, ?)
            """,
            (owner_id, booking_id, amount, status),
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