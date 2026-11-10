import flet as ft
from app.ui.theme.colors import AppColors


def create_stat_card(
    title: str,
    value: str,
    icon: str,
    icon_color: str = AppColors.PRIMARY,
    bg_icon_color: str = AppColors.PRIMARY_LIGHT,
    subtitle: str = "",
    subtitle_color: str = AppColors.TEXT_SECONDARY,
    width: int = 240,
) -> ft.Container:
    """Card moderno de indicador para o Dashboard."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            title,
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Container(
                            content=ft.Icon(icon, color=icon_color, size=22),
                            bgcolor=bg_icon_color,
                            border_radius=8,
                            padding=8,
                        ),
                    ],
                ),
                ft.Container(height=4),
                ft.Text(
                    value,
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    subtitle,
                    size=12,
                    weight=ft.FontWeight.W_500,
                    color=subtitle_color,
                ) if subtitle else ft.Container(height=0),
            ],
            spacing=2,
        ),
        bgcolor=AppColors.BG_CARD,
        border=ft.border.all(1, AppColors.BORDER),
        border_radius=12,
        padding=18,
        width=width,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=6,
            color="#0A000000",
            offset=ft.Offset(0, 2),
        ),
    )
