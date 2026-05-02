"""
src/core/sqldb.py
Gestión de conexiones SQL para Text-to-SQL.

Soporta SQLite (nativo) y cualquier base de datos compatible con SQLAlchemy
(PostgreSQL, MySQL, MS SQL Server…).

Seguridad:
  - Solo se permiten consultas SELECT / WITH / EXPLAIN
  - El workspace controla qué bases de datos puede ver cada usuario
  - Las connection strings se guardan en cortexa_meta.db (recomendado: variables
    de entorno para producción)
"""
from __future__ import annotations
import re
import sqlite3
from typing import Any

_SQLITE_PATH = "./db/cortexa_meta.db"

# ── DDL — creada en database.py al arrancar ──────────────────────────────────
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS sql_databases (
    name            TEXT PRIMARY KEY,
    description     TEXT DEFAULT '',
    connection_str  TEXT NOT NULL,
    workspaces      TEXT DEFAULT 'general',
    created_by      TEXT DEFAULT 'admin',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Palabras clave permitidas al inicio de la consulta (solo lectura)
_ALLOWED_PREFIXES = re.compile(
    r"^\s*(SELECT|WITH|EXPLAIN|PRAGMA)\b", re.IGNORECASE
)
# Palabras peligrosas que NUNCA deben aparecer en la query
_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|ATTACH|DETACH"
    r"|GRANT|REVOKE|EXEC|EXECUTE|CALL|COPY|LOAD)\b",
    re.IGNORECASE,
)


def _ensure_table():
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.execute(CREATE_SQL)
    conn.commit()
    conn.close()


# ── CRUD ─────────────────────────────────────────────────────────────────────

def register_database(name: str, description: str, connection_str: str,
                      workspaces: str, created_by: str = "admin") -> None:
    """Registra (o actualiza) una base de datos SQL accesible desde el agente."""
    _ensure_table()
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO sql_databases "
        "(name, description, connection_str, workspaces, created_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (name.strip(), description, connection_str.strip(), workspaces, created_by),
    )
    conn.commit()
    conn.close()


