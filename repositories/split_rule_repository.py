class SplitRuleRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(
        self,
        level: str,
        entity_id: int,
        owner_percent: float,
        manager_percent: float,
        stay_type: str = "all",
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO split_rules (
                level,
                entity_id,
                stay_type,
                owner_percent,
                manager_percent
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                level,
                entity_id,
                stay_type,
                owner_percent,
                manager_percent,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM split_rules ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, rule_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM split_rules WHERE id = ?",
            (rule_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_by_level_and_entity(self, level: str, entity_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM split_rules
            WHERE level = ? AND entity_id = ?
            ORDER BY id DESC
            """,
            (level, entity_id),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_by_level_entity_and_stay_type(
        self,
        level: str,
        entity_id: int,
        stay_type: str,
    ):
        cursor = self.conn.cursor()

        # 1. exact stay_type
        cursor.execute(
            """
            SELECT * FROM split_rules
            WHERE level = ? AND entity_id = ? AND stay_type = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (level, entity_id, stay_type),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # 2. fallback to all
        cursor.execute(
            """
            SELECT * FROM split_rules
            WHERE level = ? AND entity_id = ? AND stay_type = 'all'
            ORDER BY id DESC
            LIMIT 1
            """,
            (level, entity_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_applicable_rule(
        self,
        booking_id: int,
        apartment_id: int,
        owner_id: int,
        stay_type: str = "short_term",
    ):
        booking_rule = self.get_by_level_entity_and_stay_type(
            level="booking",
            entity_id=booking_id,
            stay_type=stay_type,
        )
        if booking_rule:
            return booking_rule

        apartment_rule = self.get_by_level_entity_and_stay_type(
            level="apartment",
            entity_id=apartment_id,
            stay_type=stay_type,
        )
        if apartment_rule:
            return apartment_rule

        owner_rule = self.get_by_level_entity_and_stay_type(
            level="owner",
            entity_id=owner_id,
            stay_type=stay_type,
        )
        if owner_rule:
            return owner_rule

        return None