import os
from pathlib import Path
import pytest

from app.config.settings import settings
from app.database.connection import DatabaseManager
from app.database.migrations import run_migrations
from app.services.backup_service import BackupService
from app.services.customer_service import CustomerService
from app.services.debt_service import DebtService
from app.validators.schemas import CustomerCreateSchema, DebtCreateSchema


def test_backup_validation_and_restore(tmp_path, monkeypatch):
    test_data_dir = tmp_path / "data"
    test_backup_dir = tmp_path / "backups"
    test_data_dir.mkdir(parents=True)
    test_backup_dir.mkdir(parents=True)

    db_file = test_data_dir / "fiado_manager.db"

    # Patch settings to point to isolated temp dirs
    monkeypatch.setattr(settings, "database_path", db_file)
    monkeypatch.setattr(settings, "database_dir", test_data_dir)
    monkeypatch.setattr(settings, "backup_dir", test_backup_dir)

    db_mgr = DatabaseManager(f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setattr("app.database.connection.db_manager", db_mgr)

    run_migrations(db_mgr.engine)

    cust_srv = CustomerService(db_mgr.session_scope)
    debt_srv = DebtService(db_mgr.session_scope)
    backup_srv = BackupService()

    # Inserir dados antes do backup
    c = cust_srv.create_customer(CustomerCreateSchema(name="Cliente Seguro", phone="11999991111"))
    debt_srv.create_debt(
        DebtCreateSchema(customer_id=c.id, description="Compra antes do backup", original_amount_cents=10000)
    )

    # 1. Gerar backup
    backup_path = backup_srv.create_backup(custom_dest_dir=test_backup_dir)
    assert backup_path.exists()
    assert backup_path.stat().st_size > 0

    # 2. Validar integridade do backup
    is_valid, msg = backup_srv.validate_backup_file(backup_path)
    assert is_valid is True

    # 3. Alterar os dados atuais (adicionar outro cliente)
    cust_srv.create_customer(CustomerCreateSchema(name="Cliente Criado Depois"))
    assert len(cust_srv.search_customers()) == 2

    # 4. Restaurar o backup
    backup_srv.restore_backup(backup_path)

    # 5. Reinicializar a conexão e verificar persistência do estado restaurado
    new_db_mgr = DatabaseManager(f"sqlite:///{db_file.as_posix()}")
    new_cust_srv = CustomerService(new_db_mgr.session_scope)

    restored_customers = new_cust_srv.search_customers()
    assert len(restored_customers) == 1
    assert restored_customers[0].name == "Cliente Seguro"
