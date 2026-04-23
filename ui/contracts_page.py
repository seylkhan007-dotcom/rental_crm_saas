import streamlit as st

from services.contract_service import ContractService
from services.owner_service import OwnerService


PRICING_MODEL_LABELS = {
    "management": "Управление",
    "sublease": "Субаренда",
}

SPLIT_BASIS_LABELS = {
    "owner_price": "От owner price",
    "net_profit": "От чистой прибыли",
    "custom": "Особая логика",
}

OTA_COST_MODE_LABELS = {
    "company_only": "Компания платит OTA",
    "shared": "OTA делится",
    "owner_only": "Собственник платит OTA",
}

EXPENSE_MODE_LABELS = {
    "rule_based": "По правилам",
    "company_all": "Всё на компанию",
    "owner_all": "Всё на собственника",
    "profit_share_based": "Пропорционально долям прибыли",
}

STAY_TYPE_LABELS = {
    "all": "Для всех типов аренды",
    "short_term": "Краткосрок",
    "long_term": "Долгосрок",
}

RESPONSIBILITY_MODE_LABELS = {
    "company": "Компания",
    "owner": "Собственник",
    "guest": "Гость",
    "split": "Разделить по долям",
}

SUBLEASE_COST_TYPE_LABELS = {
    "daily": "За день",
    "monthly": "За месяц",
}


def _label(code: str | None, mapping: dict, default: str = "-") -> str:
    if not code:
        return default
    return mapping.get(code, code)


def _build_options(mapping: dict) -> list[str]:
    return list(mapping.keys())


def _index_of(options: list[str], value: str | None, fallback: int = 0) -> int:
    if value in options:
        return options.index(value)
    return fallback


