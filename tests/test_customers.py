import pytest
from app.database.connection import DatabaseManager
from app.database.migrations import run_migrations
from app.services.customer_service import CustomerService
from app.validators.schemas import CustomerCreateSchema, CustomerUpdateSchema


@pytest.fixture
def cust_service(tmp_path):
    test_db = tmp_path / "test_cust.db"
    db_mgr = DatabaseManager(f"sqlite:///{test_db.as_posix()}")
    run_migrations(db_mgr.engine)
    return CustomerService(db_mgr.session_scope)


def test_customer_crud(cust_service):
    # 1. Cadastro
    data = CustomerCreateSchema(
        name="Antônio Carlos",
        phone="11977776666",
        cpf="11122233344",
        address="Av. Principal, 500",
        notes="Comprador frequente",
    )
    customer = cust_service.create_customer(data)
    assert customer.id is not None
    assert customer.name == "Antônio Carlos"
    assert customer.is_active is True

    # 2. Consulta
    found = cust_service.get_customer(customer.id)
    assert found is not None
    assert found.cpf == "11122233344"

    # 3. Busca por texto e acesso às propriedades calculadas fora da sessão
    results = cust_service.search_customers("Antônio")
    assert len(results) >= 1
    assert results[0].id == customer.id
    assert results[0].current_debt_cents == 0
    assert results[0].total_purchases_cents == 0
    assert results[0].total_paid_cents == 0

    # 4. Edição
    updated = cust_service.update_customer(
        customer.id,
        CustomerUpdateSchema(name="Antônio Carlos Ferreira", phone="11911112222")
    )
    assert updated.name == "Antônio Carlos Ferreira"
    assert updated.phone == "11911112222"


def test_customer_cpf_validation_and_duplicate(cust_service):
    # CPF inválido (menos de 11 dígitos)
    with pytest.raises(ValueError):
        CustomerCreateSchema(name="Teste", cpf="123")

    # Primeiro cliente com CPF válido
    cust_service.create_customer(CustomerCreateSchema(name="Cliente 1", cpf="99988877766"))

    # Segundo cliente tentando usar o mesmo CPF
    with pytest.raises(ValueError, match="Já existe um cliente cadastrado com este CPF"):
        cust_service.create_customer(CustomerCreateSchema(name="Cliente 2", cpf="99988877766"))


def test_customer_delete_only_when_settled(cust_service, tmp_path):
    from app.services.debt_service import DebtService
    from app.validators.schemas import DebtCreateSchema

    # Cria cliente sem débitos -> deve permitir exclusão
    c1 = cust_service.create_customer(CustomerCreateSchema(name="Cliente Quitado", credit_limit_cents=20000))
    assert c1.credit_limit_cents == 20000
    cust_service.delete_customer(c1.id)
    assert cust_service.get_customer(c1.id) is None

    # Cria cliente com débitos em aberto -> exclusão deve falhar
    c2 = cust_service.create_customer(CustomerCreateSchema(name="Cliente Devedor"))
    debt_service = DebtService(cust_service.session_factory)
    debt_service.create_debt(DebtCreateSchema(customer_id=c2.id, description="Pães", original_amount_cents=1500))

    with pytest.raises(ValueError, match="possui débitos em aberto"):
        cust_service.delete_customer(c2.id)
