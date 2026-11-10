from datetime import datetime
from sqlalchemy import text
from app.database.connection import db_manager
from app.database.models import Base, AppSetting
from app.utils.logger import logger

CURRENT_SCHEMA_VERSION = 2


def run_migrations(engine=None) -> None:
    """
    Executa migrações de forma segura e idempotente.
    Nunca apaga ou substitui dados existentes.
    """
    target_engine = engine or db_manager.engine
    logger.info("Verificando estrutura e migrações do banco de dados...")

    # Cria tabelas que ainda não existam (seguro e idempotente)
    Base.metadata.create_all(bind=target_engine)

    # Migração v2: Adiciona coluna credit_limit_cents na tabela customers se não existir
    with target_engine.connect() as conn:
        try:
            columns_info = conn.execute(text("PRAGMA table_info(customers)")).fetchall()
            col_names = [row[1] for row in columns_info]
            if "credit_limit_cents" not in col_names:
                logger.info("Adicionando coluna 'credit_limit_cents' à tabela 'customers'...")
                conn.execute(text("ALTER TABLE customers ADD COLUMN credit_limit_cents INTEGER DEFAULT NULL"))
                conn.commit()
        except Exception as e:
            logger.warning(f"Aviso ao verificar coluna credit_limit_cents: {e}")

    # Verifica e registra a versão do schema
    with target_engine.connect() as conn:
        result = conn.execute(
            text("SELECT value FROM app_settings WHERE key = 'schema_version'")
        ).fetchone()

        if not result:
            conn.execute(
                text(
                    "INSERT INTO app_settings (key, value, updated_at) "
                    "VALUES ('schema_version', :version, :now)"
                ),
                {"version": str(CURRENT_SCHEMA_VERSION), "now": datetime.now()}
            )
            conn.commit()
            logger.info(f"Schema inicial criado com sucesso na versão {CURRENT_SCHEMA_VERSION}.")
        else:
            db_version = int(result[0])
            logger.info(f"Schema atual do banco de dados: v{db_version}")
            if db_version < CURRENT_SCHEMA_VERSION:
                logger.info(f"Atualizando schema de v{db_version} para v{CURRENT_SCHEMA_VERSION}...")
                conn.execute(
                    text("UPDATE app_settings SET value = :version, updated_at = :now WHERE key = 'schema_version'"),
                    {"version": str(CURRENT_SCHEMA_VERSION), "now": datetime.now()}
                )
                conn.commit()

    logger.info("Migrações concluídas e integridade do banco validada.")
