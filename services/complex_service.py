from repositories.complex_repository import ComplexRepository


class ComplexService:
    """Сервис комплексов.

    Здесь простая бизнес-валидация:
    - название не пустое
    - нельзя создать дубль по имени
    - нельзя удалить несуществующий комплекс
    """

    def __init__(self, conn):
        self.complex_repo = ComplexRepository(conn)

    def create_complex(self, name: str) -> int:
        """Создать комплекс и вернуть его ID."""
        normalized_name = (name or "").strip()

        if not normalized_name:
            raise ValueError("Название комплекса не может быть пустым.")

        existing_complex = self.complex_repo.get_by_name(normalized_name)
        if existing_complex:
            raise ValueError("Комплекс с таким названием уже существует.")

        return self.complex_repo.create(normalized_name)

    def get_all_complexes(self):
        """Получить все комплексы."""
        return self.complex_repo.get_all()

    def get_complex_by_id(self, complex_id: int):
        """Получить комплекс по ID."""
        complex_item = self.complex_repo.get_by_id(complex_id)
        if not complex_item:
            raise ValueError("Комплекс не найден.")
        return complex_item

    def delete_complex(self, complex_id: int) -> None:
        """Удалить комплекс по ID."""
        complex_item = self.complex_repo.get_by_id(complex_id)
        if not complex_item:
            raise ValueError("Комплекс не найден.")

        self.complex_repo.delete(complex_id)