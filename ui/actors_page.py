import streamlit as st

from services.actor_service import ActorService


ACTOR_TYPE_LABELS = {
    "employee": "Сотрудник",
    "partner": "Партнёр",
    "owner_contact": "Контакт собственника",
    "admin": "Администратор",
    "contractor": "Подрядчик",
    "other": "Другое",
}

ROLE_LABELS = {
    "manager": "Менеджер",
    "founder": "Основатель",
    "cofounder": "Сооснователь",
    "director": "Директор",
    "accountant": "Бухгалтер",
    "admin": "Администратор",
    "other": "Другое",
}


def _label(code: str | None, mapping: dict, default: str = "-") -> str:
    if not code:
        return default
    return mapping.get(code, code)


def _translate_roles(roles_raw: str | None) -> str:
    if not roles_raw:
        return "-"
    parts = [part.strip() for part in roles_raw.split(",")]
    translated = [_label(part, ROLE_LABELS, part) for part in parts]
    return ", ".join(translated)


def render_actors_page(conn):
    """Страница сотрудников и участников системы."""

    actor_service = ActorService(conn)

    st.subheader("Сотрудники и участники")
    st.caption("Здесь создаются менеджеры, сооснователи, сотрудники и другие участники системы.")

    # ---------------------------------------------------------
    # ЗАГРУЗКА ДАННЫХ
    # ---------------------------------------------------------
    try:
        actors = actor_service.get_all_actors()
    except Exception as e:
        st.error(f"Ошибка загрузки сотрудников: {e}")
        return

    # ---------------------------------------------------------
    # СПИСОК
    # ---------------------------------------------------------
    if actors:
        rows = []
        for actor in actors:
            display_name = actor.get("display_name") or actor.get("full_name")

            rows.append({
                "ID": actor["id"],
                "Имя": actor["full_name"],
                "Короткое имя": display_name,
                "Тип": _label(actor.get("actor_type"), ACTOR_TYPE_LABELS),
                "Роли": _translate_roles(actor.get("roles")),
                "Ставка менеджера (%)": actor.get("default_manager_commission_pct"),
                "Активен": "Да" if actor.get("is_active") == 1 else "Нет",
                "Создано": actor.get("created_at"),
            })

        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Пока нет сотрудников и участников.")

    st.markdown("---")

    # ---------------------------------------------------------
    # СОЗДАНИЕ
    # ---------------------------------------------------------
    st.markdown("### Создать сотрудника / участника")

    with st.form("create_actor_form", clear_on_submit=True):
        full_name = st.text_input("Полное имя")
        display_name = st.text_input("Короткое имя")

        actor_type = st.selectbox(
            "Тип участника",
            list(ACTOR_TYPE_LABELS.keys()),
            format_func=lambda x: ACTOR_TYPE_LABELS[x],
        )

        primary_role_code = st.selectbox(
            "Основная роль",
            list(ROLE_LABELS.keys()),
            format_func=lambda x: ROLE_LABELS[x],
        )

        default_manager_commission_pct = st.number_input(
            "Ставка менеджера по умолчанию (%)",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=1.0
        )

        submitted = st.form_submit_button("Создать")

        if submitted:
            try:
                actor_id = actor_service.create_actor(
                    full_name=full_name,
                    display_name=display_name,
                    actor_type=actor_type,
                    default_manager_commission_pct=default_manager_commission_pct,
                    primary_role_code=primary_role_code,
                    is_active=1,
                )
                st.success(f"Участник создан. ID = {actor_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка создания участника: {e}")

    st.markdown("---")

    # ---------------------------------------------------------
    # УДАЛЕНИЕ
    # ---------------------------------------------------------
    st.markdown("### Удалить участника")

    if actors:
        actor_options = {
            f"{actor['id']} - {actor['full_name']}": actor["id"]
            for actor in actors
        }

        with st.form("delete_actor_form"):
            selected_actor = st.selectbox("Выбери участника", list(actor_options.keys()))
            submitted_delete = st.form_submit_button("Удалить")

            if submitted_delete:
                try:
                    actor_service.delete_actor(actor_options[selected_actor])
                    st.success("Участник удалён.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка удаления участника: {e}")
    else:
        st.info("Нет участников для удаления.")