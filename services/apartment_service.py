from repositories.apartment_repository import ApartmentRepository
from repositories.owner_repository import OwnerRepository
from repositories.complex_repository import ComplexRepository


class ApartmentService:
    """Сервис квартир.

    Здесь уже есть нормальная бизнес-валидация:
    - название квартиры не пустое
    - собственник должен существовать
    - комплекс должен существовать
    - квартиру нельзя удалить, если её не существует
    """

    def __init__(self, conn):
        self.apartment_repo = ApartmentRepository(conn)
        self.owner_repo = OwnerRepository(conn)
        self.complex_repo = ComplexRepository(conn)

    def create_apartment(
        self,
        name: str,
        owner_id: int,
        complex_id: int | None = None,
    ) -> int:
        """Создать квартиру и вернуть её ID."""
        normalized_name = (name or "").strip()

        if not normalized_name:
            raise ValueError("Название квартиры не может быть пустым.")

        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")

        if complex_id is not None:
            complex_item = self.complex_repo.get_by_id(complex_id)
            if not complex_item:
                raise ValueError("Комплекс не найден.")

        return self.apartment_repo.create(
            name=normalized_name,
            owner_id=owner_id,
            complex_id=complex_id,
        )

    def get_all_apartments(self):
        """Получить все квартиры."""
        return self.apartment_repo.get_all()

    def get_apartment_by_id(self, apartment_id: int):
        """Получить квартиру по ID."""
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")
        return apartment

    def get_apartments_by_owner_id(self, owner_id: int):
        """Получить все квартиры конкретного собственника."""
        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")

        return self.apartment_repo.get_by_owner_id(owner_id)

    def get_apartments_by_complex_id(self, complex_id: int):
        """Получить все квартиры конкретного комплекса."""
        complex_item = self.complex_repo.get_by_id(complex_id)
        if not complex_item:
            raise ValueError("Комплекс не найден.")

        return self.apartment_repo.get_by_complex_id(complex_id)

    def update_apartment(
        self,
        apartment_id: int,
        name: str,
        owner_id: int,
        complex_id: int | None = None,
    ) -> None:
        """Обновить квартиру."""
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        normalized_name = (name or "").strip()

        if not normalized_name:
            raise ValueError("Название квартиры не может быть пустым.")

        owner = self.owner_repo.get_by_id(owner_id)
        if not owner:
            raise ValueError("Собственник не найден.")

        if complex_id is not None:
            complex_item = self.complex_repo.get_by_id(complex_id)
            if not complex_item:
                raise ValueError("Комплекс не найден.")

        self.apartment_repo.update(
            apartment_id=apartment_id,
            name=normalized_name,
            owner_id=owner_id,
            complex_id=complex_id,
        )

    def delete_apartment(self, apartment_id: int) -> None:
        """Удалить квартиру по ID."""
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        self.apartment_repo.delete(apartment_id)