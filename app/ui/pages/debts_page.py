from typing import Callable
import flet as ft

from app.database.models import DebtStatus
from app.services.debt_service import debt_service
from app.ui.components.quick_debt_modal import QuickDebtModal
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.dialogs.payment_dialog import PaymentDialog
from app.ui.theme.colors import AppColors
from app.utils.formatters import format_currency, format_date


class DebtsPage:
    def __init__(self, page: ft.Page, navigate_to: Callable[[str, dict], None]):
        self.page = page
        self.navigate_to = navigate_to
        self.status_filter = "ALL"
        self.search_term = ""

    def build(self) -> ft.Control:
        debt_service.refresh_overdue_statuses()

        search_field = ft.TextField(
            hint_text="Filtrar por descrição ou nome do cliente...",
            prefix_icon=ft.Icons.SEARCH,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            on_change=self._on_search_change,
            expand=True,
            height=42,
        )

        status_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("ALL", "Todos os Status"),
                ft.dropdown.Option(DebtStatus.PENDING.value, "Pendentes"),
                ft.dropdown.Option(DebtStatus.PARTIALLY_PAID.value, "Parcialmente Pagos"),
                ft.dropdown.Option(DebtStatus.OVERDUE.value, "Vencidos"),
                ft.dropdown.Option(DebtStatus.PAID.value, "Quitados"),
                ft.dropdown.Option(DebtStatus.CANCELLED.value, "Cancelados"),
            ],
            value=self.status_filter,
            width=220,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            on_change=self._on_status_change,
        )

        btn_new_debt = ft.ElevatedButton(
            "NOVO FIADO",
            icon=ft.Icons.ADD_SHOPPING_CART,
            bgcolor=AppColors.PRIMARY,
            color=ft.Colors.WHITE,
            height=42,
            on_click=lambda e: QuickDebtModal.show(self.page, on_success=self.refresh),
        )

        self.table_container = ft.Container()
        self._render_table()

        return ft.ListView(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text("Gerenciamento de Fiados e Dívidas", size=24, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                                ft.Text("Consulte todos os lançamentos, vencimentos e situações financeiras", size=13, color=AppColors.TEXT_SECONDARY),
                            ],
                            spacing=2,
                        ),
                        btn_new_debt,
                    ],
                ),
                ft.Container(height=16),
                ft.Container(
                    content=ft.Row(
                        controls=[search_field, status_dropdown],
                        spacing=12,
                    ),
                    bgcolor=AppColors.BG_CARD,
                    border=ft.border.all(1, AppColors.BORDER),
                    border_radius=8,
                    padding=12,
                ),
                ft.Container(height=16),
                self.table_container,
            ],
            expand=True,
            padding=24,
        )

    def _render_table(self):
        debts = debt_service.get_all_active_debts()

        if self.status_filter != "ALL":
            debts = [d for d in debts if d.status == self.status_filter]

        if self.search_term.strip():
            st = self.search_term.strip().lower()
            debts = [
                d for d in debts
                if st in d.description.lower() or (d.customer and st in d.customer.name.lower())
            ]

        rows = []
        for d in debts:
            # Badge de status
            badge_color = AppColors.WARNING
            badge_bg = AppColors.WARNING_LIGHT
            if d.status == DebtStatus.PAID.value:
                badge_color = AppColors.SUCCESS
                badge_bg = AppColors.SUCCESS_LIGHT
            elif d.status == DebtStatus.OVERDUE.value or d.is_overdue:
                badge_color = AppColors.DANGER
                badge_bg = AppColors.DANGER_LIGHT
            elif d.status == DebtStatus.CANCELLED.value:
                badge_color = AppColors.TEXT_MUTED
                badge_bg = AppColors.BG_MAIN

            status_badge = ft.Container(
                content=ft.Text(
                    d.status,
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=badge_color,
                ),
                bgcolor=badge_bg,
                border_radius=4,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            )

            action_buttons = ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.PAYMENTS_OUTLINED,
                        tooltip="Receber Pagamento",
                        icon_color=AppColors.SUCCESS if d.remaining_cents > 0 else AppColors.BORDER,
                        disabled=d.remaining_cents == 0 or d.status == DebtStatus.CANCELLED.value,
                        icon_size=20,
                        on_click=lambda e, cid=d.customer_id, did=d.id: PaymentDialog.show(
                            self.page, customer_id=cid, debt_id=did, on_success=self.refresh
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.PERSON,
                        tooltip="Ver Perfil do Cliente",
                        icon_color=AppColors.INFO,
                        icon_size=20,
                        on_click=lambda e, cid=d.customer_id: self.navigate_to("customer_detail", {"customer_id": cid}),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CANCEL_OUTLINED,
                        tooltip="Cancelar Dívida",
                        icon_color=AppColors.DANGER if d.remaining_cents > 0 else AppColors.BORDER,
                        disabled=d.remaining_cents == 0 or d.status == DebtStatus.CANCELLED.value,
                        icon_size=20,
                        on_click=lambda e, did=d.id: self._confirm_cancel_debt(did),
                    ),
                ],
                spacing=2,
            )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.TextButton(
                                d.customer.name if d.customer else f"Cliente #{d.customer_id}",
                                on_click=lambda e, cid=d.customer_id: self.navigate_to("customer_detail", {"customer_id": cid}),
                            )
                        ),
                        ft.DataCell(ft.Text(d.description)),
                        ft.DataCell(ft.Text(format_date(d.created_at))),
                        ft.DataCell(
                            ft.Text(
                                format_date(d.due_date),
                                color=AppColors.DANGER if d.is_overdue else AppColors.TEXT_PRIMARY,
                                weight=ft.FontWeight.BOLD if d.is_overdue else ft.FontWeight.NORMAL,
                            )
                        ),
                        ft.DataCell(ft.Text(format_currency(d.original_amount_cents))),
                        ft.DataCell(
                            ft.Text(
                                format_currency(d.remaining_cents),
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.DANGER if d.remaining_cents > 0 else AppColors.SUCCESS,
                            )
                        ),
                        ft.DataCell(status_badge),
                        ft.DataCell(action_buttons),
                    ]
                )
            )

        self.table_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Cliente")),
                            ft.DataColumn(ft.Text("Descrição")),
                            ft.DataColumn(ft.Text("Data")),
                            ft.DataColumn(ft.Text("Vencimento")),
                            ft.DataColumn(ft.Text("Valor Original")),
                            ft.DataColumn(ft.Text("Saldo Restante")),
                            ft.DataColumn(ft.Text("Situação")),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=rows,
                        border=ft.border.all(1, AppColors.BORDER),
                        border_radius=8,
                        heading_row_color=AppColors.BG_MAIN,
                    ) if rows else ft.Container(
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.RECEIPT_LONG, size=48, color=AppColors.TEXT_MUTED),
                                ft.Text("Nenhum fiado encontrado para os filtros selecionados.", color=AppColors.TEXT_SECONDARY),
                            ],
                        ),
                        alignment=ft.alignment.center,
                        padding=40,
                    ),
                ],
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=8,
            padding=16,
        )

    def _confirm_cancel_debt(self, debt_id: int):
        def do_cancel():
            try:
                debt_service.cancel_debt(debt_id, reason="Cancelado pelo operador na listagem geral")
                self.page.snack_bar = ft.SnackBar(content=ft.Text("Dívida cancelada com sucesso."), bgcolor=AppColors.SUCCESS)
                self.page.snack_bar.open = True
                self.refresh()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(str(ex)), bgcolor=AppColors.DANGER)
                self.page.snack_bar.open = True
                self.page.update()

        ConfirmDialog.show(
            self.page,
            title="Cancelar Fiado",
            message="Tem certeza que deseja cancelar este fiado? Esta operação registrará auditoria.",
            is_destructive=True,
            on_confirm=do_cancel,
        )

    def _on_search_change(self, e):
        self.search_term = e.control.value
        self._render_table()
        self.page.update()

    def _on_status_change(self, e):
        self.status_filter = e.control.value
        self._render_table()
        self.page.update()

    def refresh(self):
        self.navigate_to("debts", {})
