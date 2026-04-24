from repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository):
    """Репозиторий задач.

    Здесь только работа с таблицей tasks:
    - создать
    - получить все
    - получить по id
    - обновить статус
    - получить по apartment_id
    """

    def create(
        self,
        apartment_id: int,
        task_type: str,
        booking_id: int | None = None,
        notes: str | None = None,
    ) -> int:
        """Создать новую задачу и вернуть её ID."""
        self.cursor.execute(
            """
            INSERT INTO tasks (apartment_id, booking_id, task_type, status, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (apartment_id, booking_id, task_type, "new", notes),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all(self):
        """Получить все задачи."""
        self.cursor.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY created_at DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, task_id: int):
        """Получить задачу по ID."""
        self.cursor.execute(
            """
            SELECT *
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_status(self, task_id: int, status: str) -> None:
        """Обновить статус задачи."""
        self.cursor.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, task_id),
        )
        self.conn.commit()

    def get_by_apartment_id(self, apartment_id: int):
        """Получить все задачи конкретной квартиры."""
        self.cursor.execute(
            """
            SELECT *
            FROM tasks
            WHERE apartment_id = ?
            ORDER BY created_at DESC
            """,
            (apartment_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
