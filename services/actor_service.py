from repositories.actor_repository import ActorRepository


class ActorService:
    """Сервис сотрудников и участников системы.

    Здесь уже есть бизнес-валидация:
    - имя не пустое
    - роль не пустая
    - нельзя работать с несуществующим актором
    - можно создать актора вместе с основной ролью
    """

    def __init__(self, conn):
        self.actor_repo = ActorRepository(conn)

    def create_actor(
        self,
        full_name: str,
        display_name: str | None = None,
        actor_type: str = "employee",
        default_manager_commission_pct: float = 0.0,
        primary_role_code: str | None = None,
        is_active: int = 1,
    ) -> int:
        """Создать актора и при необходимости сразу добавить основную роль."""
        normalized_full_name = (full_name or "").strip()
        normalized_display_name = (display_name or "").strip() or None
        normalized_actor_type = (actor_type or "employee").strip()
        normalized_role = (primary_role_code or "").strip() or None

        if not normalized_full_name:
            raise ValueError("Имя сотрудника не может быть пустым.")

        if default_manager_commission_pct < 0:
            raise ValueError("Комиссия менеджера не может быть отрицательной.")

        actor_id = self.actor_repo.create(
            full_name=normalized_full_name,
            display_name=normalized_display_name,
            actor_type=normalized_actor_type,
            default_manager_commission_pct=default_manager_commission_pct,
            is_active=is_active,
        )

        if normalized_role:
            self.actor_repo.add_role(
                actor_id=actor_id,
                role_code=normalized_role,
                is_primary=1,
            )

        return actor_id

    def add_role_to_actor(self, actor_id: int, role_code: str, is_primary: int = 0) -> int:
        """Добавить роль существующему актору."""
        actor = self.actor_repo.get_by_id(actor_id)
        if not actor:
            raise ValueError("Сотрудник не найден.")

        normalized_role = (role_code or "").strip()
        if not normalized_role:
            raise ValueError("Роль не может быть пустой.")

        return self.actor_repo.add_role(
            actor_id=actor_id,
            role_code=normalized_role,
            is_primary=is_primary,
        )

    def get_all_actors(self):
        """Получить всех сотрудников и участников."""
        return self.actor_repo.get_all()

    def get_active_actors(self):
        """Получить только активных сотрудников и участников."""
        return self.actor_repo.get_active()

    def get_actor_by_id(self, actor_id: int):
        """Получить актора по ID."""
        actor = self.actor_repo.get_by_id(actor_id)
        if not actor:
            raise ValueError("Сотрудник не найден.")
        return actor

    def get_actor_roles(self, actor_id: int):
        """Получить все роли актора."""
        actor = self.actor_repo.get_by_id(actor_id)
        if not actor:
            raise ValueError("Сотрудник не найден.")

        return self.actor_repo.get_roles_by_actor_id(actor_id)

    def get_actors_by_role(self, role_code: str):
        """Получить всех акторов по роли."""
        normalized_role = (role_code or "").strip()
        if not normalized_role:
            raise ValueError("Роль не может быть пустой.")

        return self.actor_repo.get_by_role(normalized_role)

    def update_actor(
        self,
        actor_id: int,
        full_name: str,
        display_name: str | None = None,
        actor_type: str = "employee",
        default_manager_commission_pct: float = 0.0,
        is_active: int = 1,
        role_codes: list[str] | None = None,
    ) -> None:
        """Обновить актора и при необходимости полностью пересобрать роли."""
        actor = self.actor_repo.get_by_id(actor_id)
        if not actor:
            raise ValueError("Сотрудник не найден.")

        normalized_full_name = (full_name or "").strip()
        normalized_display_name = (display_name or "").strip() or None
        normalized_actor_type = (actor_type or "employee").strip()

        if not normalized_full_name:
            raise ValueError("Имя сотрудника не может быть пустым.")

        if default_manager_commission_pct < 0:
            raise ValueError("Комиссия менеджера не может быть отрицательной.")

        self.actor_repo.update(
            actor_id=actor_id,
            full_name=normalized_full_name,
            display_name=normalized_display_name,
            actor_type=normalized_actor_type,
            default_manager_commission_pct=default_manager_commission_pct,
            is_active=is_active,
        )

        if role_codes is not None:
            cleaned_roles = []
            for role in role_codes:
                normalized_role = (role or "").strip()
                if normalized_role:
                    cleaned_roles.append(normalized_role)

            self.actor_repo.delete_roles(actor_id)

            for index, role_code in enumerate(cleaned_roles):
                self.actor_repo.add_role(
                    actor_id=actor_id,
                    role_code=role_code,
                    is_primary=1 if index == 0 else 0,
                )

    def delete_actor(self, actor_id: int) -> None:
        """Удалить актора."""
        actor = self.actor_repo.get_by_id(actor_id)
        if not actor:
            raise ValueError("Сотрудник не найден.")

        self.actor_repo.delete(actor_id)