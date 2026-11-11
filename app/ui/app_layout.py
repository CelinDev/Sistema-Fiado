from typing import Dict, Optional
import flet as ft

from app.ui.components.quick_debt_modal import QuickDebtModal
from app.ui.dialogs.customer_dialog import CustomerDialog
from app.ui.dialogs.quick_payment_search_dialog import QuickPaymentSearchDialog
from app.ui.pages.customer_detail_page import CustomerDetailPage
from app.ui.pages.customers_page import CustomersPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.debts_page import DebtsPage
from app.ui.pages.payments_page import PaymentsPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.settings_backup_page import SettingsBackupPage
from app.ui.theme.colors import AppColors


class AppLayout:
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_route = "dashboard"
        self.route_params: Dict = {}
        self.content_area = ft.Container(expand=True, bgcolor=AppColors.BG_MAIN)
        self.nav_buttons: Dict[str, ft.Container] = {}

    def build(self) -> ft.Control:
        # Botão em destaque "NOVO FIADO (F2)" no topo da Sidebar
        btn_quick_debt = ft.Container(
            content=ft.ElevatedButton(
                "NOVO FIADO (F2)",
                icon=ft.Icons.ADD_SHOPPING_CART,
                style=ft.ButtonStyle(
                    bgcolor=AppColors.PRIMARY,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=16, vertical=16),
                ),
                width=200,
                on_click=lambda e: QuickDebtModal.show(self.page, on_success=self._on_quick_debt_success),
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
        )

        # Itens de Menu
        menu_items = [
            ("dashboard", "Dashboard", ft.Icons.DASHBOARD_OUTLINED),
            ("customers", "Clientes", ft.Icons.PEOPLE_ALT_OUTLINED),
            ("debts", "Fiados & Dívidas", ft.Icons.RECEIPT_LONG),
            ("payments", "Pagamentos", ft.Icons.PAYMENTS_OUTLINED),
            ("reports", "Relatórios", ft.Icons.INSERT_CHART_OUTLINED),
            ("settings", "Backups & Dados", ft.Icons.SETTINGS_OUTLINED),
        ]

        sidebar_items = []
        for route_key, label, icon in menu_items:
            nav_item = self._create_nav_item(route_key, label, icon)
            self.nav_buttons[route_key] = nav_item
            sidebar_items.append(nav_item)

        sidebar = ft.Container(
            content=ft.Column(
                controls=[
                    # Logo e Título
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.POINT_OF_SALE, color=AppColors.PRIMARY, size=26),
                                    bgcolor=AppColors.BG_SIDEBAR_ACTIVE,
                                    border_radius=8,
                                    padding=6,
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text("FIADO", size=18, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_ON_DARK),
                                        ft.Text("MANAGER", size=11, weight=ft.FontWeight.W_600, color=AppColors.PRIMARY),
                                    ],
                                    spacing=0,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=ft.padding.only(left=18, right=18, top=20, bottom=12),
                    ),
                    btn_quick_debt,
                    ft.Divider(color=AppColors.BG_SIDEBAR_ACTIVE, thickness=1),
                    ft.Column(controls=sidebar_items, spacing=4),
                    ft.Container(expand=True),
                    # Rodapé da Sidebar com Dicas de Atalhos
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("ATALHOS DO CAIXA", size=10, weight=ft.FontWeight.BOLD, color=AppColors.PRIMARY),
                                ft.Text("F2 • Lançar Fiado", size=11, color=AppColors.TEXT_MUTED),
                                ft.Text("F3 • Receber Pagamento", size=11, color=AppColors.TEXT_MUTED),
                                ft.Text("F4 • Buscar Clientes", size=11, color=AppColors.TEXT_MUTED),
                                ft.Text("F5 • Novo Cliente", size=11, color=AppColors.TEXT_MUTED),
                                ft.Divider(color=AppColors.BG_SIDEBAR_ACTIVE, thickness=0.5),
                                ft.Text("v1.0.0 • Offline", size=10, color=AppColors.TEXT_MUTED),
                            ],
                            spacing=3,
                        ),
                        padding=ft.padding.only(left=18, right=18, bottom=16),
                    ),
                ],
                spacing=4,
            ),
            width=230,
            bgcolor=AppColors.BG_SIDEBAR,
        )

        # Monta a rota inicial
        self._render_current_page()

        # Vincula os atalhos de teclado globais
        self.page.on_keyboard_event = self._on_keyboard_event

        return ft.Row(
            controls=[
                sidebar,
                self.content_area,
            ],
            expand=True,
            spacing=0,
        )

    def _create_nav_item(self, route_key: str, label: str, icon: str) -> ft.Container:
        is_active = self.current_route == route_key

        def on_click(e):
            self.navigate_to(route_key, {})

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        icon,
                        size=20,
                        color=AppColors.PRIMARY if is_active else AppColors.TEXT_MUTED,
                    ),
                    ft.Text(
                        label,
                        size=14,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                        color=AppColors.TEXT_ON_DARK if is_active else AppColors.TEXT_MUTED,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=AppColors.BG_SIDEBAR_ACTIVE if is_active else ft.Colors.TRANSPARENT,
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            margin=ft.padding.symmetric(horizontal=10),
            on_click=on_click,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
        )

    def navigate_to(self, route: str, params: Optional[Dict] = None):
        self.current_route = route
        self.route_params = params or {}

        # Atualiza destaques da sidebar
        for k, btn in self.nav_buttons.items():
            is_active = (k == route)
            btn.bgcolor = AppColors.BG_SIDEBAR_ACTIVE if is_active else ft.Colors.TRANSPARENT
            # Atualiza cor do texto e ícone
            row = btn.content
            row.controls[0].color = AppColors.PRIMARY if is_active else AppColors.TEXT_MUTED
            row.controls[1].color = AppColors.TEXT_ON_DARK if is_active else AppColors.TEXT_MUTED
            row.controls[1].weight = ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500

        self._render_current_page()
        self.page.update()

    def _render_current_page(self):
        if self.current_route == "dashboard":
            view = DashboardPage(self.page, self.navigate_to).build()
        elif self.current_route == "customers":
            view = CustomersPage(self.page, self.navigate_to).build()
        elif self.current_route == "customer_detail":
            cid = self.route_params.get("customer_id", 0)
            view = CustomerDetailPage(self.page, cid, self.navigate_to).build()
        elif self.current_route == "debts":
            view = DebtsPage(self.page, self.navigate_to).build()
        elif self.current_route == "payments":
            view = PaymentsPage(self.page, self.navigate_to).build()
        elif self.current_route == "reports":
            view = ReportsPage(self.page, self.navigate_to).build()
        elif self.current_route == "settings":
            view = SettingsBackupPage(self.page, self.navigate_to).build()
        else:
            view = DashboardPage(self.page, self.navigate_to).build()

        self.content_area.content = view

    def _on_quick_debt_success(self):
        self.navigate_to(self.current_route, self.route_params)

    def _on_keyboard_event(self, e: ft.KeyboardEvent):
        key = e.key.upper() if e.key else ""
        if key == "F2":
            QuickDebtModal.show(self.page, on_success=self._on_quick_debt_success)
        elif key == "F3":
            QuickPaymentSearchDialog.show(self.page, on_success=self._on_quick_debt_success)
        elif key == "F4":
            self.navigate_to("customers", {})
        elif key == "F5":
            CustomerDialog.show(self.page, on_saved=lambda c: self.navigate_to("customers", {}))
        elif key == "ESCAPE":
            # Fecha qualquer diálogo/modal aberto
            for dialog in list(self.page.overlay):
                if isinstance(dialog, ft.AlertDialog) and getattr(dialog, "open", False):
                    dialog.open = False
                    self.page.update()

