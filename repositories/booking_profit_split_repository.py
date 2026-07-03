from repositories.base_repository import BaseRepository


class BookingProfitSplitRepository(BaseRepository):
    """Repository for booking profit distribution rows."""

    def list_pending(self):
        return self._list_by_status("pending")

    def list_accepted(self):
        return self._list_by_status("accepted")

    def list_pending_grouped_rows(self):
        return self._list_by_status("pending")

    def list_accepted_grouped_rows(self):
        return self._list_by_status("accepted")

    def list_all_grouped_rows(self):
        return self.list_all()

    def list_all(self):
        self.cursor.execute(
            """
            SELECT
                s.id AS split_id,
                s.booking_id,
                b.guest_name,
                b.apartment_id,
                a.name AS apartment_name,
                b.check_in,
                b.check_out,
                s.finance_snapshot_id,
                s.actor_id,
                s.role_snapshot,
                s.percent_snapshot,
                s.basis_amount_snapshot,
                s.amount_snapshot,
                fs.guest_price_snapshot,
                fs.owner_amount_due,
                fs.distributable_profit_amount,
                fs.snapshot_status,
                s.distribution_status,
                s.accepted_at,
                s.created_at
            FROM booking_profit_splits s
            INNER JOIN bookings b ON b.id = s.booking_id
            LEFT JOIN apartments a ON a.id = b.apartment_id
            LEFT JOIN booking_finance_snapshots fs ON fs.id = s.finance_snapshot_id
            ORDER BY s.created_at DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, split_id: int):
        self.cursor.execute(
            """
            SELECT
                s.id AS split_id,
                s.booking_id,
                b.guest_name,
                b.apartment_id,
                a.name AS apartment_name,
                b.check_in,
                b.check_out,
                s.finance_snapshot_id,
                s.actor_id,
                s.role_snapshot,
                s.percent_snapshot,
                s.basis_amount_snapshot,
                s.amount_snapshot,
                fs.guest_price_snapshot,
                fs.owner_amount_due,
                fs.distributable_profit_amount,
                fs.snapshot_status,
                s.distribution_status,
                s.accepted_at,
                s.created_at
            FROM booking_profit_splits s
            INNER JOIN bookings b ON b.id = s.booking_id
            LEFT JOIN apartments a ON a.id = b.apartment_id
            LEFT JOIN booking_finance_snapshots fs ON fs.id = s.finance_snapshot_id
            WHERE s.id = ?
            """,
            (split_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def mark_accepted(
        self,
        split_id: int,
        accepted_by_actor_id: int,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE booking_profit_splits
            SET
                distribution_status = 'accepted',
                accepted_at = CURRENT_TIMESTAMP,
                accepted_by_actor_id = ?
            WHERE id = ?
            """,
            (accepted_by_actor_id, split_id),
        )
        self.conn.commit()

    def mark_group_accepted(
        self,
        booking_id: int,
        finance_snapshot_id: int,
        accepted_by_actor_id: int,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE booking_profit_splits
            SET
                distribution_status = 'accepted',
                accepted_at = CURRENT_TIMESTAMP,
                accepted_by_actor_id = ?
            WHERE booking_id = ?
              AND finance_snapshot_id = ?
              AND distribution_status = 'pending'
            """,
            (accepted_by_actor_id, booking_id, finance_snapshot_id),
        )
        self.conn.commit()

    def _list_by_status(self, distribution_status: str):
        self.cursor.execute(
            """
            SELECT
                s.id AS split_id,
                s.booking_id,
                b.guest_name,
                b.apartment_id,
                a.name AS apartment_name,
                b.check_in,
                b.check_out,
                s.finance_snapshot_id,
                s.actor_id,
                s.role_snapshot,
                s.percent_snapshot,
                s.basis_amount_snapshot,
                s.amount_snapshot,
                fs.guest_price_snapshot,
                fs.owner_amount_due,
                fs.distributable_profit_amount,
                fs.snapshot_status,
                s.distribution_status,
                s.accepted_at,
                s.created_at
            FROM booking_profit_splits s
            INNER JOIN bookings b ON b.id = s.booking_id
            LEFT JOIN apartments a ON a.id = b.apartment_id
            LEFT JOIN booking_finance_snapshots fs ON fs.id = s.finance_snapshot_id
            WHERE s.distribution_status = ?
              AND (
                  ? <> 'pending'
                  OR (
                      fs.snapshot_status NOT IN ('superseded', 'cancelled')
                      AND fs.id = (
                          SELECT MAX(current_fs.id)
                          FROM booking_finance_snapshots current_fs
                          WHERE current_fs.booking_id = s.booking_id
                            AND current_fs.snapshot_status NOT IN (
                                'superseded',
                                'cancelled'
                            )
                      )
                  )
              )
            ORDER BY s.created_at DESC
            """,
            (distribution_status, distribution_status),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
