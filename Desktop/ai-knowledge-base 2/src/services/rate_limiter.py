"""Rate limiter basado en SQLite. Cuenta consultas diarias por usuario."""
import sqlite3
from datetime import date
from src.core.userdb import userdb  # usa db de users para settings


class RateLimiter:
    def __init__(self):
        self.db_path = "./db/cortexa_meta.db"

    def _ensure_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                username TEXT,
                date TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (username, date)
            )
        """)

    def get_daily_limit(self):
        """Lee el límite desde settings (default 100)."""
        try:
            return int(userdb.get_setting('daily_query_limit', '100'))
        except Exception:
            return 100

    def check_and_increment(self, username) -> tuple[bool, int, int]:
        """
        Returns (allowed, current_count, daily_limit).
        Si allowed=False, el usuario ha superado el límite.
        """
        today = date.today().isoformat()
        limit = self.get_daily_limit()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        self._ensure_table(cur)
        cur.execute("""
            INSERT INTO rate_limits (username, date, count) VALUES (?, ?, 0)
            ON CONFLICT(username, date) DO NOTHING
        """, (username, today))
        cur.execute("SELECT count FROM rate_limits WHERE username=? AND date=?", (username, today))
        row = cur.fetchone()
        current = row[0] if row else 0
        if current >= limit:
            conn.commit()
            conn.close()
            return False, current, limit
        cur.execute("""
            UPDATE rate_limits SET count = count + 1 WHERE username=? AND date=?
        """, (username, today))
        conn.commit()
        cur.execute("SELECT count FROM rate_limits WHERE username=? AND date=?", (username, today))
        new_count = cur.fetchone()[0]
        conn.close()
        return True, new_count, limit

    def get_usage(self, username) -> tuple[int, int]:
        """Devuelve (consultas_hoy, límite_diario)."""
        today = date.today().isoformat()
        limit = self.get_daily_limit()
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            self._ensure_table(cur)
            cur.execute("SELECT count FROM rate_limits WHERE username=? AND date=?", (username, today))
            row = cur.fetchone()
            conn.close()
            return (row[0] if row else 0), limit
        except Exception:
            return 0, limit


rate_limiter = RateLimiter()
