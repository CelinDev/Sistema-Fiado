from datetime import date, timedelta
import pytest

from app.database.connection import DatabaseManager
from app.database.migrations import run_migrations
from app.database.models import DebtStatus
from app.services.customer_service import CustomerService
from app.services.debt_service import DebtService
from app.validators.schemas import CustomerCreateSchema, DebtCreateSchema


@pytest.fixture
def debt_suite(tmp_path):
    test_db = tmp_path / "test_debts.db"
    db_mgr = DatabaseManager(f"sqlite:///{test_db.as_posix()}")
    run_migrations(db_mgr.engine)
    return CustomerService(db_mgr.session_scope), DebtService(db_mgr.session_scope)


def test_debt_creation_and_status(debt_suite):
    cust_srv, debt_srv = debt_suite
    customer = cust_srv.create_customer(CustomerCreateSchema(name="Luciana"))

    # Dívida no prazo normal
    d1 = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=customer.id,
            description="Farinha e açúcar",
            original_amount_cents=8500,
            due_date=date.today() + timedelta(days=10),
        )
    )
    assert d1.status == DebtStatus.PENDING.value
    assert d1.remaining_cents == 8500
    assert d1.is_overdue is False

    # Dívida já vencida na data
    d2 = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=customer.id,
            description="Bebidas",
            original_amount_cents=3500,
            due_date=date.today() - timedelta(days=1),
        )
    )
    assert d2.status == DebtStatus.OVERDUE.value
    assert d2.is_overdue is True


def test_cancel_debt(debt_suite):
    cust_srv, debt_srv = debt_suite
    customer = cust_srv.create_customer(CustomerCreateSchema(name="Fernando"))

    debt = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=customer.id,
            description="Compra errada",
            original_amount_cents=5000,
        )
    )

    cancelled = debt_srv.cancel_debt(debt.id, reason="Lançamento duplicado por engano")
    assert cancelled.status == DebtStatus.CANCELLED.value
    assert cancelled.remaining_cents == 0

    # Não deve constar no saldo devedor do cliente
    summary = cust_srv.get_customer_summary(customer.id)
    assert summary["current_debt_cents"] == 0


def test_credit_limit_enforcement(debt_suite):
    cust_srv, debt_srv = debt_suite
    customer = cust_srv.create_customer(CustomerCreateSchema(name="Maria Limite", credit_limit_cents=5000))

    # Compra dentro do limite (R$ 30,00 de R$ 50,00) -> permitido
    debt_srv.create_debt(
        DebtCreateSchema(customer_id=customer.id, description="Compra 1", original_amount_cents=3000)
    )

    # Compra que estoura o limite (R$ 30,00 + R$ 25,00 = R$ 55,00 > R$ 50,00) -> deve barrar
    with pytest.raises(ValueError, match="Limite de crédito excedido"):
        debt_srv.create_debt(
            DebtCreateSchema(customer_id=customer.id, description="Compra 2", original_amount_cents=2500)
        )
