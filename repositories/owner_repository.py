from repositories.base_repository import BaseRepository


class OwnerRepository(BaseRepository):
    """Репозиторий собственников.

    Здесь только работа с таблицей owners:
    - создать
    - получить список
    - получить по id
    - получить по имени
    """

    def create(self, name: str) -> int:
        """Создать нового собственника и вернуть его ID."""
        self.cursor.execute(
            """
            INSERT INTO owners (name)
            VALUES (?)
            """,
            (name,),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all(self):
        """Получить всех собственников."""
        self.cursor.execute(
            """
            SELECT *
            FROM owners
            ORDER BY id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, owner_id: int):
        """Получить собственника по ID."""
        self.cursor.execute(
            """
            SELECT *
            FROM owners
            WHERE id = ?
            """,
            (owner_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_by_name(self, name: str):
        """Получить собственника по имени."""
        self.cursor.execute(
            """
            SELECT *
            FROM owners
            WHERE name = ?
            """,
            (name,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def delete(self, owner_id: int) -> None:
        """Удалить собственника по ID."""
        self.cursor.execute(
            """
            DELETE FROM owners
            WHERE id = ?
            """,
            (owner_id,),
        )
        self.conn.commit()