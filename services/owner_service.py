from repositories.owner_repository import OwnerRepository


class OwnerService:
    """Сервис собственников.

    Здесь уже не просто SQL-доступ, а простая бизнес-валидация:
    - имя не пустое
    - нельзя создать дубль по имени
    - нельзя удалить несуществующего собственника
    """

    def __init__(self, conn):
        self.owner_repo = OwnerRepository(conn)

    def create_owner(self, name: str) -> int:
        """Создать собственника и вернуть его ID."""
        normalized_name = (name or "").strip()

        if not normalized_name:
            raise ValueError("Имя собственника не может быть пустым.")

        existing_owner = self.owner_repo.get_by_name(normalized_name)
        if existing_owner:
            raise ValueError("Собственник с таким именем уже существует.")

        return self.owner_repo.create(normalized_name)

    def get_all_owners(self):
        """Получить всех собственников."""
        return self.owner_repo.get_all()

    def get_owner_by_id(self, owner_id: int):
        """Получить собственника по ID."""
        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")
        return owner

    def delete_owner(self, owner_id: int) -> None:
        """Удалить собственника по ID."""
        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")

        self.owner_repo.delete(owner_id)