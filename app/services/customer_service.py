from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.database.models import Customer, DebtStatus
from app.database.repositories import CustomerRepository, AuditRepository
from app.utils.logger import logger
from app.validators.schemas import CustomerCreateSchema, CustomerUpdateSchema


class CustomerService:
    def __init__(self, db_session_factory=None):
        self.session_factory = db_session_factory or db_manager.session_scope

    def create_customer(self, data: CustomerCreateSchema) -> Customer:
        with self.session_factory() as session:
            repo = CustomerRepository(session)
            audit_repo = AuditRepository(session)

            # Valida duplicidade de CPF se fornecido
            if data.cpf:
                existing_cpf = repo.find_by_cpf(data.cpf)
                if existing_cpf:
                    raise ValueError(f"Já existe um cliente cadastrado com este CPF: {existing_cpf.name}")

            # Verifica se já existe cliente com o mesmo nome (aviso / checagem)
            existing_name = repo.find_by_exact_name(data.name)
            if existing_name:
                logger.warning(f"Aviso: Cliente com nome similar já cadastrado: ID {existing_name.id}")

            customer = Customer(
                name=data.name,
                phone=data.phone,
                cpf=data.cpf,
                address=data.address,
                notes=data.notes,
                credit_limit_cents=data.credit_limit_cents,
                is_active=data.is_active,
            )
            repo.add(customer)

            audit_repo.log(
                entity_name="CUSTOMER",
                entity_id=customer.id,
                action="CREATE",
                details={"name": customer.name, "phone": customer.phone, "cpf": customer.cpf}
            )
            session.refresh(customer)
            _ = customer.debts
            _ = customer.payments
            return customer

    def update_customer(self, customer_id: int, data: CustomerUpdateSchema) -> Customer:
        with self.session_factory() as session:
            repo = CustomerRepository(session)
            audit_repo = AuditRepository(session)

            customer = repo.get_by_id(customer_id)
            if not customer:
                raise ValueError("Cliente não encontrado.")

            if data.cpf and data.cpf != customer.cpf:
                existing_cpf = repo.find_by_cpf(data.cpf)
                if existing_cpf and existing_cpf.id != customer_id:
                    raise ValueError(f"Este CPF já pertence ao cliente: {existing_cpf.name}")

            diff = {}
            if data.name is not None and data.name != customer.name:
                diff["name"] = {"old": customer.name, "new": data.name}
                customer.name = data.name
            if data.phone is not None:
                diff["phone"] = {"old": customer.phone, "new": data.phone}
                customer.phone = data.phone
            if data.cpf is not None:
                diff["cpf"] = {"old": customer.cpf, "new": data.cpf}
                customer.cpf = data.cpf
            if data.address is not None:
                diff["address"] = {"old": customer.address, "new": data.address}
                customer.address = data.address
            if data.notes is not None:
                diff["notes"] = {"old": customer.notes, "new": data.notes}
                customer.notes = data.notes
            if data.credit_limit_cents is not None:
                diff["credit_limit_cents"] = {"old": customer.credit_limit_cents, "new": data.credit_limit_cents}
                customer.credit_limit_cents = data.credit_limit_cents
            if data.is_active is not None:
                diff["is_active"] = {"old": customer.is_active, "new": data.is_active}
                customer.is_active = data.is_active

            repo.update(customer)
            if diff:
                audit_repo.log("CUSTOMER", customer.id, "UPDATE", diff)

            session.refresh(customer)
            _ = customer.debts
            _ = customer.payments
            return customer

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        with self.session_factory() as session:
            repo = CustomerRepository(session)
            return repo.get_with_details(customer_id)

    def search_customers(self, query: str = "", active_only: bool = False) -> List[Customer]:
        with self.session_factory() as session:
            repo = CustomerRepository(session)
            return repo.search(query, active_only=active_only)

    def get_all_customers_with_debts(self) -> List[Customer]:
        with self.session_factory() as session:
            repo = CustomerRepository(session)
            return repo.get_all_with_debts()

    def get_customer_summary(self, customer_id: int) -> Dict[str, Any]:
        with self.session_factory() as session:
            repo = CustomerRepository(session)
            customer = repo.get_with_details(customer_id)
            if not customer:
                raise ValueError("Cliente não encontrado.")

            open_debts = [
                d for d in customer.debts
                if d.status != DebtStatus.CANCELLED.value and d.remaining_cents > 0
            ]
            paid_debts = [
                d for d in customer.debts
                if d.status == DebtStatus.PAID.value
            ]
            valid_payments = [p for p in customer.payments if not p.is_cancelled]

            return {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "cpf": customer.cpf,
                "address": customer.address,
                "notes": customer.notes,
                "credit_limit_cents": customer.credit_limit_cents,
                "is_active": customer.is_active,
                "created_at": customer.created_at,
                "current_debt_cents": customer.current_debt_cents,
                "total_purchases_cents": customer.total_purchases_cents,
                "total_paid_cents": customer.total_paid_cents,
                "open_debts_count": len(open_debts),
                "paid_debts_count": len(paid_debts),
                "payments_count": len(valid_payments),
            }


    def delete_customer(self, customer_id: int) -> None:
        """
        Exclui um cliente somente se o saldo devedor estiver quitado (current_debt_cents == 0).
        Caso possua débitos em aberto, bloqueia com exceção clara.
        """
        with self.session_factory() as session:
            repo = CustomerRepository(session)
            audit_repo = AuditRepository(session)

            customer = repo.get_with_details(customer_id)
            if not customer:
                raise ValueError("Cliente não encontrado.")

            if customer.current_debt_cents > 0:
                raise ValueError(
                    f"Não é possível excluir o cliente '{customer.name}' porque ele possui "
                    f"débitos em aberto no valor de R$ {customer.current_debt_cents / 100:.2f}. "
                    "Para excluir, o saldo devedor deve estar totalmente quitado."
                )

            customer_name = customer.name
            audit_repo.log(
                entity_name="CUSTOMER",
                entity_id=customer.id,
                action="DELETE",
                details={"name": customer_name, "id": customer_id}
            )

            repo.delete(customer)


customer_service = CustomerService()
