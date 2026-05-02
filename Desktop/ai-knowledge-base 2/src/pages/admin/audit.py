import streamlit as st
from src.services.audit_service import audit_service

def render_audit_tab(username, user_role, display_name):
    st.markdown("<h3 style='color:#f1f5f9; font-size:1.1rem; margin-bottom:1rem;'>Registro de actividad</h3>",
                unsafe_allow_html=True)
    
    logs_df = audit_service.get_logs(limit=500)
    
    if not logs_df.empty:
        action_filter = st.multiselect("Filtrar por acción",
            options=sorted(logs_df['action'].unique()), placeholder="Todas")
            
        display_df = logs_df[logs_df['action'].isin(action_filter)] if action_filter else logs_df
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros de actividad todavía.")
