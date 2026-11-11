from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.database.models import Debt, DebtStatus
from app.database.repositories import CustomerRepository, DebtRepository, AuditRepository
from app.utils.formatters import format_currency
from app.utils.logger import logger
from app.validators.schemas import DebtCreateSchema


class DebtService:
    def __init__(self, db_session_factory=None):
        self.session_factory = db_session_factory or db_manager.session_scope

    def create_debt(self, data: DebtCreateSchema) -> Debt:
        with self.session_factory() as session:
            cust_repo = CustomerRepository(session)
            debt_repo = DebtRepository(session)
            audit_repo = AuditRepository(session)

            customer = cust_repo.get_by_id(data.customer_id)
            if not customer:
                raise ValueError("Cliente não encontrado.")
            if not customer.is_active:
                raise ValueError("Não é possível lançar dívidas para clientes inativos.")

            # Validação do Limite de Crédito
            if customer.credit_limit_cents is not None and customer.credit_limit_cents > 0:
                novo_saldo = customer.current_debt_cents + data.original_amount_cents
                if novo_saldo > customer.credit_limit_cents:
                    limite_fmt = format_currency(customer.credit_limit_cents)
                    atual_fmt = format_currency(customer.current_debt_cents)
                    novo_fmt = format_currency(novo_saldo)
                    raise ValueError(
                        f"Limite de crédito excedido! O cliente possui limite de {limite_fmt}. "
                        f"Saldo devedor atual: {atual_fmt}. Com esta compra iria para {novo_fmt}."
                    )

            # Define status inicial
            status = DebtStatus.PENDING.value
            if data.due_date and data.due_date < date.today():
                status = DebtStatus.OVERDUE.value

            debt = Debt(
                customer_id=data.customer_id,
                description=data.description,
                original_amount_cents=data.original_amount_cents,
                remaining_cents=data.original_amount_cents,
                due_date=data.due_date,
                status=status,
                notes=data.notes,
                created_at=data.debt_date or datetime.now(),
            )
            debt_repo.add(debt)

            audit_repo.log(
                entity_name="DEBT",
                entity_id=debt.id,
                action="CREATE",
                details={
                    "customer_id": data.customer_id,
                    "customer_name": customer.name,
                    "amount_cents": data.original_amount_cents,
                    "description": data.description,
                }
            )
            session.refresh(debt)
            return debt

    def cancel_debt(self, debt_id: int, reason: str) -> Debt:
        """Cancela uma dívida sem excluir fisicamente."""
        with self.session_factory() as session:
            debt_repo = DebtRepository(session)
            audit_repo = AuditRepository(session)

            debt = debt_repo.get_by_id(debt_id)
            if not debt:
                raise ValueError("Dívida não encontrada.")

            if debt.status == DebtStatus.CANCELLED.value:
                raise ValueError("Esta dívida já está cancelada.")

            # Se já houver pagamentos vinculados
            has_valid_payments = any(not p.is_cancelled for p in debt.payments)
            if has_valid_payments:
                raise ValueError("Não é possível cancelar uma dívida com pagamentos ativos. É necessário estornar os pagamentos primeiro.")

            debt.status = DebtStatus.CANCELLED.value
            debt.notes = f"{debt.notes or ''}\n[Cancelamento: {reason}]".strip()
            debt.remaining_cents = 0
            debt_repo.update(debt)

            audit_repo.log("DEBT", debt.id, "CANCEL", {"reason": reason})
            session.refresh(debt)
            _ = debt.customer
            _ = debt.payments
            return debt

    def refresh_overdue_statuses(self) -> int:
        """Atualiza dívidas com data de vencimento ultrapassada para status VENCIDO."""
        with self.session_factory() as session:
            debt_repo = DebtRepository(session)
            today = date.today()
            updated_count = 0

            debts = (
                session.query(Debt)
                .filter(
                    Debt.due_date < today,
                    Debt.remaining_cents > 0,
                    Debt.status.in_([DebtStatus.PENDING.value, DebtStatus.PARTIALLY_PAID.value])
                )
                .all()
            )
            for d in debts:
                d.status = DebtStatus.OVERDUE.value
                updated_count += 1

            return updated_count

    def get_by_customer(self, customer_id: int, include_cancelled: bool = False) -> List[Debt]:
        with self.session_factory() as session:
            debt_repo = DebtRepository(session)
            return debt_repo.get_by_customer(customer_id, include_cancelled=include_cancelled)

    def get_all_active_debts(self) -> List[Debt]:
        with self.session_factory() as session:
            debt_repo = DebtRepository(session)
            return debt_repo.get_all_active_debts()

    def get_overdue_debts(self) -> List[Debt]:
        with self.session_factory() as session:
            debt_repo = DebtRepository(session)
            return debt_repo.get_overdue_debts()


debt_service = DebtService()
