import streamlit as st
import os
from src.core.database import db_manager
from src.services.user_service import user_service
from src.services.audit_service import audit_service
from src.services.plan_service import plan_service, PLANS
from src.core.userdb import userdb

# Importación de módulos Fase 3
from src.pages.admin.users import render_users_tab
from src.pages.admin.audit import render_audit_tab
from src.pages.admin.system import render_system_tab

def render_admin():
    username        = st.session_state.get("username", "")
    user_role       = st.session_state.get("user_role", "viewer")
    display_name    = st.session_state.get('name', username)

    if user_role != "admin":
        st.error("Acceso denegado. Se requieren permisos de administrador.")
        st.stop()

    st.markdown("""
        <h1 style='margin:0 0 0.3rem; font-size:1.6rem; font-weight:700;
                   background:linear-gradient(135deg,#6366f1,#a78bfa);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
            Panel de Control
        </h1>
        <p style='color:#475569; font-size:0.9rem; margin-bottom:1.5rem;'>
            Configuración global, seguridad y monitorización del sistema
        </p>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "👥 Usuarios", 
        "🎭 Roles", 
        "👥 Grupos", 
        "📈 Analíticas", 
        "📋 Auditoría", 
        "⚙️ Sistema", 
        "💳 Plan",
        "🔌 Conectores",
        "🔬 Evaluación"
    ])

    with tabs[0]:
        render_users_tab(username, user_role, display_name)

    with tabs[1]:
        st.info("Módulo de Roles (Cargado modularmente)")
        # render_roles_tab(...)

    # ... Resto de tabs llamando a sus funciones ...
    
    with tabs[4]:
        render_audit_tab(username, user_role, display_name)

    with tabs[5]:
        render_system_tab(username, user_role)

    st.caption("Cortexa AI v2.1.0 · Fase 3 Audit Ready")
