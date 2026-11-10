from typing import Callable, Optional
import flet as ft
from app.ui.theme.colors import AppColors


class ConfirmDialog:
    @staticmethod
    def show(
        page: ft.Page,
        title: str,
        message: str,
        on_confirm: Callable[[], None],
        confirm_text: str = "Confirmar",
        is_destructive: bool = False,
    ):
        def close_dialog(e):
            dialog.open = False
            page.update()

        def confirm_action(e):
            dialog.open = False
            page.update()
            on_confirm()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.WARNING_AMBER_ROUNDED if is_destructive else ft.Icons.HELP_OUTLINE,
                        color=AppColors.DANGER if is_destructive else AppColors.PRIMARY,
                        size=28,
                    ),
                    ft.Text(title, weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=10,
            ),
            content=ft.Text(message, size=14, color=AppColors.TEXT_PRIMARY),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(color=AppColors.TEXT_SECONDARY),
                ),
                ft.ElevatedButton(
                    confirm_text,
                    on_click=confirm_action,
                    bgcolor=AppColors.DANGER if is_destructive else AppColors.PRIMARY,
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
