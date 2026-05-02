import streamlit as st
import os
from src.core.userdb import userdb

def render_system_tab(username, user_role):
    st.markdown("<h3 style='color:#f1f5f9; font-size:1.1rem; margin-bottom:1rem;'>Configuración del sistema</h3>",
                unsafe_allow_html=True)
    
    with st.expander("🤖 Modelo de IA", expanded=True):
        current_model = userdb.get_setting("ollama_model", "qwen2.5:7b")
        st.write(f"Modelo actual: **{current_model}**")
        # Lógica de cambio de modelo...
    
    with st.expander("🛡️ Backups", expanded=False):
        st.write("Gestión de copias de seguridad...")
