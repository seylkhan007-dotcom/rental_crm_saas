import streamlit as st

from services.owner_service import OwnerService


def render_owners_page(conn):
    """Страница собственников."""

    owner_service = OwnerService(conn)

    st.subheader("Собственники")
    st.caption("Здесь создаются и отображаются собственники квартир.")

    # ---------------------------------------------------------
    # СПИСОК СОБСТВЕННИКОВ
    # ---------------------------------------------------------
    try:
        owners = owner_service.get_all_owners()
    except Exception as e:
        st.error(f"Ошибка загрузки собственников: {e}")
        return

    if owners:
        owner_rows = []
        for owner in owners:
            owner_rows.append({
                "ID": owner["id"],
                "Имя": owner["name"],
                "Создано": owner.get("created_at"),
            })

        st.dataframe(owner_rows, use_container_width=True)
    else:
        st.info("Собственники пока не созданы.")

    st.markdown("---")

    # ---------------------------------------------------------
    # СОЗДАНИЕ СОБСТВЕННИКА
    # ---------------------------------------------------------
    st.markdown("### Создать собственника")

    with st.form("create_owner_form"):
        owner_name = st.text_input("Имя собственника")
        submitted_create = st.form_submit_button("Создать")

        if submitted_create:
            try:
                owner_id = owner_service.create_owner(owner_name)
                st.success(f"Собственник создан. ID = {owner_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка создания собственника: {e}")

    st.markdown("---")

    # ---------------------------------------------------------
    # УДАЛЕНИЕ СОБСТВЕННИКА
    # ---------------------------------------------------------
    st.markdown("### Удалить собственника")
    st.caption("Удаляй только тех собственников, которые реально не нужны.")

    if owners:
        owner_options = {
            f"{owner['id']} - {owner['name']}": owner["id"]
            for owner in owners
        }

        with st.form("delete_owner_form"):
            selected_owner_label = st.selectbox(
                "Выбери собственника",
                list(owner_options.keys())
            )
            submitted_delete = st.form_submit_button("Удалить")

            if submitted_delete:
                try:
                    owner_id = owner_options[selected_owner_label]
                    owner_service.delete_owner(owner_id)
                    st.success("Собственник удалён.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка удаления собственника: {e}")
    else:
        st.info("Нет собственников для удаления.")