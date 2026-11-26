import json
from typing import Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.report_snapshot import ReportSnapshot


class ReportRepository:
    def save_snapshot(
        self,
        db: Session,
        report_type: str,
        requested_by: int,
        requested_role: str,
        payload: Any,
        filter_context: Optional[str] = None,
    ) -> ReportSnapshot:
        snapshot = ReportSnapshot(
            report_type=report_type,
            requested_by=requested_by,
            requested_role=requested_role,
            filter_context=filter_context,
            payload_json=json.dumps(payload, default=str),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    def list_recent(self, db: Session, limit: int = 20) -> List[ReportSnapshot]:
        stmt = select(ReportSnapshot).order_by(ReportSnapshot.generated_at.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())


report_repository = ReportRepository()
