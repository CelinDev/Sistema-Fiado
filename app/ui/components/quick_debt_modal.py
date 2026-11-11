from datetime import date, datetime, timedelta
from typing import Callable, Optional
import flet as ft

from app.database.models import Customer
from app.services.customer_service import customer_service
from app.services.debt_service import debt_service
from app.services.report_service import report_service
from app.ui.dialogs.customer_dialog import CustomerDialog
from app.ui.theme.colors import AppColors
from app.utils.formatters import format_currency, parse_currency_to_cents
from app.validators.schemas import DebtCreateSchema


class QuickDebtModal:
    @staticmethod
    def show(
        page: ft.Page,
        preselected_customer_id: Optional[int] = None,
        on_success: Optional[Callable[[], None]] = None,
    ):
        customers = customer_service.search_customers(active_only=True)

        customer_search_input = ft.TextField(
            hint_text="Buscar cliente por nome ou fone...",
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            height=38,
            text_size=13,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        customer_dropdown = ft.Dropdown(
            label="Selecione o Cliente *",
            options=[
                ft.dropdown.Option(
                    key=str(c.id),
                    text=f"{c.name} {f'({c.phone})' if c.phone else ''}",
                )
                for c in customers
            ],
            value=str(preselected_customer_id) if preselected_customer_id else None,
            expand=True,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        def on_customer_search_change(e):
            term = (customer_search_input.value or "").strip().lower()
            filtered = [
                c for c in customers
                if not term or term in c.name.lower() or (c.phone and term in c.phone.lower())
            ]
            customer_dropdown.options = [
                ft.dropdown.Option(
                    key=str(c.id),
                    text=f"{c.name} {f'({c.phone})' if c.phone else ''}",
                )
                for c in filtered
            ]
            # Se a seleção atual não estiver na lista filtrada, limpa a seleção
            current_keys = [opt.key for opt in customer_dropdown.options]
            if customer_dropdown.value not in current_keys:
                customer_dropdown.value = current_keys[0] if len(current_keys) == 1 else None
            page.update()

        customer_search_input.on_change = on_customer_search_change

        def refresh_customer_list(newly_created: Optional[Customer] = None):
            nonlocal customers
            customers = customer_service.search_customers(active_only=True)
            customer_search_input.value = ""
            customer_dropdown.options = [
                ft.dropdown.Option(
                    key=str(c.id),
                    text=f"{c.name} {f'({c.phone})' if c.phone else ''}",
                )
                for c in customers
            ]
            if newly_created:
                customer_dropdown.value = str(newly_created.id)
            page.update()

        def open_quick_new_customer(e):
            CustomerDialog.show(page, on_saved=refresh_customer_list)

        btn_new_customer = ft.IconButton(
            icon=ft.Icons.PERSON_ADD_ALT_1,
            tooltip="Cadastrar Novo Cliente Rapidamente",
            icon_color=AppColors.PRIMARY,
            on_click=open_quick_new_customer,
        )

        desc_input = ft.TextField(
            label="Descrição da Compra *",
            value="Diversos",
            hint_text="Ex: Diversos, Pães, Mercearia",
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        amount_input = ft.TextField(
            label="Valor Total (R$) *",
            hint_text="0,00",
            prefix_text="R$ ",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        # Data da compra (padrão hoje, mas personalizável)
        today_str = datetime.now().strftime("%d/%m/%Y")
        debt_date_input = ft.TextField(
            label="Data da Compra (DD/MM/AAAA) *",
            value=today_str,
            hint_text="DD/MM/AAAA",
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            expand=True,
        )

        # Sugestão de vencimento padrão (15 dias ou 30 dias)
        default_due = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
        due_date_input = ft.TextField(
            label="Data de Vencimento (DD/MM/AAAA)",
            value=default_due,
            hint_text="DD/MM/AAAA",
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            expand=True,
        )

        def set_due_days(days: int):
            def handler(e):
                due_date_input.value = (date.today() + timedelta(days=days)).strftime("%d/%m/%Y")
                page.update()
            return handler

        due_chips = ft.Row(
            controls=[
                ft.Text("Atalhos:", size=11, color=AppColors.TEXT_SECONDARY),
                ft.OutlinedButton("7 dias", on_click=set_due_days(7), height=28),
                ft.OutlinedButton("15 dias", on_click=set_due_days(15), height=28),
                ft.OutlinedButton("30 dias", on_click=set_due_days(30), height=28),
            ],
            spacing=6,
        )

        error_text = ft.Text("", color=AppColors.DANGER, size=13, visible=False)

        def close_dialog(e):
            dialog.open = False
            page.update()

        def save_debt(e):
            error_text.visible = False
            page.update()

            if not customer_dropdown.value:
                error_text.value = "Por favor, selecione um cliente."
                error_text.visible = True
                page.update()
                return

            desc = desc_input.value.strip()
            if not desc:
                error_text.value = "Informe a descrição dos itens ou compra."
                error_text.visible = True
                page.update()
                return

            try:
                cents = parse_currency_to_cents(amount_input.value)
                if cents <= 0:
                    raise ValueError("O valor deve ser maior que zero.")
            except Exception:
                error_text.value = "Valor inválido. Digite um valor como 15,50."
                error_text.visible = True
                page.update()
                return

            debt_dt = None
            if debt_date_input.value and debt_date_input.value.strip():
                try:
                    parsed_d = datetime.strptime(debt_date_input.value.strip(), "%d/%m/%Y")
                    # Mantém o horário atual se for hoje, ou 12:00 se for data retroativa
                    now = datetime.now()
                    if parsed_d.date() == now.date():
                        debt_dt = now
                    else:
                        debt_dt = parsed_d.replace(hour=12, minute=0, second=0)
                except ValueError:
                    error_text.value = "Data da compra inválida. Use DD/MM/AAAA."
                    error_text.visible = True
                    page.update()
                    return

            due_date = None
            if due_date_input.value and due_date_input.value.strip():
                try:
                    dt = datetime.strptime(due_date_input.value.strip(), "%d/%m/%Y").date()
                    due_date = dt
                except ValueError:
                    error_text.value = "Formato de data inválido. Use DD/MM/AAAA."
                    error_text.visible = True
                    page.update()
                    return

            try:
                debt_data = DebtCreateSchema(
                    customer_id=int(customer_dropdown.value),
                    description=desc,
                    original_amount_cents=cents,
                    debt_date=debt_dt,
                    due_date=due_date,
                    notes=None,
                )
                created_debt = debt_service.create_debt(debt_data)

                # Gera o comprovante térmico automaticamente para o comerciante
                try:
                    report_service.generate_thermal_receipt_pdf("DEBT", created_debt.id, paper_width_mm=80)
                except Exception:
                    pass

                dialog.open = False
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Fiado de {format_currency(cents)} registrado! Cupom térmico gerado em exports."),
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

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.POST_ADD, color=AppColors.PRIMARY, size=24),
                        bgcolor=AppColors.PRIMARY_LIGHT,
                        border_radius=8,
                        padding=6,
                    ),
                    ft.Text("Lançar Novo Fiado", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        customer_search_input,
                        ft.Row(
                            controls=[customer_dropdown, btn_new_customer],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        desc_input,
                        amount_input,
                        ft.Row(
                            controls=[debt_date_input, due_date_input],
                            spacing=10,
                        ),
                        due_chips,
                        error_text,
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=500,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dialog),
                ft.ElevatedButton(
                    "Salvar Fiado",
                    icon=ft.Icons.CHECK,
                    on_click=save_debt,
                    bgcolor=AppColors.PRIMARY,
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
