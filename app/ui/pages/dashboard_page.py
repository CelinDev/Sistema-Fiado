from typing import Callable
import flet as ft

from app.database.models import DebtStatus
from app.services.dashboard_service import dashboard_service
from app.services.debt_service import debt_service
from app.ui.components.quick_debt_modal import QuickDebtModal
from app.ui.components.stat_card import create_stat_card
from app.ui.theme.colors import AppColors
from app.utils.formatters import format_currency, format_date


class DashboardPage:
    def __init__(self, page: ft.Page, navigate_to: Callable[[str, dict], None]):
        self.page = page
        self.navigate_to = navigate_to

    def build(self) -> ft.Control:
        debt_service.refresh_overdue_statuses()
        metrics = dashboard_service.get_dashboard_metrics()

        # 1. Cabeçalho com Título e Botão NOVO FIADO
        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Visão Geral do Negócio", size=24, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                        ft.Text("Acompanhamento financeiro em tempo real e controle de fiados", size=13, color=AppColors.TEXT_SECONDARY),
                    ],
                    spacing=2,
                ),
                ft.ElevatedButton(
                    "NOVO FIADO",
                    icon=ft.Icons.ADD_SHOPPING_CART,
                    style=ft.ButtonStyle(
                        bgcolor=AppColors.PRIMARY,
                        color=ft.Colors.WHITE,
                        padding=ft.padding.symmetric(horizontal=20, vertical=16),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: QuickDebtModal.show(self.page, on_success=self._on_data_updated),
                ),
            ],
        )

        # 2. Grid de Indicadores (KPI Cards)
        kpi_row_1 = ft.ResponsiveRow(
            columns=12,
            controls=[
                ft.Container(
                    col={"sm": 12, "md": 6, "lg": 4},
                    content=create_stat_card(
                        title="TOTAL A RECEBER",
                        value=format_currency(metrics["total_receivable_cents"]),
                        icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                        icon_color=AppColors.SECONDARY,
                        bg_icon_color=AppColors.SECONDARY_LIGHT,
                        subtitle=f"{metrics['pending_debts_count']} fiados em aberto",
                        width=320,
                    ),
                ),
                ft.Container(
                    col={"sm": 12, "md": 6, "lg": 4},
                    content=create_stat_card(
                        title="RECEBIDO ESTE MÊS",
                        value=format_currency(metrics["received_this_month_cents"]),
                        icon=ft.Icons.TRENDING_UP,
                        icon_color=AppColors.SUCCESS,
                        bg_icon_color=AppColors.SUCCESS_LIGHT,
                        subtitle="Pagamentos confirmados",
                        subtitle_color=AppColors.SUCCESS,
                        width=320,
                    ),
                ),
                ft.Container(
                    col={"sm": 12, "md": 6, "lg": 4},
                    content=create_stat_card(
                        title="DÍVIDAS VENCIDAS",
                        value=format_currency(metrics["total_overdue_cents"]),
                        icon=ft.Icons.WARNING_AMBER_ROUNDED,
                        icon_color=AppColors.DANGER,
                        bg_icon_color=AppColors.DANGER_LIGHT,
                        subtitle=f"{metrics['defaulters_count']} clientes inadimplentes",
                        subtitle_color=AppColors.DANGER,
                        width=320,
                    ),
                ),
            ],
        )

        kpi_row_2 = ft.ResponsiveRow(
            columns=12,
            controls=[
                ft.Container(
                    col={"sm": 12, "md": 6, "lg": 4},
                    content=create_stat_card(
                        title="TOTAL DE CLIENTES",
                        value=str(metrics["total_customers"]),
                        icon=ft.Icons.PEOPLE_ALT_OUTLINED,
                        icon_color=AppColors.INFO,
                        bg_icon_color="#E0F2FE",
                        subtitle="Clientes cadastrados",
                        width=320,
                    ),
                ),
                ft.Container(
                    col={"sm": 12, "md": 6, "lg": 4},
                    content=create_stat_card(
                        title="DÍVIDAS PENDENTES",
                        value=str(metrics["pending_debts_count"]),
                        icon=ft.Icons.RECEIPT_LONG,
                        icon_color=AppColors.WARNING,
                        bg_icon_color=AppColors.WARNING_LIGHT,
                        subtitle="Aguardando quitação",
                        width=320,
                    ),
                ),
                ft.Container(
                    col={"sm": 12, "md": 6, "lg": 4},
                    content=create_stat_card(
                        title="INADIMPLÊNCIA ATIVA",
                        value=str(metrics["defaulters_count"]),
                        icon=ft.Icons.PERSON_OFF_OUTLINED,
                        icon_color=AppColors.DANGER,
                        bg_icon_color=AppColors.DANGER_LIGHT,
                        subtitle="Com atraso de vencimento",
                        subtitle_color=AppColors.DANGER,
                        width=320,
                    ),
                ),
            ],
        )

        # 3. Gráfico de Evolução dos Recebimentos (Últimos 6 meses)
        monthly_bars = []
        max_cents = max([m["amount_cents"] for m in metrics["monthly_evolution"]] + [1])
        
        for item in metrics["monthly_evolution"]:
            ratio = item["amount_cents"] / max_cents
            bar_height = max(10, int(ratio * 120))
            monthly_bars.append(
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(format_currency(item["amount_cents"]), size=10, weight=ft.FontWeight.W_600, color=AppColors.TEXT_SECONDARY),
                        ft.Container(
                            height=bar_height,
                            width=36,
                            bgcolor=AppColors.PRIMARY if item["amount_cents"] > 0 else AppColors.BORDER,
                            border_radius=ft.border_radius.only(top_left=6, top_right=6),
                            tooltip=f"{item['label']}: {format_currency(item['amount_cents'])}",
                        ),
                        ft.Text(item["label"], size=12, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                    ],
                    spacing=6,
                )
            )

        chart_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Evolução Mensal de Recebimentos", size=16, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                            ft.Icon(ft.Icons.BAR_CHART, color=AppColors.PRIMARY, size=24),
                        ],
                    ),
                    ft.Text("Histórico dos últimos 6 meses de pagamentos recebidos", size=12, color=AppColors.TEXT_SECONDARY),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                            controls=monthly_bars,
                        ),
                        height=170,
                        padding=ft.padding.only(top=10),
                    ),
                ],
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=12,
            padding=20,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=6, color="#0A000000", offset=ft.Offset(0, 2)),
        )

        # 4. Tabela de Alertas de Vencimento / Fiados Pendentes Recentes
        overdue_list = debt_service.get_overdue_debts()[:6]
        overdue_rows = []
        for d in overdue_list:
            overdue_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(d.customer.name, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(d.description)),
                        ft.DataCell(ft.Text(format_date(d.due_date), color=AppColors.DANGER, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(format_currency(d.remaining_cents), weight=ft.FontWeight.BOLD)),
                        ft.DataCell(
                            ft.ElevatedButton(
                                "Cobrar / Ver",
                                height=28,
                                on_click=lambda e, cid=d.customer_id: self.navigate_to("customer_detail", {"customer_id": cid}),
                            )
                        ),
                    ]
                )
            )

        overdue_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Atenção: Fiados Vencidos", size=16, weight=ft.FontWeight.BOLD, color=AppColors.DANGER),
                            ft.TextButton(
                                "Ver Todos os Fiados",
                                on_click=lambda e: self.navigate_to("debts", {}),
                            ),
                        ],
                    ),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Cliente")),
                            ft.DataColumn(ft.Text("Descrição")),
                            ft.DataColumn(ft.Text("Vencimento")),
                            ft.DataColumn(ft.Text("Saldo Restante")),
                            ft.DataColumn(ft.Text("Ação")),
                        ],
                        rows=overdue_rows,
                        border=ft.border.all(1, AppColors.BORDER),
                        border_radius=8,
                    ) if overdue_rows else ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=AppColors.SUCCESS, size=20),
                            ft.Text("Nenhum fiado vencido no momento. Parabéns!", color=AppColors.SUCCESS, weight=ft.FontWeight.W_500),
                        ]),
                        padding=20,
                    ),
                ],
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=12,
            padding=20,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=6, color="#0A000000", offset=ft.Offset(0, 2)),
        )

        return ft.ListView(
            controls=[
                header,
                ft.Container(height=16),
                kpi_row_1,
                ft.Container(height=10),
                kpi_row_2,
                ft.Container(height=16),
                chart_card,
                ft.Container(height=16),
                overdue_card,
            ],
            expand=True,
            spacing=0,
            padding=24,
        )

    def _on_data_updated(self):
        self.navigate_to("dashboard", {})
