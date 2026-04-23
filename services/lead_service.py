from repositories.lead_repository import LeadRepository


class LeadService:
    """Сервис управления лидами (потенциальные клиенты).

    Здесь базовая валидация и CRUD операции.
    Без сложной бизнес-логики.
    """

    def __init__(self, conn):
        self.lead_repo = LeadRepository(conn)

    def create_lead(
        self,
        name: str,
        phone: str,
        source_channel: str,
        created_by: int,
        whatsapp_number: str | None = None,
        email: str | None = None,
        apartment_id: int | None = None,
        notes: str | None = None,
    ) -> dict:
        """Создать нового лида. Базовая валидация: имя и телефон обязательны."""
        normalized_name = (name or "").strip()
        normalized_phone = (phone or "").strip()
        normalized_source = (source_channel or "").strip()

        if not normalized_name:
            raise ValueError("Имя лида не может быть пустым.")
        if not normalized_phone:
            raise ValueError("Телефон лида не может быть пустым.")
        if not normalized_source:
            raise ValueError("Источник лида не может быть пустым.")

        lead_data = {
            "name": normalized_name,
            "phone": normalized_phone,
            "whatsapp_number": (whatsapp_number or "").strip() or None,
            "email": (email or "").strip() or None,
            "source_channel": normalized_source,
            "pipeline_status": "NEW",
            "apartment_id": apartment_id,
            "notes": (notes or "").strip() or None,
            "created_by": created_by,
        }

        return self.lead_repo.create(lead_data)

    def get_all_leads(self) -> list:
        """Получить всех лидов."""
        return self.lead_repo.get_all()

    def update_lead(self, lead_id: int, updates: dict) -> dict:
        """Обновить поля лида."""
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError("Лид не найден.")

        return self.lead_repo.update(lead_id, updates)
