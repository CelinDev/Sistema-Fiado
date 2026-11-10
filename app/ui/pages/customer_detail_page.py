from typing import Callable
import flet as ft

from app.database.models import DebtStatus
from app.services.customer_service import customer_service
from app.services.debt_service import debt_service
from app.services.payment_service import payment_service
from app.services.report_service import report_service
from app.ui.components.quick_debt_modal import QuickDebtModal
from app.ui.components.stat_card import create_stat_card
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.dialogs.customer_dialog import CustomerDialog
from app.ui.dialogs.payment_dialog import PaymentDialog
from app.ui.theme.colors import AppColors
from app.utils.formatters import (
    format_cpf,
    format_currency,
    format_date,
    format_datetime,
    format_phone,
)


class CustomerDetailPage:
    def __init__(self, page: ft.Page, customer_id: int, navigate_to: Callable[[str, dict], None]):
        self.page = page
        self.customer_id = customer_id
        self.navigate_to = navigate_to

    def build(self) -> ft.Control:
        customer = customer_service.get_customer(self.customer_id)
        if not customer:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Cliente não encontrado.", size=18, color=AppColors.DANGER),
                        ft.ElevatedButton("Voltar para Clientes", on_click=lambda e: self.navigate_to("customers", {})),
                    ]
                ),
                padding=24,
            )

        summary = customer_service.get_customer_summary(self.customer_id)

        # 1. Barra de Ações Superior
        top_bar = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="Voltar para Lista de Clientes",
                            on_click=lambda e: self.navigate_to("customers", {}),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(customer.name, size=22, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                                ft.Text(
                                    f"Cadastrado em {format_date(customer.created_at)} • Status: {'Ativo' if customer.is_active else 'Inativo'}",
                                    size=12,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                            spacing=1,
                        ),
                    ],
                    spacing=6,
                ),
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "Extrato PDF",
                            icon=ft.Icons.PICTURE_AS_PDF,
                            on_click=lambda e: self._generate_statement_pdf(),
                        ),
                        ft.OutlinedButton(
                            "Cupom 80mm",
                            icon=ft.Icons.PRINT,
                            on_click=lambda e: self._print_thermal_summary(80),
                        ),
                        ft.OutlinedButton(
                            "Editar Cadastro",
                            icon=ft.Icons.EDIT,
                            on_click=lambda e: CustomerDialog.show(self.page, customer=customer, on_saved=lambda sc: self.refresh()),
                        ),
                        ft.ElevatedButton(
                            "Novo Fiado",
                            icon=ft.Icons.ADD,
                            bgcolor=AppColors.PRIMARY,
                            color=ft.Colors.WHITE,
                            on_click=lambda e: QuickDebtModal.show(self.page, preselected_customer_id=customer.id, on_success=self.refresh),
                        ),
                        ft.ElevatedButton(
                            "Receber Pagamento",
                            icon=ft.Icons.PAYMENTS,
                            bgcolor=AppColors.SUCCESS,
                            color=ft.Colors.WHITE,
                            disabled=summary["current_debt_cents"] == 0,
                            on_click=lambda e: PaymentDialog.show(self.page, customer_id=customer.id, on_success=self.refresh),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            tooltip="Excluir Cliente (Apenas se Quitado)" if summary["current_debt_cents"] == 0 else "Bloqueado: Cliente com débitos pendentes",
                            icon_color=AppColors.DANGER if summary["current_debt_cents"] == 0 else AppColors.BORDER,
                            disabled=summary["current_debt_cents"] > 0,
                            on_click=lambda e: self._confirm_delete_customer(customer.id, customer.name),
                        ),
                    ],
                    spacing=8,
                ),
            ],
        )

        # 2. Informações Cadastrais e Indicadores
        profile_card = ft.Container(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("DADOS CADASTRAIS", size=12, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_SECONDARY),
                            ft.Text(f"Telefone: {format_phone(customer.phone) if customer.phone else '-'}", size=13),
                            ft.Text(f"CPF: {format_cpf(customer.cpf) if customer.cpf else '-'}", size=13),
                            ft.Text(f"Endereço: {customer.address or '-'}", size=13),
                            ft.Text(
                                f"Limite de Crédito: {format_currency(customer.credit_limit_cents) if customer.credit_limit_cents else 'Sem limite definido'}",
                                size=13,
                                weight=ft.FontWeight.W_600 if customer.credit_limit_cents else ft.FontWeight.NORMAL,
                                color=AppColors.SECONDARY if customer.credit_limit_cents else AppColors.TEXT_SECONDARY,
                            ),
                            ft.Text(f"Observações: {customer.notes or '-'}", size=13, italic=True),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Row(
                        controls=[
                            create_stat_card(
                                title="SALDO DEVEDOR ATUAL",
                                value=format_currency(summary["current_debt_cents"]),
                                icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                                icon_color=AppColors.DANGER if summary["current_debt_cents"] > 0 else AppColors.SUCCESS,
                                bg_icon_color=AppColors.DANGER_LIGHT if summary["current_debt_cents"] > 0 else AppColors.SUCCESS_LIGHT,
                                width=210,
                            ),
                            create_stat_card(
                                title="TOTAL DE COMPRAS",
                                value=format_currency(summary["total_purchases_cents"]),
                                icon=ft.Icons.SHOPPING_BAG_OUTLINED,
                                icon_color=AppColors.INFO,
                                bg_icon_color="#E0F2FE",
                                width=210,
                            ),
                            create_stat_card(
                                title="TOTAL JÁ PAGO",
                                value=format_currency(summary["total_paid_cents"]),
                                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                                icon_color=AppColors.SUCCESS,
                                bg_icon_color=AppColors.SUCCESS_LIGHT,
                                width=210,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=12,
            padding=18,
        )

        # 3. Dívidas em Aberto
        open_debts = [d for d in customer.debts if d.status != DebtStatus.CANCELLED.value and d.remaining_cents > 0]
        open_rows = []
        for d in open_debts:
            open_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(format_date(d.created_at))),
                        ft.DataCell(ft.Text(d.description, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(format_currency(d.original_amount_cents))),
                        ft.DataCell(
                            ft.Text(
                                format_currency(d.remaining_cents),
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.DANGER if d.is_overdue else AppColors.TEXT_PRIMARY,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                format_date(d.due_date),
                                color=AppColors.DANGER if d.is_overdue else AppColors.TEXT_SECONDARY,
                                weight=ft.FontWeight.BOLD if d.is_overdue else ft.FontWeight.NORMAL,
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton(
                                        "Pagar",
                                        height=28,
                                        bgcolor=AppColors.SUCCESS,
                                        color=ft.Colors.WHITE,
                                        on_click=lambda e, did=d.id: PaymentDialog.show(
                                            self.page, customer_id=customer.id, debt_id=did, on_success=self.refresh
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.PRINT,
                                        tooltip="Imprimir Cupom Térmico (80mm/58mm)",
                                        icon_color=AppColors.SECONDARY,
                                        icon_size=18,
                                        on_click=lambda e, did=d.id: self._print_thermal_debt(did),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.CANCEL_OUTLINED,
                                        tooltip="Cancelar Fiado",
                                        icon_color=AppColors.DANGER,
                                        icon_size=18,
                                        on_click=lambda e, did=d.id: self._confirm_cancel_debt(did),
                                    ),
                                ],
                                spacing=4,
                            )
                        ),
                    ]
                )
            )

        open_debts_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Dívidas em Aberto ({len(open_debts)})", size=16, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Data Compra")),
                            ft.DataColumn(ft.Text("Descrição")),
                            ft.DataColumn(ft.Text("Valor Original")),
                            ft.DataColumn(ft.Text("Saldo Restante")),
                            ft.DataColumn(ft.Text("Vencimento")),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=open_rows,
                        border=ft.border.all(1, AppColors.BORDER),
                        border_radius=8,
                    ) if open_rows else ft.Text("Nenhuma dívida em aberto. Cliente em dia!", color=AppColors.SUCCESS, italic=True),
                ],
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=12,
            padding=18,
        )

        # 4. Histórico Cronológico de Pagamentos
        payments = sorted(customer.payments, key=lambda p: p.payment_date, reverse=True)
        pay_rows = []
        for p in payments:
            pay_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(format_datetime(p.payment_date))),
                        ft.DataCell(
                            ft.Text(
                                format_currency(p.amount_cents),
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_MUTED if p.is_cancelled else AppColors.SUCCESS,
                            )
                        ),
                        ft.DataCell(ft.Text(p.payment_method)),
                        ft.DataCell(ft.Text(f"Fiado #{p.debt_id}" if p.debt_id else "Abatimento Geral")),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    "ESTORNADO" if p.is_cancelled else "CONFIRMADO",
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.DANGER if p.is_cancelled else AppColors.SUCCESS,
                                ),
                                bgcolor=AppColors.DANGER_LIGHT if p.is_cancelled else AppColors.SUCCESS_LIGHT,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                border_radius=4,
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.PRINT,
                                        tooltip="Imprimir Cupom Térmico (80mm/58mm)",
                                        icon_color=AppColors.SECONDARY,
                                        icon_size=18,
                                        on_click=lambda e, pid=p.id: self._print_thermal_payment(pid),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.REPLAY,
                                        tooltip="Estornar Pagamento",
                                        icon_color=AppColors.DANGER,
                                        disabled=p.is_cancelled,
                                        icon_size=18,
                                        on_click=lambda e, pid=p.id: self._confirm_cancel_payment(pid),
                                    ),
                                ],
                                spacing=2,
                            )
                        ),
                    ]
                )
            )

        payments_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Histórico de Pagamentos ({len(payments)})", size=16, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Data / Hora")),
                            ft.DataColumn(ft.Text("Valor")),
                            ft.DataColumn(ft.Text("Forma")),
                            ft.DataColumn(ft.Text("Referência")),
                            ft.DataColumn(ft.Text("Status")),
                            ft.DataColumn(ft.Text("Estorno")),
                        ],
                        rows=pay_rows,
                        border=ft.border.all(1, AppColors.BORDER),
                        border_radius=8,
                    ) if pay_rows else ft.Text("Nenhum pagamento registrado até o momento.", italic=True, color=AppColors.TEXT_SECONDARY),
                ],
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=12,
            padding=18,
        )

        return ft.ListView(
            controls=[
                top_bar,
                ft.Container(height=16),
                profile_card,
                ft.Container(height=16),
                open_debts_card,
                ft.Container(height=16),
                payments_card,
            ],
            expand=True,
            padding=24,
        )

    def _confirm_cancel_debt(self, debt_id: int):
        def do_cancel():
            try:
                debt_service.cancel_debt(debt_id, reason="Cancelado pelo operador no perfil do cliente")
                self.page.snack_bar = ft.SnackBar(content=ft.Text("Dívida cancelada."), bgcolor=AppColors.INFO)
                self.page.snack_bar.open = True
                self.refresh()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(str(ex)), bgcolor=AppColors.DANGER)
                self.page.snack_bar.open = True
                self.page.update()

        ConfirmDialog.show(
            self.page,
            title="Cancelar Dívida",
            message="Tem certeza que deseja cancelar esta dívida? Esta ação não pode ser desfeita.",
            is_destructive=True,
            on_confirm=do_cancel,
        )

    def _confirm_cancel_payment(self, payment_id: int):
        def do_cancel():
            try:
                payment_service.cancel_payment(payment_id, reason="Estorno solicitado no histórico do cliente")
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
            message="O estorno devolverá o saldo devedor para a dívida e registrará o cancelamento na auditoria. Deseja prosseguir?",
            is_destructive=True,
            on_confirm=do_cancel,
        )

    def _generate_statement_pdf(self):
        try:
            pdf_path = report_service.generate_customer_statement_pdf(self.customer_id)
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Extrato gerado com sucesso em: {pdf_path}"),
                bgcolor=AppColors.SUCCESS,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Erro ao gerar extrato: {ex}"), bgcolor=AppColors.DANGER)
            self.page.snack_bar.open = True
            self.page.update()

    def _confirm_delete_customer(self, customer_id: int, customer_name: str):
        def do_delete():
            try:
                customer_service.delete_customer(customer_id)
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Cliente '{customer_name}' excluído com sucesso!"),
                    bgcolor=AppColors.SUCCESS,
                )
                self.page.snack_bar.open = True
                self.navigate_to("customers", {})
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(str(ex)),
                    bgcolor=AppColors.DANGER,
                )
                self.page.snack_bar.open = True
                self.page.update()

        ConfirmDialog.show(
            self.page,
            title="Excluir Cliente",
            message=f"Tem certeza que deseja excluir o cliente '{customer_name}'? Todos os registros serão removidos e essa ação não pode ser desfeita.",
            confirm_text="Excluir Definitivamente",
            is_destructive=True,
            on_confirm=do_delete,
        )

    def _print_thermal_debt(self, debt_id: int):
        try:
            cupom = report_service.generate_thermal_receipt_pdf("DEBT", debt_id, paper_width_mm=80)
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Cupom de Fiado gerado: {cupom.name}"),
                bgcolor=AppColors.SUCCESS,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Erro ao gerar cupom: {ex}"), bgcolor=AppColors.DANGER)
            self.page.snack_bar.open = True
            self.page.update()

    def _print_thermal_payment(self, payment_id: int):
        try:
            cupom = report_service.generate_thermal_receipt_pdf("PAYMENT", payment_id, paper_width_mm=80)
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Cupom de Pagamento gerado: {cupom.name}"),
                bgcolor=AppColors.SUCCESS,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Erro ao gerar cupom: {ex}"), bgcolor=AppColors.DANGER)
            self.page.snack_bar.open = True
            self.page.update()

    def _print_thermal_summary(self, width: int = 80):
        # Gera o comprovante do último fiado ou pagamento do cliente se houver
        customer = customer_service.get_customer(self.customer_id)
        if customer and customer.debts:
            latest_debt = customer.debts[-1]
            self._print_thermal_debt(latest_debt.id)
        elif customer and customer.payments:
            latest_pay = customer.payments[-1]
            self._print_thermal_payment(latest_pay.id)
        else:
            self._generate_statement_pdf()

    def refresh(self):
        self.navigate_to("customer_detail", {"customer_id": self.customer_id})
