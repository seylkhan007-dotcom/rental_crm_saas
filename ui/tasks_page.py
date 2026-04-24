import streamlit as st

from services.task_service import TaskService
from repositories.apartment_repository import ApartmentRepository
from repositories.booking_repository import BookingRepository


STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В процессе",
    "done": "Завершена",
}

TASK_TYPE_LABELS = {
    "cleaning": "Уборка",
}


def _label(code: str | None, mapping: dict, default: str = "-") -> str:
    if not code:
        return default
    return mapping.get(code, code)


def render_tasks_page(conn):
    """Страница задач."""

    task_service = TaskService(conn)
    apartment_repo = ApartmentRepository(conn)
    booking_repo = BookingRepository(conn)

    st.subheader("Задачи")
    st.caption("Управление задачами для уборки квартир.")

    # ---------------------------------------------------------
    # ЗАГРУЗКА ДАННЫХ
    # ---------------------------------------------------------
    try:
        tasks = task_service.list_tasks()
        apartments = apartment_repo.get_all()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    apartment_map = {apt["id"]: apt["name"] for apt in apartments}

    # ---------------------------------------------------------
    # СПИСОК ЗАДАЧ
    # ---------------------------------------------------------
    st.markdown("### Все задачи")

    if tasks:
        rows = []
        for task in tasks:
            rows.append({
                "ID": task["id"],
                "Квартира": apartment_map.get(task["apartment_id"], f"ID {task['apartment_id']}"),
                "Бронь ID": task["booking_id"] or "-",
                "Тип": _label(task.get("task_type"), TASK_TYPE_LABELS),
                "Статус": _label(task.get("status"), STATUS_LABELS),
                "Заметки": task.get("notes") or "-",
                "Создано": task.get("created_at"),
            })

        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Пока нет задач.")

    st.markdown("---")

    # ---------------------------------------------------------
    # СОЗДАНИЕ ЗАДАЧИ УБОРКИ
    # ---------------------------------------------------------
    st.markdown("### Создать задачу уборки")

    if not apartments:
        st.warning("Сначала создай хотя бы одну квартиру.")
    else:
        apartment_options = {
            f"{apt['id']} - {apt['name']}": apt["id"]
            for apt in apartments
        }

        with st.form("create_task_form"):
            selected_apartment = st.selectbox("Квартира", list(apartment_options.keys()))
            booking_id_input = st.text_input(
                "ID бронирования (опционально)",
                value="",
                placeholder="Оставь пусто если задача не связана с бронью",
            )
            submitted = st.form_submit_button("Создать задачу")

            if submitted:
                try:
                    apartment_id = apartment_options[selected_apartment]
                    booking_id = None

                    if booking_id_input.strip():
                        try:
                            booking_id = int(booking_id_input.strip())
                        except ValueError:
                            st.error("ID бронирования должно быть числом.")
                            st.stop()

                    task_id = task_service.create_cleaning_task(
                        apartment_id=apartment_id,
                        booking_id=booking_id,
                    )
                    st.success(f"Задача создана. ID = {task_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка создания задачи: {e}")

    st.markdown("---")

    # ---------------------------------------------------------
    # УПРАВЛЕНИЕ СТАТУСОМ ЗАДАЧИ
    # ---------------------------------------------------------
    st.markdown("### Управление статусом")

    if tasks:
        task_options = {}
        for task in tasks:
            apartment_name = apartment_map.get(task["apartment_id"], f"ID {task['apartment_id']}")
            label = f"{task['id']} - {_label(task.get('task_type'), TASK_TYPE_LABELS)} - {apartment_name} - {_label(task.get('status'), STATUS_LABELS)}"
            task_options[label] = task["id"]

        with st.form("task_status_form"):
            selected_task_label = st.selectbox("Выбери задачу", list(task_options.keys()))
            selected_task_id = task_options[selected_task_label]

            # Получи текущий статус задачи
            current_task = next((t for t in tasks if t["id"] == selected_task_id), None)
            current_status = current_task.get("status") if current_task else "new"

            col1, col2 = st.columns(2)

            with col1:
                start_submitted = st.form_submit_button("Начать выполнение")

            with col2:
                complete_submitted = st.form_submit_button("Завершить")

            if start_submitted:
                try:
                    task_service.start_task(selected_task_id)
                    st.success("Задача начата.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")

            if complete_submitted:
                try:
                    task_service.complete_task(selected_task_id)
                    st.success("Задача завершена.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    else:
        st.info("Нет задач для управления.")
