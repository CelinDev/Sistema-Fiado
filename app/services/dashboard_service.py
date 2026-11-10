from datetime import date, datetime
from typing import Any, Dict, List

from app.database.connection import db_manager
from app.database.models import Customer, Debt, DebtStatus, Payment
from app.database.repositories import CustomerRepository, DebtRepository, PaymentRepository


class DashboardService:
    def __init__(self, db_session_factory=None):
        self.session_factory = db_session_factory or db_manager.session_scope

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calcula todos os indicadores diretamente a partir dos dados persistidos."""
        with self.session_factory() as session:
            cust_repo = CustomerRepository(session)
            debt_repo = DebtRepository(session)
            pay_repo = PaymentRepository(session)

            today = date.today()
            now = datetime.now()

            # 1. Total de clientes
            total_customers = cust_repo.count_total()

            # 2. Total a receber e quantidade de dívidas pendentes
            total_receivable_cents = debt_repo.sum_total_receivable_cents()
            pending_debts_count = debt_repo.count_pending_debts()

            # 3. Total vencido
            total_overdue_cents = debt_repo.sum_total_overdue_cents()
            overdue_debts = debt_repo.get_overdue_debts()
            overdue_debts_count = len(overdue_debts)

            # 4. Total recebido no mês atual
            received_this_month_cents = pay_repo.sum_payments_in_month(now.year, now.month)

            # 5. Clientes inadimplentes (com dívidas vencidas ativas)
            defaulter_customer_ids = {d.customer_id for d in overdue_debts}
            defaulters_count = len(defaulter_customer_ids)

            # 6. Histórico dos últimos 6 meses para visualização gráfica
            monthly_evolution = []
            for i in range(5, -1, -1):
                # Calcula ano e mês para cada um dos 6 meses anteriores
                m = now.month - i
                y = now.year
                while m <= 0:
                    m += 12
                    y -= 1
                month_cents = pay_repo.sum_payments_in_month(y, m)
                month_label = f"{m:02d}/{str(y)[2:]}"
                monthly_evolution.append({
                    "month": m,
                    "year": y,
                    "label": month_label,
                    "amount_cents": month_cents
                })

            return {
                "total_customers": total_customers,
                "pending_debts_count": pending_debts_count,
                "total_receivable_cents": total_receivable_cents,
                "total_overdue_cents": total_overdue_cents,
                "overdue_debts_count": overdue_debts_count,
                "received_this_month_cents": received_this_month_cents,
                "defaulters_count": defaulters_count,
                "monthly_evolution": monthly_evolution,
            }


dashboard_service = DashboardService()
