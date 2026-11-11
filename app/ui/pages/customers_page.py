from typing import Callable, List
import flet as ft

from app.database.models import Customer
from app.services.customer_service import customer_service
from app.ui.components.quick_debt_modal import QuickDebtModal
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.dialogs.customer_dialog import CustomerDialog
from app.ui.dialogs.payment_dialog import PaymentDialog
from app.ui.theme.colors import AppColors
from app.utils.formatters import format_cpf, format_currency, format_phone


class CustomersPage:
    def __init__(self, page: ft.Page, navigate_to: Callable[[str, dict], None]):
        self.page = page
        self.navigate_to = navigate_to
        self.filter_mode = "ALL"  # ALL, WITH_DEBT, CLEAN
        self.search_term = ""

    def build(self) -> ft.Control:
        search_field = ft.TextField(
            hint_text="Pesquisar por nome, telefone ou CPF...",
            prefix_icon=ft.Icons.SEARCH,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            on_change=self._on_search_change,
            expand=True,
            height=42,
        )

        filter_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("ALL", "Todos os Clientes"),
                ft.dropdown.Option("WITH_DEBT", "Somente com Débitos"),
                ft.dropdown.Option("CLEAN", "Sem Débitos (Zerados)"),
            ],
            value=self.filter_mode,
            width=220,
            border_color=AppColors.BORDER,
            focused_border_color=AppColors.PRIMARY,
            on_change=self._on_filter_change,
        )

        btn_new_customer = ft.ElevatedButton(
            "+ Novo Cliente",
            icon=ft.Icons.PERSON_ADD,
            bgcolor=AppColors.PRIMARY,
            color=ft.Colors.WHITE,
            height=42,
            on_click=lambda e: CustomerDialog.show(self.page, on_saved=lambda c: self.refresh()),
        )

        def on_file_picked(e: ft.FilePickerResultEvent):
            if not e.files or len(e.files) == 0:
                return
            file_path = e.files[0].path
            try:
                res = customer_service.import_customers_from_file(file_path)
                created = res.get("created", 0)
                skipped = res.get("skipped", 0)
                errors = res.get("errors", [])
                
                msg = f"Importação concluída: {created} cadastrado(s), {skipped} ignorado(s)."
                if errors:
                    msg += f" {len(errors)} com erro."
                
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(msg),
                    bgcolor=AppColors.SUCCESS if created > 0 else AppColors.WARNING,
                )
                self.page.snack_bar.open = True
                self.refresh()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Erro na importação: {ex}"),
                    bgcolor=AppColors.DANGER,
                )
                self.page.snack_bar.open = True
                self.page.update()

        file_picker = ft.FilePicker(on_result=on_file_picked)
        if file_picker not in self.page.overlay:
            self.page.overlay.append(file_picker)

        btn_import = ft.OutlinedButton(
            "Importar Excel / CSV",
            icon=ft.Icons.UPLOAD_FILE,
            height=42,
            style=ft.ButtonStyle(
                color=AppColors.PRIMARY,
                side=ft.BorderSide(1.5, AppColors.PRIMARY),
            ),
            on_click=lambda e: file_picker.pick_files(
                dialog_title="Selecione a planilha de clientes (.xlsx, .csv)",
                allowed_extensions=["xlsx", "xls", "csv"],
                allow_multiple=False,
            ),
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
                                ft.Text("Gerenciamento de Clientes", size=24, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                                ft.Text("Consulte históricos, saldos devedores e cadastre novos clientes", size=13, color=AppColors.TEXT_SECONDARY),
                            ],
                            spacing=2,
                        ),
                        ft.Row(
                            controls=[btn_import, btn_new_customer],
                            spacing=10,
                        ),
                    ],
                ),
                ft.Container(height=16),
                ft.Container(
                    content=ft.Row(
                        controls=[search_field, filter_dropdown],
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
        customers = customer_service.search_customers(self.search_term)

        # Filtros adicionais
        if self.filter_mode == "WITH_DEBT":
            customers = [c for c in customers if c.current_debt_cents > 0]
        elif self.filter_mode == "CLEAN":
            customers = [c for c in customers if c.current_debt_cents == 0]

        rows = []
        for c in customers:
            debt_cents = c.current_debt_cents
            has_debt = debt_cents > 0

            status_badge = ft.Container(
                content=ft.Text(
                    "EM ABERTO" if has_debt else "QUITADO",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.DANGER if has_debt else AppColors.SUCCESS,
                ),
                bgcolor=AppColors.DANGER_LIGHT if has_debt else AppColors.SUCCESS_LIGHT,
                border_radius=4,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            )

            action_buttons = ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        tooltip="Ver Extrato e Histórico Detalhado",
                        icon_color=AppColors.INFO,
                        icon_size=20,
                        on_click=lambda e, cid=c.id: self.navigate_to("customer_detail", {"customer_id": cid}),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.POST_ADD,
                        tooltip="Lançar Novo Fiado para este Cliente",
                        icon_color=AppColors.PRIMARY,
                        icon_size=20,
                        on_click=lambda e, cid=c.id: QuickDebtModal.show(self.page, preselected_customer_id=cid, on_success=self.refresh),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.PAYMENTS_OUTLINED,
                        tooltip="Receber Pagamento",
                        icon_color=AppColors.SUCCESS if has_debt else AppColors.BORDER,
                        disabled=not has_debt,
                        icon_size=20,
                        on_click=lambda e, cid=c.id: PaymentDialog.show(self.page, customer_id=cid, on_success=self.refresh),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Editar Dados Cadastrais",
                        icon_color=AppColors.TEXT_SECONDARY,
                        icon_size=20,
                        on_click=lambda e, cust=c: CustomerDialog.show(self.page, customer=cust, on_saved=lambda sc: self.refresh()),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip="Excluir Cliente (Apenas se Quitado)" if not has_debt else "Não é possível excluir cliente com saldo devedor",
                        icon_color=AppColors.DANGER if not has_debt else AppColors.BORDER,
                        disabled=has_debt,
                        icon_size=20,
                        on_click=lambda e, cid=c.id, cname=c.name: self._confirm_delete_customer(cid, cname),
                    ),
                ],
                spacing=2,
            )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            c.name,
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            color=AppColors.TEXT_PRIMARY,
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                            tooltip=c.name,
                                        ),
                                        ft.Text(
                                            f"CPF: {format_cpf(c.cpf)}" if c.cpf else "CPF não informado",
                                            size=11,
                                            color=AppColors.TEXT_SECONDARY,
                                            no_wrap=True,
                                        ),
                                    ],
                                    spacing=2,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                width=220,
                                padding=ft.padding.symmetric(vertical=4),
                            )
                        ),
                        ft.DataCell(ft.Text(format_phone(c.phone) if c.phone else "-", no_wrap=True)),
                        ft.DataCell(ft.Text(format_currency(c.total_purchases_cents), no_wrap=True)),
                        ft.DataCell(
                            ft.Text(
                                format_currency(debt_cents),
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.DANGER if has_debt else AppColors.TEXT_PRIMARY,
                                size=14,
                                no_wrap=True,
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
                        column_spacing=24,
                        data_row_min_height=52,
                        data_row_max_height=64,
                        columns=[
                            ft.DataColumn(ft.Text("Nome / CPF")),
                            ft.DataColumn(ft.Text("Telefone")),
                            ft.DataColumn(ft.Text("Total Compras")),
                            ft.DataColumn(ft.Text("Saldo Devedor")),
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
                                ft.Icon(ft.Icons.SEARCH_OFF, size=48, color=AppColors.TEXT_MUTED),
                                ft.Text("Nenhum cliente encontrado com os critérios de busca.", color=AppColors.TEXT_SECONDARY),
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

    def _on_search_change(self, e):
        self.search_term = e.control.value
        self._render_table()
        self.page.update()

    def _on_filter_change(self, e):
        self.filter_mode = e.control.value
        self._render_table()
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
                self.refresh()
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
            message=f"Tem certeza que deseja excluir o cadastro de '{customer_name}'? Esta ação removerá o histórico e não poderá ser desfeita.",
            confirm_text="Excluir Definitivamente",
            is_destructive=True,
            on_confirm=do_delete,
        )

    def refresh(self):
        self.navigate_to("customers", {})
