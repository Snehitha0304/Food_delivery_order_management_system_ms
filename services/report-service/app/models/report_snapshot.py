from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base
from app.models.base import utc_now


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(100), nullable=False, index=True)
    requested_by = Column(Integer, nullable=False, index=True)
    requested_role = Column(String(50), nullable=False)
    filter_context = Column(String(255), nullable=True)
    payload_json = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=utc_now, nullable=False)
