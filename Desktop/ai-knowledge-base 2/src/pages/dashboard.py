import streamlit as st
from src.core.brain import get_brain
from src.core.database import db_manager
from src.core.userdb import userdb
from src.services.audit_service import audit_service
from src.services.user_service import user_service
from src.services.rate_limiter import rate_limiter
from src.services.verifier_service import verifier_service
from datetime import datetime


def _export_chat_md(messages, title):
    """Genera el contenido del chat como markdown para descargar."""
    try:
        product_name = userdb.get_setting('product_name', 'Cortexa AI')
    except Exception:
        product_name = 'Cortexa AI'
    lines = [f"# {title}", f"_Exportado el {datetime.now().strftime('%d/%m/%Y %H:%M')}_\n"]
    for m in messages:
        if m["role"] == "user":
            lines.append(f"## 🧑 Tú\n{m['content']}\n")
        else:
            lines.append(f"## 🤖 {product_name}\n{m['content']}\n")
        lines.append("---")
    return "\n".join(lines)


def _export_chat_html(messages, title):
    """Feature N: Genera el chat como HTML imprimible (Ctrl+P → PDF en navegador)."""
    import html as _hl
    try:
        product_name = userdb.get_setting('product_name', 'Cortexa AI')
    except Exception:
        product_name = 'Cortexa AI'

    rows = []
    for m in messages:
        is_user = m["role"] == "user"
        role_label = "🧑 Tú" if is_user else f"🤖 {product_name}"
        bg     = "#f1f5f9" if is_user else "#ffffff"
        border = "#cbd5e1" if is_user else "#e2e8f0"
        color  = "#1e40af" if is_user else "#6d28d9"
        content_escaped = _hl.escape(m["content"]).replace("\n", "<br>")
        ts_str = ""
        if m.get("ts"):
            try:
                _ts = datetime.fromisoformat(m["ts"])
                ts_str = f"<div class='ts'>{_ts.strftime('%H:%M · %d/%m/%Y')}</div>"
            except Exception:
                pass
        rows.append(f"""<div class="msg">
            <div class="role" style="color:{color};">{role_label}</div>
            <div class="body">{content_escaped}</div>
            {ts_str}
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{_hl.escape(title)} — {_hl.escape(product_name)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Segoe UI", Arial, sans-serif; background: #f8fafc;
           color: #1e293b; padding: 32px; max-width: 820px; margin: 0 auto; }}
  h1 {{ color: #4f46e5; font-size: 1.5rem; margin-bottom: 4px; }}
  .meta {{ color: #94a3b8; font-size: 0.8rem; margin-bottom: 28px; }}
  .msg {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
           padding: 16px 20px; margin-bottom: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.05); }}
  .role {{ font-weight: 700; font-size: 0.85rem; text-transform: uppercase;
            letter-spacing: .5px; margin-bottom: 8px; }}
  .body {{ font-size: 0.95rem; line-height: 1.65; white-space: pre-wrap; }}
  .ts {{ font-size: 0.72rem; color: #94a3b8; margin-top: 8px; }}
  @media print {{
    body {{ background: white; padding: 16px; }}
    .msg {{ break-inside: avoid; box-shadow: none; }}
  }}
</style>
</head>
<body>
  <h1>{_hl.escape(title)}</h1>
  <div class="meta">Exportado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · {_hl.escape(product_name)}</div>
  {"".join(rows)}
</body>
</html>"""


def _get_workspace_config(user_workspaces):
    """Feature C/H: obtiene system_prompt y cite_only del workspace activo."""
    system_prompt = ""
    cite_only = False
    try:
        for ws in (user_workspaces or []):
            if ws in ("all", "admin-only"):
                continue
            cfg = db_manager.get_workspace_config(ws)
            if cfg.get("system_prompt"):
                system_prompt = cfg["system_prompt"]
            if cfg.get("cite_only"):
                cite_only = True
    except Exception:
        pass
    return system_prompt, cite_only



def _reset_chat_state():
    """Limpia el estado de la sesión para una nueva conversación o cambio de chat."""
    st.session_state.messages = []
    st.session_state.ratings = {}
    st.session_state.sources = {}
    st.session_state.chunks = {}
    st.session_state.verifications = {}
    st.session_state.pop("_ratings_session_id", None)
    st.session_state.pop("_pending_prompt", None)
    # Limpiar flags de UX por conversación (las sugerencias NO se limpian — son por biblioteca)
    keys_to_clear = [k for k in st.session_state if k.startswith(("_show_neg_", "_copy_open_"))]
    for k in keys_to_clear:
        st.session_state.pop(k, None)


def render_dashboard():
    username        = st.session_state.get("username", "")
    user_role       = st.session_state.get("user_role", "viewer")
    user_workspaces = st.session_state.get("user_workspaces", ["all"])
    display_name    = st.session_state.get('name', username)

    try:
        product_name  = userdb.get_setting('product_name',  'Cortexa AI')
        welcome_title = userdb.get_setting('welcome_title', 'Base de conocimiento corporativo')
    except Exception:
        product_name  = 'Cortexa AI'
        welcome_title = 'Base de conocimiento corporativo'

    # Feature C/H: config del workspace
    ws_system_prompt, ws_cite_only = _get_workspace_config(user_workspaces)

    # ── Modo Agente ────────────────────────────────────────────────────────
    if "agent_mode" not in st.session_state:
        st.session_state["agent_mode"] = False

    # ── SIDEBAR ───────────────────────────────────────────────────────────
    with st.sidebar:
        if st.button("＋  Nueva conversación", use_container_width=True, type="primary"):
            try:
                session_id = db_manager.create_session(username)
                st.session_state["current_session_id"] = session_id
                _reset_chat_state()
            except Exception as e:
                st.error(f"No se pudo crear la sesión: {e}")
            st.rerun()

        # ── Modo Agente (destacado al inicio del sidebar) ─────────────────
        st.markdown(
            "<div style='margin:0.8rem 0 0.3rem; font-size:0.75rem; font-weight:600; "
            "text-transform:uppercase; letter-spacing:1px; color:#475569;'>Modo de respuesta</div>",
            unsafe_allow_html=True
        )
        _agent_mode_sidebar = st.toggle(
            "🤖 Modo Agente",
            value=st.session_state["agent_mode"],
            help=(
                "**RAG Directo** — responde buscando en los documentos (rápido, preciso).\n\n"
                "**Modo Agente** — razona en múltiples pasos, usa herramientas, "
                "puede calcular, comparar documentos y buscar en la web.\n\n"
                "💡 Actívalo para preguntas complejas que cruzan varios documentos."
            ),
        )
        if _agent_mode_sidebar != st.session_state["agent_mode"]:
            st.session_state["agent_mode"] = _agent_mode_sidebar
            st.rerun()

        if st.session_state["agent_mode"]:
            st.markdown("""
                <div style='background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.25);
                            border-radius:10px; padding:0.6rem 0.8rem; font-size:0.78rem; color:#a5b4fc;
                            margin-bottom:0.5rem;'>
                    🛠️ <b>Herramientas activas:</b><br>
                    • Búsqueda en base de conocimiento<br>
                    • Resumen y comparación de docs<br>
                    • Extracción de datos<br>
                    • Consulta SQL (Text-to-SQL)<br>
                    • Calculadora y estadísticas<br>
                    • Búsqueda web (si está activa)
                </div>
            """, unsafe_allow_html=True)

        # Feature A: mostrar uso de rate limit
        if user_role != "admin":
            try:
                usage, limit = rate_limiter.get_usage(username)
                pct = int(usage / limit * 100) if limit > 0 else 0
                color = "#10b981" if pct < 80 else ("#f59e0b" if pct < 100 else "#ef4444")
                st.markdown(
                    f"<div style='margin:0.5rem 0; padding:0.5rem 0.8rem; background:rgba(255,255,255,0.03);"
                    f"border-radius:8px; border:1px solid {color}33;'>"
                    f"<div style='font-size:0.7rem; color:#64748b; text-transform:uppercase; letter-spacing:1px;'>Consultas hoy</div>"
                    f"<div style='font-size:1.1rem; font-weight:700; color:{color};'>{usage}/{limit}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            except Exception:
                pass

        # Feature L: búsqueda en historial
        st.markdown(
            "<div style='margin:0.8rem 0 0.3rem; font-size:0.75rem; font-weight:600; "
            "text-transform:uppercase; letter-spacing:1px; color:#475569;'>Buscar</div>",
            unsafe_allow_html=True
        )
        chat_search = st.text_input(
            "Buscar en conversaciones",
            placeholder="🔍 Buscar en historial…",
            label_visibility="collapsed",
            key="chat_search_input"
        )
        if chat_search and chat_search.strip():
            try:
                search_results = db_manager.search_chat_history(username, chat_search.strip(), limit=10)
                if search_results:
                    seen_sessions = set()
                    for sr in search_results:
                        sid = sr["session_id"]
                        if sid in seen_sessions:
                            continue
                        seen_sessions.add(sid)
                        snippet = sr["content"][:60] + "…" if len(sr["content"]) > 60 else sr["content"]
                        if st.button(
                            f"📝 {sr['session_title'][:25]}", key=f"sr_{sid}_{hash(snippet)}",
                            help=snippet, use_container_width=True
                        ):
                            st.session_state["current_session_id"] = sid
                            _reset_chat_state()
                            st.session_state.messages = db_manager.get_chat_history(sid)
                            st.rerun()
                else:
                    st.caption("Sin resultados.")
            except Exception:
                pass

        st.markdown(
            "<div style='margin:1rem 0 0.5rem; font-size:0.75rem; font-weight:600; "
            "text-transform:uppercase; letter-spacing:1px; color:#475569;'>Conversaciones</div>",
            unsafe_allow_html=True
        )

        try:
            sessions = db_manager.get_user_sessions(username)
        except Exception:
            sessions = []

        for session in sessions:
            is_active = st.session_state.get("current_session_id") == session["id"]
            pending_del_key = f"_pending_del_{session['id']}"
            col1, col2 = st.columns([0.82, 0.18])
            with col1:
                label = session["title"][:28] + "…" if len(session["title"]) > 28 else session["title"]
                if st.button(label, key=f"sess_{session['id']}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    try:
                        st.session_state["current_session_id"] = session["id"]
                        _reset_chat_state()
                        st.session_state.messages = db_manager.get_chat_history(session["id"])
                    except Exception:
                        st.session_state.messages = []
                    st.session_state.pop(pending_del_key, None)
                    st.rerun()
            with col2:
                if st.session_state.get(pending_del_key):
                    # Confirmation state — show ✓ to confirm
                    if st.button("✓", key=f"del_ok_{session['id']}", help="Confirmar eliminación"):
                        try:
                            db_manager.delete_session(session["id"])
                        except Exception:
                            pass
                        if st.session_state.get("current_session_id") == session["id"]:
                            st.session_state.pop("current_session_id", None)
                            _reset_chat_state()
                        st.session_state.pop(pending_del_key, None)
                        st.toast("Conversación eliminada")
                        st.rerun()
                else:
                    if st.button("🗑", key=f"del_{session['id']}", help="Eliminar conversación"):
                        st.session_state[pending_del_key] = True
                        st.rerun()

        # ── Mi cuenta — cambio de contraseña ─────────────────────────────
        st.markdown("---")
        with st.expander("⚙️ Mi cuenta"):
            with st.form("self_pwd_form", clear_on_submit=True):
                sp1 = st.text_input("Nueva contraseña",  type="password", placeholder="Mínimo 8 caracteres")
                sp2 = st.text_input("Confirmar",         type="password", placeholder="Repite la contraseña")
                if st.form_submit_button("Actualizar contraseña", use_container_width=True):
                    if not sp1 or len(sp1) < 8:
                        st.error("Mínimo 8 caracteres.")
                    elif sp1 != sp2:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        try:
                            ok, msg = user_service.update_password(username, sp1, temp=False)
                            if ok:
                                st.toast("✅ Contraseña actualizada correctamente")
                                st.success("✅ Contraseña actualizada.")
                            else:
                                st.error(msg)
                        except Exception as e:
                            st.error(f"Error: {e}")

    # ── INICIALIZAR SESIÓN ────────────────────────────────────────────────
    try:
        sessions = db_manager.get_user_sessions(username)
    except Exception:
        sessions = []

    if "current_session_id" not in st.session_state:
        try:
            if sessions:
                st.session_state["current_session_id"] = sessions[0]["id"]
                st.session_state.messages = db_manager.get_chat_history(sessions[0]["id"])
            else:
                sid = db_manager.create_session(username)
                st.session_state["current_session_id"] = sid
                st.session_state.messages = []
        except Exception:
            st.session_state.messages = []

    current_session_id = st.session_state.get("current_session_id")

    # Cargar feedback de la sesión actual
    if st.session_state.get("_ratings_session_id") != current_session_id:
        try:
            st.session_state.ratings = db_manager.get_feedback_for_session(current_session_id)
        except Exception:
            st.session_state.ratings = {}
        st.session_state["_ratings_session_id"] = current_session_id
        st.session_state.sources = {}

    if "sources" not in st.session_state:
        st.session_state.sources = {}
    if "chunks" not in st.session_state:
        st.session_state.chunks = {}
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ratings" not in st.session_state:
        st.session_state.ratings = {}
    if "verifications" not in st.session_state:
        st.session_state.verifications = {}

    # ── DOCS DISPONIBLES ─────────────────────────────────────────────────
    try:
        doc_count = len(db_manager.get_all_documents(workspace_filter=user_workspaces))
    except Exception:
        doc_count = 0

    if "docs_at_session_start" not in st.session_state:
        st.session_state["docs_at_session_start"] = doc_count
    new_doc_count = max(0, doc_count - st.session_state["docs_at_session_start"])

    # ── CABECERA ──────────────────────────────────────────────────────────
    current_session_title = next(
        (s["title"] for s in sessions if s["id"] == current_session_id),
        "Conversación"
    )
    hcol1, hcol2 = st.columns([1, 0.3])
    with hcol1:
        st.markdown(f"""
            <div style='margin-bottom:1.5rem; padding-bottom:1rem;
                        border-bottom:1px solid rgba(255,255,255,0.06);'>
                <h1 style='margin:0; font-size:1.6rem; font-weight:700;
                           background:linear-gradient(135deg,#818cf8,#c084fc);
                           -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
                    {product_name}
                </h1>
                <p style='margin:0; color:#475569; font-size:0.85rem;'>{welcome_title}</p>
            </div>
        """, unsafe_allow_html=True)
    with hcol2:
        st.markdown("<div style='margin-top:0.4rem;'></div>", unsafe_allow_html=True)
        if st.session_state.messages:
            try:
                # Feature N: export MD + HTML (printable to PDF via browser Ctrl+P)
                exp_col1, exp_col2 = st.columns(2)
                safe_name  = product_name.lower().replace(' ', '_')
                safe_title = current_session_title[:30].replace(' ', '_')
                with exp_col1:
                    st.download_button(
                        "⬇ MD",
                        data=_export_chat_md(st.session_state.messages, current_session_title),
                        file_name=f"{safe_name}_{safe_title}.md",
                        mime="text/markdown",
                        use_container_width=True,
                        key="export_chat_btn"
                    )
                with exp_col2:
                    st.download_button(
                        "📄 HTML",
                        data=_export_chat_html(st.session_state.messages, current_session_title),
                        file_name=f"{safe_name}_{safe_title}.html",
                        mime="text/html",
                        use_container_width=True,
                        key="export_html_btn",
                        help="Abre en el navegador y usa Ctrl+P para imprimir/exportar como PDF"
                    )
            except Exception:
                pass

    # Feature H: indicador de modo cite-only
    if ws_cite_only:
        st.markdown("""
            <div style='background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3);
                        border-radius:10px; padding:0.6rem 1rem; margin-bottom:1rem;
                        font-size:0.85rem; color:#fbbf24;'>
                📋 <b>Modo cita textual</b> — La IA solo citará fragmentos textuales de los documentos, sin interpretar.
            </div>
        """, unsafe_allow_html=True)

    # Notificación de documentos nuevos
    if new_doc_count > 0:
        pl = 's' if new_doc_count > 1 else ''
        st.info(f"🆕 **{new_doc_count} documento{pl} nuevo{pl}** disponible{pl} en la biblioteca desde que iniciaste sesión.")

    # ── ONBOARDING ────────────────────────────────────────────────────────
    is_new_user = len(sessions) <= 1 and len(st.session_state.messages) == 0
    if is_new_user and doc_count == 0:
        st.markdown(f"""
            <div style='background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.25);
                        border-radius:16px; padding:2rem; margin-bottom:1.5rem;'>
                <h3 style='color:#f1f5f9; margin:0 0 1.2rem;'>👋 Bienvenido a {product_name}</h3>
                <div style='display:flex; gap:1.5rem; flex-wrap:wrap;'>
                    <div style='flex:1; min-width:160px;'>
                        <div style='font-size:1.8rem; margin-bottom:0.4rem;'>1️⃣</div>
                        <div style='color:#c084fc; font-weight:600; margin-bottom:0.3rem;'>Sube documentos</div>
                        <div style='color:#64748b; font-size:0.85rem;'>
                            Ve a <b style="color:#818cf8;">Biblioteca</b> y sube PDFs o DOCXs corporativos.
                        </div>
                    </div>
                    <div style='flex:1; min-width:160px;'>
                        <div style='font-size:1.8rem; margin-bottom:0.4rem;'>2️⃣</div>
                        <div style='color:#c084fc; font-weight:600; margin-bottom:0.3rem;'>Gestiona permisos</div>
                        <div style='color:#64748b; font-size:0.85rem;'>
                            Controla qué grupos pueden ver cada documento.
                        </div>
                    </div>
                    <div style='flex:1; min-width:160px;'>
                        <div style='font-size:1.8rem; margin-bottom:0.4rem;'>3️⃣</div>
                        <div style='color:#c084fc; font-weight:600; margin-bottom:0.3rem;'>Pregunta</div>
                        <div style='color:#64748b; font-size:0.85rem;'>
                            Escribe cualquier consulta sobre tus documentos aquí abajo.
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── EMPTY STATE ───────────────────────────────────────────────────────
    if not st.session_state.messages:
        if doc_count == 0 and not is_new_user:
            st.markdown("""
                <div style='text-align:center; padding:4rem 2rem;'>
                    <div style='font-size:4rem; margin-bottom:1rem;'>📂</div>
                    <h3 style='color:#f1f5f9; margin-bottom:0.5rem;'>La biblioteca está vacía</h3>
                    <p style='color:#475569; max-width:360px; margin:0 auto;'>
                        Ve a <b style='color:#818cf8;'>Biblioteca</b> y sube tus primeros documentos.
                    </p>
                </div>
            """, unsafe_allow_html=True)
        elif doc_count > 0:
            st.markdown(f"""
                <div style='text-align:center; padding:2rem 1rem 1rem;'>
                    <div style='font-size:3rem; margin-bottom:0.8rem;'>🧠</div>
                    <h3 style='color:#f1f5f9; margin-bottom:0.3rem;'>¿En qué puedo ayudarte?</h3>
                    <p style='color:#475569; font-size:0.9rem;'>
                        Tengo acceso a {doc_count} documento{"s" if doc_count != 1 else ""}. Pregúntame lo que necesites.
                    </p>
                </div>
            """, unsafe_allow_html=True)


    # ── HISTORIAL CON FEEDBACK Y FUENTES ─────────────────────────────────
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Timestamp
            if message.get("ts"):
                try:
                    _ts = datetime.fromisoformat(message["ts"])
                    st.caption(f"🕐 {_ts.strftime('%H:%M  ·  %d/%m/%Y')}")
                except Exception:
                    pass

            if message["role"] == "assistant":
                # ── Fuentes ──────────────────────────────────────────────
                msg_sources = st.session_state.sources.get(i, [])
                if msg_sources:
                    with st.expander(
                        f"📚 {len(msg_sources)} fuente{'s' if len(msg_sources) > 1 else ''} "
                        f"consultada{'s' if len(msg_sources) > 1 else ''}",
                        expanded=False
                    ):
                        for src in msg_sources:
                            ext  = src.split(".")[-1].upper() if "." in src else "FILE"
                            icon = "📄" if ext == "PDF" else "📝"
                            st.markdown(f"{icon} `{src}`")

                # ── Fila de acciones ─────────────────────────────────────
                action_cols = st.columns([1, 1, 1, 7])

                # Botón copiar
                with action_cols[0]:
                    _copy_key = f"_copy_open_{i}"
                    if st.button("📋", key=f"copy_btn_{i}", help="Copiar respuesta"):
                        st.session_state[_copy_key] = not st.session_state.get(_copy_key, False)

                # Feedback positivo
                existing_rating = st.session_state.ratings.get(i)
                if existing_rating is None:
                    with action_cols[1]:
                        if st.button("👍", key=f"good_{i}_{current_session_id}", help="Respuesta útil"):
                            try:
                                db_manager.save_feedback(current_session_id, i, username, 1)
                            except Exception:
                                pass
                            st.session_state.ratings[i] = 1
                            st.rerun()
                    with action_cols[2]:
                        if st.button("👎", key=f"bad_{i}_{current_session_id}", help="Respuesta mejorable"):
                            st.session_state[f"_show_neg_{i}"] = True
                            st.rerun()
                else:
                    with action_cols[1]:
                        emoji = "👍" if existing_rating == 1 else "👎"
                        st.caption(f"{emoji} Valorado")

                # Botón verificar (solo si hay chunks guardados y aún no verificado)
                if i in st.session_state.get("chunks", {}) and not st.session_state.verifications.get(i):
                    with action_cols[3]:
                        if st.button("🔍 Verificar fidelidad", key=f"verify_btn_{i}", help="Comprueba si la respuesta es fiel a los documentos"):
                            with st.spinner("Verificando…"):
                                _b, _ = get_brain()
                                if _b:
                                    _question = st.session_state.messages[i - 1]["content"] if i > 0 else ""
                                    _v = verifier_service.verify_answer(
                                        _question, message["content"],
                                        st.session_state.chunks.get(i, [])
                                    )
                                    st.session_state.verifications[i] = _v
                                    st.rerun()

                # Área de texto para copiar
                if st.session_state.get(f"_copy_open_{i}"):
                    st.text_area(
                        "Selecciona todo (Ctrl+A) y copia:",
                        value=message["content"],
                        height=120,
                        key=f"copy_ta_{i}",
                        label_visibility="collapsed"
                    )

                # Formulario de feedback negativo con razón
                if st.session_state.get(f"_show_neg_{i}"):
                    _reason = st.text_area(
                        "¿Qué estuvo mal? (opcional)",
                        placeholder="Ej: La fecha es incorrecta, falta información sobre…",
                        key=f"neg_reason_{i}",
                        height=80
                    )
                    _fb_cols = st.columns(2)
                    with _fb_cols[0]:
                        if st.button("Enviar valoración", key=f"neg_send_{i}", type="primary"):
                            try:
                                db_manager.save_feedback(current_session_id, i, username, -1)
                            except Exception:
                                pass
                            if _reason and _reason.strip():
                                print(f"[feedback] session={current_session_id} msg={i} reason={_reason.strip()}")
                            st.session_state.ratings[i] = -1
                            st.session_state.pop(f"_show_neg_{i}", None)
                            st.toast("Gracias por tu valoración")
                            st.rerun()
                    with _fb_cols[1]:
                        if st.button("Cancelar", key=f"neg_cancel_{i}"):
                            st.session_state.pop(f"_show_neg_{i}", None)
                            st.rerun()

                # Resultado de verificación
                v_res = st.session_state.verifications.get(i)
                if v_res:
                    status = v_res.get("status", "UNKNOWN")
                    reason = v_res.get("reasoning", "")
                    if status == "VERIFIED":
                        st.markdown(f"<div style='font-size:0.8rem; color:#10b981; margin-top:4px;'>✅ <b>Verificado:</b> {reason}</div>", unsafe_allow_html=True)
                    elif status == "WARNING":
                        st.markdown(f"<div style='font-size:0.8rem; color:#f59e0b; margin-top:4px;'>⚠️ <b>Aviso:</b> {reason}</div>", unsafe_allow_html=True)
                    elif status == "FAILED":
                        st.error(f"❌ **Alucinación detectada:** {reason}")

    # ── INPUT ─────────────────────────────────────────────────────────────
    pending = st.session_state.pop("_pending_prompt", None)
    prompt  = st.chat_input("Escribe tu consulta…") or pending

    if prompt:
        # Feature A: rate limiting (admins exentos)
        if user_role != "admin":
            try:
                allowed, current, limit = rate_limiter.check_and_increment(username)
                if not allowed:
                    st.warning(
                        f"⚠️ Has alcanzado el límite diario de **{limit}** consultas. "
                        f"Inténtalo de nuevo mañana o contacta con el administrador."
                    )
                    st.stop()
                elif limit > 0 and current / limit >= 0.8:
                    remaining = limit - current
                    st.toast(
                        f"⚠️ Solo te quedan **{remaining}** consulta{'s' if remaining != 1 else ''} hoy.",
                        icon="⚠️"
                    )
            except Exception:
                pass

        is_first_message = len(st.session_state.messages) == 0
        _now_ts = datetime.now().isoformat()

        st.session_state.messages.append({"role": "user", "content": prompt, "ts": _now_ts})
        with st.chat_message("user"):
            st.markdown(prompt)
            st.caption(f"🕐 {datetime.now().strftime('%H:%M  ·  %d/%m/%Y')}")

        try:
            db_manager.save_message(username, "user", prompt, current_session_id)
        except Exception:
            pass
        try:
            audit_service.log_event(username, user_role, "QUERY", prompt, display_name=display_name)
        except Exception:
            pass

        _ans_ts = datetime.now().isoformat()
        answer = ""
        with st.chat_message("assistant"):
            b, brain_err = get_brain()

            if b is None:
                answer = (
                    "⚠️ El servicio de IA no está disponible en este momento. "
                    "Si el problema persiste, contacta con el administrador."
                )
                st.warning(answer)

            elif doc_count == 0:
                answer = (
                    "📂 No hay documentos indexados todavía. "
                    "Ve a **Biblioteca** para subir tus primeros documentos PDF o DOCX."
                )
                st.markdown(answer)

            else:
                try:
                    history = []
                    for m in st.session_state.messages[:-1]:
                        if m["role"] == "user":
                            history.append(("human", m["content"]))
                        else:
                            history.append(("ai", m["content"]))

                    status_placeholder = st.empty()

                    # POST-AUDITORÍA · indicador visible de Modo Agente activo
                    if st.session_state.get("agent_mode"):
                        st.caption("🤖 **Modo Agente activo** · respuestas más lentas pero con uso de herramientas.")

                    # ── Modo Agente ──────────────────────────────────────
                    if st.session_state.get("agent_mode"):
                        from src.core.agent import get_agent
                        agent, agent_err = get_agent()
                        if agent is None:
                            # Mensaje específico según el error subyacente
                            if agent_err and "ollama" in str(agent_err).lower():
                                answer = ("⚠️ El motor de IA (Ollama) no responde. Si el problema persiste, "
                                         "el administrador puede revisarlo en Admin → Sistema → Estado. "
                                         "Cierra y vuelve a intentarlo en unos segundos.")
                            elif agent_err and "timeout" in str(agent_err).lower():
                                answer = ("⏱️ El servicio tarda en responder más de lo normal. "
                                         "Inténtalo de nuevo en unos segundos.")
                            else:
                                answer = ("⚠️ No se pudo iniciar el agente. Si el problema persiste, "
                                         "contacta con soporte indicando el código: AGENT_INIT_FAIL.")
                            st.error(answer)
                        else:
                            _TOOL_STATUS = {
                                "search_knowledge_base":      "🔍 Buscando en documentos…",
                                "list_available_documents":   "📂 Listando documentos disponibles…",
                                "summarize_document":         "📝 Resumiendo documento…",
                                "compare_documents":          "⚖️ Comparando documentos…",
                                "extract_data_from_document": "📊 Extrayendo datos del documento…",
                                "list_sql_databases":         "🗄️ Consultando bases de datos SQL…",
                                "query_database":             "🗄️ Consultando base de datos SQL…",
                                "calculator":                 "🧮 Calculando…",
                                "statistics_summary":         "📈 Calculando estadísticas…",
                                "web_search":                 "🌐 Buscando en la web…",
                            }

                            status_placeholder.caption("🤔 Analizando tu consulta…")

                            if st.button("⏹ Detener generación", key="stop_agent"):
                                st.rerun()

                            def stream_agent():
                                first = True
                                def _on_tool(tool_name):
                                    msg = _TOOL_STATUS.get(tool_name, f"🛠️ Usando {tool_name}…")
                                    status_placeholder.caption(msg)

                                for chunk in agent.stream(
                                    prompt, history,
                                    workspaces=user_workspaces,
                                    on_tool_call=_on_tool,
                                ):
                                    if first:
                                        status_placeholder.empty()
                                        first = False
                                    yield chunk

                            answer = st.write_stream(stream_agent())
                            status_placeholder.empty()

                    # ── RAG Directo (modo por defecto) ───────────────────
                    else:
                        status_placeholder.caption("⟳ Buscando en documentos…")
                        
                        # Botón para detener
                        if st.button("⏹ Detener generación", key="stop_rag"):
                            st.rerun()

                        def stream_with_indicator():
                            first = True
                            for chunk in b.query_stream(
                                prompt, history, workspaces=user_workspaces,
                                system_prompt_override=ws_system_prompt,
                                cite_only=ws_cite_only,
                            ):
                                if first:
                                    status_placeholder.empty()
                                    first = False
                                yield chunk

                        answer = st.write_stream(stream_with_indicator())
                    status_placeholder.empty()

                    # Índice donde se guardará el mensaje asistente (antes de appended)
                    assistant_msg_index = len(st.session_state.messages)

                    # Fuentes — leídas desde contextvars (aislamiento per-request)
                    try:
                        from src.core.brain import CortexaBrain as _CB
                        sources = _CB.get_last_sources()
                    except Exception:
                        sources = []
                    st.session_state.sources[assistant_msg_index] = sources

                    # Guardar chunks para verificación bajo demanda
                    try:
                        from src.core.brain import CortexaBrain as _CB
                        st.session_state.chunks[assistant_msg_index] = _CB.get_last_chunks()[:10]
                    except Exception:
                        pass

                    if sources:
                        with st.expander(
                            f"📚 {len(sources)} fuente{'s' if len(sources) > 1 else ''} "
                            f"consultada{'s' if len(sources) > 1 else ''}",
                            expanded=True
                        ):
                            for src in sources:
                                ext  = src.split(".")[-1].upper() if "." in src else "FILE"
                                icon = "📄" if ext == "PDF" else "📝"
                                st.markdown(f"{icon} `{src}`")
                        try:
                            db_manager.increment_doc_query_count(sources)
                        except Exception:
                            pass

                    # Título IA para la primera consulta
                    if is_first_message:
                        try:
                            title_resp = b.llm.invoke(
                                "Genera un título de máximo 5 palabras en español para esta consulta. "
                                f"Solo el título, sin comillas, puntos ni explicaciones:\n{prompt}"
                            )
                            title = title_resp.content.strip()[:50]
                        except Exception:
                            title = prompt[:50]
                        try:
                            db_manager.update_session_title(current_session_id, title)
                        except Exception:
                            pass

                except Exception as e:
                    import traceback
                    print(f"[dashboard] Error en query: {e}")
                    print(traceback.format_exc())
                    answer = "⚠️ No pude procesar tu consulta en este momento. Inténtalo de nuevo."
                    st.error(answer)

        # Guardar respuesta siempre, pase lo que pase
        if answer:
            st.session_state.messages.append({"role": "assistant", "content": answer, "ts": _ans_ts})
            try:
                db_manager.save_message(username, "assistant", answer, current_session_id)
            except Exception:
                pass
            st.rerun()
