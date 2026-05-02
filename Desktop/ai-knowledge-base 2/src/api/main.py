"""
src/api/main.py
FastAPI REST + Streaming API para Cortexa AI.

POST-AUDITORÍA · Cambios principales:
  - CORS: SIN wildcard. Si CORS_ORIGINS no está definida, lista vacía y
    se loggea WARNING. Métodos y headers explícitos.
  - IDOR: /api/sessions/{id}/messages, delete y rename verifican que la
    sesión pertenece al usuario autenticado.
  - Path traversal: el filename se sanitiza con basename + whitelist regex
    antes de cualquier os.path.join.
  - Subida: descarga máxima limitada a MAX_FILE_SIZE_MB (variable de entorno).

Endpoints:
  GET    /api/health
  GET    /api/documents
  POST   /api/documents/upload
  POST   /api/query
  POST   /api/agent
  GET    /api/sessions
  GET    /api/sessions/{id}/messages
  DELETE /api/sessions/{id}
  PATCH  /api/sessions/{id}
"""
from __future__ import annotations
import os
import re
import hashlib
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

logger = logging.getLogger("cortexa.api")

app = FastAPI(
    title="Cortexa AI API",
    description="REST + Streaming API para la base de conocimiento corporativa Cortexa AI.",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS (sin wildcard) ───────────────────────────────────────────────────
_cors_raw = os.getenv("CORS_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else []
if not _cors_origins:
    logger.warning(
        "CORS_ORIGINS vacía: la API solo aceptará peticiones same-origin. "
        "Configura CORS_ORIGINS en .env para habilitar dominios externos."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

_bearer = HTTPBearer(auto_error=False)

# Sanitizador de nombres de archivo: solo alfanumérico, guion, underscore, punto
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024


def _sanitize_filename(raw: str) -> str:
    """Sanitiza el nombre de archivo. Lanza HTTPException(400) si no es válido."""
    if not raw:
        raise HTTPException(400, "Nombre de archivo vacío.")
    base = os.path.basename(raw)  # quita cualquier path
    if not _SAFE_NAME.match(base) or base in (".", ".."):
        raise HTTPException(400, "Nombre de archivo inválido. Solo se permiten letras, dígitos, ., - y _.")
    return base


def _data_dir() -> str:
    return os.getenv("DATA_DIR", "./data")


def _verify_path_within(target: str, base: str) -> str:
    """Resuelve realpath y verifica que target queda dentro de base."""
    real_base = os.path.realpath(base)
    real_target = os.path.realpath(target)
    if not real_target.startswith(real_base + os.sep) and real_target != real_base:
        raise HTTPException(400, "Ruta inválida.")
    return real_target


# ── Autenticación ─────────────────────────────────────────────────────────────

def _resolve_api_key(token: str) -> dict | None:
    """Valida una API Key y devuelve la info del usuario."""
    from src.core.database import db_manager
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    return db_manager.validate_api_key(key_hash)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="API Key requerida (Bearer token).")
    user_info = _resolve_api_key(creds.credentials)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="API Key inválida o revocada.")
    return user_info


def require_scope(scope: str):
    def _check(user: dict = Depends(get_current_user)):
        scopes = user.get("scopes", [])
        if scope not in scopes and "admin" not in scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Scope '{scope}' requerido.")
        return user
    return _check


def _require_session_owner(session_id: int, username: str) -> None:
    """
    Garantiza que la sesión pertenece al usuario. Lanza 404 si no existe (no
    revelamos si existe pero pertenece a otro). Esto cierra la vulnerabilidad
    IDOR detectada en la auditoría.
    """
    from src.core.database import db_manager
    try:
        owner = db_manager.get_session_owner(session_id)  # implementado en DB
    except AttributeError:
        # Fallback si la BD aún no tiene get_session_owner — usamos el listado
        sessions = db_manager.get_user_sessions(username)
        if not any(s.get("id") == session_id for s in sessions):
            raise HTTPException(404, "Sesión no encontrada.")
        return
    if owner is None:
        raise HTTPException(404, "Sesión no encontrada.")
    if owner != username:
        # Devolvemos 404 (no 403) para no filtrar la existencia de la sesión.
        raise HTTPException(404, "Sesión no encontrada.")


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    history: list[list[str]] = []   # [["human","…"], ["ai","…"]]
    workspaces: list[str] | None = None
    cite_only: bool = False


class AgentRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    history: list[list[str]] = []
    workspaces: list[str] | None = None


class SessionUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Sistema"])
def health():
    """Estado de los servicios principales."""
    from src.core.brain import get_brain
    from src.core.database import db_manager

    brain, brain_err = get_brain()
    try:
        vs = db_manager.get_vectorstore()
        doc_count = vs.count()
        vs_ok = True
    except Exception as e:
        doc_count = 0
        vs_ok = False
        logger.exception("VS health check fallido: %s", e)

    return {
        "status": "ok" if (brain and vs_ok) else "degraded",
        "llm":    {"ok": brain is not None, "model": getattr(brain, "model_name", None), "error": brain_err},
        "vectorstore": {"ok": vs_ok, "documents": doc_count},
    }


# ── Documentos ───────────────────────────────────────────────────────────────

@app.get("/api/documents", tags=["Documentos"])
def list_documents(user: dict = Depends(require_scope("documents"))):
    """Lista los documentos accesibles para el usuario."""
    from src.core.database import db_manager
    from src.core.userdb import userdb

    user_data = userdb.get_user(user["username"]) or {}
    role = user_data.get("role", "viewer")
    workspaces = ["all"] if role == "admin" else user_data.get("workspaces", ["general"])

    docs_df = db_manager.get_all_documents(workspace_filter=workspaces)
    if docs_df is None or (hasattr(docs_df, "empty") and docs_df.empty):
        return {"documents": [], "total": 0}

    docs = docs_df[["filename", "workspace", "upload_date", "user",
                     "chunk_count", "query_count", "summary"]].to_dict(orient="records")
    return {"documents": docs, "total": len(docs)}


@app.post("/api/documents/upload", tags=["Documentos"], status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    workspace: str = Form("general"),
    user: dict = Depends(require_scope("documents")),
):
    """Sube e indexa un documento (PDF o DOCX). Tamaño máximo: MAX_FILE_SIZE_MB."""
    import tempfile, shutil
    from src.services.ingest_service import ingest_service
    from src.core.database import db_manager

    safe_name = _sanitize_filename(file.filename or "")
    if not safe_name.lower().endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(400, "Solo se admiten archivos PDF o DOCX.")

    # Lectura con límite de tamaño
    contents = b""
    chunk_size = 1024 * 1024  # 1 MB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        contents += chunk
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"El archivo supera el límite de {MAX_UPLOAD_BYTES // (1024*1024)} MB.")

    if db_manager.document_exists(safe_name):
        raise HTTPException(409, f"'{safe_name}' ya está indexado. Usa /reindex para actualizarlo.")

    data_dir = _data_dir()
    os.makedirs(data_dir, exist_ok=True)
    save_path = _verify_path_within(os.path.join(data_dir, safe_name), data_dir)

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(safe_name)[1]) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        shutil.copy(tmp_path, save_path)
        ok, msg = ingest_service.process_file(save_path, user["username"], workspace)
        if not ok:
            raise HTTPException(422, msg)
        return {"ok": True, "message": msg, "filename": safe_name}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── Query RAG ────────────────────────────────────────────────────────────────

