from repositories.base_repository import BaseRepository


class BookingRepository(BaseRepository):
    """Репозиторий бронирований."""

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        apartment_id: int,
        guest_name: str,
        check_in: str,
        check_out: str,
        total_amount: float,
        guest_price: float | None = None,
        settlement_base_amount: float | None = None,
        tax_base_price: float | None = None,
        source_channel: str | None = None,
        ota_account_name: str | None = None,
        ota_commission_pct: float | None = None,
        ota_vat_pct: float | None = None,
        pricing_model: str = "management",
        fixed_rent_type: str | None = None,
        fixed_rent_value: float | None = None,
        contract_profile_id: int | None = None,
        stay_type: str = "short_term",
        settlement_base_mode_snapshot: str | None = None,
        profit_mode_snapshot: str | None = None,
        owner_percent_snapshot: float | None = None,
        company_percent_snapshot: float | None = None,
        fixed_rent_type_snapshot: str | None = None,
        fixed_rent_value_snapshot: float | None = None,
        fixed_rent_currency_snapshot: str | None = None,
        ota_cost_mode_snapshot: str | None = None,
        expense_mode_snapshot: str | None = None,
        checkin_actor_id: int | None = None,
        manager_commission_actor_id: int | None = None,
        manager_commission_pct_snapshot: float | None = None,
        finance_status: str = "draft",
        finance_locked_at: str | None = None,
        finance_locked_by: int | None = None,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO bookings (
                apartment_id,
                guest_name,
                check_in,
                check_out,
                total_amount,

                guest_price,
                settlement_base_amount,
                tax_base_price,

                source_channel,
                ota_account_name,
                ota_commission_pct,
                ota_vat_pct,

                pricing_model,
                fixed_rent_type,
                fixed_rent_value,

                contract_profile_id,
                stay_type,

                settlement_base_mode_snapshot,
                profit_mode_snapshot,
                owner_percent_snapshot,
                company_percent_snapshot,
                fixed_rent_type_snapshot,
                fixed_rent_value_snapshot,
                fixed_rent_currency_snapshot,
                ota_cost_mode_snapshot,
                expense_mode_snapshot,

                checkin_actor_id,
                manager_commission_actor_id,
                manager_commission_pct_snapshot,

                finance_status,
                finance_locked_at,
                finance_locked_by,

                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                apartment_id,
                guest_name,
                check_in,
                check_out,
                total_amount,

                guest_price,
                settlement_base_amount,
                tax_base_price,

                source_channel,
                ota_account_name,
                ota_commission_pct,
                ota_vat_pct,

                pricing_model,
                fixed_rent_type,
                fixed_rent_value,

                contract_profile_id,
                stay_type,

                settlement_base_mode_snapshot,
                profit_mode_snapshot,
                owner_percent_snapshot,
                company_percent_snapshot,
                fixed_rent_type_snapshot,
                fixed_rent_value_snapshot,
                fixed_rent_currency_snapshot,
                ota_cost_mode_snapshot,
                expense_mode_snapshot,

                checkin_actor_id,
                manager_commission_actor_id,
                manager_commission_pct_snapshot,

                finance_status,
                finance_locked_at,
                finance_locked_by,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    # ---------------------------------------------------------
    # READ
    # ---------------------------------------------------------

    def get_all(self):
        self.cursor.execute(
            """
            SELECT *
            FROM bookings
            ORDER BY id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, booking_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = ?
            """,
            (booking_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_by_apartment_id(self, apartment_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM bookings
            WHERE apartment_id = ?
            ORDER BY check_in DESC, id DESC
            """,
            (apartment_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_date_range(self, date_from: str, date_to: str):
        self.cursor.execute(
            """
            SELECT *
            FROM bookings
            WHERE check_in <= ?
              AND check_out >= ?
            ORDER BY check_in ASC, id ASC
            """,
            (date_to, date_from),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        booking_id: int,
        apartment_id: int,
        guest_name: str,
        check_in: str,
        check_out: str,
        total_amount: float,
        guest_price: float | None = None,
        settlement_base_amount: float | None = None,
        tax_base_price: float | None = None,
        source_channel: str | None = None,
        ota_account_name: str | None = None,
        ota_commission_pct: float | None = None,
        ota_vat_pct: float | None = None,
        pricing_model: str = "management",
        fixed_rent_type: str | None = None,
        fixed_rent_value: float | None = None,
        contract_profile_id: int | None = None,
        stay_type: str = "short_term",
        settlement_base_mode_snapshot: str | None = None,
        profit_mode_snapshot: str | None = None,
        owner_percent_snapshot: float | None = None,
        company_percent_snapshot: float | None = None,
        fixed_rent_type_snapshot: str | None = None,
        fixed_rent_value_snapshot: float | None = None,
        fixed_rent_currency_snapshot: str | None = None,
        ota_cost_mode_snapshot: str | None = None,
        expense_mode_snapshot: str | None = None,
        checkin_actor_id: int | None = None,
        manager_commission_actor_id: int | None = None,
        manager_commission_pct_snapshot: float | None = None,
        finance_status: str = "draft",
        finance_locked_at: str | None = None,
        finance_locked_by: int | None = None,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE bookings
            SET
                apartment_id = ?,
                guest_name = ?,
                check_in = ?,
                check_out = ?,
                total_amount = ?,

                guest_price = ?,
                settlement_base_amount = ?,
                tax_base_price = ?,

                source_channel = ?,
                ota_account_name = ?,
                ota_commission_pct = ?,
                ota_vat_pct = ?,

                pricing_model = ?,
                fixed_rent_type = ?,
                fixed_rent_value = ?,

                contract_profile_id = ?,
                stay_type = ?,

                settlement_base_mode_snapshot = ?,
                profit_mode_snapshot = ?,
                owner_percent_snapshot = ?,
                company_percent_snapshot = ?,
                fixed_rent_type_snapshot = ?,
                fixed_rent_value_snapshot = ?,
                fixed_rent_currency_snapshot = ?,
                ota_cost_mode_snapshot = ?,
                expense_mode_snapshot = ?,

                checkin_actor_id = ?,
                manager_commission_actor_id = ?,
                manager_commission_pct_snapshot = ?,

                finance_status = ?,
                finance_locked_at = ?,
                finance_locked_by = ?
            WHERE id = ?
            """,
            (
                apartment_id,
                guest_name,
                check_in,
                check_out,
                total_amount,

                guest_price,
                settlement_base_amount,
                tax_base_price,

                source_channel,
                ota_account_name,
                ota_commission_pct,
                ota_vat_pct,

                pricing_model,
                fixed_rent_type,
                fixed_rent_value,

                contract_profile_id,
                stay_type,

                settlement_base_mode_snapshot,
                profit_mode_snapshot,
                owner_percent_snapshot,
                company_percent_snapshot,
                fixed_rent_type_snapshot,
                fixed_rent_value_snapshot,
                fixed_rent_currency_snapshot,
                ota_cost_mode_snapshot,
                expense_mode_snapshot,

                checkin_actor_id,
                manager_commission_actor_id,
                manager_commission_pct_snapshot,

                finance_status,
                finance_locked_at,
                finance_locked_by,

                booking_id,
            ),
        )
        self.conn.commit()

    def update_finance_status(
        self,
        booking_id: int,
        finance_status: str,
        finance_locked_at: str | None = None,
        finance_locked_by: int | None = None,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE bookings
            SET
                finance_status = ?,
                finance_locked_at = ?,
                finance_locked_by = ?
            WHERE id = ?
            """,
            (
                finance_status,
                finance_locked_at,
                finance_locked_by,
                booking_id,
            ),
        )
        self.conn.commit()

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(self, booking_id: int) -> None:
        self.cursor.execute(
            """
            DELETE FROM bookings
            WHERE id = ?
            """,
            (booking_id,),
        )
        self.conn.commit()