from repositories.base_repository import BaseRepository


class ApartmentRepository(BaseRepository):
    """Репозиторий квартир.

    Здесь только работа с таблицей apartments:
    - создать
    - получить список
    - получить по id
    - получить по owner_id
    - получить по complex_id
    - удалить
    """

    def create(self, name: str, owner_id: int, complex_id: int | None = None) -> int:
        """Создать новую квартиру и вернуть её ID."""
        self.cursor.execute(
            """
            INSERT INTO apartments (name, owner_id, complex_id)
            VALUES (?, ?, ?)
            """,
            (name, owner_id, complex_id),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all(self):
        """Получить все квартиры."""
        self.cursor.execute(
            """
            SELECT *
            FROM apartments
            ORDER BY id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, apartment_id: int):
        """Получить квартиру по ID."""
        self.cursor.execute(
            """
            SELECT *
            FROM apartments
            WHERE id = ?
            """,
            (apartment_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_by_owner_id(self, owner_id: int):
        """Получить все квартиры конкретного собственника."""
        self.cursor.execute(
            """
            SELECT *
            FROM apartments
            WHERE owner_id = ?
            ORDER BY id DESC
            """,
            (owner_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_complex_id(self, complex_id: int):
        """Получить все квартиры конкретного комплекса."""
        self.cursor.execute(
            """
            SELECT *
            FROM apartments
            WHERE complex_id = ?
            ORDER BY id DESC
            """,
            (complex_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def delete(self, apartment_id: int) -> None:
        """Удалить квартиру по ID."""
        self.cursor.execute(
            """
            DELETE FROM apartments
            WHERE id = ?
            """,
            (apartment_id,),
        )
        self.conn.commit()