import streamlit as st

from services.complex_service import ComplexService


def render_complexes_page(conn):
    """Страница комплексов."""

    complex_service = ComplexService(conn)

    st.subheader("Комплексы")
    st.caption("Здесь создаются комплексы, например: Solis, White Sails и другие.")

    # ---------------------------------------------------------
    # СПИСОК КОМПЛЕКСОВ
    # ---------------------------------------------------------
    try:
        complexes = complex_service.get_all_complexes()
    except Exception as e:
        st.error(f"Ошибка загрузки комплексов: {e}")
        return

    if complexes:
        rows = []
        for complex_item in complexes:
            rows.append({
                "ID": complex_item["id"],
                "Название": complex_item["name"],
                "Создано": complex_item.get("created_at"),
            })

        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Пока нет комплексов.")

    st.markdown("---")

    # ---------------------------------------------------------
    # СОЗДАНИЕ КОМПЛЕКСА
    # ---------------------------------------------------------
    st.markdown("### Создать комплекс")

    with st.form("create_complex_form"):
        name = st.text_input("Название комплекса")
        submitted = st.form_submit_button("Создать")

        if submitted:
            try:
                complex_id = complex_service.create_complex(name)
                st.success(f"Комплекс создан. ID = {complex_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка создания комплекса: {e}")

    st.markdown("---")

    # ---------------------------------------------------------
    # УДАЛЕНИЕ КОМПЛЕКСА
    # ---------------------------------------------------------
    st.markdown("### Удалить комплекс")

    if complexes:
        options = {
            f"{complex_item['id']} - {complex_item['name']}": complex_item["id"]
            for complex_item in complexes
        }

        with st.form("delete_complex_form"):
            selected = st.selectbox("Выбери комплекс", list(options.keys()))
            submitted_delete = st.form_submit_button("Удалить")

            if submitted_delete:
                try:
                    complex_service.delete_complex(options[selected])
                    st.success("Комплекс удалён.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка удаления комплекса: {e}")
    else:
        st.info("Нет комплексов для удаления.")