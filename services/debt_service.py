# services/debt_service.py

from repositories.debt_repository import DebtRepository
from repositories.owner_payout_repository import OwnerPayoutRepository


class DebtService:
    def __init__(self, conn):
        self.debt_repo = DebtRepository(conn)
        self.owner_payout_repo = OwnerPayoutRepository(conn)

    def create_debt_from_payout(self, payout_id: int):
        """
        Новый универсальный метод.
        Используется новым booking_service.py
        """
        return self.create_owner_debt_from_payout(payout_id)

    def create_owner_debt_from_payout(self, payout_id: int):
        payouts = self.owner_payout_repo.get_all()
        payout = None

        for p in payouts:
            if p["id"] == payout_id:
                payout = p
                break

        if not payout:
            raise ValueError("payout_id не существует")

        return self.debt_repo.create(
            counterparty_type="owner",
            counterparty_id=payout["owner_id"],
            booking_id=payout["booking_id"],
            related_payout_id=payout["id"],
            amount=payout["amount"],
            status="open",
            description=f"Owner payout debt for booking {payout['booking_id']}",
        )

    def get_all_debts(self):
        return self.debt_repo.get_all()

    def get_owner_debts(self, owner_id: int):
        return self.debt_repo.get_by_counterparty("owner", owner_id)

    def mark_debt_as_settled(self, debt_id: int):
        self.debt_repo.mark_as_settled(debt_id)

    def get_owner_balance_summary(self, owner_id: int):
        debts = self.get_owner_debts(owner_id)

        open_debts = [d for d in debts if d["status"] == "open"]
        settled_debts = [d for d in debts if d["status"] == "settled"]

        open_amount = round(sum(d["amount"] for d in open_debts), 2)
        settled_amount = round(sum(d["amount"] for d in settled_debts), 2)
        total_debt_amount = round(sum(d["amount"] for d in debts), 2)

        return {
            "owner_id": owner_id,
            "total_debt_amount": total_debt_amount,
            "open_debt_amount": open_amount,
            "settled_debt_amount": settled_amount,
            "open_debts_count": len(open_debts),
            "settled_debts_count": len(settled_debts),
            "current_balance": open_amount,
        }