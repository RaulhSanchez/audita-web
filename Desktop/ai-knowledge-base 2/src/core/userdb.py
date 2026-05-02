import sqlite3
import os
import json
from datetime import datetime

SQLITE_PATH = "./db/cortexa_meta.db"


class UserDatabase:
    """Pure SQLite user management — no Ollama dependency."""

    def init_tables(self):
        os.makedirs("./db", exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            name          TEXT DEFAULT '',
            email         TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            role          TEXT DEFAULT 'viewer',
            workspaces    TEXT DEFAULT '["general"]',
            can_upload    INTEGER DEFAULT 0,
            upload_groups TEXT DEFAULT '[]',
            can_delete    INTEGER DEFAULT 0,
            delete_groups TEXT DEFAULT '[]',
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            temp_password INTEGER DEFAULT 0
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_by TEXT DEFAULT 'system',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        # Migraciones: totp columns
        c.execute("PRAGMA table_info(users)")
        user_cols = [col[1] for col in c.fetchall()]
        if "totp_secret" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT DEFAULT ''")
        if "totp_enabled" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN totp_enabled INTEGER DEFAULT 0")

        defaults = [
            ('product_name',      'Cortexa AI'),
            ('company_name',      'Tu Empresa'),
            ('welcome_title',     'Base de conocimiento corporativo'),
            ('welcome_subtitle',  '100% local. Tus datos no salen de tu organización.'),
            ('superadmin',        'admin'),
            ('logo_path',         'assets/logo.png'),
            ('primary_color',     '#6366f1'),
            ('current_plan',      'starter'),   # Plan activo: starter | business | enterprise
            ('daily_query_limit', '50'),         # Sincronizado con el plan activo
        ]
        for key, val in defaults:
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

        conn.commit()
        conn.close()

    def migrate_from_yaml(self):
        """
        Inicialización segura del primer admin.

        Tras la auditoría de seguridad, NO migramos hashes desde config.yaml
        (porque incluían un hash hardcoded committeado al repo). En su lugar:

          1. Si ya existe al menos un usuario en SQLite, no hacemos nada.
          2. Si no existe ninguno, creamos un admin con la contraseña indicada
             en la variable de entorno ADMIN_INITIAL_PASSWORD. Si está vacía,
             generamos una aleatoria, la imprimimos UNA SOLA VEZ por logging
             y la marcamos como temporal para forzar cambio en el primer login.
        """
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            count = c.fetchone()[0]
            conn.close()
            if count > 0:
                return  # ya inicializado
        except Exception:
            return

        import os as _os
        import secrets as _secrets
        import logging as _logging
        try:
            import bcrypt as _bcrypt
        except ImportError:
            _logging.error("bcrypt no está instalado: ABORTANDO la creación del admin inicial.")
            return

        username = "admin"
        email = _os.getenv("ADMIN_INITIAL_EMAIL", "admin@empresa.com")
        password = _os.getenv("ADMIN_INITIAL_PASSWORD", "").strip()
        is_temp = False
        if not password:
            password = _secrets.token_urlsafe(16)
            is_temp = True
            _logging.warning(
                "ADMIN_INITIAL_PASSWORD no definida en .env. Se ha generado una "
                "contraseña temporal aleatoria. CÁMBIALA en el primer login.\n"
                f">>> Contraseña temporal admin: {password}"
            )

        password_hash = _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            c = conn.cursor()
            c.execute('''INSERT OR IGNORE INTO users
                (username, name, email, password_hash, role, workspaces,
                 can_upload, upload_groups, can_delete, delete_groups, temp_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    username, "Administrador", email, password_hash, "admin",
                    json.dumps(["all"]), 1, json.dumps([]), 1, json.dumps([]),
                    int(is_temp),
                )
            )
            conn.commit()
            conn.close()
            _logging.info(f"Admin inicial creado (username={username}, email={email}, temp={is_temp}).")
        except Exception as e:
            _logging.error(f"Error creando admin inicial: {e}")

    def get_credentials_dict(self):
        """Devuelve el dict de credenciales para streamlit-authenticator."""
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute("SELECT username, name, email, password_hash FROM users")
        result = {}
        for username, name, email, pwd in c.fetchall():
            result[username] = {"name": name, "email": email, "password": pwd}
        conn.close()
        return {"usernames": result}

    def get_all_users(self):
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT username, name, email, role, workspaces, can_upload, "
            "upload_groups, can_delete, delete_groups FROM users ORDER BY role DESC, username"
        )
        rows = c.fetchall()
        conn.close()
        users = []
        for r in rows:
            can_up  = bool(r[5])
            can_del = bool(r[7])
            users.append({
                "username":      r[0],
                "name":          r[1],
                "email":         r[2],
                "role":          r[3],
                "workspaces":    json.loads(r[4] or '["general"]'),
                "can_upload":    can_up,
                "upload_groups": json.loads(r[6] or '[]'),
                "can_delete":    can_del,
                "delete_groups": json.loads(r[8] or '[]'),
            })
        return users

    def get_user(self, username):
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT username, name, email, role, workspaces, can_upload, "
            "upload_groups, can_delete, delete_groups, temp_password FROM users WHERE username=?",
            (username,)
        )
        r = c.fetchone()
        conn.close()
        if not r:
            return None
        return {
            "username":      r[0], "name": r[1], "email": r[2], "role": r[3],
            "workspaces":    json.loads(r[4] or '["general"]'),
            "can_upload":    bool(r[5]),
            "upload_groups": json.loads(r[6] or '[]'),
            "can_delete":    bool(r[7]),
            "delete_groups": json.loads(r[8] or '[]'),
            "temp_password": bool(r[9]),
            "totp_enabled":  False,  # will be populated if col exists
        }

    def add_user(self, username, name, email, password_hash, role, workspaces,
                 can_upload, upload_groups, can_delete, delete_groups):
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        try:
            c.execute(
                '''INSERT INTO users
                   (username, name, email, password_hash, role, workspaces,
                    can_upload, upload_groups, can_delete, delete_groups)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (username, name, email, password_hash, role,
                 json.dumps(workspaces), int(can_upload), json.dumps(upload_groups),
                 int(can_delete), json.dumps(delete_groups))
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    # POST-AUDITORÍA · Whitelist explícita de columnas actualizables.
    # Sin esto, una key user-controlable podía inyectar SQL en el f-string.
    _USER_UPDATABLE_COLS = {
        "name", "email", "password_hash", "role",
        "workspaces", "can_upload", "upload_groups",
        "can_delete", "delete_groups", "temp_password",
        "totp_enabled", "totp_secret", "language",
    }

    def update_user(self, username, **kwargs):
        """Actualiza campos del usuario. Serializa listas a JSON.

        Solo se permiten columnas listadas en `_USER_UPDATABLE_COLS`. Cualquier
        otra clave se ignora (no levanta error para no romper callers que
        pasen claves opcionales no soportadas).
        """
        if not kwargs:
            return
        # Filtrar contra whitelist
        safe_kwargs = {k: v for k, v in kwargs.items() if k in self._USER_UPDATABLE_COLS}
        if not safe_kwargs:
            return
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        for k in ('workspaces', 'upload_groups', 'delete_groups'):
            if k in safe_kwargs and isinstance(safe_kwargs[k], list):
                safe_kwargs[k] = json.dumps(safe_kwargs[k])
        for k in ('can_upload', 'can_delete', 'temp_password', 'totp_enabled'):
            if k in safe_kwargs:
                safe_kwargs[k] = int(bool(safe_kwargs[k]))
        sets = ", ".join(f"{k}=?" for k in safe_kwargs)
        vals = list(safe_kwargs.values()) + [username]
        c.execute(f"UPDATE users SET {sets} WHERE username=?", vals)
        conn.commit()
        conn.close()

    def update_password(self, username, new_password_hash, temp=False):
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE users SET password_hash=?, temp_password=? WHERE username=?",
            (new_password_hash, int(temp), username)
        )
        conn.commit()
        conn.close()

    def delete_user(self, username):
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username=?", (username,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    # ── Settings ─────────────────────────────────────────────────────────────

    def get_setting(self, key, default=None):
        # POST-AUDITORÍA · descifra valores marcados con prefijo fernet:
        try:
            from src.core.secrets_box import decrypt_if_needed
        except Exception:
            decrypt_if_needed = lambda x: x
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key=?", (key,))
            r = c.fetchone()
            conn.close()
            if r is None:
                return default
            return decrypt_if_needed(r[0])
        except Exception:
            return default

    def set_setting(self, key, value, updated_by="system"):
        # POST-AUDITORÍA · cifra valores sensibles antes de persistir
        try:
            from src.core.secrets_box import encrypt_if_sensitive
            stored_value = encrypt_if_sensitive(key, str(value) if value is not None else "")
        except Exception:
            stored_value = str(value) if value is not None else ""
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_by, updated_at) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (key, stored_value, updated_by)
        )
        conn.commit()
        conn.close()

    def get_all_settings(self):
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute("SELECT key, value FROM settings")
        result = {k: v for k, v in c.fetchall()}
        conn.close()
        return result


userdb = UserDatabase()
