import streamlit as st

from services.apartment_service import ApartmentService
from services.owner_service import OwnerService
from services.complex_service import ComplexService


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