from datetime import date
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.database.models import Customer, Debt, DebtStatus
from app.database.repositories.base_repository import BaseRepository


class DebtRepository(BaseRepository[Debt]):
    def __init__(self, session: Session):
        super().__init__(Debt, session)

    def get_by_customer(self, customer_id: int, include_cancelled: bool = False) -> List[Debt]:
        query = (
            self.session.query(Debt)
            .options(joinedload(Debt.payments))
            .filter(Debt.customer_id == customer_id)
        )
        if not include_cancelled:
            query = query.filter(Debt.status != DebtStatus.CANCELLED.value)
        return query.order_by(Debt.created_at.desc()).all()

    def get_open_debts_by_customer(self, customer_id: int) -> List[Debt]:
        """Retorna dívidas em aberto ordenadas da mais antiga para a mais recente (FIFO)."""
        return (
            self.session.query(Debt)
            .filter(
                Debt.customer_id == customer_id,
                Debt.remaining_cents > 0,
                Debt.status.in_([DebtStatus.PENDING.value, DebtStatus.PARTIALLY_PAID.value, DebtStatus.OVERDUE.value])
            )
            .order_by(Debt.created_at.asc())
            .all()
        )

    def get_overdue_debts(self) -> List[Debt]:
        today = date.today()
        return (
            self.session.query(Debt)
            .join(Debt.customer)
            .options(joinedload(Debt.customer))
            .filter(
                Debt.due_date < today,
                Debt.remaining_cents > 0,
                Debt.status != DebtStatus.CANCELLED.value
            )
            .order_by(Debt.due_date.asc())
            .all()
        )

    def get_all_active_debts(self) -> List[Debt]:
        return (
            self.session.query(Debt)
            .join(Debt.customer)
            .options(joinedload(Debt.customer), joinedload(Debt.payments))
            .filter(Debt.status != DebtStatus.CANCELLED.value)
            .order_by(Debt.created_at.desc())
            .all()
        )

    def get_debts_by_period(self, start_date, end_date) -> List[Debt]:
        return (
            self.session.query(Debt)
            .join(Debt.customer)
            .options(joinedload(Debt.customer))
            .filter(
                Debt.created_at >= start_date,
                Debt.created_at <= end_date,
                Debt.status != DebtStatus.CANCELLED.value
            )
            .order_by(Debt.created_at.desc())
            .all()
        )

    def sum_total_receivable_cents(self) -> int:
        """Soma o saldo restante de todas as dívidas não quitadas e não canceladas."""
        result = (
            self.session.query(func.sum(Debt.remaining_cents))
            .filter(Debt.status.in_([DebtStatus.PENDING.value, DebtStatus.PARTIALLY_PAID.value, DebtStatus.OVERDUE.value]))
            .scalar()
        )
        return result or 0

    def sum_total_overdue_cents(self) -> int:
        today = date.today()
        result = (
            self.session.query(func.sum(Debt.remaining_cents))
            .filter(
                Debt.due_date < today,
                Debt.remaining_cents > 0,
                Debt.status != DebtStatus.CANCELLED.value
            )
            .scalar()
        )
        return result or 0

    def count_pending_debts(self) -> int:
        return (
            self.session.query(func.count(Debt.id))
            .filter(Debt.remaining_cents > 0, Debt.status != DebtStatus.CANCELLED.value)
            .scalar() or 0
        )
