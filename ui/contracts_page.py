import streamlit as st

from services.apartment_service import ApartmentService
from services.contract_service import ContractService
from services.owner_service import OwnerService


PRICING_MODEL_LABELS = {
    "management": "Управление",
    "sublease": "Субаренда",
}

SETTLEMENT_BASE_MODE_LABELS = {
    "from_guest_price": "Из цены гостя",
    "manual_base": "Ручная база",
}

PROFIT_MODE_LABELS = {
    "gross_split": "Валовый сплит",
    "net_split": "Сплит чистой прибыли",
}

OTA_COST_MODE_LABELS = {
    "company_only": "Компания платит OTA",
    "shared": "OTA делится",
    "owner_only": "Собственник платит OTA",
}

EXPENSE_MODE_LABELS = {
    "rule_based": "По правилам",
    "company_all": "Все на компанию",
    "owner_all": "Все на собственника",
    "profit_share_based": "Пропорционально долям прибыли",
}

STAY_TYPE_LABELS = {
    "all": "Для всех типов аренды",
    "short_term": "Краткосрок",
    "long_term": "Долгосрок",
}

RESPONSIBILITY_MODE_LABELS = {
    "company": "Компания платит",
    "owner": "Собственник платит",
    "guest": "Гость платит",
    "split": "Делится по процентам",
}

EXPENSE_TYPE_CODES = {
    "service_fee": "Сервисные платежи",
    "utilities": "Коммуналка",
    "cleaning": "Уборка",
    "laundry": "Стирка / химчистка",
    "breakfast": "Завтраки",
    "consumables": "Расходники",
    "minor_repair": "Мелкий ремонт",
    "major_repair": "Крупный ремонт",
    "guest_damage": "Ущерб гостя",
    "ota_commission": "Комиссия OTA",
}

FIXED_RENT_TYPE_LABELS = {
    "daily": "За день",
    "monthly": "За месяц",
}

SPLIT_BASIS_LABELS = {
    "owner_price": "От owner price",
    "net_profit": "От чистой прибыли",
    "custom": "Особая логика",
}

CONTRACT_PAGE_FLASH_MESSAGE_KEY = "contracts_page_flash_message"


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


def _find_item_by_id(items: list[dict], item_id: int):
    for item in items:
        if item["id"] == item_id:
            return item
    return None


def _build_apartment_options(apartments: list[dict]) -> dict[str, int]:
    return {
        f"{apartment['id']} - {apartment['name']}": apartment["id"]
        for apartment in apartments
    }


def _get_selected_apartment_labels(
    apartment_options: dict[str, int],
    selected_ids: list[int],
) -> list[str]:
    return [
        label
        for label, apartment_id in apartment_options.items()
        if apartment_id in selected_ids
    ]


def _show_flash_message():
    message = st.session_state.pop(CONTRACT_PAGE_FLASH_MESSAGE_KEY, None)
    if message:
        st.success(message)


