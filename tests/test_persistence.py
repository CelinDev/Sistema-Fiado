import os
import pytest
from app.config.settings import Settings
from app.database.connection import DatabaseManager
from app.database.migrations import run_migrations
from app.database.models import Customer, Debt, DebtStatus, Payment, PaymentMethod
from app.database.repositories import CustomerRepository, DebtRepository, PaymentRepository, AuditRepository


@pytest.fixture
def test_db(tmp_path):
    test_db_path = tmp_path / "test_fiado.db"
    db_mgr = DatabaseManager(f"sqlite:///{test_db_path.as_posix()}")
    run_migrations(db_mgr.engine)
    return db_mgr


def test_customer_and_debt_persistence(test_db):
    with test_db.session_scope() as session:
        cust_repo = CustomerRepository(session)
        customer = cust_repo.add(
            Customer(
                name="João da Silva",
                phone="11999998888",
                cpf="12345678901",
                address="Rua das Flores, 100",
                notes="Cliente antigo",
                is_active=True
            )
        )
        assert customer.id is not None
        cust_id = customer.id

    with test_db.session_scope() as session:
        cust_repo = CustomerRepository(session)
        debt_repo = DebtRepository(session)
        
        c = cust_repo.get_by_id(cust_id)
        assert c is not None
        assert c.name == "João da Silva"

        debt = debt_repo.add(
            Debt(
                customer_id=c.id,
                description="Pão francês e frios",
                original_amount_cents=5500,  # R$ 55,00
                remaining_cents=5500,
                status=DebtStatus.PENDING.value
            )
        )
        assert debt.id is not None
        debt_id = debt.id

    with test_db.session_scope() as session:
        cust_repo = CustomerRepository(session)
        detailed = cust_repo.get_with_details(cust_id)
        assert len(detailed.debts) == 1
        assert detailed.current_debt_cents == 5500
        assert detailed.total_purchases_cents == 5500
        assert detailed.total_paid_cents == 0


def test_payment_and_audit(test_db):
    with test_db.session_scope() as session:
        cust_repo = CustomerRepository(session)
        debt_repo = DebtRepository(session)
        pay_repo = PaymentRepository(session)
        audit_repo = AuditRepository(session)

        c = cust_repo.add(Customer(name="Maria Oliveira", phone="1188887777"))
        d = debt_repo.add(
            Debt(
                customer_id=c.id,
                description="Bolo de aniversário",
                original_amount_cents=10000,
                remaining_cents=10000,
                status=DebtStatus.PENDING.value
            )
        )
        # Pagamento parcial de R$ 40,00
        p = pay_repo.add(
            Payment(
                customer_id=c.id,
                debt_id=d.id,
                amount_cents=4000,
                payment_method=PaymentMethod.PIX.value
            )
        )
        d.remaining_cents -= 4000
        d.status = DebtStatus.PARTIALLY_PAID.value

        audit_repo.log("PAYMENT", p.id, "CREATE", {"amount": 4000, "method": "PIX"})

    with test_db.session_scope() as session:
        cust_repo = CustomerRepository(session)
        c = cust_repo.get_with_details(c.id)
        assert c.current_debt_cents == 6000
        assert c.total_paid_cents == 4000
