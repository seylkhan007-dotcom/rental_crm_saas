from repositories.base_repository import BaseRepository


class ComplexRepository(BaseRepository):
    """Репозиторий комплексов.

    Здесь только работа с таблицей complexes:
    - создать
    - получить список
    - получить по id
    - получить по имени
    - удалить
    """

    def create(self, name: str) -> int:
        """Создать новый комплекс и вернуть его ID."""
        self.cursor.execute(
            """
            INSERT INTO complexes (name)
            VALUES (?)
            """,
            (name,),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all(self):
        """Получить все комплексы."""
        self.cursor.execute(
            """
            SELECT *
            FROM complexes
            ORDER BY id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, complex_id: int):
        """Получить комплекс по ID."""
        self.cursor.execute(
            """
            SELECT *
            FROM complexes
            WHERE id = ?
            """,
            (complex_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_by_name(self, name: str):
        """Получить комплекс по имени."""
        self.cursor.execute(
            """
            SELECT *
            FROM complexes
            WHERE name = ?
            """,
            (name,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def delete(self, complex_id: int) -> None:
        """Удалить комплекс по ID."""
        self.cursor.execute(
            """
            DELETE FROM complexes
            WHERE id = ?
            """,
            (complex_id,),
        )
        self.conn.commit()