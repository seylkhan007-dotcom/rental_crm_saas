from repositories.base_repository import BaseRepository


class ExpenseRuleRepository(BaseRepository):
    def get_by_expense_type(self, expense_type: str):
        self.cursor.execute(
            """
            SELECT * FROM expense_rules
            WHERE expense_type = ?
            LIMIT 1
            """,
            (expense_type,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_all(self):
        self.cursor.execute("SELECT * FROM expense_rules")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]