import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database.models import AuditLog
from app.database.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: Session):
        super().__init__(AuditLog, session)

    def log(self, entity_name: str, entity_id: int, action: str, details: Optional[Dict[str, Any]] = None) -> AuditLog:
        details_str = json.dumps(details, ensure_ascii=False, default=str) if details else None
        log_entry = AuditLog(
            entity_name=entity_name,
            entity_id=entity_id,
            action=action,
            details=details_str,
            created_at=datetime.now()
        )
        self.session.add(log_entry)
        self.session.flush()
        return log_entry

    def get_logs_by_entity(self, entity_name: str, entity_id: int) -> List[AuditLog]:
        return (
            self.session.query(AuditLog)
            .filter(AuditLog.entity_name == entity_name, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc())
            .all()
        )
