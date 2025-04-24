from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import datetime


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    event_type = Column(String, index=True)  # 'object_detected', 'validation_result', 'error'
    seq_number = Column(Integer, nullable=True)

    sticker_present = Column(Boolean, nullable=True)
    sticker_matches_design = Column(Boolean, nullable=True)

    error_message = Column(String, nullable=True)
    error_type = Column(String, nullable=True)  # e.g., 'system', 'validation', 'camera'
    error_severity = Column(String, nullable=True)  # e.g., 'info', 'warning', 'error', 'critical'