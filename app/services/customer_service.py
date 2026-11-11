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

            # Validação para importação / criação: evitar duplicidade exata de cliente com mesmo nome e telefone ou mesmo CPF
            if data.cpf:
                existing_cpf = repo.find_by_cpf(data.cpf)
                if existing_cpf:
                    raise ValueError(f"Já existe um cliente cadastrado com este CPF: {existing_cpf.name}")

            # Verifica se já existe cliente com o mesmo nome (aviso / checagem)
            existing_name = repo.find_by_exact_name(data.name)
            if existing_name:
                if (data.phone and existing_name.phone == data.phone) or (not data.phone and not existing_name.phone):
                    raise ValueError(f"Cliente '{data.name}' já está cadastrado no sistema.")
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

    def import_customers_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Importa clientes a partir de um arquivo Excel (.xlsx) ou CSV.
        Retorna o resumo com contagem de importados, ignorados e erros.
        """
        import csv
        from pathlib import Path
        import openpyxl
        from app.utils.formatters import clean_digits, parse_currency_to_cents

        path = Path(file_path)
        if not path.is_file():
            raise ValueError("Arquivo de importação não encontrado.")

        created_count = 0
        skipped_count = 0
        errors = []

        rows_data = []

        if path.suffix.lower() in [".xlsx", ".xls"]:
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            headers = None
            for row in ws.iter_rows(values_only=True):
                if not any(row):
                    continue
                if headers is None:
                    headers = [str(c).strip().lower() if c else "" for c in row]
                    continue
                row_dict = {}
                for idx, h in enumerate(headers):
                    if idx < len(row):
                        row_dict[h] = str(row[idx]).strip() if row[idx] is not None else ""
                rows_data.append(row_dict)
        else:
            # CSV
            with open(path, mode="r", encoding="utf-8-sig", errors="replace") as f:
                # Detecta delimitador (vírgula ou ponto e vírgula)
                sample = f.read(2048)
                f.seek(0)
                delimiter = ";" if ";" in sample else ","
                reader = csv.DictReader(f, delimiter=delimiter)
                for r in reader:
                    normalized = {k.strip().lower() if k else "": v.strip() if v else "" for k, v in r.items()}
                    rows_data.append(normalized)

        for line_idx, r in enumerate(rows_data, start=2):
            # Identificação flexível de colunas
            name = r.get("nome") or r.get("nome completo") or r.get("cliente") or r.get("name") or ""
            phone = r.get("telefone") or r.get("whatsapp") or r.get("fone") or r.get("phone") or ""
            cpf = r.get("cpf") or r.get("documento") or ""
            address = r.get("endereco") or r.get("endereço") or r.get("address") or ""
            notes = r.get("observacoes") or r.get("observações") or r.get("notes") or ""
            limit_raw = r.get("limite") or r.get("limite de credito") or r.get("limite de crédito") or ""

            if not name:
                continue

            # Converte limite se informado
            credit_limit_cents = None
            if limit_raw:
                try:
                    credit_limit_cents = parse_currency_to_cents(limit_raw)
                    if credit_limit_cents <= 0:
                        credit_limit_cents = None
                except Exception:
                    credit_limit_cents = None

            try:
                schema = CustomerCreateSchema(
                    name=name,
                    phone=clean_digits(phone) or None,
                    cpf=clean_digits(cpf) or None,
                    address=address or None,
                    notes=notes or None,
                    credit_limit_cents=credit_limit_cents,
                    is_active=True,
                )
                self.create_customer(schema)
                created_count += 1
            except Exception as e:
                skipped_count += 1
                errors.append(f"Linha {line_idx} ({name}): {str(e)}")

        return {
            "created": created_count,
            "skipped": skipped_count,
            "errors": errors[:10],  # Primeiros 10 para exibição limpa
        }


customer_service = CustomerService()
