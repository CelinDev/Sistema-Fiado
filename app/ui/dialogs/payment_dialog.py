from datetime import datetime
from typing import Callable, Optional
import flet as ft

from app.database.models import Debt, PaymentMethod
from app.services.customer_service import customer_service
from app.services.debt_service import debt_service
from app.services.payment_service import payment_service
from app.services.report_service import report_service
from app.ui.theme.colors import AppColors
from app.utils.formatters import format_currency, parse_currency_to_cents
from app.validators.schemas import PaymentCreateSchema


class PaymentDialog:
    @staticmethod
    def show(
        page: ft.Page,
        customer_id: int,
        debt_id: Optional[int] = None,
        on_success: Optional[Callable[[], None]] = None,
    ):
        customer = customer_service.get_customer(customer_id)
        if not customer:
            return

        open_debts = [d for d in customer.debts if d.remaining_cents > 0]
        selected_debt: Optional[Debt] = None

        if debt_id:
            for d in open_debts:
                if d.id == debt_id:
                    selected_debt = d
                    break

        # Max payable
        max_amount_cents = selected_debt.remaining_cents if selected_debt else customer.current_debt_cents

        info_banner = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, color=AppColors.SECONDARY, size=20),
                    ft.Text(
                        f"Saldo Devedor: {format_currency(max_amount_cents)}",
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                        size=14,
                    ),
                ],
                spacing=8,
            ),
            bgcolor=AppColors.SECONDARY_LIGHT,
            border_radius=8,
            padding=10,
        )

        amount_input = ft.TextField(
            label="Valor a Pagar (R$) *",
            value=f"{max_amount_cents / 100:.2f}".replace(".", ","),
            prefix_text="R$ ",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        def set_total_pay(e):
            amount_input.value = f"{max_amount_cents / 100:.2f}".replace(".", ",")
            page.update()

        btn_fill_total = ft.TextButton(
            "Pagar Saldo Total",
            on_click=set_total_pay,
            style=ft.ButtonStyle(color=AppColors.PRIMARY),
        )

        method_dropdown = ft.Dropdown(
            label="Forma de Pagamento *",
            options=[
                ft.dropdown.Option(PaymentMethod.CASH.value, "Dinheiro"),
                ft.dropdown.Option(PaymentMethod.PIX.value, "PIX"),
                ft.dropdown.Option(PaymentMethod.CARD.value, "Cartão (Débito/Crédito)"),
                ft.dropdown.Option(PaymentMethod.TRANSFER.value, "Transferência Bancária"),
                ft.dropdown.Option(PaymentMethod.OTHER.value, "Outros"),
            ],
            value=PaymentMethod.PIX.value,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        notes_input = ft.TextField(
            label="Observações / Comprovante",
            multiline=True,
            max_lines=2,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        error_text = ft.Text("", color=AppColors.DANGER, size=13, visible=False)

        def close_dialog(e):
            dialog.open = False
            page.update()

        def confirm_payment(e):
            error_text.visible = False
            page.update()

            try:
                cents = parse_currency_to_cents(amount_input.value)
                if cents <= 0:
                    raise ValueError("O valor deve ser maior que zero.")
                if cents > max_amount_cents:
                    raise ValueError(
                        f"O valor ({format_currency(cents)}) não pode ser superior ao saldo devedor ({format_currency(max_amount_cents)})."
                    )
            except Exception as ex:
                error_text.value = str(ex)
                error_text.visible = True
                page.update()
                return

            try:
                payment_schema = PaymentCreateSchema(
                    customer_id=customer.id,
                    debt_id=selected_debt.id if selected_debt else None,
                    amount_cents=cents,
                    payment_method=PaymentMethod(method_dropdown.value),
                    payment_date=datetime.now(),
                    notes=notes_input.value.strip() or None,
                )
                registered_payments = payment_service.register_payment(payment_schema)

                # Gera o comprovante térmico do pagamento
                try:
                    if registered_payments:
                        report_service.generate_thermal_receipt_pdf("PAYMENT", registered_payments[0].id, paper_width_mm=80)
                except Exception:
                    pass

                dialog.open = False
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Pagamento de {format_currency(cents)} recebido! Cupom térmico gerado em exports."),
                    bgcolor=AppColors.SUCCESS,
                )
                page.snack_bar.open = True
                page.update()

                if on_success:
                    on_success()

            except Exception as ex:
                error_text.value = str(ex)
                error_text.visible = True
                page.update()

        title_text = f"Receber Pagamento - {customer.name}"
        if selected_debt:
            title_text += f" (Dívida #{selected_debt.id})"

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PAYMENTS_OUTLINED, color=AppColors.SUCCESS, size=26),
                    ft.Text("Baixa de Pagamento", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        info_banner,
                        amount_input,
                        btn_fill_total,
                        method_dropdown,
                        notes_input,
                        error_text,
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=460,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dialog),
                ft.ElevatedButton(
                    "Confirmar Recebimento",
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    on_click=confirm_payment,
                    bgcolor=AppColors.SUCCESS,
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