def render_contracts_page(conn):
    contract_service = ContractService(conn)
    owner_service = OwnerService(conn)

    st.subheader("Контракты")
    st.caption("Здесь настраиваются профили контрактов, правила распределения и правила расходов.")

    try:
        owners = owner_service.get_all_owners()
        contract_profiles = contract_service.get_all_profiles()
        split_rules = contract_service.get_all_split_rules()
        expense_rules = contract_service.get_all_expense_rules()
    except Exception as e:
        st.error(f"Ошибка загрузки данных по контрактам: {e}")
        return

    # ---------------------------------------------------------
    # ПРОФИЛИ КОНТРАКТОВ
    # ---------------------------------------------------------
    st.markdown("### Профили контрактов")

    if contract_profiles:
        profile_rows = []
        for profile in contract_profiles:
            profile_rows.append({
                "ID": profile["id"],
                "Собственник": profile.get("owner_name"),
                "Название": profile.get("profile_name"),
                "Модель": _label(profile.get("pricing_model"), PRICING_MODEL_LABELS),
                "База распределения": _label(profile.get("split_basis"), SPLIT_BASIS_LABELS),
                "Кто несёт OTA": _label(profile.get("ota_cost_mode"), OTA_COST_MODE_LABELS),
                "Режим расходов": _label(profile.get("expense_mode"), EXPENSE_MODE_LABELS),
                "Тип фикс. субаренды": _label(profile.get("sublease_cost_type"), SUBLEASE_COST_TYPE_LABELS),
                "Фикс. субаренда": profile.get("sublease_cost_value") or 0,
                "Валюта субаренды": profile.get("sublease_currency") or "-",
                "Активен": "Да" if profile.get("is_active") == 1 else "Нет",
                "Комментарий": profile.get("notes"),
                "Создано": profile.get("created_at"),
            })

        st.dataframe(profile_rows, use_container_width=True)
    else:
        st.info("Пока нет контрактов.")

    st.markdown("---")
    st.markdown("### Создать профиль контракта")

    if not owners:
        st.warning("Сначала создай хотя бы одного собственника.")
    else:
        owner_options = {
            f"{owner['id']} - {owner['name']}": owner["id"]
            for owner in owners
        }

        with st.form("create_contract_profile_form"):
            selected_owner = st.selectbox("Собственник", list(owner_options.keys()))
            profile_name = st.text_input("Название контракта", value="Основной контракт")

            pricing_model = st.selectbox(
                "Модель",
                _build_options(PRICING_MODEL_LABELS),
                format_func=lambda x: PRICING_MODEL_LABELS[x],
            )

            split_basis = st.selectbox(
                "База распределения",
                _build_options(SPLIT_BASIS_LABELS),
                format_func=lambda x: SPLIT_BASIS_LABELS[x],
            )

            ota_cost_mode = st.selectbox(
                "Кто несёт OTA",
                _build_options(OTA_COST_MODE_LABELS),
                format_func=lambda x: OTA_COST_MODE_LABELS[x],
            )

            expense_mode = st.selectbox(
                "Режим расходов",
                _build_options(EXPENSE_MODE_LABELS),
                format_func=lambda x: EXPENSE_MODE_LABELS[x],
            )

            st.markdown("#### Условия субаренды")
            st.caption("Заполняется только если модель = субаренда")

            sublease_cost_type_options = [""] + _build_options(SUBLEASE_COST_TYPE_LABELS)
            sublease_cost_type = st.selectbox(
                "Тип фиксированной субаренды",
                sublease_cost_type_options,
                format_func=lambda x: "— не выбрано —" if x == "" else SUBLEASE_COST_TYPE_LABELS[x],
            )

            sublease_cost_value = st.number_input(
                "Фиксированная стоимость субаренды",
                min_value=0.0,
                value=0.0,
                step=10.0
            )

            sublease_currency = st.selectbox(
                "Валюта субаренды",
                ["GEL", "USD", "EUR"]
            )

            notes = st.text_area("Комментарий")
            submitted_profile = st.form_submit_button("Создать контракт")

            if submitted_profile:
                try:
                    normalized_sublease_cost_type = sublease_cost_type if sublease_cost_type else None

                    profile_id = contract_service.create_profile(
                        owner_id=owner_options[selected_owner],
                        profile_name=profile_name,
                        pricing_model=pricing_model,
                        split_basis=split_basis,
                        ota_cost_mode=ota_cost_mode,
                        expense_mode=expense_mode,
                        sublease_cost_type=normalized_sublease_cost_type,
                        sublease_cost_value=sublease_cost_value,
                        sublease_currency=sublease_currency,
                        notes=notes,
                        is_active=1,
                    )
                    st.success(f"Контракт создан. ID = {profile_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка создания контракта: {e}")

    # ---------------------------------------------------------
    # РЕДАКТИРОВАНИЕ ПРОФИЛЯ КОНТРАКТА
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Редактировать профиль контракта")

    if contract_profiles and owners:
        edit_profile_options = {
            f"{profile['id']} - {profile['owner_name']} - {profile['profile_name']}": profile["id"]
            for profile in contract_profiles
        }

        selected_profile_label = st.selectbox(
            "Выбери контракт для редактирования",
            list(edit_profile_options.keys()),
            key="edit_contract_profile_select"
        )

        selected_profile_id = edit_profile_options[selected_profile_label]
        selected_profile = None
        for profile in contract_profiles:
            if profile["id"] == selected_profile_id:
                selected_profile = profile
                break

        if selected_profile:
            owner_keys = list(owner_options.keys())
            current_owner_key = None
            for key, owner_id in owner_options.items():
                if owner_id == selected_profile["owner_id"]:
                    current_owner_key = key
                    break

            pricing_model_options = _build_options(PRICING_MODEL_LABELS)
            split_basis_options = _build_options(SPLIT_BASIS_LABELS)
            ota_cost_mode_options = _build_options(OTA_COST_MODE_LABELS)
            expense_mode_options = _build_options(EXPENSE_MODE_LABELS)
            sublease_cost_type_options = [""] + _build_options(SUBLEASE_COST_TYPE_LABELS)
            currency_options = ["GEL", "USD", "EUR"]

            with st.form("edit_contract_profile_form"):
                edit_owner = st.selectbox(
                    "Собственник",
                    owner_keys,
                    index=_index_of(owner_keys, current_owner_key),
                    key="edit_owner"
                )

                edit_profile_name = st.text_input(
                    "Название контракта",
                    value=selected_profile.get("profile_name") or "",
                    key="edit_profile_name"
                )

                edit_pricing_model = st.selectbox(
                    "Модель",
                    pricing_model_options,
                    index=_index_of(pricing_model_options, selected_profile.get("pricing_model"), 0),
                    format_func=lambda x: PRICING_MODEL_LABELS[x],
                    key="edit_pricing_model"
                )

                edit_split_basis = st.selectbox(
                    "База распределения",
                    split_basis_options,
                    index=_index_of(split_basis_options, selected_profile.get("split_basis"), 0),
                    format_func=lambda x: SPLIT_BASIS_LABELS[x],
                    key="edit_split_basis"
                )

                edit_ota_cost_mode = st.selectbox(
                    "Кто несёт OTA",
                    ota_cost_mode_options,
                    index=_index_of(ota_cost_mode_options, selected_profile.get("ota_cost_mode"), 0),
                    format_func=lambda x: OTA_COST_MODE_LABELS[x],
                    key="edit_ota_cost_mode"
                )

                edit_expense_mode = st.selectbox(
                    "Режим расходов",
                    expense_mode_options,
                    index=_index_of(expense_mode_options, selected_profile.get("expense_mode"), 0),
                    format_func=lambda x: EXPENSE_MODE_LABELS[x],
                    key="edit_expense_mode"
                )

                st.markdown("#### Условия субаренды")
                edit_sublease_cost_type = st.selectbox(
                    "Тип фиксированной субаренды",
                    sublease_cost_type_options,
                    index=_index_of(sublease_cost_type_options, selected_profile.get("sublease_cost_type") or "", 0),
                    format_func=lambda x: "— не выбрано —" if x == "" else SUBLEASE_COST_TYPE_LABELS[x],
                    key="edit_sublease_cost_type"
                )

                edit_sublease_cost_value = st.number_input(
                    "Фиксированная стоимость субаренды",
                    min_value=0.0,
                    value=float(selected_profile.get("sublease_cost_value") or 0.0),
                    step=10.0,
                    key="edit_sublease_cost_value"
                )

                edit_sublease_currency = st.selectbox(
                    "Валюта субаренды",
                    currency_options,
                    index=_index_of(currency_options, selected_profile.get("sublease_currency") or "GEL", 0),
                    key="edit_sublease_currency"
                )

                edit_notes = st.text_area(
                    "Комментарий",
                    value=selected_profile.get("notes") or "",
                    key="edit_notes"
                )

                current_is_active = 1 if selected_profile.get("is_active") == 1 else 0
                edit_is_active = st.checkbox(
                    "Контракт активен",
                    value=True if current_is_active == 1 else False,
                    key="edit_is_active"
                )

                submitted_update = st.form_submit_button("Сохранить изменения")

                if submitted_update:
                    try:
                        normalized_sublease_cost_type = edit_sublease_cost_type if edit_sublease_cost_type else None

                        contract_service.update_profile(
                            contract_profile_id=selected_profile_id,
                            owner_id=owner_options[edit_owner],
                            profile_name=edit_profile_name,
                            pricing_model=edit_pricing_model,
                            split_basis=edit_split_basis,
                            ota_cost_mode=edit_ota_cost_mode,
                            expense_mode=edit_expense_mode,
                            sublease_cost_type=normalized_sublease_cost_type,
                            sublease_cost_value=edit_sublease_cost_value,
                            sublease_currency=edit_sublease_currency,
                            notes=edit_notes,
                            is_active=1 if edit_is_active else 0,
                        )
                        st.success("Контракт обновлён.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка обновления контракта: {e}")
    else:
        st.info("Нет контрактов для редактирования.")

    # ---------------------------------------------------------
    # ПРАВИЛА РАСПРЕДЕЛЕНИЯ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Правила распределения")

    if split_rules:
        split_rows = []
        for rule in split_rules:
            split_rows.append({
                "ID": rule["id"],
                "Контракт": rule.get("profile_name"),
                "Собственник": rule.get("owner_name"),
                "Тип аренды": _label(rule.get("stay_type"), STAY_TYPE_LABELS),
                "Процент собственника": rule.get("owner_percent"),
                "Процент компании": rule.get("company_percent"),
                "База": _label(rule.get("split_basis"), SPLIT_BASIS_LABELS),
                "Комментарий": rule.get("notes"),
                "Создано": rule.get("created_at"),
            })

        st.dataframe(split_rows, use_container_width=True)
    else:
        st.info("Пока нет правил распределения.")

    st.markdown("---")
    st.markdown("### Создать правило распределения")

    if not contract_profiles:
        st.warning("Сначала создай хотя бы один контракт.")
    else:
        profile_options = {
            f"{profile['id']} - {profile['owner_name']} - {profile['profile_name']}": profile["id"]
            for profile in contract_profiles
        }

        with st.form("create_split_rule_form"):
            selected_profile = st.selectbox("Контракт", list(profile_options.keys()))

            stay_type = st.selectbox(
                "Тип аренды",
                _build_options(STAY_TYPE_LABELS),
                format_func=lambda x: STAY_TYPE_LABELS[x],
            )

            owner_percent = st.number_input(
                "Процент собственника",
                min_value=0.0,
                max_value=100.0,
                value=60.0,
                step=1.0
            )

            company_percent = st.number_input(
                "Процент компании",
                min_value=0.0,
                max_value=100.0,
                value=40.0,
                step=1.0
            )

            split_basis_for_rule = st.selectbox(
                "База правила",
                _build_options(SPLIT_BASIS_LABELS),
                format_func=lambda x: SPLIT_BASIS_LABELS[x],
            )

            split_notes = st.text_input("Комментарий к правилу")
            submitted_split_rule = st.form_submit_button("Создать правило распределения")

            if submitted_split_rule:
                try:
                    rule_id = contract_service.create_split_rule(
                        contract_profile_id=profile_options[selected_profile],
                        stay_type=stay_type,
                        owner_percent=owner_percent,
                        company_percent=company_percent,
                        split_basis=split_basis_for_rule,
                        notes=split_notes,
                    )
                    st.success(f"Правило распределения создано. ID = {rule_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка создания правила распределения: {e}")

    # ---------------------------------------------------------
    # РЕДАКТИРОВАНИЕ ПРАВИЛА РАСПРЕДЕЛЕНИЯ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Редактировать правило распределения")

    if split_rules and contract_profiles:
        split_rule_options = {
            f"{rule['id']} - {rule.get('profile_name')} - { _label(rule.get('stay_type'), STAY_TYPE_LABELS) }": rule["id"]
            for rule in split_rules
        }

        selected_split_rule_label = st.selectbox(
            "Выбери правило распределения",
            list(split_rule_options.keys()),
            key="edit_split_rule_select"
        )

        selected_split_rule_id = split_rule_options[selected_split_rule_label]
        selected_split_rule = None
        for rule in split_rules:
            if rule["id"] == selected_split_rule_id:
                selected_split_rule = rule
                break

        if selected_split_rule:
            profile_options = {
                f"{profile['id']} - {profile['owner_name']} - {profile['profile_name']}": profile["id"]
                for profile in contract_profiles
            }
            profile_keys = list(profile_options.keys())
            current_profile_key = None
            for key, profile_id in profile_options.items():
                if profile_id == selected_split_rule["contract_profile_id"]:
                    current_profile_key = key
                    break

            stay_type_options = _build_options(STAY_TYPE_LABELS)
            split_basis_options = _build_options(SPLIT_BASIS_LABELS)

            with st.form("edit_split_rule_form"):
                edit_split_profile = st.selectbox(
                    "Контракт",
                    profile_keys,
                    index=_index_of(profile_keys, current_profile_key),
                    key="edit_split_profile"
                )

                edit_split_stay_type = st.selectbox(
                    "Тип аренды",
                    stay_type_options,
                    index=_index_of(stay_type_options, selected_split_rule.get("stay_type"), 0),
                    format_func=lambda x: STAY_TYPE_LABELS[x],
                    key="edit_split_stay_type"
                )

                edit_owner_percent = st.number_input(
                    "Процент собственника",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_split_rule.get("owner_percent") or 0),
                    step=1.0,
                    key="edit_owner_percent"
                )

                edit_company_percent = st.number_input(
                    "Процент компании",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_split_rule.get("company_percent") or 0),
                    step=1.0,
                    key="edit_company_percent"
                )

                edit_split_basis = st.selectbox(
                    "База правила",
                    split_basis_options,
                    index=_index_of(split_basis_options, selected_split_rule.get("split_basis"), 0),
                    format_func=lambda x: SPLIT_BASIS_LABELS[x],
                    key="edit_split_basis_rule"
                )

                edit_split_notes = st.text_input(
                    "Комментарий к правилу",
                    value=selected_split_rule.get("notes") or "",
                    key="edit_split_notes"
                )

                submitted_edit_split = st.form_submit_button("Сохранить правило распределения")

                if submitted_edit_split:
                    try:
                        contract_service.update_split_rule(
                            rule_id=selected_split_rule_id,
                            contract_profile_id=profile_options[edit_split_profile],
                            stay_type=edit_split_stay_type,
                            owner_percent=edit_owner_percent,
                            company_percent=edit_company_percent,
                            split_basis=edit_split_basis,
                            notes=edit_split_notes,
                        )
                        st.success("Правило распределения обновлено.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка обновления правила распределения: {e}")
    else:
        st.info("Нет правил распределения для редактирования.")

    # ---------------------------------------------------------
    # ПРАВИЛА РАСХОДОВ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Правила расходов")

    if expense_rules:
        expense_rows = []
        for rule in expense_rules:
            expense_rows.append({
                "ID": rule["id"],
                "Контракт": rule.get("profile_name"),
                "Собственник": rule.get("owner_name"),
                "Тип расхода": rule.get("expense_type_code"),
                "Режим": _label(rule.get("responsibility_mode"), RESPONSIBILITY_MODE_LABELS),
                "Owner %": rule.get("owner_pct"),
                "Company %": rule.get("company_pct"),
                "Guest %": rule.get("guest_pct"),
                "Комментарий": rule.get("notes"),
                "Создано": rule.get("created_at"),
            })

        st.dataframe(expense_rows, use_container_width=True)
    else:
        st.info("Пока нет правил расходов.")

    st.markdown("---")
    st.markdown("### Создать правило расхода")

    if not contract_profiles:
        st.warning("Сначала создай хотя бы один контракт.")
    else:
        profile_options_for_expense = {
            f"{profile['id']} - {profile['owner_name']} - {profile['profile_name']}": profile["id"]
            for profile in contract_profiles
        }

        with st.form("create_expense_rule_form"):
            selected_profile_for_expense = st.selectbox(
                "Контракт",
                list(profile_options_for_expense.keys()),
                key="expense_profile_select"
            )

            expense_type_code = st.text_input("Тип расхода", value="cleaning")

            responsibility_mode = st.selectbox(
                "Кто несёт расход",
                _build_options(RESPONSIBILITY_MODE_LABELS),
                format_func=lambda x: RESPONSIBILITY_MODE_LABELS[x],
            )

            owner_pct = st.number_input(
                "Owner %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0
            )

            company_pct = st.number_input(
                "Company %",
                min_value=0.0,
                max_value=100.0,
                value=100.0,
                step=1.0
            )

            guest_pct = st.number_input(
                "Guest %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=1.0
            )

            expense_notes = st.text_input("Комментарий к правилу расхода")
            submitted_expense_rule = st.form_submit_button("Создать правило расхода")

            if submitted_expense_rule:
                try:
                    rule_id = contract_service.create_expense_rule(
                        contract_profile_id=profile_options_for_expense[selected_profile_for_expense],
                        expense_type_code=expense_type_code,
                        responsibility_mode=responsibility_mode,
                        owner_pct=owner_pct,
                        company_pct=company_pct,
                        guest_pct=guest_pct,
                        notes=expense_notes,
                    )
                    st.success(f"Правило расхода создано. ID = {rule_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка создания правила расхода: {e}")

    # ---------------------------------------------------------
    # РЕДАКТИРОВАНИЕ ПРАВИЛА РАСХОДА
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### Редактировать правило расхода")

    if expense_rules and contract_profiles:
        expense_rule_options = {
            f"{rule['id']} - {rule.get('profile_name')} - {rule.get('expense_type_code')}": rule["id"]
            for rule in expense_rules
        }

        selected_expense_rule_label = st.selectbox(
            "Выбери правило расхода",
            list(expense_rule_options.keys()),
            key="edit_expense_rule_select"
        )

        selected_expense_rule_id = expense_rule_options[selected_expense_rule_label]
        selected_expense_rule = None
        for rule in expense_rules:
            if rule["id"] == selected_expense_rule_id:
                selected_expense_rule = rule
                break

        if selected_expense_rule:
            profile_options_for_expense = {
                f"{profile['id']} - {profile['owner_name']} - {profile['profile_name']}": profile["id"]
                for profile in contract_profiles
            }
            expense_profile_keys = list(profile_options_for_expense.keys())
            current_expense_profile_key = None
            for key, profile_id in profile_options_for_expense.items():
                if profile_id == selected_expense_rule["contract_profile_id"]:
                    current_expense_profile_key = key
                    break

            responsibility_options = _build_options(RESPONSIBILITY_MODE_LABELS)

            with st.form("edit_expense_rule_form"):
                edit_expense_profile = st.selectbox(
                    "Контракт",
                    expense_profile_keys,
                    index=_index_of(expense_profile_keys, current_expense_profile_key),
                    key="edit_expense_profile"
                )

                edit_expense_type_code = st.text_input(
                    "Тип расхода",
                    value=selected_expense_rule.get("expense_type_code") or "",
                    key="edit_expense_type_code"
                )

                edit_responsibility_mode = st.selectbox(
                    "Кто несёт расход",
                    responsibility_options,
                    index=_index_of(responsibility_options, selected_expense_rule.get("responsibility_mode"), 0),
                    format_func=lambda x: RESPONSIBILITY_MODE_LABELS[x],
                    key="edit_responsibility_mode"
                )

                edit_owner_pct = st.number_input(
                    "Owner %",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_expense_rule.get("owner_pct") or 0),
                    step=1.0,
                    key="edit_owner_pct"
                )

                edit_company_pct = st.number_input(
                    "Company %",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_expense_rule.get("company_pct") or 0),
                    step=1.0,
                    key="edit_company_pct"
                )

                edit_guest_pct = st.number_input(
                    "Guest %",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_expense_rule.get("guest_pct") or 0),
                    step=1.0,
                    key="edit_guest_pct"
                )

                edit_expense_notes = st.text_input(
                    "Комментарий к правилу расхода",
                    value=selected_expense_rule.get("notes") or "",
                    key="edit_expense_notes"
                )

                submitted_edit_expense = st.form_submit_button("Сохранить правило расхода")

                if submitted_edit_expense:
                    try:
                        contract_service.update_expense_rule(
                            rule_id=selected_expense_rule_id,
                            contract_profile_id=profile_options_for_expense[edit_expense_profile],
                            expense_type_code=edit_expense_type_code,
                            responsibility_mode=edit_responsibility_mode,
                            owner_pct=edit_owner_pct,
                            company_pct=edit_company_pct,
                            guest_pct=edit_guest_pct,
                            notes=edit_expense_notes,
                        )
                        st.success("Правило расхода обновлено.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка обновления правила расхода: {e}")
    else:
        st.info("Нет правил расходов для редактирования.")