@app.post("/api/query", tags=["Consultas"])
def query_rag(req: QueryRequest, user: dict = Depends(require_scope("query"))):
    """
    Consulta RAG con streaming SSE.
    Devuelve text/event-stream con chunks de la respuesta.
    """
    from src.core.brain import get_brain
    from src.core.userdb import userdb

    brain, err = get_brain()
    if not brain:
        raise HTTPException(503, f"LLM no disponible: {err}")

    user_data = userdb.get_user(user["username"]) or {}
    role = user_data.get("role", "viewer")
    workspaces = req.workspaces or (
        ["all"] if role == "admin" else user_data.get("workspaces", ["general"])
    )

    history = [(r, c) for r, c in req.history]

    def _stream() -> AsyncIterator[str]:
        for chunk in brain.query_stream(
            req.question, history,
            workspaces=workspaces,
            cite_only=req.cite_only,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


# ── Query Agente ─────────────────────────────────────────────────────────────

@app.post("/api/agent", tags=["Consultas"])
def query_agent(req: AgentRequest, user: dict = Depends(require_scope("query"))):
    """
    Consulta al agente LangGraph con streaming SSE.
    El agente puede usar herramientas (búsqueda, SQL, calculadora…).
    """
    from src.core.agent import get_agent
    from src.core.userdb import userdb

    agent, err = get_agent()
    if not agent:
        raise HTTPException(503, f"Agente no disponible: {err}")

    user_data = userdb.get_user(user["username"]) or {}
    role = user_data.get("role", "viewer")
    workspaces = req.workspaces or (
        ["all"] if role == "admin" else user_data.get("workspaces", ["general"])
    )

    history = [(r, c) for r, c in req.history]

    def _stream():
        for chunk in agent.stream(req.question, history, workspaces=workspaces):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


# ── Sesiones de chat ─────────────────────────────────────────────────────────

@app.get("/api/sessions", tags=["Chat"])
def get_sessions(user: dict = Depends(require_scope("query"))):
    """Devuelve el historial de sesiones de chat DEL USUARIO autenticado."""
    from src.core.database import db_manager
    sessions = db_manager.get_user_sessions(user["username"])
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}/messages", tags=["Chat"])
def get_messages(session_id: int, user: dict = Depends(require_scope("query"))):
    """
    Devuelve los mensajes de una sesión. Verifica que la sesión pertenece al
    usuario autenticado (cierra IDOR).
    """
    from src.core.database import db_manager
    _require_session_owner(session_id, user["username"])
    messages = db_manager.get_chat_history(session_id)
    return {"messages": messages, "session_id": session_id}


@app.delete("/api/sessions/{session_id}", tags=["Chat"], status_code=204)
def delete_session(session_id: int, user: dict = Depends(require_scope("query"))):
    """Elimina una sesión de chat propiedad del usuario."""
    from src.core.database import db_manager
    _require_session_owner(session_id, user["username"])
    db_manager.delete_session(session_id)


@app.patch("/api/sessions/{session_id}", tags=["Chat"])
def rename_session(session_id: int,
                   payload: SessionUpdate = Body(...),
                   user: dict = Depends(require_scope("query"))):
    """Renombra una sesión propiedad del usuario."""
    from src.core.database import db_manager
    _require_session_owner(session_id, user["username"])
    db_manager.update_session_title(session_id, payload.title)
    return {"ok": True, "session_id": session_id, "title": payload.title}
