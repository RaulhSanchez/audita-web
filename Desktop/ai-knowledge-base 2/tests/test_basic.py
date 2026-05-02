import pytest
import sqlite3
import os

def test_db_initialization():
    """Verifica que la base de datos se crea correctamente."""
    from src.services.audit_service import audit_service
    from src.core.userdb import userdb
    userdb.init_tables()
    db_path = "./db/cortexa_meta.db"
    assert os.path.exists(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert cursor.fetchone() is not None
    conn.close()

def test_audit_log_indexes():
    """Verifica que los índices de la Fase 3 existen."""
    db_path = "./db/cortexa_meta.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_audit_timestamp'")
    assert cursor.fetchone() is not None
    conn.close()

def test_logger_creation():
    """Verifica que el logger crea el archivo de log."""
    from src.core.logger import logger
    logger.info("Test log message")
    assert os.path.exists("logs/app.log")
