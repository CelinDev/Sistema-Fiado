from typing import Callable, Optional
import flet as ft
from app.database.models import Customer
from app.services.customer_service import customer_service
from app.ui.theme.colors import AppColors
from app.utils.formatters import clean_digits, format_cpf, format_phone, parse_currency_to_cents
from app.validators.schemas import CustomerCreateSchema, CustomerUpdateSchema


class CustomerDialog:
    @staticmethod
    def show(
        page: ft.Page,
        customer: Optional[Customer] = None,
        on_saved: Optional[Callable[[Customer], None]] = None,
    ):
        is_edit = customer is not None

        # Campos
        name_input = ft.TextField(
            label="Nome Completo *",
            value=customer.name if is_edit else "",
            autofocus=True,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        phone_input = ft.TextField(
            label="Telefone / WhatsApp",
            value=format_phone(customer.phone) if is_edit and customer.phone else "",
            hint_text="(00) 00000-0000",
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            expand=True,
        )

        cpf_input = ft.TextField(
            label="CPF (Opcional)",
            value=format_cpf(customer.cpf) if is_edit and customer.cpf else "",
            hint_text="000.000.000-00",
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            expand=True,
        )

        address_input = ft.TextField(
            label="Endereço",
            value=customer.address if is_edit and customer.address else "",
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        initial_limit_val = ""
        if is_edit and customer.credit_limit_cents is not None and customer.credit_limit_cents > 0:
            initial_limit_val = f"{customer.credit_limit_cents / 100:.2f}".replace(".", ",")

        credit_limit_input = ft.TextField(
            label="Limite de Fiado (R$) - Opcional",
            value=initial_limit_val,
            hint_text="Ex: 150,00 (Deixe vazio para sem limite)",
            prefix_text="R$ ",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        notes_input = ft.TextField(
            label="Observações",
            value=customer.notes if is_edit and customer.notes else "",
            multiline=True,
            max_lines=3,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
        )

        active_checkbox = ft.Checkbox(
            label="Cliente Ativo",
            value=customer.is_active if is_edit else True,
            visible=is_edit,
        )

        error_text = ft.Text("", color=AppColors.DANGER, size=13, visible=False)

        def close_dialog(e):
            dialog.open = False
            page.update()

        def save_customer(e):
            error_text.visible = False
            page.update()

            name = name_input.value.strip()
            if not name:
                error_text.value = "O nome é obrigatório."
                error_text.visible = True
                page.update()
                return

            phone = clean_digits(phone_input.value) or None
            cpf = clean_digits(cpf_input.value) or None
            address = address_input.value.strip() or None
            notes = notes_input.value.strip() or None

            limit_cents = None
            if credit_limit_input.value and credit_limit_input.value.strip():
                try:
                    limit_cents = parse_currency_to_cents(credit_limit_input.value)
                    if limit_cents < 0:
                        raise ValueError("O limite de crédito não pode ser negativo.")
                except Exception:
                    error_text.value = "Valor de limite de crédito inválido."
                    error_text.visible = True
                    page.update()
                    return

            try:
                if is_edit:
                    update_data = CustomerUpdateSchema(
                        name=name,
                        phone=phone,
                        cpf=cpf,
                        address=address,
                        notes=notes,
                        credit_limit_cents=limit_cents,
                        is_active=active_checkbox.value,
                    )
                    saved = customer_service.update_customer(customer.id, update_data)
                    msg = "Cliente atualizado com sucesso!"
                else:
                    create_data = CustomerCreateSchema(
                        name=name,
                        phone=phone,
                        cpf=cpf,
                        address=address,
                        notes=notes,
                        credit_limit_cents=limit_cents,
                        is_active=True,
                    )
                    saved = customer_service.create_customer(create_data)
                    msg = "Cliente cadastrado com sucesso!"

                dialog.open = False
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(msg),
                    bgcolor=AppColors.SUCCESS,
                )
                page.snack_bar.open = True
                page.update()

                if on_saved:
                    on_saved(saved)

            except Exception as ex:
                error_text.value = str(ex)
                error_text.visible = True
                page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.PERSON_ADD if not is_edit else ft.Icons.EDIT,
                        color=AppColors.PRIMARY,
                    ),
                    ft.Text("Novo Cliente" if not is_edit else "Editar Cliente", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        name_input,
                        ft.Row([phone_input, cpf_input], spacing=10),
                        address_input,
                        credit_limit_input,
                        notes_input,
                        active_checkbox,
                        error_text,
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=520,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dialog),
                ft.ElevatedButton(
                    "Salvar",
                    on_click=save_customer,
                    bgcolor=AppColors.PRIMARY,
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
