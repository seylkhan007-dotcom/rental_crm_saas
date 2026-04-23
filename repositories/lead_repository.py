from repositories.base_repository import BaseRepository


class LeadRepository(BaseRepository):
    """Репозиторий лидов (потенциальных клиентов).

    Работает с таблицей leads.

    Здесь только CRUD и чтение данных.
    Без бизнес-логики.
    """

    def create(self, lead_data: dict) -> dict:
        """Создать нового лида и вернуть его с id."""
        self.cursor.execute(
            """
            INSERT INTO leads (
                name,
                phone,
                whatsapp_number,
                email,
                source_channel,
                pipeline_status,
                apartment_id,
                notes,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                lead_data.get("name"),
                lead_data.get("phone"),
                lead_data.get("whatsapp_number"),
                lead_data.get("email"),
                lead_data.get("source_channel"),
                lead_data.get("pipeline_status", "NEW"),
                lead_data.get("apartment_id"),
                lead_data.get("notes"),
                lead_data.get("created_by"),
            ),
        )
        self.conn.commit()
        lead_id = self.cursor.lastrowid
        return self.get_by_id(lead_id)

    def get_by_id(self, lead_id: int) -> dict | None:
        """Получить лида по ID."""
        self.cursor.execute(
            """
            SELECT
                id,
                name,
                phone,
                whatsapp_number,
                email,
                source_channel,
                pipeline_status,
                apartment_id,
                notes,
                created_by,
                converted_to_booking_id,
                created_at,
                updated_at
            FROM leads
            WHERE id = ?
            """,
            (lead_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_all(self) -> list:
        """Получить всех лидов, отсортированных по дате создания (новые сначала)."""
        self.cursor.execute(
            """
            SELECT
                id,
                name,
                phone,
                whatsapp_number,
                email,
                source_channel,
                pipeline_status,
                apartment_id,
                notes,
                created_by,
                converted_to_booking_id,
                created_at,
                updated_at
            FROM leads
            ORDER BY created_at DESC
            """
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def update(self, lead_id: int, updates: dict) -> dict:
        """Обновить поля лида."""
        allowed_fields = {
            "name",
            "phone",
            "whatsapp_number",
            "email",
            "source_channel",
            "pipeline_status",
            "apartment_id",
            "notes",
            "converted_to_booking_id",
        }
        
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_fields:
            return self.get_by_id(lead_id)
        
        update_fields["updated_at"] = "CURRENT_TIMESTAMP"
        
        set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys() if k != "updated_at"])
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
        
        values = [v for k, v in update_fields.items() if k != "updated_at"]
        values.append(lead_id)
        
        self.cursor.execute(
            f"""
            UPDATE leads
            SET {set_clause}
            WHERE id = ?
            """,
            values,
        )
        self.conn.commit()
        return self.get_by_id(lead_id)

    def delete(self, lead_id: int) -> bool:
        """Удалить лида."""
        self.cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        self.conn.commit()
        return True
