import os
import sqlite3
import threading
from contextlib import closing
import pandas as pd
from langchain_ollama import OllamaEmbeddings

_vectorstore_lock = threading.Lock()

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.db_path = "./db"
        self.sqlite_path = "./db/cortexa_meta.db"

        import time
        max_retries = 30
        for i in range(max_retries):
            try:
                self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
                self.embeddings.embed_query("test")
                break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"⏳ Esperando modelo Nomic (Intento {i+1}/{max_retries})...")
                    time.sleep(10)
                else:
                    raise e

        os.makedirs(self.db_path, exist_ok=True)
        self._init_sqlite()
        self._vectorstore_cache = None
        self._initialized = True

    def _init_sqlite(self):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()

        # ── Users table (source of truth, replaces config.yaml) ──────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username      TEXT PRIMARY KEY,
                name          TEXT DEFAULT '',
                email         TEXT DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '',
                role          TEXT DEFAULT 'viewer',
                workspaces    TEXT DEFAULT '["general"]',
                can_upload    INTEGER DEFAULT 0,
                upload_groups TEXT DEFAULT '[]',
                can_delete    INTEGER DEFAULT 0,
                delete_groups TEXT DEFAULT '[]',
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                temp_password INTEGER DEFAULT 0
            )
        ''')

        # ── Settings table ────────────────────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_by TEXT DEFAULT 'system',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        _default_settings = [
            ('product_name',     'Cortexa AI'),
            ('company_name',     'Tu Empresa'),
            ('welcome_title',    'Base de conocimiento corporativo'),
            ('welcome_subtitle', '100% local. Tus datos no salen de tu organización.'),
            ('superadmin',       'admin'),
            ('logo_path',        'assets/logo.png'),
            ('primary_color',    '#6366f1'),
        ]
        for _k, _v in _default_settings:
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (_k, _v))

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user TEXT,
                status TEXT,
                chunk_count INTEGER,
                workspace TEXT DEFAULT 'general',
                summary TEXT DEFAULT '',
                query_count INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                username TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                username TEXT,
                role TEXT,
                action TEXT,
                details TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                message_index INTEGER,
                username TEXT,
                rating INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, message_index)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspaces (
                name TEXT PRIMARY KEY,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                system_prompt TEXT DEFAULT '',
                cite_only INTEGER DEFAULT 0
            )
        ''')
        cursor.execute("INSERT OR IGNORE INTO workspaces (name, created_by) VALUES ('general', 'system')")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                name TEXT DEFAULT '',
                role TEXT DEFAULT 'viewer',
                workspaces TEXT DEFAULT '["general"]',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                used INTEGER DEFAULT 0,
                used_at TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                uploaded_by TEXT,
                chunk_count INTEGER DEFAULT 0,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replaced_by TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                username TEXT NOT NULL,
                label TEXT DEFAULT '',
                scopes TEXT DEFAULT '["query","documents"]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                active INTEGER DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                name        TEXT PRIMARY KEY,
                description TEXT DEFAULT '',
                base_role   TEXT DEFAULT 'viewer',
                workspaces  TEXT DEFAULT '["general"]',
                can_upload  INTEGER DEFAULT 0,
                upload_groups TEXT DEFAULT '[]',
                can_delete  INTEGER DEFAULT 0,
                delete_groups TEXT DEFAULT '[]',
                color       TEXT DEFAULT '#818cf8',
                is_system   INTEGER DEFAULT 0
            )
        ''')
        # Roles de sistema que siempre deben existir
        _sys_roles = [
            ("admin",  "Acceso total al sistema",   "admin",  '["all"]', 1,'["all"]',1,'["all"]','#ef4444',1),
            ("viewer", "Solo lectura",               "viewer", '["general"]',0,'[]',0,'[]','#94a3b8',1),
            ("editor", "Puede subir documentos",     "viewer", '["general"]',1,'["all"]',0,'[]','#6366f1',0),
            ("gestor", "Puede subir y eliminar",     "viewer", '["general"]',1,'["all"]',1,'["all"]','#a78bfa',0),
        ]
        for r in _sys_roles:
            cursor.execute(
                "INSERT OR IGNORE INTO roles "
                "(name,description,base_role,workspaces,can_upload,upload_groups,can_delete,delete_groups,color,is_system)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)", r
            )

        # ── RAGAS evaluations ────────────────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ragas_evaluations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                run_name     TEXT DEFAULT '',
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by   TEXT DEFAULT 'system',
                num_samples  INTEGER DEFAULT 0,
                scores_json  TEXT DEFAULT '{}',
                samples_json TEXT DEFAULT '[]'
            )
        ''')

        # ── SQL databases (Text-to-SQL) ───────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sql_databases (
                name           TEXT PRIMARY KEY,
                description    TEXT DEFAULT '',
                connection_str TEXT NOT NULL,
                workspaces     TEXT DEFAULT 'general',
                created_by     TEXT DEFAULT 'admin',
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migraciones para instalaciones antiguas
        cursor.execute("PRAGMA table_info(chat_history)")
        if "session_id" not in [c[1] for c in cursor.fetchall()]:
            cursor.execute("ALTER TABLE chat_history ADD COLUMN session_id INTEGER")

        cursor.execute("PRAGMA table_info(documents)")
        doc_cols = [c[1] for c in cursor.fetchall()]
        if "workspace" not in doc_cols:
            cursor.execute("ALTER TABLE documents ADD COLUMN workspace TEXT DEFAULT 'general'")
        if "summary" not in doc_cols:
            cursor.execute("ALTER TABLE documents ADD COLUMN summary TEXT DEFAULT ''")
        if "query_count" not in doc_cols:
            cursor.execute("ALTER TABLE documents ADD COLUMN query_count INTEGER DEFAULT 0")

        # Migraciones workspace: system_prompt, cite_only
        cursor.execute("PRAGMA table_info(workspaces)")
        ws_cols = [c[1] for c in cursor.fetchall()]
        if "system_prompt" not in ws_cols:
            cursor.execute("ALTER TABLE workspaces ADD COLUMN system_prompt TEXT DEFAULT ''")
        if "cite_only" not in ws_cols:
            cursor.execute("ALTER TABLE workspaces ADD COLUMN cite_only INTEGER DEFAULT 0")

        # Migraciones users: totp
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [c[1] for c in cursor.fetchall()]
        if "totp_secret" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT DEFAULT ''")
        if "totp_enabled" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN totp_enabled INTEGER DEFAULT 0")

        # Migrar mensajes huérfanos
        cursor.execute("SELECT count(*) FROM chat_history WHERE session_id IS NULL")
        if cursor.fetchone()[0] > 0:
            cursor.execute("INSERT INTO chat_sessions (username, title) VALUES ('admin', 'Archivo Histórico')")
            legacy_id = cursor.lastrowid
            cursor.execute("UPDATE chat_history SET session_id = ? WHERE session_id IS NULL", (legacy_id,))

        conn.commit()
        conn.close()

    def get_vectorstore(self):
        """Devuelve el vectorstore Qdrant (singleton por proceso, thread-safe)."""
        if not getattr(self, "_vectorstore_cache", None):
            with _vectorstore_lock:
                # Double-checked locking: otro thread pudo haberlo creado ya
                if not getattr(self, "_vectorstore_cache", None):
                    from src.core.vectorstore import CortexaVectorStore
                    self._vectorstore_cache = CortexaVectorStore(
                        embeddings=self.embeddings,
                        path=os.path.join(self.db_path, "qdrant"),
                    )
        return self._vectorstore_cache

    # --- Documentos ---
    def add_document_meta(self, doc_id, filename, user, chunks, workspace="general"):
        import datetime
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT OR REPLACE INTO documents (id, filename, user, status, chunk_count, workspace, upload_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doc_id, filename, user, "indexed", chunks, workspace, now)
        )
        conn.commit()
        conn.close()

    def get_all_documents(self, workspace_filter=None):
        conn = sqlite3.connect(self.sqlite_path)
        df = pd.read_sql_query("SELECT * FROM documents", conn)
        conn.close()
        if df.empty:
            return df
        # workspace_filter=None  → sin restricción (uso interno/admin)
        # workspace_filter=["all"] → sin restricción (admin)
        # workspace_filter=[]    → no tiene acceso a nada → DataFrame vacío
        # workspace_filter=["x"] → solo docs con intersección
        if workspace_filter is None:
            return df
        if "all" in workspace_filter:
            return df
        if not workspace_filter:          # lista vacía → sin acceso
            return df.iloc[0:0]
        def user_can_see(ws_str):
            doc_ws = {w.strip() for w in str(ws_str or "general").split(",")}
            return bool(doc_ws & set(workspace_filter))
        return df[df["workspace"].apply(user_can_see)]

    def document_exists(self, filename):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM documents WHERE filename = ?", (filename,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def update_document_workspace(self, filename, new_workspaces):
        """Cambia los grupos de acceso de un documento. new_workspaces puede ser
        una lista ['RRHH','Ventas'] o un string 'RRHH,Ventas'."""
        if isinstance(new_workspaces, list):
            ws_str = ",".join(sorted(set(new_workspaces)))
        else:
            ws_str = str(new_workspaces)

        # 1. Actualizar SQLite
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE documents SET workspace = ? WHERE filename = ?",
            (ws_str, filename)
        )
        conn.commit()
        conn.close()

        # 2. Actualizar metadata en Chroma: borrar y re-añadir con nuevo workspace
        try:
            vectorstore = self.get_vectorstore()
            data = vectorstore.get(where={"source": filename})
            if data["ids"]:
                texts = data["documents"]
                metadatas = data["metadatas"]
                ids = data["ids"]
                for m in metadatas:
                    m["workspace"] = ws_str
                vectorstore.delete(ids=ids)
                from langchain_core.documents import Document as LCDoc
                docs = [LCDoc(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
                vectorstore.add_documents(docs)
        except Exception as e:
            print(f"Error actualizando workspace en Chroma: {e}")

    def delete_document(self, filename):
        vectorstore = self.get_vectorstore()
        docs = vectorstore.get(where={"source": filename})
        if docs["ids"]:
            vectorstore.delete(ids=docs["ids"])
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
        conn.commit()
        conn.close()
        # POST-AUDITORÍA · Path traversal hardening: solo borramos si el path
        # resuelto cae dentro del DATA_DIR esperado.
        data_dir = os.getenv("DATA_DIR", "./data")
        try:
            base_real = os.path.realpath(data_dir)
            cand_real = os.path.realpath(os.path.join(data_dir, os.path.basename(filename)))
            if cand_real == base_real or cand_real.startswith(base_real + os.sep):
                if os.path.exists(cand_real):
                    os.remove(cand_real)
        except Exception:
            pass

        # Invalidar cache BM25 tras borrar
        try:
            from src.core.brain import get_brain
            _b, _ = get_brain()
            if _b is not None:
                _b.invalidate_bm25()
        except Exception:
            pass

    def update_document_summary(self, filename, summary):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE documents SET summary = ? WHERE filename = ?", (summary, filename))
        conn.commit()
        conn.close()

    def increment_doc_query_count(self, filenames):
        """Incrementa el contador de consultas para cada documento usado como fuente."""
        if not filenames:
            return
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        for fn in set(filenames):
            cursor.execute("UPDATE documents SET query_count = query_count + 1 WHERE filename = ?", (fn,))
        conn.commit()
        conn.close()

    def delete_workspace(self, workspace_name):
        """Elimina un grupo y reasigna sus documentos (solo ese grupo → 'general')."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, workspace FROM documents")
        rows = cursor.fetchall()
        docs_to_update = []
        for doc_id, filename, ws_str in rows:
            parts = [w.strip() for w in str(ws_str or "general").split(",")]
            if workspace_name in parts:
                new_parts = [w for w in parts if w != workspace_name]
                new_ws = ",".join(new_parts) if new_parts else "general"
                docs_to_update.append((new_ws, filename))
        for new_ws, filename in docs_to_update:
            cursor.execute("UPDATE documents SET workspace = ? WHERE filename = ?", (new_ws, filename))
        cursor.execute("DELETE FROM workspaces WHERE name = ?", (workspace_name,))
        conn.commit()
        conn.close()
        # Actualizar Chroma
        try:
            vectorstore = self.get_vectorstore()
            for new_ws, filename in docs_to_update:
                data = vectorstore.get(where={"source": filename})
                if data["ids"]:
                    for m in data["metadatas"]:
                        m["workspace"] = new_ws
                    vectorstore.delete(ids=data["ids"])
                    from langchain_core.documents import Document as LCDoc
                    docs = [LCDoc(page_content=t, metadata=m)
                            for t, m in zip(data["documents"], data["metadatas"])]
                    vectorstore.add_documents(docs)
        except Exception as e:
            print(f"Error actualizando Chroma al eliminar grupo: {e}")
        return len(docs_to_update)

    # --- Grupos (workspaces) ---
    def add_workspace(self, name, created_by="admin"):
        """Registra un grupo personalizado para que persista entre recargas."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO workspaces (name, created_by) VALUES (?, ?)",
            (name, created_by)
        )
        conn.commit()
        conn.close()

    def get_persisted_workspaces(self):
        """Devuelve todos los grupos guardados en la tabla workspaces."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM workspaces ORDER BY name")
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names

    def get_workspace_config(self, name):
        """Devuelve system_prompt y cite_only de un workspace."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT system_prompt, cite_only FROM workspaces WHERE name=?", (name,))
        r = cursor.fetchone()
        conn.close()
        if not r:
            return {"system_prompt": "", "cite_only": False}
        return {"system_prompt": r[0] or "", "cite_only": bool(r[1])}

    def update_workspace_config(self, name, system_prompt=None, cite_only=None):
        """Actualiza system_prompt y/o cite_only de un workspace."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        if system_prompt is not None:
            cursor.execute("UPDATE workspaces SET system_prompt=? WHERE name=?", (system_prompt, name))
        if cite_only is not None:
            cursor.execute("UPDATE workspaces SET cite_only=? WHERE name=?", (int(cite_only), name))
        conn.commit()
        conn.close()

    # --- Historial de versiones de documentos ---
    def add_document_version(self, filename, version, uploaded_by, chunk_count):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO document_versions (filename, version, uploaded_by, chunk_count) VALUES (?, ?, ?, ?)",
            (filename, version, uploaded_by, chunk_count)
        )
        conn.commit()
        conn.close()

    def get_document_versions(self, filename):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version, uploaded_by, chunk_count, upload_date FROM document_versions "
            "WHERE filename=? ORDER BY version DESC", (filename,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"version": r[0], "uploaded_by": r[1], "chunk_count": r[2], "date": r[3]} for r in rows]

    def get_document_version_count(self, filename):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM document_versions WHERE filename=?", (filename,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # --- Búsqueda en chat ---
    def search_chat_history(self, username, query, limit=20):
        """Busca mensajes en el historial de chat del usuario."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ch.session_id, cs.title, ch.role, ch.content, ch.timestamp "
            "FROM chat_history ch "
            "JOIN chat_sessions cs ON ch.session_id = cs.id "
            "WHERE cs.username = ? AND ch.content LIKE ? "
            "ORDER BY ch.timestamp DESC LIMIT ?",
            (username, f"%{query}%", limit)
        )
        results = []
        for r in cursor.fetchall():
            results.append({
                "session_id": r[0], "session_title": r[1],
                "role": r[2], "content": r[3], "timestamp": r[4]
            })
        conn.close()
        return results

    # --- API Keys ---
    def add_api_key(self, key_hash, key_prefix, username, label="", scopes=None):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_keys (key_hash, key_prefix, username, label, scopes) VALUES (?, ?, ?, ?, ?)",
            (key_hash, key_prefix, username, label, json.dumps(scopes or ["query", "documents"]))
        )
        conn.commit()
        conn.close()

    def get_api_keys(self, username=None):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        if username:
            cursor.execute(
                "SELECT id, key_prefix, username, label, scopes, created_at, last_used, active "
                "FROM api_keys WHERE username=? ORDER BY created_at DESC", (username,)
            )
        else:
            cursor.execute(
                "SELECT id, key_prefix, username, label, scopes, created_at, last_used, active "
                "FROM api_keys ORDER BY created_at DESC"
            )
        rows = cursor.fetchall()
        conn.close()
        return [{
            "id": r[0], "key_prefix": r[1], "username": r[2], "label": r[3],
            "scopes": json.loads(r[4] or '[]'), "created_at": r[5],
            "last_used": r[6], "active": bool(r[7])
        } for r in rows]

    def validate_api_key(self, key_hash):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, scopes FROM api_keys WHERE key_hash=? AND active=1", (key_hash,)
        )
        r = cursor.fetchone()
        if r:
            cursor.execute(
                "UPDATE api_keys SET last_used=CURRENT_TIMESTAMP WHERE key_hash=?", (key_hash,)
            )
            conn.commit()
        conn.close()
        if not r:
            return None
        return {"username": r[0], "scopes": json.loads(r[1] or '[]')}

    def revoke_api_key(self, key_id):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE api_keys SET active=0 WHERE id=?", (key_id,))
        conn.commit()
        conn.close()

    # --- Invitaciones ---
    def add_invitation(self, token, email, name, role, workspaces, created_by, expires_at):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invitations (token, email, name, role, workspaces, created_by, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (token, email, name, role, json.dumps(workspaces), created_by, expires_at)
        )
        conn.commit()
        conn.close()

    def get_invitation(self, token):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT token, email, name, role, workspaces, created_by, expires_at, used "
            "FROM invitations WHERE token=?", (token,)
        )
        r = cursor.fetchone()
        conn.close()
        if not r:
            return None
        return {
            "token": r[0], "email": r[1], "name": r[2], "role": r[3],
            "workspaces": json.loads(r[4] or '["general"]'),
            "created_by": r[5], "expires_at": r[6], "used": bool(r[7])
        }

    def mark_invitation_used(self, token):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE invitations SET used=1, used_at=CURRENT_TIMESTAMP WHERE token=?", (token,)
        )
        conn.commit()
        conn.close()

    def get_all_invitations(self):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT token, email, name, role, workspaces, created_by, created_at, expires_at, used "
            "FROM invitations ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return [{
            "token": r[0], "email": r[1], "name": r[2], "role": r[3],
            "workspaces": json.loads(r[4] or '["general"]'),
            "created_by": r[5], "created_at": r[6], "expires_at": r[7], "used": bool(r[8])
        } for r in rows]

    # --- Sesiones ---
    def create_session(self, username, title="Nueva conversación"):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_sessions (username, title) VALUES (?, ?)", (username, title))
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def get_user_sessions(self, username):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, created_at FROM chat_sessions WHERE username = ? ORDER BY created_at DESC",
            (username,)
        )
        sessions = [{"id": r[0], "title": r[1], "date": r[2]} for r in cursor.fetchall()]
        conn.close()
        return sessions

    def get_session_owner(self, session_id):
        """Devuelve el username dueño de la sesión, o None si no existe.
        Usado por la API REST para protección IDOR.
        """
        with closing(sqlite3.connect(self.sqlite_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT username FROM chat_sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def delete_session(self, session_id, username=None):
        """Elimina una sesión. Si se pasa username, requiere ownership."""
        with closing(sqlite3.connect(self.sqlite_path)) as conn:
            cur = conn.cursor()
            if username is None:
                cur.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            else:
                cur.execute(
                    "DELETE FROM chat_sessions WHERE id = ? AND username = ?",
                    (session_id, username),
                )
            conn.commit()

    def update_session_title(self, session_id, title, username=None):
        """Renombra una sesión. Si se pasa username, requiere ownership."""
        with closing(sqlite3.connect(self.sqlite_path)) as conn:
            cur = conn.cursor()
            if username is None:
                cur.execute(
                    "UPDATE chat_sessions SET title = ? WHERE id = ?",
                    (title[:50], session_id),
                )
            else:
                cur.execute(
                    "UPDATE chat_sessions SET title = ? WHERE id = ? AND username = ?",
                    (title[:50], session_id, username),
                )
            conn.commit()

    # --- Mensajes ---
    def save_message(self, username, role, content, session_id):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (username, role, content, session_id) VALUES (?, ?, ?, ?)",
            (username, role, content, session_id)
        )
        conn.commit()
        conn.close()

    def get_chat_history(self, session_id, limit=50):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
            (session_id, limit)
        )
        history = [{"role": r, "content": c} for r, c in cursor.fetchall()]
        conn.close()
        return history

    # --- Feedback ---
    def save_feedback(self, session_id, message_index, username, rating):
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO feedback (session_id, message_index, username, rating) VALUES (?, ?, ?, ?)",
                (session_id, message_index, username, rating)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving feedback: {e}")

    def get_feedback_for_session(self, session_id):
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message_index, rating FROM feedback WHERE session_id = ?",
                (session_id,)
            )
            result = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            return result
        except Exception:
            return {}

    # --- Analytics ---
    def get_analytics(self):
        try:
            conn = sqlite3.connect(self.sqlite_path)
            queries_per_user = pd.read_sql_query(
                "SELECT username, COUNT(*) as total FROM audit_logs WHERE action='QUERY' GROUP BY username ORDER BY total DESC",
                conn
            )
            uploads_per_user = pd.read_sql_query(
                "SELECT username, COUNT(*) as total FROM audit_logs WHERE action='UPLOAD' GROUP BY username ORDER BY total DESC",
                conn
            )
            daily_activity = pd.read_sql_query(
                "SELECT DATE(timestamp) as Fecha, COUNT(*) as Consultas FROM audit_logs WHERE action='QUERY' GROUP BY DATE(timestamp) ORDER BY Fecha DESC LIMIT 30",
                conn
            )
            feedback_summary = pd.read_sql_query(
                "SELECT CASE WHEN rating=1 THEN 'Positivo' ELSE 'Negativo' END as tipo, COUNT(*) as total FROM feedback GROUP BY rating",
                conn
            )
            monthly_queries = pd.read_sql_query(
                "SELECT COUNT(*) as total FROM audit_logs WHERE action='QUERY' "
                "AND DATE(timestamp) >= DATE('now', 'start of month')", conn
            )
            top_docs = pd.read_sql_query(
                "SELECT filename, query_count FROM documents ORDER BY query_count DESC LIMIT 5", conn
            )
            conn.close()
            return {
                "queries_per_user": queries_per_user,
                "uploads_per_user": uploads_per_user,
                "daily_activity": daily_activity,
                "feedback_summary": feedback_summary,
                "monthly_queries": monthly_queries,
                "top_docs": top_docs,
            }
        except Exception as e:
            print(f"Error fetching analytics: {e}")
            return {}

    # --- Roles ---
    def get_all_roles(self):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name,description,base_role,workspaces,can_upload,upload_groups,can_delete,delete_groups,color,is_system FROM roles ORDER BY is_system DESC, name")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for r in rows:
            result.append({
                "name": r[0], "description": r[1], "base_role": r[2],
                "workspaces": json.loads(r[3] or '["general"]'),
                "can_upload": bool(r[4]),
                "upload_groups": json.loads(r[5] or '[]'),
                "can_delete": bool(r[6]),
                "delete_groups": json.loads(r[7] or '[]'),
                "color": r[8] or "#818cf8",
                "is_system": bool(r[9]),
            })
        return result

    def get_role(self, name):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name,description,base_role,workspaces,can_upload,upload_groups,can_delete,delete_groups,color,is_system FROM roles WHERE name=?", (name,))
        r = cursor.fetchone()
        conn.close()
        if not r:
            return None
        return {
            "name": r[0], "description": r[1], "base_role": r[2],
            "workspaces": json.loads(r[3] or '["general"]'),
            "can_upload": bool(r[4]),
            "upload_groups": json.loads(r[5] or '[]'),
            "can_delete": bool(r[6]),
            "delete_groups": json.loads(r[7] or '[]'),
            "color": r[8] or "#818cf8",
            "is_system": bool(r[9]),
        }

    def save_role(self, name, description, base_role, workspaces, can_upload,
                  upload_groups, can_delete, delete_groups, color="#818cf8"):
        import json
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO roles "
            "(name,description,base_role,workspaces,can_upload,upload_groups,can_delete,delete_groups,color,is_system)"
            " VALUES (?,?,?,?,?,?,?,?,?,0)",
            (name, description, base_role,
             json.dumps(workspaces), int(can_upload), json.dumps(upload_groups),
             int(can_delete), json.dumps(delete_groups), color)
        )
        conn.commit()
        conn.close()

    def delete_role(self, name):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM roles WHERE name=? AND is_system=0", (name,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def rename_workspace(self, old_name, new_name):
        """Renombra un grupo en SQLite (workspaces + documentos) y en Chroma."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        # Tabla workspaces
        cursor.execute("UPDATE workspaces SET name = ? WHERE name = ?", (new_name, old_name))
        # Columna workspace en documentos (pueden ser multi-grupo separados por coma)
        cursor.execute("SELECT filename, workspace FROM documents")
        rows = cursor.fetchall()
        for filename, ws_str in rows:
            parts = [w.strip() for w in str(ws_str or "general").split(",")]
            if old_name in parts:
                new_parts = [new_name if w == old_name else w for w in parts]
                cursor.execute("UPDATE documents SET workspace = ? WHERE filename = ?",
                               (",".join(new_parts), filename))
        conn.commit()
        conn.close()
        # Actualizar Chroma
        try:
            vectorstore = self.get_vectorstore()
            data = vectorstore.get()
            if data["ids"]:
                to_update = []
                for i, (doc_id, text, meta) in enumerate(
                    zip(data["ids"], data["documents"], data["metadatas"])
                ):
                    ws_str = meta.get("workspace", "general")
                    parts = [w.strip() for w in ws_str.split(",")]
                    if old_name in parts:
                        new_meta = dict(meta)
                        new_meta["workspace"] = ",".join(
                            [new_name if w == old_name else w for w in parts]
                        )
                        to_update.append((doc_id, text, new_meta))
                if to_update:
                    vectorstore.delete(ids=[d[0] for d in to_update])
                    from langchain_core.documents import Document as LCDoc
                    vectorstore.add_documents(
                        [LCDoc(page_content=t, metadata=m) for _, t, m in to_update]
                    )
        except Exception as e:
            print(f"Error renombrando workspace en Chroma: {e}")

    # --- Reset total ---
    def nuclear_reset(self):
        import shutil
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path)
        os.makedirs(self.db_path, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        for table in ["chat_history", "chat_sessions", "documents", "feedback", "workspaces", "roles", "users", "settings"]:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
        conn.close()
        self._init_sqlite()
        if os.path.exists("data"):
            shutil.rmtree("data")
        os.makedirs("data", exist_ok=True)
        return True

db_manager = DatabaseManager()
