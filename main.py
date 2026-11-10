import os
import sys
from pathlib import Path

# Configuração automática do runtime desktop do Flet
def _setup_flet_view_path():
    if "FLET_VIEW_PATH" in os.environ and os.path.isdir(os.environ["FLET_VIEW_PATH"]):
        return

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
        candidates = [
            base_dir / "_internal" / "flet_desktop" / "app" / "flet",
            base_dir / "flet_desktop" / "app" / "flet",
            Path(getattr(sys, "_MEIPASS", "")) / "flet_desktop" / "app" / "flet",
            Path.home() / ".flet" / "bin" / "flet-0.28.2" / "flet",
        ]
        for c in candidates:
            if (c / "flet.exe").is_file():
                os.environ["FLET_VIEW_PATH"] = str(c)
                break
    else:
        try:
            import flet_desktop
            app_dir = Path(flet_desktop.get_package_bin_dir()) / "flet"
            if (app_dir / "flet.exe").is_file():
                os.environ["FLET_VIEW_PATH"] = str(app_dir)
        except Exception:
            pass

_setup_flet_view_path()

import flet as ft

from app.config.settings import settings
from app.database.migrations import run_migrations
from app.ui.app_layout import AppLayout
from app.ui.theme.colors import AppColors
from app.utils.logger import logger


def main(page: ft.Page):
    try:
        logger.info("Iniciando FiadoManager Desktop Application...")

        # Configurações da Janela Desktop
        page.title = settings.APP_TITLE
        page.window.width = 1280
        page.window.height = 800
        page.window.min_width = 1000
        page.window.min_height = 680
        page.window.center()

        # Tema visual global
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = AppColors.BG_MAIN
        page.padding = 0

        # Inicialização do banco de dados e migrações
        try:
            run_migrations()
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}", exc_info=True)
            page.add(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color=AppColors.DANGER, size=48),
                            ft.Text("Erro Crítico ao Inicializar o Banco de Dados", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(str(e), size=14, color=AppColors.TEXT_SECONDARY),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
            return

        # Monta a estrutura da aplicação
        layout = AppLayout(page)
        page.add(layout.build())
        page.update()
        logger.info("Interface carregada com sucesso.")
    except Exception as ex:
        logger.error(f"Erro fatal ao carregar interface: {ex}", exc_info=True)
        raise


if __name__ == "__main__":
    ft.app(target=main)
