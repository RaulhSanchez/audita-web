# Cambios aplicados tras la auditoría · Mayo 2026

Este documento resume los fixes aplicados al proyecto entregado. Cada
cambio está marcado en el código con un comentario `POST-AUDITORÍA`.

## FASE 1 · Bloqueantes para vender (todos completados)

### 1.1 · Limpieza del repositorio y rotación de secretos
- `.gitignore` reescrito con cobertura de `db/`, `data/`, `logs/`,
  `backups/`, `*.db`, `*.sqlite*`, `.env`, `*.zip`, `nginx/certs/`,
  `.DS_Store`, `*.pptx`, `scratch/`, `.claude/worktrees/`, `Raul_Huete_CV.pdf`.
- `config.yaml` ya no contiene hashes bcrypt ni la cookie key. La cookie
  key se carga de `COOKIE_SECRET_KEY` (`.env`); si está vacía, la app la
  genera y la persiste en `config.runtime.yaml` (fuera del repo).
- `userdb.migrate_from_yaml()` reescrito: ya NO migra el hash hardcoded.
  Crea el admin inicial usando `ADMIN_INITIAL_PASSWORD`. Si la variable
  está vacía, genera una contraseña aleatoria y la imprime en logs UNA
  vez, marcándola como temporal (login obliga a cambiarla).
- `MANUAL_DE_INSTALACION.md` reescrito sin credenciales por defecto.
- `clients.json` vaciado (eliminadas las claves de ejemplo).

### 1.2 · `requirements.txt`
- Añadidas dependencias que el código importaba pero no estaban
  declaradas: `ragas`, `pyotp`, `qrcode[pil]`, `sqlalchemy`,
  `google-auth`, `google-auth-oauthlib`, `google-api-python-client`,
  `httpx`, `langgraph`, `pydantic`.
- Añadido upper-bound a todas las dependencias para evitar major
  releases que rompan la app.
- `streamlit` actualizado de `==1.37.1` a `>=1.40,<2.0` (CVEs corregidas).

### 1.3 · Dockerfile + `.dockerignore` + `docker-compose.yml`
- `Dockerfile` reescrito con multi-stage build, usuario no-root
  (`cortexa:1000`), `HEALTHCHECK`, dependencias mínimas.
- `.dockerignore` creado: excluye `db/`, `data/`, `logs/`, `.env`,
  `nginx/certs/`, `*.pptx`, `tests/`, `landing/`, `scratch/`, `.git/`.
- `docker-compose.yml` reescrito: healthchecks en `app` y `proxy`,
  `depends_on: condition: service_healthy`, volúmenes nombrados, perfil
  `with-ollama` opcional para despliegue 100% contenedorizado, `env_file:
  .env`, ya no monta `src/` ni `app.py` (inmutabilidad).

### 1.4 · API REST: CORS + IDOR
- `src/api/main.py` reescrito.
- `CORS_ORIGINS` sin default `*` (lista vacía + WARNING en logs).
- `_require_session_owner()` añadido. Endpoints
  `/api/sessions/{id}/messages`, `DELETE /api/sessions/{id}` y `PATCH
  /api/sessions/{id}` validan ownership antes de operar (404 si no es
  del usuario, para no revelar existencia).
- `db_manager.get_session_owner()` añadido en `database.py`.
- Sanitización de `filename` con basename + regex `[A-Za-z0-9._-]` y
  `realpath` antes de `os.path.join`.
- Tamaño máximo de upload aplicado en bucle de lectura (no después).

### 1.5 · Race condition cross-tenant en RAG (`brain.py`)
- Eliminados `self._last_sources` / `self._last_chunks` como atributos
  del singleton.
- Reemplazados por `contextvars.ContextVar` (aislamiento per-request).
- API recomendada nueva: `CortexaBrain.get_last_sources()` y
  `get_last_chunks()`.
- Properties `_last_sources` / `_last_chunks` mantenidas como
  backward-compat (leen de contextvars).
- `dashboard.py` actualizado a la API nueva.

### 1.6 · Path traversal en uploads
- `src/pages/library.py`: helpers `_sanitize_filename` y
  `_safe_save_path` añadidos. Sustituidos los 3 puntos donde se hacía
  `os.path.join("data", uf.name)` sin sanitizar.
- `src/api/main.py`: misma defensa con `_sanitize_filename` y
  `_verify_path_within`.
- `src/core/database.py:delete_document`: realpath verifica que cae
  dentro de `DATA_DIR` antes de borrar.

### 1.7 · Pricing alineado con la web
- `src/services/plan_service.py`: precios y límites cambiados a:
  - Starter: 299 €/mes, 5 usuarios, 500 documentos, 100 queries/día.
  - Business: 699 €/mes, 25 usuarios, documentos ilimitados, 1.000 queries/día.
  - Enterprise: A consultar, ilimitado, ilimitado.
- Coincide con `docs/pricing.html`.

### 1.8 · Formulario de demo y emails unificados
- `docs/index.html`: `access_key` ahora se inyecta desde `data-access-key`
  con instrucciones claras de Web3Forms; honeypot anti-spam añadido.
