from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.database.models import Debt, DebtStatus, Payment
from app.database.repositories import CustomerRepository, DebtRepository, PaymentRepository, AuditRepository
from app.utils.formatters import format_currency
from app.utils.logger import logger
from app.validators.schemas import PaymentCreateSchema


class PaymentService:
    def __init__(self, db_session_factory=None):
        self.session_factory = db_session_factory or db_manager.session_scope

    def register_payment(self, data: PaymentCreateSchema) -> List[Payment]:
        """
        Registra pagamento garantindo estritamente que não ultrapasse o saldo devedor.
        Se debt_id for informado, abate na dívida específica.
        Se debt_id for None, abate sequencialmente nas dívidas mais antigas (FIFO).
        """
        with self.session_factory() as session:
            cust_repo = CustomerRepository(session)
            debt_repo = DebtRepository(session)
            pay_repo = PaymentRepository(session)
            audit_repo = AuditRepository(session)

            customer = cust_repo.get_with_details(data.customer_id)
            if not customer:
                raise ValueError("Cliente não encontrado.")

            if data.amount_cents <= 0:
                raise ValueError("O valor do pagamento deve ser maior que zero.")

            created_payments = []

            if data.debt_id is not None:
                debt = debt_repo.get_by_id(data.debt_id)
                if not debt:
                    raise ValueError("Dívida selecionada não encontrada.")
                if debt.customer_id != customer.id:
                    raise ValueError("A dívida não pertence ao cliente informado.")
                if debt.status == DebtStatus.CANCELLED.value:
                    raise ValueError("Não é possível pagar uma dívida cancelada.")
                if debt.remaining_cents <= 0:
                    raise ValueError("Esta dívida já está totalmente quitada.")
                if data.amount_cents > debt.remaining_cents:
                    raise ValueError(
                        f"O valor informado ({format_currency(data.amount_cents)}) é superior ao "
                        f"saldo devedor da dívida ({format_currency(debt.remaining_cents)})."
                    )

                debt.remaining_cents -= data.amount_cents
                if debt.remaining_cents == 0:
                    debt.status = DebtStatus.PAID.value
                else:
                    debt.status = DebtStatus.PARTIALLY_PAID.value

                payment = Payment(
                    customer_id=customer.id,
                    debt_id=debt.id,
                    amount_cents=data.amount_cents,
                    payment_method=data.payment_method.value,
                    payment_date=data.payment_date or datetime.now(),
                    notes=data.notes,
                )
                pay_repo.add(payment)
                created_payments.append(payment)

                audit_repo.log(
                    "PAYMENT",
                    payment.id,
                    "PAYMENT_RECEIVED",
                    {
                        "customer_id": customer.id,
                        "customer_name": customer.name,
                        "debt_id": debt.id,
                        "amount_cents": data.amount_cents,
                        "method": data.payment_method.value,
                        "remaining_debt_cents": debt.remaining_cents,
                    }
                )
            else:
                # Abatimento geral FIFO nas dívidas em aberto
                total_open = customer.current_debt_cents
                if data.amount_cents > total_open:
                    raise ValueError(
                        f"O valor informado ({format_currency(data.amount_cents)}) é superior ao "
                        f"saldo devedor total do cliente ({format_currency(total_open)})."
                    )

                open_debts = debt_repo.get_open_debts_by_customer(customer.id)
                if not open_debts:
                    raise ValueError("O cliente não possui débitos em aberto para abatimento.")

                remaining_to_pay = data.amount_cents

                for debt in open_debts:
                    if remaining_to_pay <= 0:
                        break

                    alloc = min(remaining_to_pay, debt.remaining_cents)
                    debt.remaining_cents -= alloc
                    remaining_to_pay -= alloc

                    if debt.remaining_cents == 0:
                        debt.status = DebtStatus.PAID.value
                    else:
                        debt.status = DebtStatus.PARTIALLY_PAID.value

                    payment = Payment(
                        customer_id=customer.id,
                        debt_id=debt.id,
                        amount_cents=alloc,
                        payment_method=data.payment_method.value,
                        payment_date=data.payment_date or datetime.now(),
                        notes=data.notes,
                    )
                    pay_repo.add(payment)
                    created_payments.append(payment)

                    audit_repo.log(
                        "PAYMENT",
                        payment.id,
                        "PAYMENT_RECEIVED",
                        {
                            "customer_id": customer.id,
                            "debt_id": debt.id,
                            "amount_cents": alloc,
                            "method": data.payment_method.value,
                            "remaining_debt_cents": debt.remaining_cents,
                        }
                    )

            session.flush()
            return created_payments

    def cancel_payment(self, payment_id: int, reason: str) -> Payment:
        """
        Estorna/cancela um pagamento com segurança.
        Não exclui a linha do banco; marca como cancelado e estorna o saldo na dívida correspondente.
        """
        if not reason or len(reason.strip()) < 3:
            raise ValueError("O motivo do cancelamento é obrigatório e deve ter no mínimo 3 caracteres.")

        with self.session_factory() as session:
            pay_repo = PaymentRepository(session)
            debt_repo = DebtRepository(session)
            audit_repo = AuditRepository(session)

            payment = pay_repo.get_by_id(payment_id)
            if not payment:
                raise ValueError("Pagamento não encontrado.")

            if payment.is_cancelled:
                raise ValueError("Este pagamento já foi cancelado anteriormente.")

            # Devolve o valor para a dívida
            if payment.debt_id:
                debt = debt_repo.get_by_id(payment.debt_id)
                if debt and debt.status != DebtStatus.CANCELLED.value:
                    debt.remaining_cents += payment.amount_cents
                    # Recalcula o status da dívida
                    if debt.remaining_cents == debt.original_amount_cents:
                        if debt.due_date and debt.due_date < date.today():
                            debt.status = DebtStatus.OVERDUE.value
                        else:
                            debt.status = DebtStatus.PENDING.value
                    else:
                        if debt.due_date and debt.due_date < date.today():
                            debt.status = DebtStatus.OVERDUE.value
                        else:
                            debt.status = DebtStatus.PARTIALLY_PAID.value

            payment.is_cancelled = True
            payment.cancelled_at = datetime.now()
            payment.cancellation_reason = reason.strip()

            audit_repo.log(
                "PAYMENT",
                payment.id,
                "CANCEL",
                {
                    "amount_cents": payment.amount_cents,
                    "customer_id": payment.customer_id,
                    "debt_id": payment.debt_id,
                    "reason": reason.strip(),
                }
            )

            session.refresh(payment)
            return payment

    def get_recent_payments(self, limit: int = 50) -> List[Payment]:
        with self.session_factory() as session:
            pay_repo = PaymentRepository(session)
            return pay_repo.get_recent_payments(limit=limit)

    def get_by_customer(self, customer_id: int) -> List[Payment]:
        with self.session_factory() as session:
            pay_repo = PaymentRepository(session)
            return pay_repo.get_by_customer(customer_id)


payment_service = PaymentService()