def delete_database(name: str) -> bool:
    _ensure_table()
    conn = sqlite3.connect(_SQLITE_PATH)
    cur = conn.execute("DELETE FROM sql_databases WHERE name=?", (name,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_all_databases() -> list[dict]:
    _ensure_table()
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT name, description, connection_str, workspaces, created_by, created_at "
        "FROM sql_databases ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_databases_for_workspaces(workspaces: list[str] | None) -> list[dict]:
    """Devuelve solo las bases de datos accesibles para los workspaces del usuario."""
    all_dbs = get_all_databases()
    if workspaces is None or "all" in workspaces:
        return all_dbs
    result = []
    for db in all_dbs:
        db_ws = {w.strip() for w in db["workspaces"].split(",")}
        if db_ws & set(workspaces):
            result.append(db)
    return result


# ── Introspección de esquema ─────────────────────────────────────────────────

def _get_engine(connection_str: str):
    """Retorna un engine SQLAlchemy para la connection string dada."""
    try:
        from sqlalchemy import create_engine
        return create_engine(connection_str, future=True)
    except ImportError:
        raise RuntimeError(
            "SQLAlchemy no está instalado. Ejecuta: pip install sqlalchemy"
        )


def get_schema(db_name: str, workspaces: list[str] | None = None) -> str:
    """
    Retorna el esquema de la base de datos (tablas y columnas) como texto.
    Usado por el LLM para generar SQL correcto.
    """
    accessible = get_databases_for_workspaces(workspaces)
    db_info = next((d for d in accessible if d["name"] == db_name), None)
    if not db_info:
        return f"Base de datos '{db_name}' no encontrada o sin acceso."

    conn_str = db_info["connection_str"]

    # SQLite nativo (sin SQLAlchemy necesario)
    if conn_str.startswith("sqlite:///") or conn_str.endswith(".db") or conn_str.endswith(".sqlite"):
        path = conn_str.replace("sqlite:///", "")
        return _sqlite_schema(path)

    # Cualquier otro motor vía SQLAlchemy
    try:
        from sqlalchemy import inspect, text
        engine = _get_engine(conn_str)
        inspector = inspect(engine)
        lines = [f"-- Base de datos: {db_name}"]
        for table in inspector.get_table_names():
            cols = inspector.get_columns(table)
            col_defs = ", ".join(f"{c['name']} {c['type']}" for c in cols)
            lines.append(f"CREATE TABLE {table} ({col_defs});")
        return "\n".join(lines)
    except Exception as e:
        return f"Error obteniendo esquema: {e}"


def _sqlite_schema(path: str) -> str:
    """Esquema de un fichero SQLite."""
    try:
        conn = sqlite3.connect(path)
        cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return "La base de datos está vacía (sin tablas)."
        return "\n".join(sql for _, sql in rows if sql)
    except Exception as e:
        return f"Error leyendo esquema SQLite: {e}"


# ── Ejecución segura ─────────────────────────────────────────────────────────

def execute_readonly(db_name: str, sql: str,
                     workspaces: list[str] | None = None,
                     max_rows: int = 100) -> tuple[bool, Any]:
    """
    Ejecuta una consulta SQL de solo lectura.
    Retorna (ok: bool, result: str | error_str).
    """
    # 1. Validación de seguridad
    sql_clean = sql.strip().rstrip(";")
    if not _ALLOWED_PREFIXES.match(sql_clean):
        return False, "Solo se permiten consultas SELECT, WITH o EXPLAIN."
    if _DANGEROUS.search(sql_clean):
        return False, "La consulta contiene operaciones no permitidas."

    # 2. Verificar acceso
    accessible = get_databases_for_workspaces(workspaces)
    db_info = next((d for d in accessible if d["name"] == db_name), None)
    if not db_info:
        return False, f"Base de datos '{db_name}' no encontrada o sin acceso."

    conn_str = db_info["connection_str"]

    # 3. Ejecutar
    try:
        if conn_str.startswith("sqlite:///") or conn_str.endswith(".db") or conn_str.endswith(".sqlite"):
            path = conn_str.replace("sqlite:///", "")
            return _execute_sqlite(path, sql_clean, max_rows)
        else:
            return _execute_sqlalchemy(conn_str, sql_clean, max_rows)
    except Exception as e:
        return False, f"Error ejecutando consulta: {e}"


def _execute_sqlite(path: str, sql: str, max_rows: int) -> tuple[bool, str]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in (cur.description or [])]
        rows = cur.fetchmany(max_rows)
        return True, _rows_to_markdown(columns, rows, max_rows)
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def _execute_sqlalchemy(conn_str: str, sql: str, max_rows: int) -> tuple[bool, str]:
    from sqlalchemy import text
    engine = _get_engine(conn_str)
    with engine.connect() as connection:
        result = connection.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchmany(max_rows)
    return True, _rows_to_markdown(columns, rows, max_rows)


def _md_escape(value) -> str:
    """
    POST-AUDITORÍA · Escape para celdas de tabla Markdown.
    Sin esto, una columna que contenga '|' o saltos de línea rompe el render
    Y, peor, abre vector de prompt injection contra el LLM downstream.
    """
    s = str(value if value is not None else "")
    # Convertir saltos de línea y tabs a espacio
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # Escapar el separador de columnas Markdown
    s = s.replace("|", "\\|")
    # Limitar tamaño por celda para evitar respuestas con tablas inmensas
    if len(s) > 500:
        s = s[:500] + "…"
    return s


def _rows_to_markdown(columns: list, rows: list, limit: int) -> str:
    if not rows:
        return "La consulta no devolvió resultados."
    header = " | ".join(_md_escape(c) for c in columns)
    sep    = " | ".join(["---"] * len(columns))
    lines  = [f"| {header} |", f"| {sep} |"]
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(v) for v in row) + " |")
    note = f"\n_(mostrando {len(rows)} de hasta {limit} filas)_" if len(rows) == limit else ""
    return "\n".join(lines) + note


# ── Test de conexión ─────────────────────────────────────────────────────────

def test_connection(connection_str: str) -> tuple[bool, str]:
    """Verifica que la connection string es válida y hay conectividad."""
    try:
        if connection_str.endswith(".db") or connection_str.endswith(".sqlite") \
                or connection_str.startswith("sqlite:///"):
            path = connection_str.replace("sqlite:///", "")
            conn = sqlite3.connect(path)
            conn.execute("SELECT 1")
            conn.close()
            return True, "Conexión SQLite correcta."
        else:
            from sqlalchemy import text
            engine = _get_engine(connection_str)
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
            return True, "Conexión correcta."
    except Exception as e:
        return False, str(e)
