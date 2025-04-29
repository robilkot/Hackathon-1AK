from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
import os
from pathlib import Path

from backend.settings import get_settings
from model.model import Base, ValidationLog


def get_db_path():
    """Ensure database directory exists and return the path"""
    settings = get_settings()
    db_url = settings.database_url

    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return db_url


def get_db_session():
    """Create database engine and session"""
    db_url = get_db_path()
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_db():
    """Dependency for FastAPI to get DB session"""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def paginate_validation_logs(start_date=None, end_date=None, page=1, page_size=100):
    """Helper function to paginate validation logs with filtering"""
    db = get_db_session()
    try:
        result = ValidationLog.paginate(db, start_date, end_date, page, page_size)
        return result
    finally:
        db.close()

def delete_validation_log_by_id(log_id: int):
    """Delete a specific validation log by ID"""
    db = get_db_session()
    try:
        log = db.query(ValidationLog).filter(ValidationLog.id == log_id).first()
        if log:
            db.delete(log)
            db.commit()
            return {"success": True, "message": f"Log with ID {log_id} deleted successfully"}
        return {"success": False, "message": f"Log with ID {log_id} not found"}
    finally:
        db.close()

def delete_all_validation_logs():
    """Delete all validation logs"""
    db = get_db_session()
    try:
        count = db.query(ValidationLog).delete()
        db.commit()
        return {"success": True, "message": f"{count} logs deleted successfully"}
    finally:
        db.close()