from repositories.base_repository import BaseRepository


class ExpenseRepository(BaseRepository):
    """Репозиторий расходов.

    Работает с таблицей expenses.
    Только доступ к данным, без бизнес-логики.
    """

    def get_all(self):
        self.cursor.execute(
            """
            SELECT *
            FROM expenses
            ORDER BY id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, expense_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM expenses
            WHERE id = ?
            """,
            (expense_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_by_booking_id(self, booking_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM expenses
            WHERE booking_id = ?
            ORDER BY id DESC
            """,
            (booking_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def create(
        self,
        booking_id: int,
        expense_type: str,
        amount: float,
        responsibility_mode_snapshot: str | None = None,
        owner_share_gel: float = 0.0,
        company_share_gel: float = 0.0,
        guest_share_gel: float = 0.0,
        status: str = "draft",
        created_by_actor_id: int | None = None,
        approved_by_actor_id: int | None = None,
        approved_at: str | None = None,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO expenses (
                booking_id,
                expense_type,
                amount,
                responsibility_mode_snapshot,
                owner_share_gel,
                company_share_gel,
                guest_share_gel,
                status,
                created_by_actor_id,
                approved_by_actor_id,
                approved_at,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                booking_id,
                expense_type,
                amount,
                responsibility_mode_snapshot,
                owner_share_gel,
                company_share_gel,
                guest_share_gel,
                status,
                created_by_actor_id,
                approved_by_actor_id,
                approved_at,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update(
        self,
        expense_id: int,
        booking_id: int,
        expense_type: str,
        amount: float,
        responsibility_mode_snapshot: str | None = None,
        owner_share_gel: float = 0.0,
        company_share_gel: float = 0.0,
        guest_share_gel: float = 0.0,
        status: str = "draft",
        created_by_actor_id: int | None = None,
        approved_by_actor_id: int | None = None,
        approved_at: str | None = None,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE expenses
            SET
                booking_id = ?,
                expense_type = ?,
                amount = ?,
                responsibility_mode_snapshot = ?,
                owner_share_gel = ?,
                company_share_gel = ?,
                guest_share_gel = ?,
                status = ?,
                created_by_actor_id = ?,
                approved_by_actor_id = ?,
                approved_at = ?
            WHERE id = ?
            """,
            (
                booking_id,
                expense_type,
                amount,
                responsibility_mode_snapshot,
                owner_share_gel,
                company_share_gel,
                guest_share_gel,
                status,
                created_by_actor_id,
                approved_by_actor_id,
                approved_at,
                expense_id,
            ),
        )
        self.conn.commit()

    def set_status(
        self,
        expense_id: int,
        status: str,
        approved_by_actor_id: int | None = None,
        approved_at: str | None = None,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE expenses
            SET
                status = ?,
                approved_by_actor_id = ?,
                approved_at = ?
            WHERE id = ?
            """,
            (
                status,
                approved_by_actor_id,
                approved_at,
                expense_id,
            ),
        )
        self.conn.commit()

    def delete(self, expense_id: int):
        self.cursor.execute(
            """
            DELETE FROM expenses
            WHERE id = ?
            """,
            (expense_id,),
        )
        self.conn.commit()