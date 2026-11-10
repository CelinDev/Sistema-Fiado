from typing import Callable
import flet as ft

from app.config.settings import settings
from app.services.report_service import report_service
from app.ui.theme.colors import AppColors


class ReportsPage:
    def __init__(self, page: ft.Page, navigate_to: Callable[[str, dict], None]):
        self.page = page
        self.navigate_to = navigate_to

    def build(self) -> ft.Control:
        def show_notification(msg: str, is_error: bool = False):
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=AppColors.DANGER if is_error else AppColors.SUCCESS,
            )
            self.page.snack_bar.open = True
            self.page.update()

        def export_customers_excel():
            try:
                path = report_service.export_customers_excel(only_with_debt=False)
                show_notification(f"Arquivo Excel gerado: {path.name}")
            except Exception as e:
                show_notification(f"Erro ao exportar: {e}", is_error=True)

        def export_debtors_excel():
            try:
                path = report_service.export_customers_excel(only_with_debt=True)
                show_notification(f"Relatório de Devedores gerado: {path.name}")
            except Exception as e:
                show_notification(f"Erro ao exportar: {e}", is_error=True)

        def export_overdue_pdf():
            try:
                path = report_service.export_overdue_debts_pdf()
                show_notification(f"Relatório PDF de Vencidos gerado: {path.name}")
            except Exception as e:
                show_notification(f"Erro ao exportar: {e}", is_error=True)

        def export_payments_excel():
            try:
                path = report_service.export_payments_excel()
                show_notification(f"Relatório de Pagamentos gerado: {path.name}")
            except Exception as e:
                show_notification(f"Erro ao exportar: {e}", is_error=True)

        def create_report_item(title: str, desc: str, icon: str, buttons: list) -> ft.Container:
            return ft.Container(
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(icon, color=AppColors.PRIMARY, size=24),
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    border_radius=8,
                                    padding=10,
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                                        ft.Text(desc, size=12, color=AppColors.TEXT_SECONDARY),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            spacing=12,
                        ),
                        ft.Row(controls=buttons, spacing=8),
                    ],
                ),
                bgcolor=AppColors.BG_CARD,
                border=ft.border.all(1, AppColors.BORDER),
                border_radius=10,
                padding=16,
            )

        reports_list = ft.Column(
            controls=[
                create_report_item(
                    title="Relatório de Todos os Clientes",
                    desc="Lista completa com dados cadastrais, total de compras e saldo devedor",
                    icon=ft.Icons.PEOPLE_ALT_OUTLINED,
                    buttons=[
                        ft.ElevatedButton("Exportar Excel", icon=ft.Icons.TABLE_CHART, bgcolor=AppColors.PRIMARY, color=ft.Colors.WHITE, on_click=lambda e: export_customers_excel()),
                    ],
                ),
                create_report_item(
                    title="Relatório de Clientes Devedores",
                    desc="Filtro específico contendo apenas clientes que possuem saldo pendente",
                    icon=ft.Icons.MONEY_OFF,
                    buttons=[
                        ft.ElevatedButton("Exportar Excel", icon=ft.Icons.TABLE_CHART, bgcolor=AppColors.PRIMARY, color=ft.Colors.WHITE, on_click=lambda e: export_debtors_excel()),
                    ],
                ),
                create_report_item(
                    title="Relatório de Fiados Vencidos (Inadimplência)",
                    desc="Lista detalhada com prazos expirados, contato dos clientes e valores pendentes",
                    icon=ft.Icons.WARNING_AMBER_ROUNDED,
                    buttons=[
                        ft.ElevatedButton("Gerar PDF", icon=ft.Icons.PICTURE_AS_PDF, bgcolor=AppColors.DANGER, color=ft.Colors.WHITE, on_click=lambda e: export_overdue_pdf()),
                    ],
                ),
                create_report_item(
                    title="Relatório de Pagamentos Recebidos",
                    desc="Histórico completo de recebimentos, formas de pagamento e auditoria",
                    icon=ft.Icons.PAYMENTS_OUTLINED,
                    buttons=[
                        ft.ElevatedButton("Exportar Excel", icon=ft.Icons.TABLE_CHART, bgcolor=AppColors.PRIMARY, color=ft.Colors.WHITE, on_click=lambda e: export_payments_excel()),
                    ],
                ),
                create_report_item(
                    title="Extrato Individual do Cliente",
                    desc="Demonstrativo completo de compras e pagamentos por cliente em PDF",
                    icon=ft.Icons.ASSIGNMENT_IND_OUTLINED,
                    buttons=[
                        ft.OutlinedButton("Selecionar Cliente", icon=ft.Icons.SEARCH, on_click=lambda e: self.navigate_to("customers", {})),
                    ],
                ),
            ],
            spacing=12,
        )

        return ft.ListView(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Central de Relatórios e Exportações", size=24, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                        ft.Text(f"Os arquivos gerados são salvos em: {settings.export_dir}", size=13, color=AppColors.TEXT_SECONDARY),
                    ],
                    spacing=2,
                ),
                ft.Container(height=16),
                reports_list,
            ],
            expand=True,
            padding=24,
        )
