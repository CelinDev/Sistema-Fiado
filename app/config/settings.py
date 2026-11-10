import os
import sys
from pathlib import Path


class Settings:
    APP_NAME: str = "FiadoManager"
    APP_TITLE: str = "Fiado Manager - Gestão de Crédito e Clientes"
    VERSION: str = "1.0.0"

    def __init__(self):
        self._init_directories()

    def _init_directories(self) -> None:
        """Define e garante a criação dos diretórios persistentes de dados do usuário."""
        override_dir = os.environ.get("FIADO_USER_DATA_DIR")
        if override_dir:
            self.base_data_dir = Path(override_dir)
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                self.base_data_dir = Path(appdata) / self.APP_NAME
            else:
                self.base_data_dir = Path.home() / f".{self.APP_NAME.lower()}"
        else:
            self.base_data_dir = Path.home() / f".{self.APP_NAME.lower()}"

        # Subpastas essenciais
        self.database_dir = self.base_data_dir / "data"
        self.backup_dir = self.base_data_dir / "backups"
        self.export_dir = self.base_data_dir / "exports"
        self.logs_dir = self.base_data_dir / "logs"

        # Criar os diretórios persistentes com segurança
        for directory in [self.base_data_dir, self.database_dir, self.backup_dir, self.export_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Caminho do arquivo SQLite
        override_db = os.environ.get("FIADO_DB_PATH")
        if override_db:
            self.database_path = Path(override_db)
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.database_path = self.database_dir / "fiado_manager.db"

    @property
    def sqlite_url(self) -> str:
        # SQLite connection string format
        return f"sqlite:///{self.database_path.as_posix()}"


settings = Settings()