- Todos los `92sanchez.raul@gmail.com` sustituidos por `hola@cortexa.ai`.
- Política de privacidad apunta a `/privacidad.html` (no `#`).

### 1.9 · Eliminada landing duplicada
- `landing/` borrada por completo.
- `docs/index.html` queda como home y enlaza a `pricing.html` desde la
  navegación principal y mobile.

### 1.10 · SSO collision + demo seed seguro
- `sso_service.py`: el username generado a partir del email ahora
  incluye un sufijo de 8 hex del hash del email original (evita
  colisiones tipo `john.doe` vs `john_doe`). Si encuentra una cuenta
  existente con email distinto, aborta con `PermissionError`.
- `demo/seed_demo.py`: eliminado el fallback SHA-256 sin salt. Si
  `bcrypt` no está instalado, el seed aborta con código 2 y mensaje
  claro.

## FASE 2 · Antes del piloto cliente

### 2.1 · Nginx hardened
- `nginx/nginx.conf` reescrito.
- TLS 1.2+1.3, ciphers fuertes, sesión sin tickets.
- Cabeceras `Strict-Transport-Security`, `X-Frame-Options: SAMEORIGIN`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`,
  `Permissions-Policy`, `Content-Security-Policy`.
- `limit_req_zone api` 10 r/s, `limit_conn` 20 conexiones por IP.
- Timeouts cambiados de 86400s (24h) a 300s.
- `client_max_body_size` alineado con MAX_FILE_SIZE_MB (50M).
- Endpoint `/healthz` para liveness probes.
- Compresión gzip activada.

### 2.2 · Cifrado de settings sensibles
- Nuevo módulo `src/core/secrets_box.py` con Fernet (AES-128 CBC + HMAC).
- Lista blanca explícita: `smtp_pass`, `sso_*_client_secret`, `ldap_bind_password`,
  `connector_*_secret`, `service_account_json`, `vendor_master_key`.
- `userdb.set_setting()` cifra automáticamente si la clave está en la
  lista; `userdb.get_setting()` descifra al leer.
- Modo backward-compat: si `SETTINGS_ENCRYPTION_KEY` no está, sigue
  guardando en plaintext con WARNING en logs.

### 2.3 · `with closing(...)` en SQLite (parcial)
- `database.py`: `closing` importado e introducido en
  `get_session_owner`, `delete_session`, `update_session_title` (rutas
  IDOR-críticas). El resto del refactor es trabajo de Fase 3 dado el
  volumen.

### 2.4 · LICENSE + SECURITY.md + RUNBOOK.md
- `LICENSE` propietaria comercial española (ley aplicable Madrid).
- `SECURITY.md` con política de reporte (security@cortexa.ai), SLAs,
  buenas prácticas para clientes.
- `RUNBOOK.md` con procedimientos: despliegue de cliente nuevo, backup,
  restore, actualizaciones, incidentes comunes, monitorización.

### 2.5 · Bugs altos
- `src/tools/calculator.py`: anti-DoS — exponente máximo 1024 en
  operaciones `**`.
- `src/core/sqldb.py`: nuevo `_md_escape()` aplicado en
  `_rows_to_markdown` para evitar Markdown injection / prompt injection
  desde resultados SQL.
- `src/tools/kb_search.py`: `list_available_documents` ahora maneja el
  DataFrame correctamente (antes intentaba iterar columnas como dicts).
- `vendor_monitor.py`: rechaza URLs no `https://` y verifica
  certificado.
- `health_check.py`: `check_chroma` reemplazado por `check_qdrant`;
  eliminado check sobre `users.db` (no existe en producción).
- `src/core/userdb.py:update_user`: whitelist explícita de columnas
  (`_USER_UPDATABLE_COLS`) para prevenir SQLi vía f-string.

### 2.6 · UX
- `app.py`: bloque "¿Olvidaste tu contraseña?" con flujo email reset
  (anti-enumeración de cuentas).
- `dashboard.py`: indicador visible cuando "Modo Agente" está activo.
- Mensajes de error específicos por tipo de fallo (Ollama caído,
  timeout, otros) con código de soporte (`AGENT_INIT_FAIL`).
- `requirements.txt`: BM25 corpus cacheado (no se reconstruye en cada
  query) — invalidación al insertar/borrar documentos.

## Performance

El cambio más visible: **el primer query no tarda 30 segundos** en
colecciones medianas. La construcción del corpus BM25 (era la causa)
ahora es lazy y cacheada.

## Pendientes / Recomendados (Fase 3)

- Dividir `src/pages/admin.py` (2.267 líneas) en módulos por tab.
- Sustituir `print()` por `logging` con formato JSON.
- Añadir índices SQL: `idx_audit_timestamp`, `idx_audit_username`.
- CSRF token explícito y SameSite=Strict en cookies.
- Reescribir el JS inyectado en `app.py:218-315` (sustituir por sidebar
  nativo de Streamlit ≥1.40).
- TTL en invitaciones y rate-limit en su creación.
- Servir Google Fonts localmente (coherencia "100% local").
- Tests automatizados con `pytest` y CI con GitHub Actions.
- DPA (Data Processing Agreement), SLA formal, política de retención.
- Conseguir 1-2 logos de cliente piloto para la web.
