from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

from app.config.settings import settings
from app.utils.logger import logger


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Garante integridade referencial e performance com WAL no SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


class DatabaseManager:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or settings.sqlite_url
        self.engine = create_engine(
            self.db_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Context manager transacional. Faz commit se sucesso, rollback se exceção."""
        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erro em transação do banco: {e}", exc_info=True)
            raise
        finally:
            session.close()


db_manager = DatabaseManager()


def get_db_session() -> Generator[Session, None, None]:
    """Helper para obter sessão do banco."""
    with db_manager.session_scope() as session:
        yield session
