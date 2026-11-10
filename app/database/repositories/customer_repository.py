from typing import List, Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.database.models import Customer, Debt, DebtStatus
from app.database.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: Session):
        super().__init__(Customer, session)

    def search(self, query_str: str, active_only: bool = False) -> List[Customer]:
        """Busca clientes por nome, telefone ou CPF."""
        query = self.session.query(Customer).options(
            joinedload(Customer.debts),
            joinedload(Customer.payments),
        )
        if active_only:
            query = query.filter(Customer.is_active.is_(True))

        if query_str and query_str.strip():
            clean_q = f"%{query_str.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(Customer.name).like(clean_q),
                    Customer.phone.like(clean_q),
                    Customer.cpf.like(clean_q),
                )
            )
        return query.order_by(Customer.name.asc()).all()

    def find_by_exact_name(self, name: str) -> Optional[Customer]:
        return (
            self.session.query(Customer)
            .filter(func.lower(Customer.name) == name.strip().lower())
            .first()
        )

    def find_by_cpf(self, cpf: str) -> Optional[Customer]:
        return (
            self.session.query(Customer)
            .filter(Customer.cpf == cpf.strip())
            .first()
        )

    def get_with_details(self, customer_id: int) -> Optional[Customer]:
        """Retorna cliente com eager loading das dívidas e pagamentos."""
        return (
            self.session.query(Customer)
            .options(
                joinedload(Customer.debts).joinedload(Debt.payments),
                joinedload(Customer.payments)
            )
            .filter(Customer.id == customer_id)
            .first()
        )

    def get_all_with_debts(self) -> List[Customer]:
        return (
            self.session.query(Customer)
            .options(joinedload(Customer.debts), joinedload(Customer.payments))
            .order_by(Customer.name.asc())
            .all()
        )

    def count_total(self) -> int:
        return self.session.query(func.count(Customer.id)).scalar() or 0
