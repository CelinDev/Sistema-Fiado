import pytest
from app.database.connection import DatabaseManager
from app.database.migrations import run_migrations
from app.database.models import PaymentMethod
from app.services.customer_service import CustomerService
from app.services.debt_service import DebtService
from app.services.payment_service import PaymentService
from app.services.report_service import ReportService
from app.validators.schemas import CustomerCreateSchema, DebtCreateSchema, PaymentCreateSchema


@pytest.fixture
def report_suite(tmp_path):
    test_db = tmp_path / "test_rep.db"
    db_mgr = DatabaseManager(f"sqlite:///{test_db.as_posix()}")
    run_migrations(db_mgr.engine)

    cust_srv = CustomerService(db_mgr.session_scope)
    debt_srv = DebtService(db_mgr.session_scope)
    pay_srv = PaymentService(db_mgr.session_scope)
    rep_srv = ReportService(db_mgr.session_scope)

    return cust_srv, debt_srv, pay_srv, rep_srv


def test_customer_statement_pdf_generation(report_suite):
    cust_srv, debt_srv, pay_srv, rep_srv = report_suite

    customer = cust_srv.create_customer(CustomerCreateSchema(name="Extrato Teste", phone="11999990000"))
    debt = debt_srv.create_debt(
        DebtCreateSchema(customer_id=customer.id, description="Compra para teste de PDF", original_amount_cents=12000)
    )
    pay_srv.register_payment(
        PaymentCreateSchema(customer_id=customer.id, debt_id=debt.id, amount_cents=5000, payment_method=PaymentMethod.PIX)
    )

    pdf_file = rep_srv.generate_customer_statement_pdf(customer.id)
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 1000  # PDF gerado com conteúdo


def test_customers_excel_export(report_suite):
    cust_srv, debt_srv, _, rep_srv = report_suite

    c = cust_srv.create_customer(CustomerCreateSchema(name="Cliente Planilha", cpf="55544433322"))
    debt_srv.create_debt(
        DebtCreateSchema(customer_id=c.id, description="Itens gerais", original_amount_cents=7500)
    )

    excel_file = rep_srv.export_customers_excel()
    assert excel_file.exists()
    assert excel_file.stat().st_size > 1000


def test_overdue_pdf_export(report_suite):
    _, _, _, rep_srv = report_suite
    pdf = rep_srv.export_overdue_debts_pdf()
    assert pdf.exists()
    assert pdf.stat().st_size > 500


def test_thermal_receipt_generation(report_suite):
    cust_srv, debt_srv, pay_srv, rep_srv = report_suite

    customer = cust_srv.create_customer(CustomerCreateSchema(name="Cupom Teste", phone="11988887777", credit_limit_cents=10000))
    debt = debt_srv.create_debt(
        DebtCreateSchema(customer_id=customer.id, description="1x Bolo, 2x Sucos", original_amount_cents=2500)
    )

    # Cupom de Fiado (80mm)
    thermal_debt_pdf = rep_srv.generate_thermal_receipt_pdf("DEBT", debt.id, paper_width_mm=80)
    assert thermal_debt_pdf.exists()
    assert thermal_debt_pdf.stat().st_size > 500

    # Cupom de Pagamento (58mm)
    payments = pay_srv.register_payment(
        PaymentCreateSchema(customer_id=customer.id, debt_id=debt.id, amount_cents=1500, payment_method=PaymentMethod.CASH)
    )
    thermal_pay_pdf = rep_srv.generate_thermal_receipt_pdf("PAYMENT", payments[0].id, paper_width_mm=58)
    assert thermal_pay_pdf.exists()
    assert thermal_pay_pdf.stat().st_size > 500
