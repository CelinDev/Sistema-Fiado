import pytest
from app.database.connection import DatabaseManager
from app.database.migrations import run_migrations
from app.database.models import DebtStatus, PaymentMethod
from app.services.customer_service import CustomerService
from app.services.debt_service import DebtService
from app.services.payment_service import PaymentService
from app.validators.schemas import CustomerCreateSchema, DebtCreateSchema, PaymentCreateSchema


@pytest.fixture
def payment_suite(tmp_path):
    test_db = tmp_path / "test_pay.db"
    db_mgr = DatabaseManager(f"sqlite:///{test_db.as_posix()}")
    run_migrations(db_mgr.engine)
    return CustomerService(db_mgr.session_scope), DebtService(db_mgr.session_scope), PaymentService(db_mgr.session_scope)


def test_payment_overflow_protection(payment_suite):
    cust_srv, debt_srv, pay_srv = payment_suite
    customer = cust_srv.create_customer(CustomerCreateSchema(name="Regina"))

    debt = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=customer.id,
            description="Doces",
            original_amount_cents=3000,  # R$ 30,00
        )
    )

    # Pagamento de R$ 30,01 -> DEVE SER REJEITADO
    with pytest.raises(ValueError, match="superior ao saldo devedor"):
        pay_srv.register_payment(
            PaymentCreateSchema(
                customer_id=customer.id,
                debt_id=debt.id,
                amount_cents=3001,
                payment_method=PaymentMethod.PIX,
            )
        )


def test_fifo_multiple_debts_payment(payment_suite):
    """Testa abatimento automático distribuído em ordem cronológica (FIFO)."""
    cust_srv, debt_srv, pay_srv = payment_suite
    customer = cust_srv.create_customer(CustomerCreateSchema(name="Marcos"))

    # Dívida 1: R$ 40,00
    d1 = debt_srv.create_debt(
        DebtCreateSchema(customer_id=customer.id, description="Fiado 1", original_amount_cents=4000)
    )
    # Dívida 2: R$ 60,00
    d2 = debt_srv.create_debt(
        DebtCreateSchema(customer_id=customer.id, description="Fiado 2", original_amount_cents=6000)
    )

    # Pagamento geral de R$ 70,00 (sem debt_id)
    payments = pay_srv.register_payment(
        PaymentCreateSchema(
            customer_id=customer.id,
            debt_id=None,
            amount_cents=7000,
            payment_method=PaymentMethod.CASH,
        )
    )

    assert len(payments) == 2
    # Dívida 1 quitada (R$ 40,00)
    assert payments[0].amount_cents == 4000
    assert payments[0].debt_id == d1.id

    # Dívida 2 recebeu restante (R$ 30,00)
    assert payments[1].amount_cents == 3000
    assert payments[1].debt_id == d2.id

    summary = cust_srv.get_customer_summary(customer.id)
    assert summary["current_debt_cents"] == 3000
    assert summary["total_paid_cents"] == 7000
