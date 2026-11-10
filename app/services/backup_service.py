from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
from typing import List, Tuple

from app.config.settings import settings
from app.database.connection import db_manager
from app.utils.logger import logger


class BackupService:
    def create_backup(self, custom_dest_dir: Path = None) -> Path:
        """
        Gera um backup completo e consistente do banco de dados SQLite
        usando a API oficial de backup do SQLite (seguro durante gravações).
        """
        dest_dir = custom_dest_dir or settings.backup_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"fiado_backup_{timestamp}.db"
        dest_path = dest_dir / backup_filename

        logger.info(f"Iniciando backup para {dest_path}...")

        # Conexão de origem (forçando checkpoint do WAL)
        src_conn = sqlite3.connect(settings.database_path.as_posix())
        try:
            src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            dst_conn = sqlite3.connect(dest_path.as_posix())
            try:
                src_conn.backup(dst_conn)
                logger.info(f"Backup concluído com sucesso: {dest_path}")
            finally:
                dst_conn.close()
        finally:
            src_conn.close()

        return dest_path

    def list_backups(self) -> List[Tuple[Path, str, str]]:
        """Retorna lista de backups existentes (caminho, data_formatada, tamanho)."""
        backups = []
        if not settings.backup_dir.exists():
            return []

        for p in sorted(settings.backup_dir.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True):
            stat = p.stat()
            size_kb = f"{stat.st_size / 1024:.1f} KB"
            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y às %H:%M:%S")
            backups.append((p, mod_time, size_kb))

        return backups

    def validate_backup_file(self, backup_file: Path) -> Tuple[bool, str]:
        """
        Valida previamente a integridade e o schema de um arquivo de backup
        antes de permitir a restauração.
        """
        if not backup_file.exists():
            return False, "O arquivo de backup selecionado não existe."

        if backup_file.stat().st_size < 100:
            return False, "O arquivo de backup é inválido ou está vazio."

        try:
            conn = sqlite3.connect(backup_file.as_posix())
            cursor = conn.cursor()

            # 1. Checagem de integridade estrutural
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()
            if not integrity_result or integrity_result[0] != "ok":
                return False, f"Falha na checagem de integridade: {integrity_result}"

            # 2. Checagem de tabelas essenciais
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            expected_tables = {"customers", "debts", "payments"}
            if not expected_tables.issubset(tables):
                missing = expected_tables - tables
                return False, f"Arquivo de backup incompatível. Tabelas ausentes: {missing}"

            conn.close()
            return True, "Arquivo de backup íntegro e compatível."

        except Exception as e:
            return False, f"Erro ao ler banco de dados: {str(e)}"

    def restore_backup(self, backup_file: Path) -> None:
        """
        Restaura o banco a partir do backup após validação prévia rigorosa.
        Gera uma cópia de segurança do banco atual antes de substituir.
        """
        is_valid, reason = self.validate_backup_file(backup_file)
        if not is_valid:
            raise ValueError(f"Não é seguro restaurar este arquivo: {reason}")

        # Salva cópia de segurança preventiva do banco atual
        if settings.database_path.exists():
            pre_restore_backup = settings.backup_dir / f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            logger.info(f"Criando backup de segurança preventiva antes da restauração em {pre_restore_backup}...")
            shutil.copy2(settings.database_path, pre_restore_backup)

        logger.info(f"Restaurando banco a partir de {backup_file}...")

        # Fecha conexões ativas do SQLAlchemy
        db_manager.engine.dispose()

        # Restaura utilizando a API nativa de backup do SQLite (garante sync com WAL)
        src_conn = sqlite3.connect(backup_file.as_posix())
        try:
            dst_conn = sqlite3.connect(settings.database_path.as_posix())
            try:
                src_conn.backup(dst_conn)
                dst_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            finally:
                dst_conn.close()
        finally:
            src_conn.close()

        logger.info("Restauração concluída com sucesso.")


backup_service = BackupService()
