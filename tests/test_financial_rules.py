from datetime import date, timedelta
import pytest

from app.database.connection import DatabaseManager
from app.database.migrations import run_migrations
from app.database.models import DebtStatus, PaymentMethod
from app.services import (
    CustomerService,
    DebtService,
    PaymentService,
    DashboardService,
)
from app.validators.schemas import (
    CustomerCreateSchema,
    DebtCreateSchema,
    PaymentCreateSchema,
)


@pytest.fixture
def service_suite(tmp_path):
    test_db_path = tmp_path / "test_fiado_services.db"
    db_mgr = DatabaseManager(f"sqlite:///{test_db_path.as_posix()}")
    run_migrations(db_mgr.engine)

    cust_srv = CustomerService(db_mgr.session_scope)
    debt_srv = DebtService(db_mgr.session_scope)
    pay_srv = PaymentService(db_mgr.session_scope)
    dash_srv = DashboardService(db_mgr.session_scope)

    return cust_srv, debt_srv, pay_srv, dash_srv


def test_customer_creation_and_duplicate_cpf(service_suite):
    cust_srv, _, _, _ = service_suite

    # Cadastro válido
    c1 = cust_srv.create_customer(
        CustomerCreateSchema(name="Carlos Lima", cpf="12345678901", phone="11988887777")
    )
    assert c1.id is not None
    assert c1.name == "Carlos Lima"

    # Tentativa de duplicar CPF deve falhar
    with pytest.raises(ValueError, match="Já existe um cliente cadastrado com este CPF"):
        cust_srv.create_customer(
            CustomerCreateSchema(name="Outro Carlos", cpf="12345678901")
        )


def test_debt_creation_and_balance_tracking(service_suite):
    cust_srv, debt_srv, pay_srv, _ = service_suite

    customer = cust_srv.create_customer(CustomerCreateSchema(name="Ana Paula"))
    
    # Criar dívida de R$ 150,00 (15000 centavos)
    debt = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=customer.id,
            description="Encomenda de salgados",
            original_amount_cents=15000,
            due_date=date.today() + timedelta(days=15),
        )
    )
    assert debt.remaining_cents == 15000
    assert debt.status == DebtStatus.PENDING.value

    summary = cust_srv.get_customer_summary(customer.id)
    assert summary["current_debt_cents"] == 15000
    assert summary["total_purchases_cents"] == 15000
    assert summary["total_paid_cents"] == 0


def test_partial_and_full_payment(service_suite):
    cust_srv, debt_srv, pay_srv, _ = service_suite

    customer = cust_srv.create_customer(CustomerCreateSchema(name="Roberto Silva"))
    debt = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=customer.id,
            description="Café e pães",
            original_amount_cents=5000,  # R$ 50,00
        )
    )

    # 1. Pagamento parcial de R$ 20,00
    payments = pay_srv.register_payment(
        PaymentCreateSchema(
            customer_id=customer.id,
            debt_id=debt.id,
            amount_cents=2000,
            payment_method=PaymentMethod.PIX,
        )
    )
    assert len(payments) == 1
    assert payments[0].amount_cents == 2000

    summary = cust_srv.get_customer_summary(customer.id)
    assert summary["current_debt_cents"] == 3000
    assert summary["total_paid_cents"] == 2000

    # 2. Tentativa de pagar R$ 40,00 quando deve apenas R$ 30,00 -> DEVE FALHAR
    with pytest.raises(ValueError, match="superior ao saldo devedor"):
        pay_srv.register_payment(
            PaymentCreateSchema(
                customer_id=customer.id,
                debt_id=debt.id,
                amount_cents=4000,
                payment_method=PaymentMethod.CASH,
            )
        )

    # 3. Quitação restante de R$ 30,00
    pay_srv.register_payment(
        PaymentCreateSchema(
            customer_id=customer.id,
            debt_id=debt.id,
            amount_cents=3000,
            payment_method=PaymentMethod.CASH,
        )
    )

    summary_final = cust_srv.get_customer_summary(customer.id)
    assert summary_final["current_debt_cents"] == 0
    assert summary_final["total_paid_cents"] == 5000
    assert summary_final["open_debts_count"] == 0
    assert summary_final["paid_debts_count"] == 1


def test_payment_cancellation_and_reversal(service_suite):
    cust_srv, debt_srv, pay_srv, _ = service_suite

    customer = cust_srv.create_customer(CustomerCreateSchema(name="Juliana Dias"))
    debt = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=customer.id,
            description="Doces finos",
            original_amount_cents=8000,
        )
    )

    # Pagamento de R$ 80,00 (quitação)
    payments = pay_srv.register_payment(
        PaymentCreateSchema(
            customer_id=customer.id,
            debt_id=debt.id,
            amount_cents=8000,
            payment_method=PaymentMethod.CARD,
        )
    )
    payment = payments[0]

    summary_before = cust_srv.get_customer_summary(customer.id)
    assert summary_before["current_debt_cents"] == 0

    # Estorno / Cancelamento do pagamento
    cancelled = pay_srv.cancel_payment(payment.id, reason="Comprovante de cartão inválido")
    assert cancelled.is_cancelled is True
    assert cancelled.cancellation_reason == "Comprovante de cartão inválido"

    # Saldo deve ter retornado para R$ 80,00
    summary_after = cust_srv.get_customer_summary(customer.id)
    assert summary_after["current_debt_cents"] == 8000
    assert summary_after["total_paid_cents"] == 0


def test_dashboard_metrics(service_suite):
    cust_srv, debt_srv, pay_srv, dash_srv = service_suite

    # Cria cliente 1 em dia
    c1 = cust_srv.create_customer(CustomerCreateSchema(name="Cliente 1"))
    d1 = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=c1.id,
            description="Compra futura",
            original_amount_cents=10000,
            due_date=date.today() + timedelta(days=10),
        )
    )

    # Cria cliente 2 vencido (inadimplente)
    c2 = cust_srv.create_customer(CustomerCreateSchema(name="Cliente 2"))
    d2 = debt_srv.create_debt(
        DebtCreateSchema(
            customer_id=c2.id,
            description="Compra antiga",
            original_amount_cents=5000,
            due_date=date.today() - timedelta(days=5),
        )
    )

    # Pagamento parcial no cliente 1
    pay_srv.register_payment(
        PaymentCreateSchema(
            customer_id=c1.id,
            debt_id=d1.id,
            amount_cents=3000,
            payment_method=PaymentMethod.PIX,
        )
    )

    metrics = dash_srv.get_dashboard_metrics()
    assert metrics["total_customers"] == 2
    assert metrics["pending_debts_count"] == 2
    assert metrics["total_receivable_cents"] == 12000  # (10000 - 3000) + 5000
    assert metrics["total_overdue_cents"] == 5000
    assert metrics["overdue_debts_count"] == 1
    assert metrics["defaulters_count"] == 1
    assert metrics["received_this_month_cents"] == 3000
