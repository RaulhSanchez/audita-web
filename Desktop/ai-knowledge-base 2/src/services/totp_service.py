"""Servicio de autenticación de dos factores (2FA/OTP) con TOTP."""
import os
import base64
import io

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

from src.core.userdb import userdb


class TOTPService:
    def is_available(self) -> bool:
        return PYOTP_AVAILABLE

    def generate_secret(self) -> str:
        if not PYOTP_AVAILABLE:
            raise RuntimeError("pyotp no instalado. Ejecuta: pip install pyotp")
        return pyotp.random_base32()

    def get_provisioning_uri(self, username: str, secret: str) -> str:
        if not PYOTP_AVAILABLE:
            return ""
        product_name = userdb.get_setting("product_name", "Cortexa AI")
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=product_name)

    def generate_qr_base64(self, username: str, secret: str) -> str:
        """Genera QR code como imagen base64 para mostrar en Streamlit."""
        if not QRCODE_AVAILABLE:
            return ""
        uri = self.get_provisioning_uri(username, secret)
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def verify_code(self, secret: str, code: str) -> bool:
        if not PYOTP_AVAILABLE or not secret or not code:
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    def enable_2fa(self, username: str) -> tuple[bool, str, str]:
        """
        Genera un secret y lo guarda (pero no lo activa hasta verificar).
        Returns (success, secret, qr_base64).
        """
        if not PYOTP_AVAILABLE:
            return False, "", ""
        secret = self.generate_secret()
        userdb.update_user(username, totp_secret=secret, totp_enabled=0)
        qr = self.generate_qr_base64(username, secret)
        return True, secret, qr

    def confirm_2fa(self, username: str, code: str) -> tuple[bool, str]:
        """Verifica el código y activa 2FA si es correcto."""
        user = userdb.get_user(username)
        if not user:
            return False, "Usuario no encontrado."
        # Read secret directly from DB
        import sqlite3
        conn = sqlite3.connect("./db/cortexa_meta.db")
        c = conn.cursor()
        c.execute("SELECT totp_secret FROM users WHERE username=?", (username,))
        r = c.fetchone()
        conn.close()
        secret = r[0] if r else ""
        if not secret:
            return False, "No hay un secret 2FA pendiente. Genera uno primero."
        if self.verify_code(secret, code):
            userdb.update_user(username, totp_enabled=1)
            return True, "2FA activado correctamente."
        return False, "Código incorrecto. Inténtalo de nuevo."

    def disable_2fa(self, username: str) -> tuple[bool, str]:
        """Desactiva 2FA para el usuario."""
        userdb.update_user(username, totp_secret="", totp_enabled=0)
        return True, "2FA desactivado."

    def is_2fa_enabled(self, username: str) -> bool:
        """Comprueba si el usuario tiene 2FA activo."""
        import sqlite3
        try:
            conn = sqlite3.connect("./db/cortexa_meta.db")
            c = conn.cursor()
            c.execute("SELECT totp_enabled FROM users WHERE username=?", (username,))
            r = c.fetchone()
            conn.close()
            return bool(r and r[0])
        except Exception:
            return False

    def get_secret(self, username: str) -> str:
        import sqlite3
        try:
            conn = sqlite3.connect("./db/cortexa_meta.db")
            c = conn.cursor()
            c.execute("SELECT totp_secret FROM users WHERE username=?", (username,))
            r = c.fetchone()
            conn.close()
            return r[0] if r else ""
        except Exception:
            return ""


totp_service = TOTPService()
