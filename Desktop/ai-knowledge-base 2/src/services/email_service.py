"""Servicio de envío de emails para invitaciones y contraseñas temporales."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.userdb import userdb


class EmailService:
    def _get_smtp_config(self) -> dict:
        s = userdb.get_all_settings()
        return {
            "host": s.get("smtp_host", ""),
            "port": int(s.get("smtp_port", "587") or 587),
            "user": s.get("smtp_user", ""),
            "password": s.get("smtp_pass", ""),
            "from": s.get("smtp_from", "") or s.get("smtp_user", ""),
            "tls": s.get("smtp_tls", "true") == "true",
        }

    def is_configured(self) -> bool:
        cfg = self._get_smtp_config()
        return bool(cfg["host"] and cfg["user"])

    def send_temp_password(self, to_email: str, display_name: str, username: str,
                           temp_password: str) -> tuple[bool, str]:
        """Envía un email con la contraseña temporal al usuario."""
        if not self.is_configured():
            return False, "SMTP no configurado. Ve a Admin → Sistema → SMTP."

        try:
            product_name = userdb.get_setting("product_name", "Cortexa AI")
            cfg = self._get_smtp_config()

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Tu acceso a {product_name}"
            msg["From"] = cfg["from"]
            msg["To"] = to_email

            html = f"""
            <html><body style="font-family:Arial,sans-serif; background:#f8fafc; padding:20px;">
            <div style="max-width:480px; margin:0 auto; background:white; border-radius:12px;
                        padding:32px; box-shadow:0 2px 16px rgba(0,0,0,0.08);">
                <h2 style="color:#1e1b4b; margin-bottom:8px;">Bienvenido/a a {product_name} 👋</h2>
                <p style="color:#475569;">Hola <b>{display_name}</b>,</p>
                <p style="color:#475569;">Tu cuenta ha sido creada. Aquí están tus credenciales de acceso:</p>
                <div style="background:#f1f5f9; border-radius:8px; padding:16px; margin:20px 0;">
                    <p style="margin:4px 0; color:#334155;"><b>Usuario:</b> {username}</p>
                    <p style="margin:4px 0; color:#334155;"><b>Contraseña temporal:</b>
                        <code style="background:#e2e8f0; padding:2px 6px; border-radius:4px;">{temp_password}</code>
                    </p>
                </div>
                <p style="color:#64748b; font-size:0.9em;">
                    ⚠️ Deberás cambiar esta contraseña en tu primer inicio de sesión.
                </p>
                <hr style="border:none; border-top:1px solid #e2e8f0; margin:24px 0;">
                <p style="color:#94a3b8; font-size:0.8em;">
                    Este email fue generado automáticamente por {product_name}.
                    No respondas a este mensaje.
                </p>
            </div>
            </body></html>
            """
            msg.attach(MIMEText(html, "html"))

            if cfg["tls"]:
                server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10)

            if cfg["user"] and cfg["password"]:
                server.login(cfg["user"], cfg["password"])

            server.sendmail(cfg["from"], [to_email], msg.as_string())
            server.quit()
            return True, f"Email enviado a {to_email}"
        except Exception as e:
            return False, f"Error SMTP: {e}"


email_service = EmailService()
