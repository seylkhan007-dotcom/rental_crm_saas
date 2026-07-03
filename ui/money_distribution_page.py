import streamlit as st

from services.actor_service import ActorService
from services.booking_profit_split_service import BookingProfitSplitService


def _safe_round(value) -> float:
    return round(float(value or 0), 2)


def render_money_distribution_page(conn):
    split_service = BookingProfitSplitService(conn)
    actor_service = ActorService(conn)

    st.subheader("Распределение денег")

    try:
        pending_groups = split_service.list_pending_grouped()
        accepted_groups = split_service.list_accepted_grouped()
        all_groups = split_service.list_all_grouped()
        actors = actor_service.get_active_actors()
    except Exception as e:
        st.error(f"Ошибка загрузки распределений денег: {e}")
        return

    actor_options = {
        f"{actor['id']} - {actor.get('display_name') or actor.get('full_name')}": actor["id"]
        for actor in actors
    }

    tab1, tab2, tab3 = st.tabs(
        [
            "Нужно подтвердить",
            "Подтверждено",
            "История",
        ]
    )

    with tab1:
        if not actor_options:
            st.warning("Нет активных сотрудников / участников для подтверждения.")

        if not pending_groups:
            st.info("Нет распределений, ожидающих подтверждения.")
        else:
            for group in pending_groups:
                with st.container(border=True):
                    st.markdown(f"#### {group.get('guest_name') or '-'}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Гость", group.get("guest_name") or "-")
                    c2.metric("Квартира", group.get("apartment_name") or "-")
                    c3.metric(
                        "Даты",
                        f"{group.get('check_in') or '-'} → {group.get('check_out') or '-'}",
                    )

                    c4, c5, c6, c7, c8 = st.columns(5)
                    c4.metric(
                        "Сумма гостя",
                        _safe_round(group.get("guest_price_snapshot")),
                    )
                    c5.metric(
                        "Собственнику",
                        _safe_round(group.get("owner_amount_due")),
                    )
                    c6.metric(
                        "Прибыль компании",
                        _safe_round(group.get("distributable_profit_amount")),
                    )
                    c7.metric(
                        "Итого распределено",
                        _safe_round(group.get("distributed_total")),
                    )
                    c8.metric(
                        "Остаток",
                        _safe_round(group.get("remaining_amount")),
                    )

                    split_rows = [
                        {
                            "Участник": split.get("role_snapshot") or "-",
                            "Процент": _safe_round(split.get("percent_snapshot")),
                            "Сумма": _safe_round(split.get("amount_snapshot")),
                        }
                        for split in group.get("splits", [])
                    ]
                    st.dataframe(split_rows, use_container_width=True)

                    if actor_options:
                        selected_actor_label = st.selectbox(
                            "Кто подтверждает распределение",
                            list(actor_options.keys()),
                            key=(
                                "accept_actor_"
                                f"{group['booking_id']}_{group['finance_snapshot_id']}"
                            ),
                        )
                        accepted_by_actor_id = actor_options[selected_actor_label]

                        if st.button(
                            "Подтвердить распределение",
                            key=(
                                "accept_group_"
                                f"{group['booking_id']}_{group['finance_snapshot_id']}"
                            ),
                        ):
                            try:
                                split_service.mark_group_accepted(
                                    booking_id=group["booking_id"],
                                    finance_snapshot_id=group["finance_snapshot_id"],
                                    accepted_by_actor_id=accepted_by_actor_id,
                                )
                                st.success("Распределение подтверждено.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ошибка подтверждения распределения: {e}")

    with tab2:
        if accepted_groups:
            accepted_rows = [
                {
                    "booking_id": group.get("booking_id"),
                    "guest_name": group.get("guest_name"),
                    "apartment_name": group.get("apartment_name"),
                    "owner_amount_due": _safe_round(group.get("owner_amount_due")),
                    "distributable_profit_amount": _safe_round(
                        group.get("distributable_profit_amount")
                    ),
                    "distributed_total": _safe_round(group.get("distributed_total")),
                }
                for group in accepted_groups
            ]
            st.dataframe(accepted_rows, use_container_width=True)
        else:
            st.info("Нет подтвержденных распределений.")

    with tab3:
        if all_groups:
            st.dataframe(all_groups, use_container_width=True)
        else:
            st.info("История распределений пока пуста.")
