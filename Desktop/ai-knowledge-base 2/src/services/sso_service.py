"""
SSO / OAuth2 service — Google + Microsoft (urllib stdlib only).
Reads all configuration from userdb settings at runtime.

Settings keys used:
  sso_google_client_id, sso_google_client_secret
  sso_microsoft_client_id, sso_microsoft_client_secret, sso_microsoft_tenant_id
  sso_redirect_uri          — must match what's registered in Google/MS console
  sso_allowed_domains       — comma-separated, e.g. "miempresa.com,otrodominio.es"
                              Leave empty to allow any domain.
  sso_auto_create_users     — "true" / "false"
  sso_default_role          — "viewer" / "editor" / "admin"
"""

import json
import secrets
import urllib.parse
import urllib.request
from typing import Optional

# ─── OAuth2 endpoints ───────────────────────────────────────────────────────

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_INFO_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

MICROSOFT_AUTH_URL  = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
MICROSOFT_INFO_URL  = "https://graph.microsoft.com/v1.0/me"


def _setting(key: str, default: str = "") -> str:
    from src.core.userdb import userdb
    return userdb.get_setting(key, default) or default


# ─── Build auth URLs ────────────────────────────────────────────────────────

def get_google_auth_url(state: str) -> str:
    client_id    = _setting("sso_google_client_id")
    redirect_uri = _setting("sso_redirect_uri")
    if not client_id or not redirect_uri:
        raise ValueError("Google SSO no está configurado (client_id / redirect_uri).")
    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "prompt":        "select_account",
        "access_type":   "online",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def get_microsoft_auth_url(state: str) -> str:
    client_id    = _setting("sso_microsoft_client_id")
    redirect_uri = _setting("sso_redirect_uri")
    tenant       = _setting("sso_microsoft_tenant_id", "common")
    if not client_id or not redirect_uri:
        raise ValueError("Microsoft SSO no está configurado (client_id / redirect_uri).")
    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile User.Read",
        "state":         state,
        "prompt":        "select_account",
    }
    return MICROSOFT_AUTH_URL.format(tenant=tenant) + "?" + urllib.parse.urlencode(params)


# ─── Token exchange helpers ─────────────────────────────────────────────────

