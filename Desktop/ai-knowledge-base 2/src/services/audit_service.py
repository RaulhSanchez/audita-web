import sqlite3
import pandas as pd
import os
from src.core.logger import logger
from contextlib import closing

class AuditService:
    def __init__(self):
        self.sqlite_path = "./db/cortexa_meta.db"
        self._ensure_table()

    def _ensure_table(self):
        """Inicialización robusta con índices para la Fase 3."""
        try:
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
            with closing(sqlite3.connect(self.sqlite_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        display_name TEXT,
                        role TEXT,
                        action TEXT,
                        details TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Índices Fase 3
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs (timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_logs (username)")
                
                # Migración display_name (solo una vez)
                cursor.execute("PRAGMA table_info(audit_logs)")
                cols = [c[1] for c in cursor.fetchall()]
                if "display_name" not in cols:
                    cursor.execute("ALTER TABLE audit_logs ADD COLUMN display_name TEXT DEFAULT ''")
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error inicializando AuditService: {e}")

    def log_event(self, username, role, action, details, display_name=""):
        try:
            with closing(sqlite3.connect(self.sqlite_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO audit_logs (username, role, action, details, display_name) VALUES (?, ?, ?, ?, ?)",
                    (username, role, action, str(details), display_name or "")
                )
                conn.commit()
            logger.info(f"Audit: {username} ({role}) -> {action}")
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")

    def get_logs(self, limit=100):
        try:
            with closing(sqlite3.connect(self.sqlite_path)) as conn:
                df = pd.read_sql_query(
                    "SELECT id, username, display_name, role, action, details, timestamp "
                    "FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                    conn,
                    params=(limit,)
                )
                return df
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return pd.DataFrame()

    def export_logs_csv(self):
        df = self.get_logs(limit=10000)
        os.makedirs("logs", exist_ok=True)
        csv_path = "logs/audit_export.csv"
        df.to_csv(csv_path, index=False)
        return csv_path

audit_service = AuditService()
