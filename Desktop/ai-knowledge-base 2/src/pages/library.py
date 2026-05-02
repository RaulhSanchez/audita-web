import streamlit as st
import os
import re
import html as _html
from src.core.database import db_manager
from src.services.ingest_service import ingest_service, MAX_FILE_SIZE_MB
from src.services.audit_service import audit_service
from src.services.user_service import user_service


def _safe(text):
    """Escapa HTML y llaves para uso seguro en f-strings con unsafe_allow_html."""
    return _html.escape(str(text or "")).replace("{", "&#123;").replace("}", "&#125;")


# ──────────────────────────────────────────────────────────────────────────
# POST-AUDITORÍA · Sanitizador de nombres de archivo (path traversal fix)
# ──────────────────────────────────────────────────────────────────────────
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]+$")
_DATA_DIR = os.getenv("DATA_DIR", "./data")


def _sanitize_filename(raw: str) -> tuple[bool, str]:
    """
    Devuelve (ok, name_or_error_msg).

    Acepta solo nombres con [A-Za-z0-9._-]+ y descarta vacíos, "." y "..".
    Esto cierra el path traversal detectado en la auditoría (uf.name venía
    del cliente y se concatenaba directamente a os.path.join).
    """
    if not raw:
        return False, "nombre vacío"
    base = os.path.basename(raw)
    if base in (".", "..") or not _SAFE_FILENAME.match(base):
        return False, "caracteres inválidos en el nombre"
    return True, base


def _safe_save_path(filename: str) -> str | None:
    """
    Resuelve y verifica que la ruta queda dentro de _DATA_DIR. Devuelve la ruta
    real o None si está fuera (defensa en profundidad ante symlinks/realpath).
    """
    real_base = os.path.realpath(_DATA_DIR)
    candidate = os.path.realpath(os.path.join(_DATA_DIR, filename))
    if candidate != real_base and not candidate.startswith(real_base + os.sep):
        return None
    return candidate


