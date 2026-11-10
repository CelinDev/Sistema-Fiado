from datetime import datetime
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.database.models import Customer, Debt, Payment
from app.database.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: Session):
        super().__init__(Payment, session)

    def get_by_customer(self, customer_id: int) -> List[Payment]:
        return (
            self.session.query(Payment)
            .options(joinedload(Payment.debt))
            .filter(Payment.customer_id == customer_id)
            .order_by(Payment.payment_date.desc())
            .all()
        )

    def get_by_debt(self, debt_id: int) -> List[Payment]:
        return (
            self.session.query(Payment)
            .filter(Payment.debt_id == debt_id, Payment.is_cancelled.is_(False))
            .order_by(Payment.payment_date.asc())
            .all()
        )

    def get_recent_payments(self, limit: int = 50) -> List[Payment]:
        return (
            self.session.query(Payment)
            .join(Payment.customer)
            .options(joinedload(Payment.customer), joinedload(Payment.debt))
            .order_by(Payment.payment_date.desc())
            .limit(limit)
            .all()
        )

    def get_payments_by_period(self, start_date: datetime, end_date: datetime) -> List[Payment]:
        return (
            self.session.query(Payment)
            .join(Payment.customer)
            .options(joinedload(Payment.customer), joinedload(Payment.debt))
            .filter(
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date,
                Payment.is_cancelled.is_(False)
            )
            .order_by(Payment.payment_date.desc())
            .all()
        )

    def sum_payments_in_month(self, year: int, month: int) -> int:
        """Soma pagamentos válidos no mês especificado."""
        result = (
            self.session.query(func.sum(Payment.amount_cents))
            .filter(
                Payment.is_cancelled.is_(False),
                func.strftime("%Y", Payment.payment_date) == str(year),
                func.strftime("%m", Payment.payment_date) == f"{month:02d}"
            )
            .scalar()
        )
        return result or 0

    def sum_total_received_cents(self) -> int:
        result = (
            self.session.query(func.sum(Payment.amount_cents))
            .filter(Payment.is_cancelled.is_(False))
            .scalar()
        )
        return result or 0