def render_contracts_page(conn):
    contract_service = ContractService(conn)
    owner_service = OwnerService(conn)
    apartment_service = ApartmentService(conn)

    st.subheader("Контракты")
    st.caption(
        "Здесь настраиваются профили контрактов, правила распределения и правила расходов."
    )
    _show_flash_message()

    try:
        owners = owner_service.get_all_owners()
        apartments = apartment_service.get_all_apartments()
        contract_profiles = contract_service.get_all_profiles()
        split_rules = contract_service.get_all_split_rules()
        expense_rules = contract_service.get_all_expense_rules()
    except Exception as e:
        st.error(f"Ошибка загрузки данных по контрактам: {e}")
        return

    owner_options = {
        f"{owner['id']} - {owner['name']}": owner["id"]
        for owner in owners
    }
    apartment_options = _build_apartment_options(apartments)

    st.markdown("### Профили контрактов")

    if contract_profiles:
        profile_rows = []
        for profile in contract_profiles:
            apartment_names = ", ".join(
                apartment.get("name", "")
                for apartment in profile.get("apartments", [])
                if apartment.get("name")
            )

            profile_rows.append(
                {
                    "ID": profile["id"],
                    "Собственник": profile.get("owner_name"),
                    "Название": profile.get("profile_name"),
                    "Модель": _label(
                        profile.get("pricing_model"),
                        PRICING_MODEL_LABELS,
                    ),
                    "База расчета": _label(
                        profile.get("settlement_base_mode"),
                        SETTLEMENT_BASE_MODE_LABELS,
                    ),
                    "Режим прибыли": _label(
                        profile.get("profit_mode"),
                        PROFIT_MODE_LABELS,
                    ),
                    "Owner %": profile.get("owner_percent"),
                    "Company %": profile.get("company_percent"),
                    "Кто несет OTA": _label(
                        profile.get("ota_cost_mode"),
                        OTA_COST_MODE_LABELS,
                    ),
                    "Режим расходов": _label(
                        profile.get("expense_mode"),
                        EXPENSE_MODE_LABELS,
                    ),
                    "Тип фикс. аренды": _label(
                        profile.get("fixed_rent_type"),
                        FIXED_RENT_TYPE_LABELS,
                    ),
                    "Фикс. аренда": profile.get("fixed_rent_value") or 0,
                    "Валюта": profile.get("fixed_rent_currency") or "-",
                    "Квартиры": apartment_names or "-",
                    "Активен": "Да" if profile.get("is_active") == 1 else "Нет",
                    "Комментарий": profile.get("notes"),
                    "Создано": profile.get("created_at"),
                }
            )

        st.dataframe(profile_rows, use_container_width=True)
    else:
        st.info("Пока нет контрактов.")

    st.markdown("---")
    st.markdown("### Создать профиль контракта")

    if not owners:
        st.warning("Сначала создай хотя бы одного собственника.")
    else:
        with st.form("create_contract_profile_form", clear_on_submit=True):
            selected_owner = st.selectbox("Собственник", list(owner_options.keys()))
            profile_name = st.text_input(
                "Название контракта",
                value="Основной контракт",
            )

            pricing_model = st.selectbox(
                "Модель",
                _build_options(PRICING_MODEL_LABELS),
                format_func=lambda x: PRICING_MODEL_LABELS[x],
            )

            apartment_labels = st.multiselect(
                "Квартиры контракта",
                list(apartment_options.keys()),
                help="Для работы бронирований привяжи договор к нужным квартирам.",
            )

            settlement_base_mode = st.selectbox(
                "База расчета с собственником",
                _build_options(SETTLEMENT_BASE_MODE_LABELS),
                format_func=lambda x: SETTLEMENT_BASE_MODE_LABELS[x],
            )

            profit_mode = st.selectbox(
                "Режим расчета прибыли",
                _build_options(PROFIT_MODE_LABELS),
                format_func=lambda x: PROFIT_MODE_LABELS[x],
            )

            c1, c2 = st.columns(2)
            with c1:
                owner_percent = st.number_input(
                    "Owner %",
                    min_value=0.0,
                    max_value=100.0,
                    value=60.0,
                    step=1.0,
                )
            with c2:
                company_percent = st.number_input(
                    "Company %",
                    min_value=0.0,
                    max_value=100.0,
                    value=40.0,
                    step=1.0,
                )

            ota_cost_mode = st.selectbox(
                "Кто несет OTA",
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

            fixed_rent_type_options = [""] + _build_options(FIXED_RENT_TYPE_LABELS)
            fixed_rent_type = st.selectbox(
                "Тип фиксированной аренды",
                fixed_rent_type_options,
                format_func=lambda x: "— не выбрано —"
                if x == ""
                else FIXED_RENT_TYPE_LABELS[x],
            )

            fixed_rent_value = st.number_input(
                "Фиксированная стоимость аренды",
                min_value=0.0,
                value=0.0,
                step=10.0,
            )

            fixed_rent_currency = st.selectbox(
                "Валюта фиксированной аренды",
                ["GEL", "USD", "EUR"],
            )

            notes = st.text_area("Комментарий")
            submitted_profile = st.form_submit_button("Создать контракт")

            if submitted_profile:
                try:
                    profile_id = contract_service.create_profile(
                        owner_id=owner_options[selected_owner],
                        profile_name=profile_name,
                        pricing_model=pricing_model,
                        settlement_base_mode=settlement_base_mode,
                        profit_mode=profit_mode,
                        owner_percent=owner_percent,
                        company_percent=company_percent,
                        fixed_rent_type=fixed_rent_type or None,
                        fixed_rent_value=fixed_rent_value,
                        fixed_rent_currency=fixed_rent_currency,
                        ota_cost_mode=ota_cost_mode,
                        expense_mode=expense_mode,
                        apartment_ids=[
                            apartment_options[label] for label in apartment_labels
                        ],
                        notes=notes,
                        is_active=1,
                    )
                    st.session_state[CONTRACT_PAGE_FLASH_MESSAGE_KEY] = (
                        f"Контракт создан. ID = {profile_id}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка создания контракта: {e}")

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
            key="edit_contract_profile_select",
        )

        selected_profile_id = edit_profile_options[selected_profile_label]
        selected_profile = _find_item_by_id(contract_profiles, selected_profile_id)

        if selected_profile:
            owner_keys = list(owner_options.keys())
            current_owner_key = None
            for key, owner_id in owner_options.items():
                if owner_id == selected_profile["owner_id"]:
                    current_owner_key = key
                    break

            pricing_model_options = _build_options(PRICING_MODEL_LABELS)
            settlement_base_mode_options = _build_options(SETTLEMENT_BASE_MODE_LABELS)
            profit_mode_options = _build_options(PROFIT_MODE_LABELS)
            ota_cost_mode_options = _build_options(OTA_COST_MODE_LABELS)
            expense_mode_options = _build_options(EXPENSE_MODE_LABELS)
            fixed_rent_type_options = [""] + _build_options(FIXED_RENT_TYPE_LABELS)
            fixed_rent_currency_options = ["GEL", "USD", "EUR"]

            selected_apartment_ids = [
                apartment["id"] for apartment in selected_profile.get("apartments", [])
            ]
            default_apartment_labels = _get_selected_apartment_labels(
                apartment_options,
                selected_apartment_ids,
            )

            with st.form("edit_contract_profile_form"):
                edit_owner = st.selectbox(
                    "Собственник",
                    owner_keys,
                    index=_index_of(owner_keys, current_owner_key),
                    key="edit_owner",
                )

                edit_profile_name = st.text_input(
                    "Название контракта",
                    value=selected_profile.get("profile_name") or "",
                    key="edit_profile_name",
                )

                edit_pricing_model = st.selectbox(
                    "Модель",
                    pricing_model_options,
                    index=_index_of(
                        pricing_model_options,
                        selected_profile.get("pricing_model"),
                        0,
                    ),
                    format_func=lambda x: PRICING_MODEL_LABELS[x],
                    key="edit_pricing_model",
                )

                edit_apartment_labels = st.multiselect(
                    "Квартиры контракта",
                    list(apartment_options.keys()),
                    default=default_apartment_labels,
                    key="edit_contract_apartments",
                )

                edit_settlement_base_mode = st.selectbox(
                    "База расчета с собственником",
                    settlement_base_mode_options,
                    index=_index_of(
                        settlement_base_mode_options,
                        selected_profile.get("settlement_base_mode"),
                        0,
                    ),
                    format_func=lambda x: SETTLEMENT_BASE_MODE_LABELS[x],
                    key="edit_settlement_base_mode",
                )

                edit_profit_mode = st.selectbox(
                    "Режим расчета прибыли",
                    profit_mode_options,
                    index=_index_of(
                        profit_mode_options,
                        selected_profile.get("profit_mode"),
                        0,
                    ),
                    format_func=lambda x: PROFIT_MODE_LABELS[x],
                    key="edit_profit_mode",
                )

                c1, c2 = st.columns(2)
                with c1:
                    edit_owner_percent = st.number_input(
                        "Owner %",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(selected_profile.get("owner_percent") or 0),
                        step=1.0,
                        key="edit_owner_percent_profile",
                    )
                with c2:
                    edit_company_percent = st.number_input(
                        "Company %",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(selected_profile.get("company_percent") or 0),
                        step=1.0,
                        key="edit_company_percent_profile",
                    )

                edit_ota_cost_mode = st.selectbox(
                    "Кто несет OTA",
                    ota_cost_mode_options,
                    index=_index_of(
                        ota_cost_mode_options,
                        selected_profile.get("ota_cost_mode"),
                        0,
                    ),
                    format_func=lambda x: OTA_COST_MODE_LABELS[x],
                    key="edit_ota_cost_mode",
                )

                edit_expense_mode = st.selectbox(
                    "Режим расходов",
                    expense_mode_options,
                    index=_index_of(
                        expense_mode_options,
                        selected_profile.get("expense_mode"),
                        0,
                    ),
                    format_func=lambda x: EXPENSE_MODE_LABELS[x],
                    key="edit_expense_mode",
                )

                st.markdown("#### Условия субаренды")
                edit_fixed_rent_type = st.selectbox(
                    "Тип фиксированной аренды",
                    fixed_rent_type_options,
                    index=_index_of(
                        fixed_rent_type_options,
                        selected_profile.get("fixed_rent_type") or "",
                        0,
                    ),
                    format_func=lambda x: "— не выбрано —"
                    if x == ""
                    else FIXED_RENT_TYPE_LABELS[x],
                    key="edit_fixed_rent_type",
                )

                edit_fixed_rent_value = st.number_input(
                    "Фиксированная стоимость аренды",
                    min_value=0.0,
                    value=float(selected_profile.get("fixed_rent_value") or 0.0),
                    step=10.0,
                    key="edit_fixed_rent_value",
                )

                edit_fixed_rent_currency = st.selectbox(
                    "Валюта фиксированной аренды",
                    fixed_rent_currency_options,
                    index=_index_of(
                        fixed_rent_currency_options,
                        selected_profile.get("fixed_rent_currency") or "GEL",
                        0,
                    ),
                    key="edit_fixed_rent_currency",
                )

                edit_notes = st.text_area(
                    "Комментарий",
                    value=selected_profile.get("notes") or "",
                    key="edit_notes",
                )

                edit_is_active = st.checkbox(
                    "Контракт активен",
                    value=selected_profile.get("is_active") == 1,
                    key="edit_is_active",
                )

                submitted_update = st.form_submit_button("Сохранить изменения")

                if submitted_update:
                    try:
                        contract_service.update_profile(
                            contract_profile_id=selected_profile_id,
                            owner_id=owner_options[edit_owner],
                            profile_name=edit_profile_name,
                            pricing_model=edit_pricing_model,
                            settlement_base_mode=edit_settlement_base_mode,
                            profit_mode=edit_profit_mode,
                            owner_percent=edit_owner_percent,
                            company_percent=edit_company_percent,
                            fixed_rent_type=edit_fixed_rent_type or None,
                            fixed_rent_value=edit_fixed_rent_value,
                            fixed_rent_currency=edit_fixed_rent_currency,
                            ota_cost_mode=edit_ota_cost_mode,
                            expense_mode=edit_expense_mode,
                            apartment_ids=[
                                apartment_options[label]
                                for label in edit_apartment_labels
                            ],
                            notes=edit_notes,
                            is_active=1 if edit_is_active else 0,
                        )
                        st.session_state[CONTRACT_PAGE_FLASH_MESSAGE_KEY] = (
                            f"Контракт обновлен. ID = {selected_profile_id}"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка обновления контракта: {e}")
    else:
        st.info("Нет контрактов для редактирования.")

    st.markdown("---")
    st.markdown("### Правила распределения")

    if split_rules:
        split_rows = []
        for rule in split_rules:
            split_rows.append(
                {
                    "ID": rule["id"],
                    "Контракт": rule.get("profile_name"),
                    "Собственник": rule.get("owner_name"),
                    "Тип аренды": _label(rule.get("stay_type"), STAY_TYPE_LABELS),
                    "Процент собственника": rule.get("owner_percent"),
                    "Процент компании": rule.get("company_percent"),
                    "База": _label(rule.get("split_basis"), SPLIT_BASIS_LABELS),
                    "Комментарий": rule.get("notes"),
                    "Создано": rule.get("created_at"),
                }
            )

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
                step=1.0,
            )

            company_percent = st.number_input(
                "Процент компании",
                min_value=0.0,
                max_value=100.0,
                value=40.0,
                step=1.0,
            )

            split_basis_for_rule = st.selectbox(
                "База правила",
                _build_options(SPLIT_BASIS_LABELS),
                format_func=lambda x: SPLIT_BASIS_LABELS[x],
            )

            split_notes = st.text_input("Комментарий к правилу")
            submitted_split_rule = st.form_submit_button(
                "Создать правило распределения"
            )

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

    st.markdown("---")
    st.markdown("### Редактировать правило распределения")

    if split_rules and contract_profiles:
        split_rule_options = {
            f"{rule['id']} - {rule.get('profile_name')} - {_label(rule.get('stay_type'), STAY_TYPE_LABELS)}": rule["id"]
            for rule in split_rules
        }

        selected_split_rule_label = st.selectbox(
            "Выбери правило распределения",
            list(split_rule_options.keys()),
            key="edit_split_rule_select",
        )

        selected_split_rule_id = split_rule_options[selected_split_rule_label]
        selected_split_rule = _find_item_by_id(split_rules, selected_split_rule_id)

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
                    key="edit_split_profile",
                )

                edit_split_stay_type = st.selectbox(
                    "Тип аренды",
                    stay_type_options,
                    index=_index_of(
                        stay_type_options,
                        selected_split_rule.get("stay_type"),
                        0,
                    ),
                    format_func=lambda x: STAY_TYPE_LABELS[x],
                    key="edit_split_stay_type",
                )

                edit_owner_percent = st.number_input(
                    "Процент собственника",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_split_rule.get("owner_percent") or 0),
                    step=1.0,
                    key="edit_owner_percent",
                )

                edit_company_percent = st.number_input(
                    "Процент компании",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_split_rule.get("company_percent") or 0),
                    step=1.0,
                    key="edit_company_percent",
                )

                edit_split_basis = st.selectbox(
                    "База правила",
                    split_basis_options,
                    index=_index_of(
                        split_basis_options,
                        selected_split_rule.get("split_basis"),
                        0,
                    ),
                    format_func=lambda x: SPLIT_BASIS_LABELS[x],
                    key="edit_split_basis_rule",
                )

                edit_split_notes = st.text_input(
                    "Комментарий к правилу",
                    value=selected_split_rule.get("notes") or "",
                    key="edit_split_notes",
                )

                submitted_edit_split = st.form_submit_button(
                    "Сохранить правило распределения"
                )

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

    st.markdown("---")
    st.markdown("### Правила расходов")

    if expense_rules:
        expense_rows = []
        for rule in expense_rules:
            expense_rows.append(
                {
                    "ID": rule["id"],
                    "Контракт": rule.get("profile_name"),
                    "Собственник": rule.get("owner_name"),
                    "Тип расхода": rule.get("expense_type_code"),
                    "Режим": _label(
                        rule.get("responsibility_mode"),
                        RESPONSIBILITY_MODE_LABELS,
                    ),
                    "Owner %": rule.get("owner_pct"),
                    "Company %": rule.get("company_pct"),
                    "Guest %": rule.get("guest_pct"),
                    "Комментарий": rule.get("notes"),
                    "Создано": rule.get("created_at"),
                }
            )

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
                key="expense_profile_select",
            )

            expense_type_options = list(EXPENSE_TYPE_CODES.keys())
            expense_type_code = st.selectbox(
                "Тип расхода",
                expense_type_options,
                format_func=lambda x: EXPENSE_TYPE_CODES[x],
                key="create_expense_type_select",
            )

            responsibility_mode = st.selectbox(
                "Кто несет расход",
                _build_options(RESPONSIBILITY_MODE_LABELS),
                format_func=lambda x: RESPONSIBILITY_MODE_LABELS[x],
            )

            # Conditional display of percentage fields based on responsibility_mode
            if responsibility_mode == "split":
                st.markdown("#### Разделение по процентам")
                st.caption("Сумма всех процентов должна быть ровно 100%")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    owner_pct = st.number_input(
                        "Собственник %",
                        min_value=0.0,
                        max_value=100.0,
                        value=33.0,
                        step=1.0,
                        key="create_owner_pct_split",
                    )
                with col2:
                    company_pct = st.number_input(
                        "Компания %",
                        min_value=0.0,
                        max_value=100.0,
                        value=34.0,
                        step=1.0,
                        key="create_company_pct_split",
                    )
                with col3:
                    guest_pct = st.number_input(
                        "Гость %",
                        min_value=0.0,
                        max_value=100.0,
                        value=33.0,
                        step=1.0,
                        key="create_guest_pct_split",
                    )
                
                total_pct = round(owner_pct + company_pct + guest_pct, 2)
                if total_pct != 100.0:
                    st.warning(f"⚠️ Сумма процентов = {total_pct}% (должна быть 100%)")
            else:
                # Auto-populate percentages for non-split modes
                if responsibility_mode == "company":
                    owner_pct = 0.0
                    company_pct = 100.0
                    guest_pct = 0.0
                elif responsibility_mode == "owner":
                    owner_pct = 100.0
                    company_pct = 0.0
                    guest_pct = 0.0
                else:  # guest
                    owner_pct = 0.0
                    company_pct = 0.0
                    guest_pct = 100.0

            expense_notes = st.text_input("Комментарий к правилу расхода")
            submitted_expense_rule = st.form_submit_button("Создать правило расхода")

            if submitted_expense_rule:
                try:
                    rule_id = contract_service.create_expense_rule(
                        contract_profile_id=profile_options_for_expense[
                            selected_profile_for_expense
                        ],
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

    st.markdown("---")
    st.markdown("### Редактировать правило расхода")

    if expense_rules and contract_profiles:
        expense_rule_options = {
            f"{rule['id']} - {rule.get('profile_name')} - {EXPENSE_TYPE_CODES.get(rule.get('expense_type_code'), rule.get('expense_type_code'))}": rule["id"]
            for rule in expense_rules
        }

        selected_expense_rule_label = st.selectbox(
            "Выбери правило расхода",
            list(expense_rule_options.keys()),
            key="edit_expense_rule_select",
        )

        selected_expense_rule_id = expense_rule_options[selected_expense_rule_label]
        selected_expense_rule = _find_item_by_id(
            expense_rules,
            selected_expense_rule_id,
        )

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
            expense_type_options = list(EXPENSE_TYPE_CODES.keys())

            with st.form("edit_expense_rule_form"):
                edit_expense_profile = st.selectbox(
                    "Контракт",
                    expense_profile_keys,
                    index=_index_of(
                        expense_profile_keys,
                        current_expense_profile_key,
                    ),
                    key="edit_expense_profile",
                )

                edit_expense_type_code = st.selectbox(
                    "Тип расхода",
                    expense_type_options,
                    index=_index_of(
                        expense_type_options,
                        selected_expense_rule.get("expense_type_code"),
                        0,
                    ),
                    format_func=lambda x: EXPENSE_TYPE_CODES[x],
                    key="edit_expense_type_select",
                )

                edit_responsibility_mode = st.selectbox(
                    "Кто несет расход",
                    responsibility_options,
                    index=_index_of(
                        responsibility_options,
                        selected_expense_rule.get("responsibility_mode"),
                        0,
                    ),
                    format_func=lambda x: RESPONSIBILITY_MODE_LABELS[x],
                    key="edit_responsibility_mode",
                )

                # Conditional display of percentage fields based on responsibility_mode
                if edit_responsibility_mode == "split":
                    st.markdown("#### Разделение по процентам")
                    st.caption("Сумма всех процентов должна быть ровно 100%")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        edit_owner_pct = st.number_input(
                            "Собственник %",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(selected_expense_rule.get("owner_pct") or 0),
                            step=1.0,
                            key="edit_owner_pct_split",
                        )
                    with col2:
                        edit_company_pct = st.number_input(
                            "Компания %",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(selected_expense_rule.get("company_pct") or 0),
                            step=1.0,
                            key="edit_company_pct_split",
                        )
                    with col3:
                        edit_guest_pct = st.number_input(
                            "Гость %",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(selected_expense_rule.get("guest_pct") or 0),
                            step=1.0,
                            key="edit_guest_pct_split",
                        )
                    
                    total_pct = round(edit_owner_pct + edit_company_pct + edit_guest_pct, 2)
                    if total_pct != 100.0:
                        st.warning(f"⚠️ Сумма процентов = {total_pct}% (должна быть 100%)")
                else:
                    # Auto-populate percentages for non-split modes
                    if edit_responsibility_mode == "company":
                        edit_owner_pct = 0.0
                        edit_company_pct = 100.0
                        edit_guest_pct = 0.0
                    elif edit_responsibility_mode == "owner":
                        edit_owner_pct = 100.0
                        edit_company_pct = 0.0
                        edit_guest_pct = 0.0
                    else:  # guest
                        edit_owner_pct = 0.0
                        edit_company_pct = 0.0
                        edit_guest_pct = 100.0

                edit_expense_notes = st.text_input(
                    "Комментарий к правилу расхода",
                    value=selected_expense_rule.get("notes") or "",
                    key="edit_expense_notes",
                )

                submitted_edit_expense = st.form_submit_button(
                    "Сохранить правило расхода"
                )

                if submitted_edit_expense:
                    try:
                        contract_service.update_expense_rule(
                            rule_id=selected_expense_rule_id,
                            contract_profile_id=profile_options_for_expense[
                                edit_expense_profile
                            ],
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
