import streamlit as st

from services.lead_service import LeadService
from repositories.apartment_repository import ApartmentRepository


def render_leads_page(conn):
    """Страница управления лидами (потенциальные клиенты)."""

    lead_service = LeadService(conn)
    apartment_repo = ApartmentRepository(conn)

    st.subheader("Лиды")
    st.caption("Здесь создаются и управляются потенциальные клиенты до их превращения в бронирования.")

    # Initialize session state for flash messages and edit state
    if "lead_flash_message" not in st.session_state:
        st.session_state.lead_flash_message = None
    if "lead_flash_type" not in st.session_state:
        st.session_state.lead_flash_type = None
    if "edit_success_flag" not in st.session_state:
        st.session_state.edit_success_flag = False

    # Display flash message if exists
    if st.session_state.lead_flash_message:
        if st.session_state.lead_flash_type == "success":
            st.success(st.session_state.lead_flash_message)
        elif st.session_state.lead_flash_type == "error":
            st.error(st.session_state.lead_flash_message)
        # Clear the message after display
        st.session_state.lead_flash_message = None
        st.session_state.lead_flash_type = None

    # ---------------------------------------------------------
    # ЗАГРУЗКА ДАННЫХ
    # ---------------------------------------------------------
    try:
        leads = lead_service.get_all_leads()
        apartments = apartment_repo.get_all()
    except Exception as e:
        st.error(f"Ошибка загрузки лидов: {e}")
        return

    # ---------------------------------------------------------
    # СПИСОК ЛИДОВ
    # ---------------------------------------------------------
    if leads:
        rows = []
        for lead in leads:
            apartment_name = "-"
            if lead.get("apartment_id"):
                apt = next(
                    (a for a in apartments if a.get("id") == lead.get("apartment_id")),
                    None,
                )
                if apt:
                    apartment_name = apt.get("name", "-")

            rows.append({
                "ID": lead["id"],
                "Имя": lead["name"],
                "Телефон": lead["phone"],
                "Статус": lead.get("pipeline_status", "NEW"),
                "Источник": lead.get("source_channel", "-"),
                "Квартира": apartment_name,
                "Создано": lead.get("created_at", "-"),
            })

        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Пока нет лидов.")

    st.markdown("---")

    # ---------------------------------------------------------
    # СОЗДАНИЕ ЛИДА
    # ---------------------------------------------------------
    st.markdown("### Создать лида")

    with st.form("create_lead_form", clear_on_submit=True):
        name = st.text_input("Имя *", help="Обязательное поле", key="create_name")
        phone = st.text_input("Телефон *", help="Обязательное поле", key="create_phone")
        whatsapp = st.text_input("WhatsApp", help="Если отличается от телефона", key="create_whatsapp")
        email = st.text_input("Email", key="create_email")

        source_options = ["MANUAL_ENTRY", "PHONE_CALL", "REFERRAL", "OTHER"]
        source = st.selectbox(
            "Источник *",
            source_options,
            help="Как лид попал в систему",
            key="create_source",
        )

        apt_options = {f"{a['id']} - {a['name']}": a["id"] for a in apartments}
        apt_options_list = ["Нет"] + list(apt_options.keys())
        selected_apt = st.selectbox("Заинтересована квартира", apt_options_list, key="create_apt")
        apartment_id = apt_options.get(selected_apt) if selected_apt != "Нет" else None

        notes = st.text_area("Заметки", key="create_notes")

        submitted = st.form_submit_button("Создать", use_container_width=True)

        if submitted:
            try:
                if not name or not phone or not source:
                    st.session_state.lead_flash_message = "Заполните все обязательные поля: Имя, Телефон, Источник"
                    st.session_state.lead_flash_type = "error"
                else:
                    lead = lead_service.create_lead(
                        name=name,
                        phone=phone,
                        source_channel=source,
                        created_by=1,
                        whatsapp_number=whatsapp or None,
                        email=email or None,
                        apartment_id=apartment_id,
                        notes=notes or None,
                    )
                    st.session_state.lead_flash_message = f"✅ Лид '{lead['name']}' создан успешно!"
                    st.session_state.lead_flash_type = "success"
                    st.rerun()
            except ValueError as e:
                st.session_state.lead_flash_message = f"❌ Ошибка: {e}"
                st.session_state.lead_flash_type = "error"
                st.rerun()
            except Exception as e:
                st.session_state.lead_flash_message = f"❌ Ошибка создания лида: {e}"
                st.session_state.lead_flash_type = "error"
                st.rerun()

    st.markdown("---")

    # ---------------------------------------------------------
    # РЕДАКТИРОВАНИЕ ЛИДА
    # ---------------------------------------------------------
    if leads:
        st.markdown("### Редактировать лида")

        lead_options = {
            f"{lead['id']} - {lead['name']} ({lead.get('phone', '-')})": lead["id"]
            for lead in leads
        }

        # If edit just succeeded, reset to first option (creates clear visual feedback)
        if st.session_state.edit_success_flag:
            edit_default_index = 0
            st.session_state.edit_success_flag = False
        else:
            edit_default_index = 0

        with st.form("edit_lead_form", clear_on_submit=True):
            selected_lead_key = st.selectbox(
                "Выбери лида для редактирования",
                list(lead_options.keys()),
                key="edit_select",
                index=edit_default_index,
            )
            selected_lead_id = lead_options[selected_lead_key]
            selected_lead = next(l for l in leads if l["id"] == selected_lead_id)

            edit_name = st.text_input(
                "Имя",
                value=selected_lead.get("name", ""),
                key="edit_name",
            )
            edit_phone = st.text_input(
                "Телефон",
                value=selected_lead.get("phone", ""),
                key="edit_phone",
            )
            edit_whatsapp = st.text_input(
                "WhatsApp",
                value=selected_lead.get("whatsapp_number") or "",
                key="edit_whatsapp",
            )
            edit_email = st.text_input(
                "Email",
                value=selected_lead.get("email") or "",
                key="edit_email",
            )

            edit_status = st.selectbox(
                "Статус",
                ["NEW", "QUALIFIED", "INTERESTED", "NEGOTIATING", "LOST"],
                index=["NEW", "QUALIFIED", "INTERESTED", "NEGOTIATING", "LOST"].index(
                    selected_lead.get("pipeline_status", "NEW")
                ),
                key="edit_status",
            )

            edit_apt_options = {f"{a['id']} - {a['name']}": a["id"] for a in apartments}
            edit_apt_options_list = ["Нет"] + list(edit_apt_options.keys())
            
            current_apt_key = "Нет"
            if selected_lead.get("apartment_id"):
                for key, val in edit_apt_options.items():
                    if val == selected_lead.get("apartment_id"):
                        current_apt_key = key
                        break
            
            edit_selected_apt = st.selectbox(
                "Квартира",
                edit_apt_options_list,
                index=edit_apt_options_list.index(current_apt_key),
                key="edit_apt",
            )
            edit_apartment_id = (
                edit_apt_options.get(edit_selected_apt)
                if edit_selected_apt != "Нет"
                else None
            )

            edit_notes = st.text_area(
                "Заметки",
                value=selected_lead.get("notes") or "",
                key="edit_notes",
            )

            submitted_edit = st.form_submit_button("Сохранить", use_container_width=True)

            if submitted_edit:
                try:
                    updates = {
                        "name": edit_name,
                        "phone": edit_phone,
                        "whatsapp_number": edit_whatsapp or None,
                        "email": edit_email or None,
                        "pipeline_status": edit_status,
                        "apartment_id": edit_apartment_id,
                        "notes": edit_notes or None,
                    }
                    lead_service.update_lead(selected_lead_id, updates)
                    st.session_state.lead_flash_message = f"✅ Лид '{edit_name}' обновлён успешно!"
                    st.session_state.lead_flash_type = "success"
                    st.session_state.edit_success_flag = True
                    st.rerun()
                except Exception as e:
                    st.session_state.lead_flash_message = f"❌ Ошибка редактирования лида: {e}"
                    st.session_state.lead_flash_type = "error"
                    st.rerun()

    st.markdown("---")

    # ---------------------------------------------------------
    # УДАЛЕНИЕ ЛИДА
    # ---------------------------------------------------------
    if leads:
        st.markdown("### Удалить лида")

        delete_lead_options = {
            f"{lead['id']} - {lead['name']}": lead["id"]
            for lead in leads
        }

        with st.form("delete_lead_form", clear_on_submit=True):
            selected_delete_lead = st.selectbox(
                "Выбери лида для удаления",
                list(delete_lead_options.keys()),
                key="delete_select",
            )
            submitted_delete = st.form_submit_button("Удалить", type="secondary", use_container_width=True)

            if submitted_delete:
                try:
                    deleted_lead_id = delete_lead_options[selected_delete_lead]
                    deleted_lead_name = next(
                        (l["name"] for l in leads if l["id"] == deleted_lead_id),
                        "Лид",
                    )
                    lead_service.lead_repo.delete(deleted_lead_id)
                    st.session_state.lead_flash_message = f"✅ Лид '{deleted_lead_name}' удалён успешно!"
                    st.session_state.lead_flash_type = "success"
                    st.rerun()
                except Exception as e:
                    st.session_state.lead_flash_message = f"❌ Ошибка удаления лида: {e}"
                    st.session_state.lead_flash_type = "error"
                    st.rerun()