def render_library():
    username        = st.session_state.get("username", "")
    user_role       = st.session_state.get("user_role", "viewer")
    user_workspaces = st.session_state.get("user_workspaces", [])
    can_upload      = st.session_state.get("can_upload", False)
    upload_groups   = st.session_state.get("upload_groups", [])
    can_delete      = st.session_state.get("can_delete", False)
    delete_groups   = st.session_state.get("delete_groups", [])
    is_admin        = user_role == "admin"
    display_name    = st.session_state.get('name', username)

    def _can_delete_doc(ws_str):
        if is_admin:
            return True
        if not can_delete:
            return False
        if "all" in delete_groups:
            return True
        doc_ws = {w.strip() for w in str(ws_str or "general").split(",")}
        return bool(doc_ws & set(delete_groups))

    def _upload_preset(all_ws):
        if is_admin:
            return ["general", "admin-only"] + [w for w in all_ws if w not in ("general", "admin-only")]
        if "all" in upload_groups:
            return [w for w in user_workspaces if w not in ("all",)]
        return [w for w in upload_groups if w in user_workspaces]

    # ── CABECERA ──────────────────────────────────────────────────────────
    try:
        docs_df = db_manager.get_all_documents(workspace_filter=user_workspaces)
    except Exception:
        docs_df = __import__('pandas').DataFrame()

    total_chunks  = int(docs_df['chunk_count'].sum())  if not docs_df.empty and 'chunk_count'  in docs_df.columns else 0
    total_queries = int(docs_df['query_count'].sum())   if not docs_df.empty and 'query_count'  in docs_df.columns else 0

    st.markdown("""
        <h1 style='margin:0 0 0.3rem; font-size:1.6rem; font-weight:700;
                   background:linear-gradient(135deg,#818cf8,#c084fc);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
            Biblioteca
        </h1>
        <p style='color:#475569; font-size:0.9rem; margin-bottom:1.5rem;'>
            Gestión del conocimiento corporativo indexado
        </p>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    for col, value, label, color in [
        (col1, len(docs_df),          "Documentos",   "#818cf8"),
        (col2, f"{total_chunks:,}",   "Fragmentos",   "#a78bfa"),
        (col3, f"{total_queries:,}",  "Consultas",    "#6366f1"),
        (col4, "Activa" if len(docs_df) > 0 else "Vacía", "Base de datos",
         "#10b981" if len(docs_df) > 0 else "#f59e0b"),
    ]:
        with col:
            st.markdown(f"""
                <div style='background:rgba(99,102,241,0.07); border:1px solid rgba(99,102,241,0.2);
                            border-radius:14px; padding:1.2rem; text-align:center;'>
                    <div style='font-size:2rem; font-weight:700; color:{color};'>{value}</div>
                    <div style='font-size:0.8rem; color:#64748b; text-transform:uppercase; letter-spacing:1px;'>
                        {label}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab_docs, tab_search = st.tabs(["📂 Documentos", "🔍 Búsqueda semántica"])

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1 — DOCUMENTOS
    # ═══════════════════════════════════════════════════════════════════════
    with tab_docs:

        # ── Zona de subida ───────────────────────────────────────────────
        if can_upload:
            st.markdown(
                "<h3 style='color:#f1f5f9; font-size:1.1rem; margin-bottom:0.8rem;'>Añadir documentos</h3>",
                unsafe_allow_html=True
            )
            try:
                all_workspaces = user_service.get_all_workspaces()
            except Exception:
                all_workspaces = ["general"]

            preset_options = _upload_preset(all_workspaces)

            if not preset_options:
                st.warning("No tienes permiso para subir a ningún grupo. Contacta con el administrador.")
            else:
                st.markdown(
                    "<p style='color:#94a3b8; font-size:0.85rem; margin:0 0 0.3rem;'>"
                    "Grupos con acceso al documento</p>",
                    unsafe_allow_html=True
                )
                selected_groups = st.multiselect(
                    "Selecciona uno o varios grupos",
                    options=preset_options,
                    default=[preset_options[0]],
                    format_func=lambda w: (
                        "🌐 General (todos)" if w == "general"
                        else ("🔐 Solo administradores" if w == "admin-only" else f"👥 {w}")
                    ),
                    help="Solo los usuarios con acceso a alguno de estos grupos podrán ver el documento.",
                    label_visibility="collapsed"
                )

                # Crear nuevo grupo (solo admin)
                if is_admin:
                    col_grp, col_btn = st.columns([4, 1])
                    with col_grp:
                        new_group_name = st.text_input(
                            "Crear nuevo grupo",
                            placeholder="Nombre del grupo (ej: Ventas, RRHH…)",
                            key="new_group_input"
                        )
                    with col_btn:
                        st.markdown("<div style='margin-top:1.75rem;'></div>", unsafe_allow_html=True)
                        add_clicked = st.button("Añadir", key="add_group_btn", use_container_width=True)

                    if add_clicked:
                        if new_group_name and new_group_name.strip():
                            clean = new_group_name.strip().lower().replace(" ", "-")
                            if clean in preset_options:
                                st.warning(f"El grupo **{clean}** ya existe — selecciónalo del desplegable.")
                            else:
                                try:
                                    db_manager.add_workspace(clean, created_by=username)
                                    st.toast(f"Grupo '{clean}' creado.")
                                except Exception as e:
                                    st.error(f"Error al crear el grupo: {e}")
                                st.rerun()
                        else:
                            st.warning("Escribe un nombre para el grupo antes de añadir.")

                workspace = selected_groups if selected_groups else [preset_options[0]]

                uploaded_files = st.file_uploader(
                    f"Arrastra tus archivos aquí (PDF o DOCX · máx. {MAX_FILE_SIZE_MB}MB)",
                    type=["pdf", "docx", "doc"],
                    accept_multiple_files=True,
                    label_visibility="visible"
                )

                if uploaded_files:
                    # Clasificar archivos
                    too_large = []
                    duplicates = []
                    valid = []
                    for f in uploaded_files:
                        size_mb = f.size / (1024 * 1024)
                        if size_mb > MAX_FILE_SIZE_MB:
                            too_large.append(f)
                        elif db_manager.document_exists(f.name):
                            duplicates.append(f)
                        else:
                            valid.append(f)

                    for f in too_large:
                        st.warning(f"⚠️ **{f.name}** supera {MAX_FILE_SIZE_MB}MB — será omitido.")

                    # Feature F: ofrecer reindexar duplicados
                    if duplicates:
                        dup_names = ', '.join(f.name for f in duplicates)
                        st.info(f"🔁 Archivos ya indexados: **{dup_names}**")
                        if st.button("🔄 Reindexar archivos existentes", key="reindex_btn", type="secondary"):
                            with st.status("Reindexando...", expanded=True) as status:
                                for uf in duplicates:
                                    st.write(f"🔄 Reindexando `{uf.name}`...")
                                    try:
                                        ok_name, sanitized = _sanitize_filename(uf.name)
                                        if not ok_name:
                                            st.write(f"❌ `{uf.name}` — {sanitized}")
                                            continue
                                        os.makedirs(_DATA_DIR, exist_ok=True)
                                        tmp_path = _safe_save_path(sanitized)
                                        if tmp_path is None:
                                            st.write(f"❌ `{uf.name}` — ruta fuera de DATA_DIR")
                                            continue
                                        with open(tmp_path, "wb") as fh:
                                            fh.write(uf.getbuffer())
                                        ok, msg = ingest_service.reindex_file(tmp_path, username, workspace)
                                        if ok:
                                            st.write(f"✅ `{uf.name}` — reindexado")
                                            try:
                                                audit_service.log_event(
                                                    username, user_role, "REINDEX", uf.name,
                                                    display_name=display_name
                                                )
                                            except Exception:
                                                pass
                                        else:
                                            st.write(f"❌ `{uf.name}` — {msg}")
                                    except Exception as e:
                                        st.write(f"❌ `{uf.name}` — Error: {e}")
                                status.update(label="Reindexación completada", state="complete")
                            st.rerun()

                    if valid:
                        st.markdown(
                            f"<p style='color:#818cf8; font-size:0.9rem;'>"
                            f"📎 {len(valid)} archivo(s) listos para indexar en "
                            f"<b>{', '.join(workspace)}</b></p>",
                            unsafe_allow_html=True
                        )
                        if st.button("📥 Indexar documentos", type="primary"):
                            with st.status("Indexando documentos...", expanded=True) as status:
                                results = []
                                for uf in valid:
                                    st.write(f"⏳ Procesando `{uf.name}`...")
                                    try:
                                        ok_name, sanitized = _sanitize_filename(uf.name)
                                        if not ok_name:
                                            st.write(f"❌ `{uf.name}` — {sanitized}")
                                            continue
                                        os.makedirs(_DATA_DIR, exist_ok=True)
                                        tmp_path = _safe_save_path(sanitized)
                                        if tmp_path is None:
                                            st.write(f"❌ `{uf.name}` — ruta fuera de DATA_DIR")
                                            continue
                                        with open(tmp_path, "wb") as fh:
                                            fh.write(uf.getbuffer())
                                        ok, msg = ingest_service.process_file(tmp_path, username, workspace)
                                        if ok:
                                            st.write(f"✅ `{uf.name}` — indexado")
                                            try:
                                                audit_service.log_event(
                                                    username, user_role, "UPLOAD", uf.name,
                                                    display_name=display_name
                                                )
                                            except Exception:
                                                pass
                                        else:
                                            st.write(f"❌ `{uf.name}` — {msg}")
                                        results.append((uf.name, ok, msg))
                                    except Exception as e:
                                        st.write(f"❌ `{uf.name}` — Error inesperado: {e}")
                                        results.append((uf.name, False, str(e)))

                                success_count = sum(1 for _, ok, _ in results if ok)
                                if not results:
                                    status.update(label="⚠️ No había archivos válidos para indexar", state="complete")
                                elif success_count == len(results):
                                    status.update(
                                        label=f"✅ {success_count} documento(s) indexado(s) correctamente",
                                        state="complete"
                                    )
                                elif success_count > 0:
                                    status.update(
                                        label=f"⚠️ {success_count}/{len(results)} documentos indexados",
                                        state="complete"
                                    )
                                else:
                                    status.update(label="❌ Error al indexar documentos", state="error")

                            if results and any(ok for _, ok, _ in results):
                                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

        # ── Listado de documentos ─────────────────────────────────────────
        st.markdown(
            "<h3 style='color:#f1f5f9; font-size:1.1rem; margin-bottom:0.8rem;'>Documentos indexados</h3>",
            unsafe_allow_html=True
        )

        if docs_df.empty:
            st.markdown("""
                <div style='text-align:center; padding:3rem; background:rgba(255,255,255,0.02);
                            border:1px dashed rgba(99,102,241,0.3); border-radius:16px;'>
                    <div style='font-size:3rem; margin-bottom:0.8rem;'>📭</div>
                    <h4 style='color:#475569; margin-bottom:0.4rem;'>Sin documentos todavía</h4>
                    <p style='color:#334155; font-size:0.9rem;'>Sube tu primer archivo para comenzar.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            try:
                _known_ws = user_service.get_all_workspaces()
            except Exception:
                _known_ws = ["general"]
            all_ws_available = ["general", "admin-only"] + [
                w for w in _known_ws if w not in ("general", "admin-only")
            ]

            # Filtros
            fcol1, fcol2 = st.columns([2, 1])
            with fcol1:
                search_query = st.text_input(
                    "Buscar documento",
                    placeholder="🔎  Filtrar por nombre…",
                    label_visibility="collapsed"
                )
            with fcol2:
                ws_flat = set()
                if 'workspace' in docs_df.columns:
                    for ws_raw in docs_df['workspace'].dropna():
                        for part in str(ws_raw).split(","):
                            p = part.strip()
                            if p:
                                ws_flat.add(p)
                all_ws_in_docs = sorted(ws_flat)
                if len(all_ws_in_docs) > 1:
                    st.markdown(
                        "<p style='color:#64748b; font-size:0.78rem; margin:0 0 0.2rem; "
                        "text-transform:uppercase; letter-spacing:0.5px;'>Filtrar por grupo</p>",
                        unsafe_allow_html=True
                    )
                    ws_filter = st.multiselect(
                        "Filtrar por grupo",
                        options=all_ws_in_docs,
                        default=all_ws_in_docs,
                        format_func=lambda w: (
                            "🌐 General" if w == "general"
                            else ("🔐 Solo admin" if w == "admin-only" else f"👥 {w}")
                        ),
                        label_visibility="collapsed"
                    )
                else:
                    ws_filter = all_ws_in_docs

            # Aplicar filtros
            filtered_df = docs_df.copy()
            if search_query:
                filtered_df = filtered_df[
                    filtered_df['filename'].str.contains(search_query, case=False, na=False)
                ]
            if ws_filter and len(all_ws_in_docs) > 1:
                def _doc_matches(ws_raw):
                    parts = {p.strip() for p in str(ws_raw or "general").split(",")}
                    return bool(parts & set(ws_filter))
                filtered_df = filtered_df[filtered_df['workspace'].apply(_doc_matches)]

            if filtered_df.empty:
                st.caption("No se encontraron documentos con ese criterio.")
            else:
                # CSS hover effect for doc cards
                st.markdown("""
                    <style>
                    .doc-card {
                        padding: 1.4rem;
                        border-radius: 16px;
                        background: rgba(255,255,255,0.03);
                        border: 1px solid rgba(99,102,241,0.2);
                        margin-bottom: 0.5rem;
                        transition: all 0.2s ease;
                    }
                    .doc-card:hover {
                        background: rgba(99,102,241,0.07) !important;
                        border-color: rgba(99,102,241,0.45) !important;
                        transform: translateY(-2px);
                        box-shadow: 0 6px 20px rgba(99,102,241,0.15);
                    }
                    </style>
                """, unsafe_allow_html=True)
                cols = st.columns(3)
                for i, row in filtered_df.iterrows():
                    with cols[i % 3]:
                        name        = row['filename']
                        short       = _safe(name[:27] + "…" if len(name) > 30 else name)
                        raw_date    = str(row.get('upload_date', '') or '')
                        date        = raw_date[:10] if len(raw_date) >= 10 and raw_date[0].isdigit() else '—'
                        uploader    = _safe(row.get('user', '—'))
                        chunks      = row.get('chunk_count', 0)
                        qcount      = int(row.get('query_count', 0)) if 'query_count' in row else 0
                        ws          = row.get('workspace', 'general')
                        summary_raw = str(row.get('summary', '') or '')
                        ext         = name.split('.')[-1].upper() if '.' in name else 'FILE'
                        icon        = "📄" if ext == "PDF" else "📝"

                        ws_parts = [w.strip() for w in str(ws or "general").split(",") if w.strip()]
                        if ws_parts == ["admin-only"]:
                            ws_badge_color = "rgba(239,68,68,0.15)"; ws_badge_text = "#fca5a5"; ws_label = "🔐 Solo admin"
                        elif ws_parts == ["general"]:
                            ws_badge_color = "rgba(16,185,129,0.15)"; ws_badge_text = "#6ee7b7"; ws_label = "🌐 General"
                        elif "admin-only" in ws_parts:
                            ws_badge_color = "rgba(239,68,68,0.15)"; ws_badge_text = "#fca5a5"
                            ws_label = "🔐 " + _safe(", ".join(ws_parts))
                        else:
                            ws_badge_color = "rgba(99,102,241,0.15)"; ws_badge_text = "#818cf8"
                            ws_label = "👥 " + _safe(", ".join(ws_parts))

                        summary_escaped   = _safe(summary_raw)
                        summary_truncated = summary_escaped[:160] + ("…" if len(summary_escaped) > 160 else "")

                        st.markdown(
                            f"<div class='doc-card'>"
                            f"<div style='display:flex; align-items:flex-start; gap:0.8rem; margin-bottom:0.8rem; pointer-events:none;'>"
                            f"<div style='font-size:1.8rem; line-height:1;'>{icon}</div>"
                            f"<div style='flex:1; min-width:0;'>"
                            f"<div style='font-weight:600; color:#e2e8f0; font-size:0.9rem; word-break:break-word;'>{short}</div>"
                            f"<div style='font-size:0.7rem; color:#4f6070; margin-top:2px;'>{ext} · {date}</div>"
                            f"</div></div>"
                            + (f"<div style='font-size:0.75rem; color:#64748b; margin:0.4rem 0 0.6rem; line-height:1.4;'>{summary_truncated}</div>" if summary_truncated else "")
                            + f"<div style='border-top:1px solid rgba(255,255,255,0.05); padding-top:0.7rem;"
                            f"display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:4px;'>"
                            f"<span style='font-size:0.75rem; color:#64748b;'>👤 {uploader}</span>"
                            f"<span style='font-size:0.75rem; color:#6366f1;'>🧩 {chunks}</span>"
                            f"<span style='font-size:0.75rem; color:#a78bfa;'>💬 {qcount}</span>"
                            f"<span style='font-size:0.7rem; background:{ws_badge_color}; color:{ws_badge_text};"
                            f"padding:2px 8px; border-radius:20px; font-weight:500;'>{ws_label}</span>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )

                        # ── Vista previa ─────────────────────────────────
                        _prev_key = f"preview_{row['id']}"
                        if st.button("👁 Vista previa", key=f"prev_btn_{row['id']}",
                                     use_container_width=True):
                            st.session_state[_prev_key] = not st.session_state.get(_prev_key, False)

                        if st.session_state.get(_prev_key):
                            ok_n, sn = _sanitize_filename(name)
                            file_path = _safe_save_path(sn) if ok_n else None
                            if file_path and os.path.exists(file_path):
                                if ext == "PDF":
                                    try:
                                        import base64
                                        with open(file_path, "rb") as _pf:
                                            _b64 = base64.b64encode(_pf.read()).decode()
                                        st.components.v1.html(
                                            f'<iframe src="data:application/pdf;base64,{_b64}" '
                                            f'width="100%" height="520px" style="border:none; '
                                            f'border-radius:8px;"></iframe>',
                                            height=530,
                                        )
                                    except Exception as _pe:
                                        st.error(f"No se pudo mostrar el PDF: {_pe}")
                                else:
                                    try:
                                        import docx2txt
                                        _text = docx2txt.process(file_path)
                                        st.text_area("Contenido", _text[:4000], height=320,
                                                     key=f"prev_ta_{row['id']}",
                                                     label_visibility="collapsed")
                                    except Exception as _de:
                                        st.warning(f"Vista previa DOCX no disponible: {_de}")
                            else:
                                # Fichero físico no está — mostrar chunks indexados
                                try:
                                    _vs = db_manager.get_vectorstore()
                                    _res = _vs.get(where={"source": name})
                                    _chunks = _res.get("documents", [])[:5]
                                    if _chunks:
                                        st.markdown(
                                            "<div style='background:rgba(99,102,241,0.06);"
                                            "border-radius:8px; padding:0.8rem; font-size:0.82rem;"
                                            "color:#94a3b8; margin-bottom:0.4rem;'>"
                                            "⚠️ Fichero original no disponible. Mostrando fragmentos indexados.</div>",
                                            unsafe_allow_html=True
                                        )
                                        for _i, _c in enumerate(_chunks, 1):
                                            st.markdown(
                                                f"<div style='background:rgba(255,255,255,0.03);"
                                                f"border-left:3px solid #6366f1; padding:0.6rem 0.8rem;"
                                                f"border-radius:0 6px 6px 0; margin-bottom:0.4rem;"
                                                f"font-size:0.8rem; color:#cbd5e1;'>"
                                                f"<b>Fragmento {_i}</b><br>{_safe(_c[:600])}</div>",
                                                unsafe_allow_html=True
                                            )
                                    else:
                                        st.info("No hay contenido disponible para previsualizar.")
                                except Exception:
                                    st.info("Vista previa no disponible.")

                        # Admin: cambiar visibilidad
                        if is_admin:
                            current_ws_list = [w.strip() for w in str(ws or "general").split(",") if w.strip()]
                            extra           = [w for w in current_ws_list if w not in all_ws_available]
                            card_options    = all_ws_available + extra
                            valid_defaults  = [w for w in current_ws_list if w in card_options]

                            selected_ws = st.multiselect(
                                "Visibilidad",
                                options=card_options,
                                default=valid_defaults,
                                format_func=lambda w: (
                                    "🌐 General (todos)" if w == "general"
                                    else ("🔐 Solo administradores" if w == "admin-only" else f"👥 {w}")
                                ),
                                key=f"vis_sel_{row['id']}"
                            )
                            new_ws_str     = ",".join(sorted(set(selected_ws))) if selected_ws else "general"
                            current_ws_str = ",".join(sorted(set(current_ws_list)))
                            if new_ws_str != current_ws_str:
                                if st.button("Guardar", key=f"save_ws_{row['id']}", use_container_width=True, type="primary"):
                                    try:
                                        with st.spinner("Actualizando permisos…"):
                                            db_manager.update_document_workspace(name, selected_ws or ["general"])
                                            audit_service.log_event(
                                                username, user_role, "PERM_CHANGE",
                                                f"{name} → {new_ws_str}", display_name=display_name
                                            )
                                        st.toast("Visibilidad actualizada")
                                    except Exception as e:
                                        st.error(f"Error al actualizar: {e}")
                                    st.rerun()

                            # Generar resumen si falta
                            if not summary_raw.strip():
                                if st.button("✨ Generar resumen", key=f"sum_{row['id']}", use_container_width=True):
                                    with st.spinner("Generando resumen con IA…"):
                                        try:
                                            vectorstore = db_manager.get_vectorstore()
                                            data_vs = vectorstore.get(where={"source": name})
                                            if data_vs and data_vs.get("documents"):
                                                from langchain_core.documents import Document as _LCDoc
                                                splits = [_LCDoc(page_content=t) for t in data_vs["documents"][:6]]
                                                new_summary = ingest_service._generate_summary(splits)
                                                if new_summary:
                                                    db_manager.update_document_summary(name, new_summary)
                                                    st.toast("Resumen generado.")
                                                    st.rerun()
                                                else:
                                                    st.warning("No se pudo generar el resumen.")
                                            else:
                                                st.warning("No hay fragmentos indexados para este documento.")
                                        except Exception as e:
                                            st.error(f"Error al generar resumen: {e}")

                        # Eliminar documento (con confirmación)
                        if _can_delete_doc(ws):
                            del_key = f"confirm_del_{row['id']}"
                            if st.checkbox("Confirmar borrado", key=del_key):
                                if st.button("🗑️ Eliminar", key=f"del_{row['id']}", use_container_width=True):
                                    try:
                                        with st.spinner(f"Eliminando {name}…"):
                                            db_manager.delete_document(name)
                                            try:
                                                audit_service.log_event(
                                                    username, user_role, "DELETE", name,
                                                    display_name=display_name
                                                )
                                            except Exception:
                                                pass
                                        st.toast(f"'{name}' eliminado")
                                    except Exception as e:
                                        st.error(f"Error al eliminar '{name}': {e}")
                                    st.rerun()

                        # Feature K: Historial de versiones
                        try:
                            versions = db_manager.get_document_versions(name)
                            if versions and len(versions) > 0:
                                with st.expander(f"📋 {len(versions)} versión(es)", expanded=False):
                                    for v in versions:
                                        st.markdown(
                                            f"<div style='font-size:0.8rem; color:#94a3b8; padding:3px 0;'>"
                                            f"v{v['version']} · {v.get('uploaded_by','—')} · "
                                            f"{v.get('chunk_count',0)} chunks · {str(v.get('date',''))[:16]}"
                                            f"</div>",
                                            unsafe_allow_html=True
                                        )
                        except Exception:
                            pass

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2 — BÚSQUEDA SEMÁNTICA
    # ═══════════════════════════════════════════════════════════════════════
    with tab_search:
        if docs_df.empty:
            st.markdown("""
                <div style='text-align:center; padding:3rem; background:rgba(255,255,255,0.02);
                            border:1px dashed rgba(99,102,241,0.3); border-radius:16px;'>
                    <div style='font-size:3rem; margin-bottom:0.8rem;'>🔍</div>
                    <h4 style='color:#475569; margin-bottom:0.4rem;'>Sin documentos para buscar</h4>
                    <p style='color:#334155; font-size:0.9rem;'>
                        Sube documentos en la pestaña <b>Documentos</b> para usar la búsqueda semántica.
                    </p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                "<p style='color:#94a3b8; font-size:0.9rem; margin-bottom:1rem;'>"
                "Busca fragmentos exactos dentro de tus documentos sin pasar por el chat.</p>",
                unsafe_allow_html=True
            )
            scol1, scol2 = st.columns([4, 1])
            with scol1:
                search_text = st.text_input(
                    "Término de búsqueda",
                    placeholder="Escribe lo que quieres encontrar en los documentos…",
                    label_visibility="collapsed"
                )
            with scol2:
                k_results = st.selectbox("Resultados", [5, 10, 20], index=0, label_visibility="collapsed")

            if st.button("🔍 Buscar", type="primary", use_container_width=False) and search_text:
                with st.spinner("Buscando en la base vectorial…"):
                    try:
                        vectorstore = db_manager.get_vectorstore()
                        results_raw = vectorstore.similarity_search_with_score(search_text, k=k_results * 3)

                        def _can_see_ws(metadata):
                            if not user_workspaces or "all" in user_workspaces:
                                return True
                            doc_ws = {w.strip() for w in str(metadata.get("workspace", "general")).split(",")}
                            return bool(doc_ws & set(user_workspaces))

                        filtered_results = [
                            (doc, score) for doc, score in results_raw
                            if _can_see_ws(doc.metadata)
                        ][:k_results]

                        if not filtered_results:
                            st.info("No se encontraron fragmentos relevantes para esa búsqueda.")
                        else:
                            st.markdown(
                                f"<p style='color:#818cf8; font-size:0.85rem; margin-bottom:1rem;'>"
                                f"Se encontraron <b>{len(filtered_results)}</b> fragmentos relevantes</p>",
                                unsafe_allow_html=True
                            )
                            by_doc = {}
                            for doc, score in filtered_results:
                                src = doc.metadata.get("source", "Desconocido")
                                by_doc.setdefault(src, []).append((doc, score))

                            for src, chunks in by_doc.items():
                                ext  = src.split(".")[-1].upper() if "." in src else "FILE"
                                icon = "📄" if ext == "PDF" else "📝"
                                label_exp = f"{icon} {src} — {len(chunks)} fragmento{'s' if len(chunks) > 1 else ''}"
                                with st.expander(label_exp, expanded=True):
                                    for doc, score in chunks:
                                        relevance = max(0, int((1 - min(float(score), 2) / 2) * 100))
                                        st.markdown(f"""
                                            <div style='background:rgba(99,102,241,0.06);
                                                        border-left:3px solid #6366f1;
                                                        padding:0.8rem 1rem;
                                                        border-radius:0 8px 8px 0;
                                                        margin-bottom:0.8rem;'>
                                                <div style='font-size:0.7rem; color:#475569; margin-bottom:0.4rem;'>
                                                    Relevancia: <b style='color:#818cf8;'>{relevance}%</b>
                                                </div>
                                                <div style='font-size:0.85rem; color:#cbd5e1; line-height:1.6;'>
                                                    {_safe(doc.page_content)}
                                                </div>
                                            </div>
                                        """, unsafe_allow_html=True)
                    except Exception as e:
                        err_str = str(e).lower()
                        if "no documents" in err_str or "empty" in err_str or "collection" in err_str:
                            st.info("No hay documentos indexados en la base vectorial todavía.")
                        else:
                            st.error(f"Error en la búsqueda: {e}")
