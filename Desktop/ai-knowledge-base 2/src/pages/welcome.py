import streamlit as st
from src.core.database import db_manager
from src.services.user_service import user_service
from src.core.userdb import userdb


def render_welcome():
    username        = st.session_state.get("username", "")
    user_role       = st.session_state.get("user_role", "viewer")
    user_name       = st.session_state.get("name", username)
    user_workspaces = st.session_state.get("user_workspaces", [])

    product_name  = userdb.get_setting("product_name", "Cortexa AI")
    company_name  = userdb.get_setting("company_name", "Tu Empresa")
    welcome_title = userdb.get_setting("welcome_title", "Base de conocimiento corporativo")
    welcome_sub   = userdb.get_setting(
        "welcome_subtitle", "100% local. Tus datos no salen de tu organización."
    )

    # ── Stats ─────────────────────────────────────────────────────────────────
    try:
        docs_df = db_manager.get_all_documents(workspace_filter=user_workspaces)
        doc_count = len(docs_df)
    except Exception:
        doc_count = 0

    try:
        all_users  = user_service.get_all_users()
        user_count = len(all_users)
    except Exception:
        user_count = 0

    try:
        analytics = db_manager.get_analytics()
        qpu = analytics.get("queries_per_user")
        if qpu is not None and not qpu.empty and "total" in qpu.columns:
            total_queries = int(qpu["total"].sum())
        else:
            total_queries = 0
    except Exception:
        total_queries = 0

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(f"""
        <div style='text-align:center; padding:3rem 1rem 2rem;'>
            <div style='font-size:0.85rem; color:#6366f1; font-weight:600;
                        text-transform:uppercase; letter-spacing:2px; margin-bottom:0.8rem;'>
                {company_name}
            </div>
            <h1 style='font-size:2.8rem; font-weight:800; margin:0 0 0.5rem;
                       background:linear-gradient(135deg,#818cf8,#c084fc,#60a5fa);
                       -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
                {product_name}
            </h1>
            <p style='color:#94a3b8; font-size:1.1rem; max-width:600px; margin:0 auto 0.5rem;'>
                {welcome_title}
            </p>
            <p style='color:#475569; font-size:0.9rem; max-width:500px; margin:0 auto;'>
                {welcome_sub}
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Feature cards ─────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns(3)
    for col, icon, title, desc in [
        (f1, "🔒", "100% Local",
         "Tus documentos nunca salen de tu infraestructura. Sin internet, sin terceros."),
        (f2, "🧠", "IA Privada",
         "Powered by Ollama. Sin APIs externas, sin costes por consulta, sin límites."),
        (f3, "👥", "Control total",
         "Roles, grupos y permisos granulares. Cada usuario ve solo lo que debe ver."),
    ]:
        with col:
            st.markdown(f"""
                <div style='background:rgba(99,102,241,0.06);
                            border:1px solid rgba(99,102,241,0.2);
                            border-radius:16px; padding:1.5rem; text-align:center;
                            min-height:160px; display:flex; flex-direction:column;
                            justify-content:center;'>
                    <div style='font-size:2rem; margin-bottom:0.6rem;'>{icon}</div>
                    <div style='color:#f1f5f9; font-weight:600; margin-bottom:0.4rem;'>
                        {title}
                    </div>
                    <div style='color:#64748b; font-size:0.82rem; line-height:1.4;'>
                        {desc}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Stats row ─────────────────────────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns(4)
    estado_val   = "Activo"  if doc_count > 0 else "Sin datos"
    estado_color = "#10b981" if doc_count > 0 else "#f59e0b"

    is_admin = user_role == "admin"
    for col, val, label, color in [
        (sc1, doc_count,                                  "Documentos",  "#818cf8"),
        (sc2, user_count if is_admin else "—",            "Usuarios",    "#a78bfa" if is_admin else "#334155"),
        (sc3, total_queries if is_admin else "—",         "Consultas",   "#6366f1" if is_admin else "#334155"),
        (sc4, estado_val,                                 "Estado",      estado_color),
    ]:
        with col:
            st.markdown(f"""
                <div style='background:rgba(15,23,42,0.6);
                            border:1px solid rgba(255,255,255,0.06);
                            border-radius:12px; padding:1rem; text-align:center;'>
                    <div style='font-size:1.8rem; font-weight:700; color:{color};'>
                        {val}
                    </div>
                    <div style='font-size:0.75rem; color:#64748b; text-transform:uppercase;
                                letter-spacing:1px; margin-top:4px;'>
                        {label}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CTA ───────────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if doc_count > 0:
            st.markdown(f"""
                <div style='text-align:center; padding:1rem;'>
                    <p style='color:#94a3b8; font-size:0.9rem;'>
                        Bienvenido de vuelta,
                        <b style='color:#f1f5f9;'>{user_name}</b>.
                        Tienes acceso a {doc_count}
                        documento{'s' if doc_count != 1 else ''}.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("💬 Ir al Chat →", type="primary", use_container_width=True):
                st.session_state["_nav_to_chat"] = True
                st.rerun()
        else:
            st.info(
                "📂 Aún no hay documentos. "
                "Ve a **Biblioteca** para subir tus primeros archivos."
            )

    # ── Getting-started guide (admin only, no docs yet) ───────────────────────
    if doc_count == 0 and user_role == "admin":
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='background:rgba(99,102,241,0.08);
                        border:1px solid rgba(99,102,241,0.25);
                        border-radius:16px; padding:2rem;'>
                <h3 style='color:#f1f5f9; margin:0 0 1.2rem;'>🚀 Primeros pasos</h3>
                <div style='display:grid; grid-template-columns:repeat(3,1fr); gap:1.2rem;'>
                    <div>
                        <div style='color:#6366f1; font-weight:700; font-size:1.2rem;
                                    margin-bottom:0.3rem;'>01</div>
                        <div style='color:#c084fc; font-weight:600; margin-bottom:0.3rem;'>
                            Crea grupos
                        </div>
                        <div style='color:#64748b; font-size:0.82rem; line-height:1.5;'>
                            Ve a <b style='color:#94a3b8;'>Administración → Grupos</b> para
                            organizar el conocimiento por departamento.
                        </div>
                    </div>
                    <div>
                        <div style='color:#6366f1; font-weight:700; font-size:1.2rem;
                                    margin-bottom:0.3rem;'>02</div>
                        <div style='color:#c084fc; font-weight:600; margin-bottom:0.3rem;'>
                            Sube documentos
                        </div>
                        <div style='color:#64748b; font-size:0.82rem; line-height:1.5;'>
                            <b style='color:#94a3b8;'>Biblioteca</b> → arrastra PDFs o DOCXs.
                            El sistema los indexa automáticamente.
                        </div>
                    </div>
                    <div>
                        <div style='color:#6366f1; font-weight:700; font-size:1.2rem;
                                    margin-bottom:0.3rem;'>03</div>
                        <div style='color:#c084fc; font-weight:600; margin-bottom:0.3rem;'>
                            Invita usuarios
                        </div>
                        <div style='color:#64748b; font-size:0.82rem; line-height:1.5;'>
                            <b style='color:#94a3b8;'>Administración → Nuevo usuario</b>.
                            Asigna roles y grupos de acceso.
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
