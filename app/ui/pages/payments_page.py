from typing import Callable
import flet as ft

from app.database.models import Payment
from app.services.payment_service import payment_service
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.theme.colors import AppColors
from app.utils.formatters import format_currency, format_datetime


class PaymentsPage:
    def __init__(self, page: ft.Page, navigate_to: Callable[[str, dict], None]):
        self.page = page
        self.navigate_to = navigate_to
        self.search_term = ""

    def build(self) -> ft.Control:
        search_field = ft.TextField(
            hint_text="Buscar pagamentos por nome do cliente ou forma...",
            prefix_icon=ft.Icons.SEARCH,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            on_change=self._on_search_change,
            expand=True,
            height=42,
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
                                ft.Text("Histórico Geral de Pagamentos", size=24, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                                ft.Text("Registro de todas as entradas, baixas e estornos com auditoria", size=13, color=AppColors.TEXT_SECONDARY),
                            ],
                            spacing=2,
                        ),
                    ],
                ),
                ft.Container(height=16),
                ft.Container(
                    content=ft.Row(controls=[search_field]),
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
        payments = payment_service.get_recent_payments(limit=100)

        if self.search_term.strip():
            st = self.search_term.strip().lower()
            payments = [
                p for p in payments
                if (p.customer and st in p.customer.name.lower()) or st in p.payment_method.lower()
            ]

        rows = []
        for p in payments:
            is_canc = p.is_cancelled

            status_badge = ft.Container(
                content=ft.Text(
                    "ESTORNADO" if is_canc else "CONFIRMADO",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.DANGER if is_canc else AppColors.SUCCESS,
                ),
                bgcolor=AppColors.DANGER_LIGHT if is_canc else AppColors.SUCCESS_LIGHT,
                border_radius=4,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            )

            actions = ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.REPLAY,
                        tooltip="Estornar Pagamento",
                        icon_color=AppColors.DANGER if not is_canc else AppColors.BORDER,
                        disabled=is_canc,
                        icon_size=20,
                        on_click=lambda e, pid=p.id: self._confirm_cancel_payment(pid),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.PERSON,
                        tooltip="Ver Cliente",
                        icon_color=AppColors.INFO,
                        icon_size=20,
                        on_click=lambda e, cid=p.customer_id: self.navigate_to("customer_detail", {"customer_id": cid}),
                    ),
                ],
                spacing=2,
            )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(format_datetime(p.payment_date))),
                        ft.DataCell(
                            ft.TextButton(
                                p.customer.name if p.customer else f"Cliente #{p.customer_id}",
                                on_click=lambda e, cid=p.customer_id: self.navigate_to("customer_detail", {"customer_id": cid}),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                format_currency(p.amount_cents),
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_MUTED if is_canc else AppColors.SUCCESS,
                                size=14,
                            )
                        ),
                        ft.DataCell(ft.Text(p.payment_method)),
                        ft.DataCell(ft.Text(f"Fiado #{p.debt_id}" if p.debt_id else "Abatimento Geral")),
                        ft.DataCell(status_badge),
                        ft.DataCell(actions),
                    ]
                )
            )

        self.table_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Data / Hora")),
                            ft.DataColumn(ft.Text("Cliente")),
                            ft.DataColumn(ft.Text("Valor Recebido")),
                            ft.DataColumn(ft.Text("Forma")),
                            ft.DataColumn(ft.Text("Referência")),
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
                                ft.Icon(ft.Icons.PAYMENTS_OUTLINED, size=48, color=AppColors.TEXT_MUTED),
                                ft.Text("Nenhum pagamento encontrado.", color=AppColors.TEXT_SECONDARY),
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

    def _confirm_cancel_payment(self, payment_id: int):
        def do_cancel():
            try:
                payment_service.cancel_payment(payment_id, reason="Estorno solicitado na tela de pagamentos")
                self.page.snack_bar = ft.SnackBar(content=ft.Text("Pagamento estornado com sucesso."), bgcolor=AppColors.SUCCESS)
                self.page.snack_bar.open = True
                self.refresh()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(str(ex)), bgcolor=AppColors.DANGER)
                self.page.snack_bar.open = True
                self.page.update()

        ConfirmDialog.show(
            self.page,
            title="Estornar Pagamento",
            message="O estorno devolverá o valor ao saldo devedor do cliente e ficará registrado no histórico. Deseja prosseguir?",
            is_destructive=True,
            on_confirm=do_cancel,
        )

    def _on_search_change(self, e):
        self.search_term = e.control.value
        self._render_table()
        self.page.update()

    def refresh(self):
        self.navigate_to("payments", {})
