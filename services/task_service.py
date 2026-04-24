from repositories.task_repository import TaskRepository
from repositories.apartment_repository import ApartmentRepository
from repositories.booking_repository import BookingRepository


class TaskService:
    """Сервис задач.

    Здесь уже есть нормальная бизнес-валидация:
    - квартира должна существовать
    - бронь должна существовать (если указана)
    - статус должен быть валидным
    - задачу нельзя обновить, если её не существует
    """

    VALID_STATUSES = {"new", "in_progress", "done"}
    TASK_TYPE_CLEANING = "cleaning"

    def __init__(self, conn):
        self.task_repo = TaskRepository(conn)
        self.apartment_repo = ApartmentRepository(conn)
        self.booking_repo = BookingRepository(conn)

    def create_cleaning_task(
        self,
        apartment_id: int,
        booking_id: int | None = None,
    ) -> int:
        """Создать новую задачу уборки и вернуть её ID."""
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        if booking_id is not None:
            booking = self.booking_repo.get_by_id(booking_id)
            if not booking:
                raise ValueError("Бронь не найдена.")

        return self.task_repo.create(
            apartment_id=apartment_id,
            booking_id=booking_id,
            task_type=self.TASK_TYPE_CLEANING,
            notes=None,
        )

    def start_task(self, task_id: int) -> None:
        """Начать выполнение задачи."""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Задача не найдена.")

        if task["status"] not in {"new", "in_progress"}:
            raise ValueError(f"Задача не может быть начата со статуса '{task['status']}'.")

        self.task_repo.update_status(task_id, "in_progress")

    def complete_task(self, task_id: int) -> None:
        """Завершить задачу."""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Задача не найдена.")

        if task["status"] == "done":
            raise ValueError("Задача уже завершена.")

        self.task_repo.update_status(task_id, "done")

    def list_tasks(self):
        """Получить все задачи."""
        return self.task_repo.get_all()

    def get_tasks_by_apartment(self, apartment_id: int):
        """Получить все задачи конкретной квартиры."""
        apartment = self.apartment_repo.get_by_id(apartment_id)
        if not apartment:
            raise ValueError("Квартира не найдена.")

        return self.task_repo.get_by_apartment_id(apartment_id)
