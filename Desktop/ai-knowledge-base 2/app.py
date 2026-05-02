import streamlit as st
import yaml
import os
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from src.services.audit_service import audit_service

# ── Inicializar base de datos de usuarios (antes que cualquier otra cosa) ──
from src.core.userdb import userdb
try:
    userdb.init_tables()
    userdb.migrate_from_yaml()
except Exception as _db_init_err:
    st.error(
        f"⚠️ Error inicializando la base de datos: {_db_init_err}. "
        "Verifica que el directorio './db' sea accesible y reinicia la aplicación."
    )
    st.stop()

try:
    PRODUCT_NAME = userdb.get_setting('product_name', 'Cortexa AI')
except Exception:
    PRODUCT_NAME = 'Cortexa AI'

# ── Scheduler de sync programado (una sola vez por proceso) ──────────────────
try:
    from src.services.scheduler_service import start_scheduler
    start_scheduler()
except Exception as _sched_err:
    import logging as _logging
    _logging.warning(f"Scheduler no iniciado: {_sched_err}")

st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
    <style>
    /* Fuentes locales Fase 3 */
    @font-face {
        font-family: 'Outfit';
        src: url('/assets/fonts/Outfit-Bold.ttf') format('truetype');
        font-weight: 700;
    }
    @font-face {
        font-family: 'Outfit';
        src: url('/assets/fonts/Outfit-Regular.ttf') format('truetype');
        font-weight: 400;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Outfit', sans-serif; }

    .stApp {
        background: radial-gradient(ellipse at top left, #1e1b4b 0%, #0f172a 50%, #020617 100%);
        color: #f1f5f9;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* Sidebar nativo de Streamlit 1.40+ */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(99, 102, 241, 0.2) !important;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] strong { color: #f1f5f9 !important; }

    [data-testid="stSidebarNav"] { background: transparent !important; }
    [data-testid="stSidebarNavLink"] {
        border-radius: 10px !important;
        margin: 2px 8px !important;
        padding: 10px 14px !important;
        color: #94a3b8 !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebarNavLink"]:hover {
        background: rgba(99, 102, 241, 0.15) !important;
        color: #a5b4fc !important;
    }
    [data-testid="stSidebarNavLink"][aria-selected="true"] {
        background: rgba(99, 102, 241, 0.25) !important;
        color: #818cf8 !important;
        border-left: 3px solid #6366f1 !important;
    }

    .stButton > button {
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        background: rgba(99, 102, 241, 0.1) !important;
        color: #a5b4fc !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3) !important;
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: rgba(99, 102, 241, 0.6) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 25px rgba(99, 102, 241, 0.5) !important;
    }

    .stChatMessage {
        border-radius: 16px !important;
        margin-bottom: 1.2rem !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        background: rgba(255,255,255,0.03) !important;
        backdrop-filter: blur(10px) !important;
        padding: 1rem 1.2rem !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        border-color: rgba(99, 102, 241, 0.2) !important;
        background: rgba(99, 102, 241, 0.05) !important;
    }

    .stChatInput textarea {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: 14px !important;
        color: #f1f5f9 !important;
    }
    .stChatInput textarea:focus {
        border-color: rgba(99, 102, 241, 0.7) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.5) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 4px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        color: #64748b !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.2) !important;
        color: #a5b4fc !important;
    }

    .stTextInput input, .stSelectbox > div > div {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(99, 102, 241, 0.25) !important;
        border-radius: 10px !important;
        color: #f1f5f9 !important;
    }

    .stDataFrame { border-radius: 12px !important; overflow: hidden !important; }

    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.5) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        color: #a5b4fc !important;
        font-weight: 500 !important;
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.6); }

    .stAlert { border-radius: 12px !important; border: none !important; }
    .stProgress > div > div {
        background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
        border-radius: 4px !important;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(24px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .login-card-anim {
        animation: fadeInUp 0.55s cubic-bezier(0.16,1,0.3,1) both;
    }
    </style>
""", unsafe_allow_html=True)

# ── Cargar config.yaml solo para cookie settings ──────────────────────────
try:
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader) or {}
except Exception:
    config = {}
config.setdefault('cookie', {'name': 'cortexa_session', 'key': '', 'expiry_days': 30})

# ── Cookie secret: env > runtime persistido > autogenerado ───────────────
# NUNCA dejamos un default 'change-me' que pueda colarse en producción.
import secrets as _secrets
_runtime_path = os.path.join(os.path.dirname(__file__), 'config.runtime.yaml')
_runtime: dict = {}
if os.path.exists(_runtime_path):
    try:
        with open(_runtime_path) as _rh:
            _runtime = yaml.load(_rh, Loader=SafeLoader) or {}
    except Exception:
        _runtime = {}

cookie_key = os.getenv("COOKIE_SECRET_KEY") or _runtime.get('cookie_key') or config['cookie'].get('key') or ''
if not cookie_key:
    cookie_key = _secrets.token_urlsafe(48)
    _runtime['cookie_key'] = cookie_key
    try:
        with open(_runtime_path, 'w') as _rh:
            yaml.safe_dump(_runtime, _rh)
        os.chmod(_runtime_path, 0o600)
    except Exception:
        pass
    import logging as _logging
    _logging.warning("COOKIE_SECRET_KEY no definida; generada y persistida en config.runtime.yaml. Defínela explícitamente en .env para producción.")

# ── Autenticación con credenciales desde SQLite ───────────────────────────
try:
    _db_credentials = userdb.get_credentials_dict()
except Exception:
    _db_credentials = {"usernames": {}}

try:
    _expiry_days = int(userdb.get_setting('session_expiry_days', str(config['cookie'].get('expiry_days', 30))))
except Exception:
    _expiry_days = config['cookie'].get('expiry_days', 30)

authenticator = stauth.Authenticate(
    _db_credentials,
    config['cookie']['name'],
    cookie_key,
    _expiry_days
)

# ── SSO: manejar callback OAuth2 antes del flujo normal ──────────────────
_sso_handled = False
try:
    _qp = st.query_params
    _sso_code     = _qp.get("sso_code")
    _sso_state    = _qp.get("sso_state")
    _sso_provider = _qp.get("sso_provider")

    if _sso_code and _sso_state and _sso_provider:
        # Recuperar state guardado en session
        _expected_state = st.session_state.get("sso_state", "")
        from src.services.sso_service import handle_callback
        _sso_result = handle_callback(_sso_provider, _sso_code, _sso_state, _expected_state)
        # Limpiar params de la URL
        st.query_params.clear()
        st.session_state.pop("sso_state", None)
        if _sso_result["ok"]:
            _sso_handled = True
            # No llamamos a authenticator.login() — la sesión ya fue inyectada
        else:
            import logging as _logging
            _logging.warning(f"SSO error: {_sso_result.get('error')}")
            st.error("❌ No se pudo completar el inicio de sesión. Inténtalo de nuevo o usa usuario y contraseña.")
except Exception as _sso_ex:
    import logging as _logging
    _logging.exception("SSO callback error")
    st.error("❌ Error en el inicio de sesión. Por favor, inténtalo de nuevo.")

# ── Estado: no autenticado (Login o Fallo) ──────────────────────────────
if not st.session_state.get("authentication_status"):
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='collapsedControl'], header[data-testid='stHeader'] { display: none !important; }</style>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
            <div class='login-card-anim' style='background:rgba(15,23,42,0.8); border:1px solid rgba(99,102,241,0.2);
                        border-radius:24px; padding:3rem; backdrop-filter:blur(20px);
                        box-shadow:0 25px 50px rgba(0,0,0,0.4);'>
        """, unsafe_allow_html=True)
        try:
            st.image("assets/logo.png", use_container_width=True)
        except Exception:
            pass
        try:
            _product_name  = userdb.get_setting('product_name',  'Cortexa AI')
            _welcome_title = userdb.get_setting('welcome_title', 'Base de conocimiento corporativo')
        except Exception:
            _product_name  = 'Cortexa AI'
            _welcome_title = 'Base de conocimiento corporativo'
        st.markdown(f"""
            <div style='text-align:center; margin-bottom:1.5rem;'>
                <h1 style='font-size:1.8rem; font-weight:700;
                           background:linear-gradient(135deg,#818cf8,#c084fc);
                           -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0;'>
                    {_product_name}
                </h1>
                <p style='color:#64748b; font-size:0.9rem; margin-top:0.3rem;'>{_welcome_title}</p>
            </div>
        """, unsafe_allow_html=True)

        # ── Mostrar error de login si falló ──────────────────────────────
        if st.session_state.get("authentication_status") is False:
            st.error("❌ Usuario o contraseña incorrectos.")

        # ── Botones SSO (si están configurados) ──────────────────────────
        try:
            _google_cfg    = userdb.get_setting("sso_google_client_id", "")
            _microsoft_cfg = userdb.get_setting("sso_microsoft_client_id", "")
            _sso_enabled   = bool(_google_cfg or _microsoft_cfg)
        except Exception:
            _sso_enabled = False

        if _sso_enabled:
            st.markdown("""
                <p style='text-align:center; color:#64748b; font-size:0.8rem;
                           margin:0.5rem 0 0.8rem;'>Inicia sesión con tu cuenta corporativa</p>
            """, unsafe_allow_html=True)
            _btn_cols = st.columns(2 if (_google_cfg and _microsoft_cfg) else 1)
            if _google_cfg:
                with _btn_cols[0]:
                    if st.button("🔵 Continuar con Google", use_container_width=True):
                        from src.services.sso_service import get_google_auth_url, new_state
                        _state = new_state()
                        st.session_state["sso_state"] = _state
                        st.markdown(
                            f'<meta http-equiv="refresh" content="0; url={get_google_auth_url(_state)}">',
                            unsafe_allow_html=True
                        )
            if _microsoft_cfg:
                _ms_idx = 1 if (_google_cfg and _microsoft_cfg) else 0
                with _btn_cols[_ms_idx]:
                    if st.button("🟦 Continuar con Microsoft", use_container_width=True):
                        from src.services.sso_service import get_microsoft_auth_url, new_state
                        _state = new_state()
                        st.session_state["sso_state"] = _state
                        st.markdown(
                            f'<meta http-equiv="refresh" content="0; url={get_microsoft_auth_url(_state)}">',
                            unsafe_allow_html=True
                        )

        # ── Formulario de Login Estándar ─────────────────────────────
        if not _sso_handled:
             authenticator.login(location='main')

        # POST-AUDITORÍA · Recuperación de contraseña self-service
        with st.expander("¿Olvidaste tu contraseña?"):
            st.caption(
                "Introduce tu email corporativo. Si está registrado y el "
                "administrador ha configurado el envío SMTP, recibirás una "
                "contraseña temporal en unos minutos."
            )
            with st.form("forgot_password_form", clear_on_submit=True):
                _fp_email = st.text_input("Email", key="fp_email", placeholder="tu@empresa.com")
                _fp_btn = st.form_submit_button("Enviar contraseña temporal")
            if _fp_btn:
                # Devolvemos siempre el mismo mensaje para no filtrar si el
                # email existe o no (anti-enumeración).
                _generic = (
                    "Si el email está registrado y SMTP está configurado, "
                    "recibirás una contraseña temporal en unos minutos."
                )
                try:
                    from src.services.email_service import email_service
                    import secrets as _s, bcrypt as _bc
                    target_user = None
                    for u in userdb.get_all_users():
                        if (u.get("email") or "").strip().lower() == (_fp_email or "").strip().lower():
                            target_user = u
                            break
                    if target_user and email_service.is_configured():
                        _new_pwd = _s.token_urlsafe(16)
                        _hash = _bc.hashpw(_new_pwd.encode(), _bc.gensalt()).decode()
                        userdb.update_password(target_user["username"], _hash, temp=True)
                        try:
                            email_service.send_temp_password(
                                target_user["email"], target_user["username"], _new_pwd
                            )
                        except Exception:
                            pass
                except Exception:
                    pass
                st.info(_generic)

        st.markdown('</div>', unsafe_allow_html=True)

# ── Estado: autenticado ───────────────────────────────────────────────────
elif st.session_state.get("authentication_status"):
    username = st.session_state["username"]

    # Leer datos del usuario desde SQLite en cada render
    try:
        user_data = userdb.get_user(username) or {}
    except Exception:
        user_data = {}

    user_role = user_data.get('role', 'viewer')

    if user_role == 'admin':
        user_workspaces = ['all']
        can_upload      = True
        upload_groups   = ['all']
        can_delete      = True
        delete_groups   = ['all']
    else:
        user_workspaces = user_data.get('workspaces', [])
        can_upload      = user_data.get('can_upload', False)
        upload_groups   = user_data.get('upload_groups', ['all'] if can_upload else [])
        can_delete      = user_data.get('can_delete', False)
        delete_groups   = user_data.get('delete_groups', [])

    # Limpiar sesión si cambió el usuario
    if st.session_state.get("_logged_user") != username:
        for key in ["current_session_id", "messages", "ratings", "_ratings_session_id"]:
            st.session_state.pop(key, None)
        st.session_state["_logged_user"] = username

    # Guardar en session_state para que las páginas lo lean
    st.session_state["user_role"]       = user_role
    st.session_state["user_workspaces"] = user_workspaces
    st.session_state["can_upload"]      = can_upload
    st.session_state["upload_groups"]   = upload_groups
    st.session_state["can_delete"]      = can_delete
    st.session_state["delete_groups"]   = delete_groups

    # ── Forzar cambio de contraseña temporal ─────────────────────────────
    if user_data.get('temp_password', False) and user_role != 'admin':
        st.markdown("""
            <div style='max-width:480px; margin:4rem auto;
                        background:rgba(15,23,42,0.9); border:1px solid rgba(99,102,241,0.3);
                        border-radius:20px; padding:2.5rem; backdrop-filter:blur(20px);
                        box-shadow:0 20px 40px rgba(0,0,0,0.4);'>
                <div style='text-align:center; margin-bottom:2rem;'>
                    <div style='font-size:2.5rem; margin-bottom:0.5rem;'>🔑</div>
                    <h2 style='color:#f1f5f9; margin:0 0 0.4rem; font-size:1.4rem;'>
                        Cambia tu contraseña
                    </h2>
                    <p style='color:#64748b; font-size:0.9rem; margin:0;'>
                        Tu cuenta usa una contraseña temporal.<br>
                        Debes establecer una nueva antes de continuar.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        with st.form("force_pwd_change"):
            new_pwd  = st.text_input("Nueva contraseña",    type="password", placeholder="Mínimo 8 caracteres")
            new_pwd2 = st.text_input("Confirmar contraseña", type="password", placeholder="Repite la contraseña")
            submitted = st.form_submit_button("Establecer contraseña", type="primary", use_container_width=True)
        if submitted:
            if not new_pwd or len(new_pwd) < 8:
                st.error("La contraseña debe tener al menos 8 caracteres.")
            elif new_pwd != new_pwd2:
                st.error("Las contraseñas no coinciden.")
            else:
                try:
                    from src.services.user_service import user_service
                    ok, msg = user_service.update_password(username, new_pwd, temp=False)
                    if ok:
                        st.success("✅ Contraseña actualizada. Redirigiendo…")
                        st.rerun()
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"Error al actualizar la contraseña: {e}")
        st.stop()

    # ── Sidebar ───────────────────────────────────────────────────────────
    with st.sidebar:
        try:
            st.image("assets/logo.png", width=110)
        except Exception:
            pass

        _role_label = '👑 Superadmin' if user_role == 'admin' else f'🏷️ {user_data.get("role", user_role).capitalize()}'
        st.markdown(f"""
            <div style='margin:0.8rem 0; padding:0.8rem; background:rgba(99,102,241,0.1);
                        border-radius:12px; border:1px solid rgba(99,102,241,0.2);'>
                <div style='font-size:1rem; color:#f1f5f9; font-weight:600;'>
                    {st.session_state.get('name', username)}
                </div>
                <div style='font-size:0.75rem; color:#6366f1; font-weight:600;
                            text-transform:uppercase; letter-spacing:1px; margin-top:4px;'>
                    {_role_label}
                </div>
            </div>
        """, unsafe_allow_html=True)
        authenticator.logout('Cerrar sesión', 'sidebar')
        st.markdown("---")

    # ── Navegación ────────────────────────────────────────────────────────
    from src.pages.welcome   import render_welcome
    from src.pages.dashboard import render_dashboard
    from src.pages.library   import render_library
    from src.pages.admin     import render_admin

    pages = [
        st.Page(render_welcome,   title="Inicio",        icon="🏠", default=True),
        st.Page(render_dashboard, title="Chat",           icon="💬"),
        st.Page(render_library,   title="Biblioteca",     icon="📚"),
    ]
    if user_role == "admin":
        pages.append(st.Page(render_admin, title="Administración", icon="⚙️"))

    # Redirigir al chat si el usuario pulsó "Ir al Chat" en la página de inicio
    if st.session_state.pop("_nav_to_chat", False):
        try:
            chat_page = next(p for p in pages if p.title == "Chat")
            st.switch_page(chat_page)
        except Exception:
            pass  # Si falla switch_page, simplemente renderiza normal

    st.navigation(pages).run()
