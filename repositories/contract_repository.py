from repositories.base_repository import BaseRepository


class ContractRepository(BaseRepository):
    """Репозиторий контрактов и правил контрактов."""

    # ---------------------------------------------------------
    # CONTRACT PROFILES
    # ---------------------------------------------------------

    def create_profile(
        self,
        owner_id: int,
        profile_name: str,
        pricing_model: str = "management",
        settlement_base_mode: str = "from_guest_price",
        profit_mode: str = "gross_split",
        owner_percent: float = 0.0,
        company_percent: float = 0.0,
        fixed_rent_type: str | None = None,
        fixed_rent_value: float = 0.0,
        fixed_rent_currency: str = "GEL",
        ota_cost_mode: str = "company_only",
        expense_mode: str = "rule_based",
        notes: str | None = None,
        is_active: int = 1,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO owner_contract_profiles (
                owner_id,
                profile_name,
                pricing_model,
                settlement_base_mode,
                profit_mode,
                owner_percent,
                company_percent,
                fixed_rent_type,
                fixed_rent_value,
                fixed_rent_currency,
                ota_cost_mode,
                expense_mode,
                notes,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                owner_id,
                profile_name,
                pricing_model,
                settlement_base_mode,
                profit_mode,
                owner_percent,
                company_percent,
                fixed_rent_type,
                fixed_rent_value,
                fixed_rent_currency,
                ota_cost_mode,
                expense_mode,
                notes,
                is_active,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_profiles(self):
        self.cursor.execute(
            """
            SELECT
                p.*,
                o.name AS owner_name
            FROM owner_contract_profiles p
            INNER JOIN owners o ON o.id = p.owner_id
            ORDER BY p.id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_active_profiles(self):
        self.cursor.execute(
            """
            SELECT
                p.*,
                o.name AS owner_name
            FROM owner_contract_profiles p
            INNER JOIN owners o ON o.id = p.owner_id
            WHERE p.is_active = 1
            ORDER BY p.id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_profile_by_id(self, contract_profile_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM owner_contract_profiles
            WHERE id = ?
            """,
            (contract_profile_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_profiles_by_owner_id(self, owner_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM owner_contract_profiles
            WHERE owner_id = ?
            ORDER BY id DESC
            """,
            (owner_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_active_profile_by_apartment_id(self, apartment_id: int):
        self.cursor.execute(
            """
            SELECT
                p.*,
                o.name AS owner_name
            FROM owner_contract_profiles p
            INNER JOIN contract_apartments ca ON ca.contract_profile_id = p.id
            INNER JOIN owners o ON o.id = p.owner_id
            WHERE ca.apartment_id = ?
              AND p.is_active = 1
            ORDER BY p.id DESC
            LIMIT 1
            """,
            (apartment_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_profile(
        self,
        contract_profile_id: int,
        owner_id: int,
        profile_name: str,
        pricing_model: str = "management",
        settlement_base_mode: str = "from_guest_price",
        profit_mode: str = "gross_split",
        owner_percent: float = 0.0,
        company_percent: float = 0.0,
        fixed_rent_type: str | None = None,
        fixed_rent_value: float = 0.0,
        fixed_rent_currency: str = "GEL",
        ota_cost_mode: str = "company_only",
        expense_mode: str = "rule_based",
        notes: str | None = None,
        is_active: int = 1,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE owner_contract_profiles
            SET
                owner_id = ?,
                profile_name = ?,
                pricing_model = ?,
                settlement_base_mode = ?,
                profit_mode = ?,
                owner_percent = ?,
                company_percent = ?,
                fixed_rent_type = ?,
                fixed_rent_value = ?,
                fixed_rent_currency = ?,
                ota_cost_mode = ?,
                expense_mode = ?,
                notes = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                owner_id,
                profile_name,
                pricing_model,
                settlement_base_mode,
                profit_mode,
                owner_percent,
                company_percent,
                fixed_rent_type,
                fixed_rent_value,
                fixed_rent_currency,
                ota_cost_mode,
                expense_mode,
                notes,
                is_active,
                contract_profile_id,
            ),
        )
        self.conn.commit()

    def delete_profile(self, contract_profile_id: int) -> None:
        self.delete_contract_apartments_by_profile_id(contract_profile_id)
        self.delete_split_rules_by_profile_id(contract_profile_id)
        self.delete_expense_rules_by_profile_id(contract_profile_id)

        self.cursor.execute(
            """
            DELETE FROM owner_contract_profiles
            WHERE id = ?
            """,
            (contract_profile_id,),
        )
        self.conn.commit()

    # ---------------------------------------------------------
    # CONTRACT ↔ APARTMENTS
    # ---------------------------------------------------------

    def add_apartment_to_profile(self, contract_profile_id: int, apartment_id: int) -> int:
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO contract_apartments (
                contract_profile_id,
                apartment_id,
                created_at
            )
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (
                contract_profile_id,
                apartment_id,
            ),
        )
        self.conn.commit()

        self.cursor.execute(
            """
            SELECT id
            FROM contract_apartments
            WHERE contract_profile_id = ?
              AND apartment_id = ?
            """,
            (contract_profile_id, apartment_id),
        )
        row = self.cursor.fetchone()
        return row["id"] if row else 0

    def remove_apartment_from_profile(self, contract_profile_id: int, apartment_id: int) -> None:
        self.cursor.execute(
            """
            DELETE FROM contract_apartments
            WHERE contract_profile_id = ?
              AND apartment_id = ?
            """,
            (contract_profile_id, apartment_id),
        )
        self.conn.commit()

    def replace_profile_apartments(self, contract_profile_id: int, apartment_ids: list[int]) -> None:
        self.delete_contract_apartments_by_profile_id(contract_profile_id)

        for apartment_id in apartment_ids:
            self.add_apartment_to_profile(contract_profile_id, apartment_id)

    def get_apartments_by_profile_id(self, contract_profile_id: int):
        self.cursor.execute(
            """
            SELECT
                a.*,
                ca.id AS contract_apartment_link_id
            FROM contract_apartments ca
            INNER JOIN apartments a ON a.id = ca.apartment_id
            WHERE ca.contract_profile_id = ?
            ORDER BY a.name ASC
            """,
            (contract_profile_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_profile_links_by_apartment_id(self, apartment_id: int):
        self.cursor.execute(
            """
            SELECT
                ca.*,
                p.profile_name,
                p.owner_id,
                p.is_active
            FROM contract_apartments ca
            INNER JOIN owner_contract_profiles p ON p.id = ca.contract_profile_id
            WHERE ca.apartment_id = ?
            ORDER BY ca.id DESC
            """,
            (apartment_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def delete_contract_apartments_by_profile_id(self, contract_profile_id: int) -> None:
        self.cursor.execute(
            """
            DELETE FROM contract_apartments
            WHERE contract_profile_id = ?
            """,
            (contract_profile_id,),
        )
        self.conn.commit()

    # ---------------------------------------------------------
    # SPLIT RULES
    # ---------------------------------------------------------

    def create_split_rule(
        self,
        contract_profile_id: int,
        stay_type: str,
        owner_percent: float,
        company_percent: float,
        split_basis: str = "owner_price",
        notes: str | None = None,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO contract_split_rules (
                contract_profile_id,
                stay_type,
                owner_percent,
                company_percent,
                split_basis,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                contract_profile_id,
                stay_type,
                owner_percent,
                company_percent,
                split_basis,
                notes,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_split_rules(self):
        self.cursor.execute(
            """
            SELECT
                r.*,
                p.profile_name,
                p.owner_id,
                o.name AS owner_name
            FROM contract_split_rules r
            INNER JOIN owner_contract_profiles p ON p.id = r.contract_profile_id
            INNER JOIN owners o ON o.id = p.owner_id
            ORDER BY r.id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_split_rule_by_id(self, rule_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM contract_split_rules
            WHERE id = ?
            """,
            (rule_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_split_rules_by_profile_id(self, contract_profile_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM contract_split_rules
            WHERE contract_profile_id = ?
            ORDER BY id DESC
            """,
            (contract_profile_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_split_rule_by_profile_and_stay_type(self, contract_profile_id: int, stay_type: str):
        self.cursor.execute(
            """
            SELECT *
            FROM contract_split_rules
            WHERE contract_profile_id = ?
              AND stay_type = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (contract_profile_id, stay_type),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_split_rule(
        self,
        rule_id: int,
        contract_profile_id: int,
        stay_type: str,
        owner_percent: float,
        company_percent: float,
        split_basis: str = "owner_price",
        notes: str | None = None,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE contract_split_rules
            SET
                contract_profile_id = ?,
                stay_type = ?,
                owner_percent = ?,
                company_percent = ?,
                split_basis = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                contract_profile_id,
                stay_type,
                owner_percent,
                company_percent,
                split_basis,
                notes,
                rule_id,
            ),
        )
        self.conn.commit()

    def delete_split_rule(self, rule_id: int) -> None:
        self.cursor.execute(
            """
            DELETE FROM contract_split_rules
            WHERE id = ?
            """,
            (rule_id,),
        )
        self.conn.commit()

    def delete_split_rules_by_profile_id(self, contract_profile_id: int) -> None:
        self.cursor.execute(
            """
            DELETE FROM contract_split_rules
            WHERE contract_profile_id = ?
            """,
            (contract_profile_id,),
        )
        self.conn.commit()

    # ---------------------------------------------------------
    # EXPENSE RULES
    # ---------------------------------------------------------

    def create_expense_rule(
        self,
        contract_profile_id: int,
        expense_type_code: str,
        responsibility_mode: str = "company",
        owner_pct: float = 0.0,
        company_pct: float = 0.0,
        guest_pct: float = 0.0,
        notes: str | None = None,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO contract_expense_rules (
                contract_profile_id,
                expense_type_code,
                responsibility_mode,
                owner_pct,
                company_pct,
                guest_pct,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                contract_profile_id,
                expense_type_code,
                responsibility_mode,
                owner_pct,
                company_pct,
                guest_pct,
                notes,
            ),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_expense_rules(self):
        self.cursor.execute(
            """
            SELECT
                r.*,
                p.profile_name,
                p.owner_id,
                o.name AS owner_name
            FROM contract_expense_rules r
            INNER JOIN owner_contract_profiles p ON p.id = r.contract_profile_id
            INNER JOIN owners o ON o.id = p.owner_id
            ORDER BY r.id DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_expense_rule_by_id(self, rule_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM contract_expense_rules
            WHERE id = ?
            """,
            (rule_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_expense_rules_by_profile_id(self, contract_profile_id: int):
        self.cursor.execute(
            """
            SELECT *
            FROM contract_expense_rules
            WHERE contract_profile_id = ?
            ORDER BY id DESC
            """,
            (contract_profile_id,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_expense_rule_by_profile_and_type(self, contract_profile_id: int, expense_type_code: str):
        self.cursor.execute(
            """
            SELECT *
            FROM contract_expense_rules
            WHERE contract_profile_id = ?
              AND expense_type_code = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (contract_profile_id, expense_type_code),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_expense_rule(
        self,
        rule_id: int,
        contract_profile_id: int,
        expense_type_code: str,
        responsibility_mode: str = "company",
        owner_pct: float = 0.0,
        company_pct: float = 0.0,
        guest_pct: float = 0.0,
        notes: str | None = None,
    ) -> None:
        self.cursor.execute(
            """
            UPDATE contract_expense_rules
            SET
                contract_profile_id = ?,
                expense_type_code = ?,
                responsibility_mode = ?,
                owner_pct = ?,
                company_pct = ?,
                guest_pct = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                contract_profile_id,
                expense_type_code,
                responsibility_mode,
                owner_pct,
                company_pct,
                guest_pct,
                notes,
                rule_id,
            ),
        )
        self.conn.commit()

    def delete_expense_rule(self, rule_id: int) -> None:
        self.cursor.execute(
            """
            DELETE FROM contract_expense_rules
            WHERE id = ?
            """,
            (rule_id,),
        )
        self.conn.commit()

    def delete_expense_rules_by_profile_id(self, contract_profile_id: int) -> None:
        self.cursor.execute(
            """
            DELETE FROM contract_expense_rules
            WHERE contract_profile_id = ?
            """,
            (contract_profile_id,),
        )
        self.conn.commit()