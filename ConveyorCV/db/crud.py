from sqlalchemy.orm import Session
from . import model
import datetime


def create_object_detected_log(db: Session, seq_number: int):
    db_log = model.LogEntry(
        event_type="object_detected",
        seq_number=seq_number,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def create_validation_result_log(db: Session, seq_number: int, sticker_present: bool,
                                sticker_matches_design: bool):
    db_log = model.LogEntry(
        event_type="validation_result",
        seq_number=seq_number,
        sticker_present=sticker_present,
        sticker_matches_design=sticker_matches_design,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def create_error_log(db: Session, error_message: str, error_type: str = "system",
                    error_severity: str = "error", seq_number: int = None):
    db_log = model.LogEntry(
        event_type="error",
        seq_number=seq_number,
        error_message=error_message,
        error_type=error_type,
        error_severity=error_severity,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_logs(db: Session, skip: int = 0, limit: int = 100, event_type: str = None):
    query = db.query(model.LogEntry)
    if event_type:
        query = query.filter(model.LogEntry.event_type == event_type)
    return query.order_by(model.LogEntry.timestamp.desc()).offset(skip).limit(limit).all()


def get_log(db: Session, log_id: int):
    return db.query(model.LogEntry).filter(model.LogEntry.id == log_id).first()


def get_logs_by_date_range(db: Session, start_datetime, end_datetime, event_type=None):
    try:
        query = db.query(model.LogEntry).filter(
            model.LogEntry.timestamp >= start_datetime,
            model.LogEntry.timestamp <= end_datetime
        )

        if event_type:
            query = query.filter(model.LogEntry.event_type == event_type)

        return query.order_by(model.LogEntry.timestamp).all()
    finally:
        db.close()