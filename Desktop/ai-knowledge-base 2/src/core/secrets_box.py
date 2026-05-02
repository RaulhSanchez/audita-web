"""
src/core/secrets_box.py
========================

POST-AUDITORÍA · Cifrado simétrico de settings sensibles en reposo.

La auditoría detectó que los siguientes settings se guardaban en SQLite en
texto plano: smtp_pass, sso_*_client_secret, connector_*_api_token,
service_account_json. Si un atacante o un backup mal cifrado escapase, esas
credenciales quedaban comprometidas.

Solución: Fernet (AES-128 en CBC + HMAC-SHA256) con clave en la variable de
entorno `SETTINGS_ENCRYPTION_KEY`. Si la variable no existe, la app sigue
funcionando con un WARNING en logs y los settings van en plaintext (modo
backward-compat). Cuando defines la clave por primera vez, los nuevos writes
quedan cifrados; los antiguos plaintext siguen leyéndose hasta que se reescriban.

Formato del valor cifrado en BD:  "fernet:" + token_b64.
Cualquier valor que no empiece por "fernet:" se trata como plaintext (legacy).
"""
from __future__ import annotations
import os
import logging
from typing import Optional

logger = logging.getLogger("cortexa.secrets")

_PREFIX = "fernet:"
_FERNET_OBJ = None
_FERNET_INIT_DONE = False


def _get_fernet():
    """Devuelve un objeto Fernet listo para usar, o None si la clave no existe."""
    global _FERNET_OBJ, _FERNET_INIT_DONE
    if _FERNET_INIT_DONE:
        return _FERNET_OBJ
    _FERNET_INIT_DONE = True
    key = os.getenv("SETTINGS_ENCRYPTION_KEY", "").strip()
    if not key:
        logger.warning(
            "SETTINGS_ENCRYPTION_KEY no definida: los settings sensibles se "
            "almacenarán en plaintext. Genera una clave con "
            "`python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`."
        )
        return None
    try:
        from cryptography.fernet import Fernet
        _FERNET_OBJ = Fernet(key.encode("utf-8"))
        logger.info("Cifrado de settings activado (Fernet).")
    except Exception as e:
        logger.error(f"SETTINGS_ENCRYPTION_KEY inválida: {e}. Los settings irán en plaintext.")
        _FERNET_OBJ = None
    return _FERNET_OBJ


# ── Lista blanca de settings que SÍ deben cifrarse ─────────────────────────
SENSITIVE_SETTINGS = {
    "smtp_pass",
    "sso_google_client_secret",
    "sso_microsoft_client_secret",
    "sso_ldap_bind_password",
    "connector_gdrive_service_account_json",
    "connector_sharepoint_client_secret",
    "connector_confluence_api_token",
    "vendor_master_key",
}


def is_sensitive(key: str) -> bool:
    """Devuelve True si la clave debe persistirse cifrada."""
    if not key:
        return False
    if key in SENSITIVE_SETTINGS:
        return True
    # Reglas heurísticas adicionales (por si añaden settings nuevos sin actualizar la lista).
    lower = key.lower()
    return any(token in lower for token in (
        "password", "secret", "token", "api_key", "service_account",
    ))


def encrypt_if_sensitive(key: str, value: Optional[str]) -> Optional[str]:
    """Cifra `value` si la clave es sensible y la SETTINGS_ENCRYPTION_KEY existe.
    Si no, devuelve `value` tal cual.
    """
    if value is None or value == "":
        return value
    if not is_sensitive(key):
        return value
    f = _get_fernet()
    if not f:
        return value
    try:
        return _PREFIX + f.encrypt(str(value).encode("utf-8")).decode("ascii")
    except Exception as e:
        logger.error(f"Error cifrando '{key}': {e}. Se guardará en plaintext.")
        return value


def decrypt_if_needed(value: Optional[str]) -> Optional[str]:
    """Si `value` empieza por 'fernet:' lo descifra; si no, lo devuelve tal cual."""
    if not value:
        return value
    if not isinstance(value, str) or not value.startswith(_PREFIX):
        return value
    f = _get_fernet()
    if not f:
        # No tenemos la clave para descifrar — devolvemos el token cifrado tal
        # cual; el caller debería detectar el prefijo y mostrar error de
        # configuración al admin.
        return value
    try:
        return f.decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except Exception as e:
        logger.error(f"Error descifrando setting: {e}")
        return value


def is_encrypted(value: Optional[str]) -> bool:
    """True si el valor está cifrado (formato fernet:...)."""
    return isinstance(value, str) and value.startswith(_PREFIX)
