from repositories.booking_profit_split_repository import BookingProfitSplitRepository


class BookingProfitSplitService:
    def __init__(self, conn):
        self.booking_profit_split_repo = BookingProfitSplitRepository(conn)

    def list_pending(self):
        return self.booking_profit_split_repo.list_pending()

    def list_accepted(self):
        return self.booking_profit_split_repo.list_accepted()

    def list_all(self):
        return self.booking_profit_split_repo.list_all()

    def list_pending_grouped(self):
        rows = self.booking_profit_split_repo.list_pending_grouped_rows()
        return self._group_rows_by_booking_snapshot(rows)

    def list_accepted_grouped(self):
        rows = self.booking_profit_split_repo.list_accepted_grouped_rows()
        return self._group_rows_by_booking_snapshot(rows)

    def list_all_grouped(self):
        rows = self.booking_profit_split_repo.list_all_grouped_rows()
        return self._group_rows_by_booking_snapshot(rows)

    def mark_accepted(
        self,
        split_id: int,
        accepted_by_actor_id: int,
    ):
        if not split_id:
            raise ValueError("split_id обязателен.")

        if not accepted_by_actor_id:
            raise ValueError("accepted_by_actor_id обязателен.")

        split = self.booking_profit_split_repo.get_by_id(split_id)
        if not split:
            raise ValueError("Распределение не найдено.")

        distribution_status = split.get("distribution_status")
        if distribution_status == "accepted":
            return split

        if distribution_status != "pending":
            raise ValueError("Некорректный статус распределения.")

        self.booking_profit_split_repo.mark_accepted(
            split_id=split_id,
            accepted_by_actor_id=accepted_by_actor_id,
        )
        return self.booking_profit_split_repo.get_by_id(split_id)

    def mark_group_accepted(
        self,
        booking_id: int,
        finance_snapshot_id: int,
        accepted_by_actor_id: int,
    ):
        if not booking_id:
            raise ValueError("booking_id обязателен.")

        if not finance_snapshot_id:
            raise ValueError("finance_snapshot_id обязателен.")

        if not accepted_by_actor_id:
            raise ValueError("accepted_by_actor_id обязателен.")

        pending_groups = self.list_pending_grouped()
        pending_group = self._find_group(
            pending_groups,
            booking_id,
            finance_snapshot_id,
        )

        if pending_group:
            self.booking_profit_split_repo.mark_group_accepted(
                booking_id=booking_id,
                finance_snapshot_id=finance_snapshot_id,
                accepted_by_actor_id=accepted_by_actor_id,
            )
            accepted_groups = self.list_accepted_grouped()
            return self._find_group(
                accepted_groups,
                booking_id,
                finance_snapshot_id,
            )

        accepted_groups = self.list_accepted_grouped()
        accepted_group = self._find_group(
            accepted_groups,
            booking_id,
            finance_snapshot_id,
        )

        if accepted_group:
            return accepted_group

        raise ValueError("Распределение по брони не найдено.")

    def _group_rows_by_booking_snapshot(self, rows):
        groups_by_key = {}

        for row in rows:
            booking_id = row.get("booking_id")
            finance_snapshot_id = row.get("finance_snapshot_id")
            group_key = (booking_id, finance_snapshot_id)

            if group_key not in groups_by_key:
                groups_by_key[group_key] = {
                    "booking_id": booking_id,
                    "finance_snapshot_id": finance_snapshot_id,
                    "guest_name": row.get("guest_name"),
                    "apartment_id": row.get("apartment_id"),
                    "apartment_name": row.get("apartment_name"),
                    "check_in": row.get("check_in"),
                    "check_out": row.get("check_out"),
                    "guest_price_snapshot": row.get("guest_price_snapshot"),
                    "owner_amount_due": row.get("owner_amount_due"),
                    "distributable_profit_amount": row.get(
                        "distributable_profit_amount"
                    ),
                    "distributed_total": 0,
                    "remaining_amount": 0,
                    "distribution_status": "accepted",
                    "splits": [],
                }

            group = groups_by_key[group_key]
            split_amount = float(row.get("amount_snapshot") or 0)
            group["distributed_total"] += split_amount

            if row.get("distribution_status") == "pending":
                group["distribution_status"] = "pending"

            group["splits"].append(
                {
                    "split_id": row.get("split_id"),
                    "actor_id": row.get("actor_id"),
                    "role_snapshot": row.get("role_snapshot"),
                    "percent_snapshot": row.get("percent_snapshot"),
                    "basis_amount_snapshot": row.get("basis_amount_snapshot"),
                    "amount_snapshot": row.get("amount_snapshot"),
                    "distribution_status": row.get("distribution_status"),
                    "accepted_at": row.get("accepted_at"),
                    "created_at": row.get("created_at"),
                }
            )

        for group in groups_by_key.values():
            distributable_profit = float(
                group.get("distributable_profit_amount") or 0
            )
            group["remaining_amount"] = (
                distributable_profit - group["distributed_total"]
            )

        return list(groups_by_key.values())

    def _find_group(
        self,
        groups,
        booking_id: int,
        finance_snapshot_id: int,
    ):
        for group in groups:
            if (
                group.get("booking_id") == booking_id
                and group.get("finance_snapshot_id") == finance_snapshot_id
            ):
                return group

        return None
