from typing import Callable, Optional
import flet as ft

from app.services.customer_service import customer_service
from app.ui.dialogs.payment_dialog import PaymentDialog
from app.ui.theme.colors import AppColors
from app.utils.formatters import format_currency, format_phone


class QuickPaymentSearchDialog:
    @staticmethod
    def show(
        page: ft.Page,
        on_success: Optional[Callable[[], None]] = None,
    ):
        customers = customer_service.search_customers(active_only=True)
        # Filtra apenas quem tem saldo devedor
        debtor_customers = [c for c in customers if c.current_debt_cents > 0]

        search_input = ft.TextField(
            hint_text="Buscar cliente por nome ou telefone...",
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            height=40,
            text_size=13,
            autofocus=True,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        customer_dropdown = ft.Dropdown(
            label="Selecione o Cliente Devedor *",
            options=[
                ft.dropdown.Option(
                    key=str(c.id),
                    text=f"{c.name} - Saldo: {format_currency(c.current_debt_cents)} {f'({format_phone(c.phone)})' if c.phone else ''}",
                )
                for c in debtor_customers
            ],
            value=str(debtor_customers[0].id) if debtor_customers else None,
            expand=True,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        error_text = ft.Text("", color=AppColors.DANGER, size=13, visible=False)

        def on_search_change(e):
            term = (search_input.value or "").strip().lower()
            filtered = [
                c for c in debtor_customers
                if not term or term in c.name.lower() or (c.phone and term in c.phone.lower())
            ]
            customer_dropdown.options = [
                ft.dropdown.Option(
                    key=str(c.id),
                    text=f"{c.name} - Saldo: {format_currency(c.current_debt_cents)} {f'({format_phone(c.phone)})' if c.phone else ''}",
                )
                for c in filtered
            ]
            keys = [opt.key for opt in customer_dropdown.options]
            customer_dropdown.value = keys[0] if len(keys) == 1 else (customer_dropdown.value if customer_dropdown.value in keys else None)
            page.update()

        search_input.on_change = on_search_change

        def close_dialog(e):
            dialog.open = False
            page.update()

        def proceed_payment(e):
            if not customer_dropdown.value:
                error_text.value = "Selecione um cliente para receber o pagamento."
                error_text.visible = True
                page.update()
                return

            cid = int(customer_dropdown.value)
            dialog.open = False
            page.update()
            PaymentDialog.show(page, customer_id=cid, on_success=on_success)

        search_input.on_submit = proceed_payment

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.PAYMENTS_OUTLINED, color=AppColors.SUCCESS, size=24),
                        bgcolor=AppColors.SUCCESS_LIGHT,
                        border_radius=8,
                        padding=6,
                    ),
                    ft.Text("Receber Pagamento (F3)", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        search_input,
                        ft.Row(
                            controls=[customer_dropdown],
                        ),
                        error_text,
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=480,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dialog),
                ft.ElevatedButton(
                    "Avançar para Pagamento",
                    icon=ft.Icons.ARROW_FORWARD,
                    on_click=proceed_payment,
                    bgcolor=AppColors.SUCCESS,
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
