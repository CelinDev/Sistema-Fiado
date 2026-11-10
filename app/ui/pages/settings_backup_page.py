from pathlib import Path
from typing import Callable
import flet as ft

from app.config.settings import settings
from app.services.backup_service import backup_service
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.theme.colors import AppColors


class SettingsBackupPage:
    def __init__(self, page: ft.Page, navigate_to: Callable[[str, dict], None]):
        self.page = page
        self.navigate_to = navigate_to

    def build(self) -> ft.Control:
        header = ft.Column(
            controls=[
                ft.Text("Configurações e Segurança de Dados", size=24, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                ft.Text("Gerencie backups, restaurações e consulte a persistência local dos seus dados", size=13, color=AppColors.TEXT_SECONDARY),
            ],
            spacing=2,
        )

        paths_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("DIRETÓRIOS PERSISTENTES DO SISTEMA", size=12, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_SECONDARY),
                    ft.Container(height=4),
                    ft.Text(f"Banco de Dados: {settings.database_path}", size=13, weight=ft.FontWeight.W_500),
                    ft.Text(f"Pasta de Backups: {settings.backup_dir}", size=13, color=AppColors.TEXT_SECONDARY),
                    ft.Text(f"Pasta de Exportações: {settings.export_dir}", size=13, color=AppColors.TEXT_SECONDARY),
                    ft.Text(f"Pasta de Logs: {settings.logs_dir}", size=13, color=AppColors.TEXT_SECONDARY),
                ],
                spacing=4,
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=10,
            padding=16,
        )

        btn_generate_backup = ft.ElevatedButton(
            "GERAR NOVO BACKUP AGORA",
            icon=ft.Icons.BACKUP,
            bgcolor=AppColors.PRIMARY,
            color=ft.Colors.WHITE,
            height=44,
            on_click=lambda e: self._create_backup(),
        )

        self.backups_container = ft.Container()
        self._render_backups_list()

        return ft.ListView(
            controls=[
                header,
                ft.Container(height=16),
                paths_card,
                ft.Container(height=16),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Cópias de Segurança Disponíveis", size=18, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                        btn_generate_backup,
                    ],
                ),
                ft.Container(height=12),
                self.backups_container,
            ],
            expand=True,
            padding=24,
        )

    def _render_backups_list(self):
        backups = backup_service.list_backups()
        rows = []
        for path, date_str, size_str in backups:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(path.name, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(date_str)),
                        ft.DataCell(ft.Text(size_str)),
                        ft.DataCell(
                            ft.ElevatedButton(
                                "Restaurar",
                                icon=ft.Icons.RESTORE,
                                bgcolor=AppColors.SECONDARY,
                                color=ft.Colors.WHITE,
                                height=28,
                                on_click=lambda e, p=path: self._confirm_restore(p),
                            )
                        ),
                    ]
                )
            )

        self.backups_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Arquivo")),
                            ft.DataColumn(ft.Text("Data e Hora")),
                            ft.DataColumn(ft.Text("Tamanho")),
                            ft.DataColumn(ft.Text("Ação")),
                        ],
                        rows=rows,
                        border=ft.border.all(1, AppColors.BORDER),
                        border_radius=8,
                        heading_row_color=AppColors.BG_MAIN,
                    ) if rows else ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=AppColors.TEXT_MUTED, size=20),
                            ft.Text("Nenhum arquivo de backup gerado ainda.", color=AppColors.TEXT_SECONDARY),
                        ]),
                        padding=20,
                    ),
                ],
            ),
            bgcolor=AppColors.BG_CARD,
            border=ft.border.all(1, AppColors.BORDER),
            border_radius=10,
            padding=16,
        )

    def _create_backup(self):
        try:
            backup_path = backup_service.create_backup()
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Backup gerado com sucesso: {backup_path.name}"),
                bgcolor=AppColors.SUCCESS,
            )
            self.page.snack_bar.open = True
            self.refresh()
        except Exception as e:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Erro ao gerar backup: {e}"), bgcolor=AppColors.DANGER)
            self.page.snack_bar.open = True
            self.page.update()

    def _confirm_restore(self, backup_file: Path):
        def do_restore():
            try:
                backup_service.restore_backup(backup_file)
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Backup restaurado com sucesso! Dados atualizados."),
                    bgcolor=AppColors.SUCCESS,
                )
                self.page.snack_bar.open = True
                self.navigate_to("dashboard", {})
            except Exception as e:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Erro ao restaurar: {e}"), bgcolor=AppColors.DANGER)
                self.page.snack_bar.open = True
                self.page.update()

        ConfirmDialog.show(
            self.page,
            title="Restaurar Banco de Dados",
            message=f"Tem certeza que deseja restaurar o backup '{backup_file.name}'? Uma cópia preventiva do estado atual será salva automaticamente antes da operação.",
            is_destructive=True,
            on_confirm=do_restore,
        )

    def refresh(self):
        self._render_backups_list()
        self.page.update()
