from repositories.base_repository import BaseRepository


class ActorRepository(BaseRepository):
    """Репозиторий сотрудников и участников системы.

    Работает с таблицами:
    - app_actors
    - actor_roles

    Здесь только CRUD и чтение данных.
    Без бизнес-логики.
    """

    def create(
        self,
        full_name: str,
        display_name: str | None = None,
        actor_type: str = "employee",
        default_manager_commission_pct: float = 0.0,
        is_active: int = 1,
    ) -> int:
        """Создать нового актора и вернуть его ID."""
        self.cursor.execute(
            """
            INSERT INTO app_actors (
                full_name,
                display_name,
                actor_type,
                default_manager_commission_pct,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                full_name,
                display_name,
                actor_type,
                default_manager_commission_pct,
                is_active,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def add_role(self, actor_id: int, role_code: str, is_primary: int = 0) -> int:
        """Добавить роль актору."""
        self.cursor.execute(
            """
            INSERT INTO actor_roles (
                actor_id,
                role_code,
                is_primary,
                created_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                actor_id,
                role_code,
                is_primary,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all(self):
        """Получить список всех акторов вместе с их ролями."""
        self.cursor.execute(
            """
            SELECT
                a.id,
                a.full_name,
                a.display_name,
                a.actor_type,
                a.default_manager_commission_pct,
                a.is_active,
                a.created_at,
                a.updated_at,
                GROUP_CONCAT(ar.role_code, ', ') AS roles
            FROM app_actors a
            LEFT JOIN actor_roles ar ON ar.actor_id = a.id
            GROUP BY
                a.id,
                a.full_name,
                a.display_name,
                a.actor_type,
                a.default_manager_commission_pct,
                a.is_active,
                a.created_at,
                a.updated_at
            ORDER BY a.id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, actor_id: int):
        """Получить актора по ID."""
        self.cursor.execute(
            """
            SELECT *
            FROM app_actors
            WHERE id = ?
            """,
            (actor_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_roles_by_actor_id(self, actor_id: int):
        """Получить все роли одного актора."""
        self.cursor.execute(
            """
            SELECT *
            FROM actor_roles
            WHERE actor_id = ?
            ORDER BY is_primary DESC, id ASC
            """,
            (actor_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_role(self, role_code: str):
        """Получить всех акторов по конкретной роли."""
        self.cursor.execute(
            """
            SELECT
                a.id,
                a.full_name,
                a.display_name,
                a.actor_type,
                a.default_manager_commission_pct,
                a.is_active,
                a.created_at,
                a.updated_at
            FROM app_actors a
            INNER JOIN actor_roles ar ON ar.actor_id = a.id
            WHERE ar.role_code = ?
            ORDER BY a.id DESC
            """,
            (role_code,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_active(self):
        """Получить только активных акторов."""
        self.cursor.execute(
            """
            SELECT
                a.id,
                a.full_name,
                a.display_name,
                a.actor_type,
                a.default_manager_commission_pct,
                a.is_active,
                a.created_at,
                a.updated_at,
                GROUP_CONCAT(ar.role_code, ', ') AS roles
            FROM app_actors a
            LEFT JOIN actor_roles ar ON ar.actor_id = a.id
            WHERE a.is_active = 1
            GROUP BY
                a.id,
                a.full_name,
                a.display_name,
                a.actor_type,
                a.default_manager_commission_pct,
                a.is_active,
                a.created_at,
                a.updated_at
            ORDER BY a.id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def update(
        self,
        actor_id: int,
        full_name: str,
        display_name: str | None = None,
        actor_type: str = "employee",
        default_manager_commission_pct: float = 0.0,
        is_active: int = 1,
    ) -> None:
        """Обновить основную информацию об акторе."""
        self.cursor.execute(
            """
            UPDATE app_actors
            SET
                full_name = ?,
                display_name = ?,
                actor_type = ?,
                default_manager_commission_pct = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                full_name,
                display_name,
                actor_type,
                default_manager_commission_pct,
                is_active,
                actor_id,
            ),
        )
        self.conn.commit()

    def delete_roles(self, actor_id: int) -> None:
        """Удалить все роли актора."""
        self.cursor.execute(
            """
            DELETE FROM actor_roles
            WHERE actor_id = ?
            """,
            (actor_id,),
        )
        self.conn.commit()

    def delete(self, actor_id: int) -> None:
        """Удалить актора и его роли."""
        self.delete_roles(actor_id)

        self.cursor.execute(
            """
            DELETE FROM app_actors
            WHERE id = ?
            """,
            (actor_id,),
        )
        self.conn.commit()