def _post_form(url: str, data: dict) -> dict:
    """POST application/x-www-form-urlencoded, return parsed JSON."""
    body = urllib.parse.urlencode(data).encode()
    req  = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _get_bearer(url: str, access_token: str) -> dict:
    """GET with Bearer auth, return parsed JSON."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


# ─── Code exchange ──────────────────────────────────────────────────────────

def exchange_google_code(code: str) -> dict:
    """Exchange auth code → access_token → user info dict."""
    token_data = _post_form(GOOGLE_TOKEN_URL, {
        "code":          code,
        "client_id":     _setting("sso_google_client_id"),
        "client_secret": _setting("sso_google_client_secret"),
        "redirect_uri":  _setting("sso_redirect_uri"),
        "grant_type":    "authorization_code",
    })
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError(f"Google token error: {token_data}")
    info = _get_bearer(GOOGLE_INFO_URL, access_token)
    return {
        "email": info.get("email", ""),
        "name":  info.get("name", info.get("email", "")),
        "sub":   info.get("sub", ""),
        "provider": "google",
    }


def exchange_microsoft_code(code: str) -> dict:
    """Exchange auth code → access_token → user info dict."""
    tenant = _setting("sso_microsoft_tenant_id", "common")
    token_data = _post_form(MICROSOFT_TOKEN_URL.format(tenant=tenant), {
        "code":          code,
        "client_id":     _setting("sso_microsoft_client_id"),
        "client_secret": _setting("sso_microsoft_client_secret"),
        "redirect_uri":  _setting("sso_redirect_uri"),
        "grant_type":    "authorization_code",
        "scope":         "openid email profile User.Read",
    })
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError(f"Microsoft token error: {token_data}")
    info = _get_bearer(MICROSOFT_INFO_URL, access_token)
    email = info.get("mail") or info.get("userPrincipalName", "")
    return {
        "email": email,
        "name":  info.get("displayName", email),
        "sub":   info.get("id", ""),
        "provider": "microsoft",
    }


# ─── Domain allowlist ───────────────────────────────────────────────────────

def _domain_allowed(email: str) -> bool:
    allowed_raw = _setting("sso_allowed_domains", "")
    if not allowed_raw.strip():
        return True   # no restriction
    domain = email.split("@")[-1].lower()
    allowed = [d.strip().lower() for d in allowed_raw.split(",") if d.strip()]
    return domain in allowed


# ─── Resolve / auto-create user ─────────────────────────────────────────────

def resolve_user(user_info: dict) -> Optional[dict]:
    """
    Given the dict returned by exchange_*_code, find or create the local user.
    Returns the user dict (same shape as userdb.get_user) or None on failure.
    """
    from src.core.userdb import userdb

    email    = user_info.get("email", "").strip().lower()
    name     = user_info.get("name", email)
    provider = user_info.get("provider", "sso")

    if not email:
        return None

    if not _domain_allowed(email):
        raise PermissionError(
            f"El dominio de '{email}' no está en la lista de dominios permitidos."
        )

    # POST-AUDITORÍA · Generación determinista pero a prueba de colisiones.
    # La versión original colapsaba "john.doe@a.com" y "john_doe@a.com" al mismo
    # username, permitiendo que un usuario heredase la cuenta del otro. Ahora:
    #   1) sustituimos chars no seguros con `_`
    #   2) añadimos sufijo de 8 hex del hash del email original
    #   3) verificamos que el email coincide antes de devolver la cuenta
    import hashlib as _hashlib
    _email_norm = email.strip().lower()
    _safe_part = _email_norm.replace("@", "_at_").replace(".", "_").replace("+", "_plus_")
    _suffix = _hashlib.sha256(_email_norm.encode("utf-8")).hexdigest()[:8]
    username = f"{_safe_part}__{_suffix}"

    existing = userdb.get_user(username)
    if existing:
        # Verificar que el email coincide; si no, abortar para no fusionar cuentas.
        if (existing.get("email") or "").strip().lower() != _email_norm:
            raise PermissionError(
                "Conflicto de cuenta: el username ya existe con otro email. "
                "Contacta con el administrador."
            )
        return existing

    # Auto-create?
    if _setting("sso_auto_create_users", "false").lower() != "true":
        raise PermissionError(
            f"El usuario '{email}' no existe y la creación automática está desactivada."
        )

    from src.services.plan_service import plan_service
    ok, msg = plan_service.check_user_limit()
    if not ok:
        raise PermissionError(f"Límite de usuarios alcanzado: {msg}")

    import bcrypt
    fake_hash = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()

    default_role = _setting("sso_default_role", "viewer")
    created = userdb.add_user(
        username      = username,
        name          = name,
        email         = email,
        password_hash = fake_hash,
        role          = default_role,
        workspaces    = ["general"],
        can_upload    = False,
        upload_groups = [],
        can_delete    = False,
        delete_groups = [],
    )
    if not created:
        return None

    return userdb.get_user(username)


# ─── Inject into Streamlit session ──────────────────────────────────────────

def inject_session(user: dict) -> None:
    """
    Writes the user into st.session_state in the same shape that
    streamlit-authenticator would — so the rest of the app works unchanged.
    """
    import streamlit as st
    st.session_state["authentication_status"] = True
    st.session_state["username"]              = user["username"]
    st.session_state["name"]                  = user.get("name", user["username"])
    st.session_state["role"]                  = user.get("role", "viewer")
    st.session_state["workspaces"]            = user.get("workspaces", ["general"])
    st.session_state["can_upload"]            = user.get("can_upload", False)
    st.session_state["can_delete"]            = user.get("can_delete", False)
    st.session_state["sso_login"]             = True


# ─── High-level callback handler ────────────────────────────────────────────

def handle_callback(provider: str, code: str, state: str, expected_state: str) -> dict:
    """
    Full callback flow: validate state → exchange code → resolve user → inject session.
    Returns {"ok": True, "user": {...}} or {"ok": False, "error": "..."}
    """
    if state != expected_state:
        return {"ok": False, "error": "State mismatch — posible ataque CSRF."}

    try:
        if provider == "google":
            user_info = exchange_google_code(code)
        elif provider == "microsoft":
            user_info = exchange_microsoft_code(code)
        else:
            return {"ok": False, "error": f"Proveedor desconocido: {provider}"}

        user = resolve_user(user_info)
        if not user:
            return {"ok": False, "error": "No se pudo resolver el usuario."}

        inject_session(user)
        return {"ok": True, "user": user}

    except PermissionError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"Error SSO: {e}"}


# ─── Generate a secure state token ──────────────────────────────────────────

def new_state() -> str:
    return secrets.token_urlsafe(32)
