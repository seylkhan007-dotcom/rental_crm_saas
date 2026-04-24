import streamlit as st

from services.apartment_service import ApartmentService
from services.owner_service import OwnerService
from services.complex_service import ComplexService


def _find_item_by_id(items: list[dict], item_id: int):
    """Найти элемент по ID в списке."""
    for item in items:
        if item["id"] == item_id:
            return item
    return None


def _index_of(options: list[str], value: str | None, fallback: int = 0) -> int:
    """Найти индекс значения в списке опций."""
    if value in options:
        return options.index(value)
    return fallback


def render_apartments_page(conn):
    """Страница квартир."""

    apartment_service = ApartmentService(conn)
    owner_service = OwnerService(conn)
    complex_service = ComplexService(conn)

    st.subheader("Квартиры")
    st.caption("Здесь создаются квартиры и связываются с собственниками и комплексами.")

    # ---------------------------------------------------------
    # ЗАГРУЗКА ДАННЫХ
    # ---------------------------------------------------------
    try:
        apartments = apartment_service.get_all_apartments()
        owners = owner_service.get_all_owners()
        complexes = complex_service.get_all_complexes()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    owner_map = {owner["id"]: owner["name"] for owner in owners}
    complex_map = {complex_item["id"]: complex_item["name"] for complex_item in complexes}

    # ---------------------------------------------------------
    # СПИСОК КВАРТИР
    # ---------------------------------------------------------
    if apartments:
        rows = []
        for apartment in apartments:
            rows.append({
                "ID": apartment["id"],
                "Квартира": apartment["name"],
                "Собственник": owner_map.get(apartment.get("owner_id"), "-"),
                "Комплекс": complex_map.get(apartment.get("complex_id"), "-"),
                "Создано": apartment.get("created_at"),
            })

        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Пока нет квартир.")

    st.markdown("---")

    # ---------------------------------------------------------
    # СОЗДАНИЕ КВАРТИРЫ
    # ---------------------------------------------------------
    st.markdown("### Создать квартиру")

    if not owners:
        st.warning("Сначала создай хотя бы одного собственника.")
    elif not complexes:
        st.warning("Сначала создай хотя бы один комплекс.")
    else:
        owner_options = {
            f"{owner['id']} - {owner['name']}": owner["id"]
            for owner in owners
        }

        complex_options = {
            f"{complex_item['id']} - {complex_item['name']}": complex_item["id"]
            for complex_item in complexes
        }

        with st.form("create_apartment_form"):
            apartment_name = st.text_input("Название / номер квартиры")
            selected_owner = st.selectbox("Собственник", list(owner_options.keys()))
            selected_complex = st.selectbox("Комплекс", list(complex_options.keys()))
            submitted = st.form_submit_button("Создать")

            if submitted:
                try:
                    apartment_id = apartment_service.create_apartment(
                        name=apartment_name,
                        owner_id=owner_options[selected_owner],
                        complex_id=complex_options[selected_complex],
                    )
                    st.success(f"Квартира создана. ID = {apartment_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка создания квартиры: {e}")

    st.markdown("---")

    # ---------------------------------------------------------
    # РЕДАКТИРОВАНИЕ КВАРТИРЫ
    # ---------------------------------------------------------
    st.markdown("### Редактировать квартиру")

    if apartments and owners and complexes:
        apartment_options = {
            f"{apartment['id']} - {apartment['name']}": apartment["id"]
            for apartment in apartments
        }

        selected_apartment_label = st.selectbox(
            "Выбери квартиру для редактирования",
            list(apartment_options.keys()),
            key="edit_apartment_select",
        )

        selected_apartment_id = apartment_options[selected_apartment_label]
        selected_apartment = _find_item_by_id(apartments, selected_apartment_id)

        if selected_apartment:
            owner_options = {
                f"{owner['id']} - {owner['name']}": owner["id"]
                for owner in owners
            }

            complex_options = {
                f"{complex_item['id']} - {complex_item['name']}": complex_item["id"]
                for complex_item in complexes
            }

            owner_keys = list(owner_options.keys())
            complex_keys = list(complex_options.keys())

            current_owner_key = None
            for key, owner_id in owner_options.items():
                if owner_id == selected_apartment["owner_id"]:
                    current_owner_key = key
                    break

            current_complex_key = None
            if selected_apartment.get("complex_id"):
                for key, complex_id in complex_options.items():
                    if complex_id == selected_apartment["complex_id"]:
                        current_complex_key = key
                        break

            with st.form("edit_apartment_form"):
                edit_apartment_name = st.text_input(
                    "Название / номер квартиры",
                    value=selected_apartment.get("name") or "",
                    key="edit_apartment_name",
                )

                edit_owner = st.selectbox(
                    "Собственник",
                    owner_keys,
                    index=_index_of(owner_keys, current_owner_key),
                    key="edit_owner",
                )

                edit_complex = st.selectbox(
                    "Комплекс",
                    complex_keys,
                    index=_index_of(complex_keys, current_complex_key),
                    key="edit_complex",
                )

                submitted_edit = st.form_submit_button("Сохранить изменения")

                if submitted_edit:
                    try:
                        apartment_service.update_apartment(
                            apartment_id=selected_apartment_id,
                            name=edit_apartment_name,
                            owner_id=owner_options[edit_owner],
                            complex_id=complex_options[edit_complex],
                        )
                        st.success(f"Квартира обновлена. ID = {selected_apartment_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка обновления квартиры: {e}")
    else:
        if not apartments:
            st.info("Нет квартир для редактирования.")
        elif not owners or not complexes:
            st.warning("Для редактирования нужны собственники и комплексы.")

    st.markdown("---")

    # ---------------------------------------------------------
    # УДАЛЕНИЕ КВАРТИРЫ
    # ---------------------------------------------------------
    st.markdown("### Удалить квартиру")

    if apartments:
        apartment_options = {
            f"{apartment['id']} - {apartment['name']}": apartment["id"]
            for apartment in apartments
        }

        with st.form("delete_apartment_form"):
            selected_apartment = st.selectbox("Выбери квартиру", list(apartment_options.keys()))
            submitted_delete = st.form_submit_button("Удалить")

            if submitted_delete:
                try:
                    apartment_service.delete_apartment(apartment_options[selected_apartment])
                    st.success("Квартира удалена.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка удаления квартиры: {e}")
    else:
        st.info("Нет квартир для удаления.")