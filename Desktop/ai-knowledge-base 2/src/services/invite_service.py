"""Servicio de invitaciones por email con token."""
import uuid
from datetime import datetime, timedelta
from src.core.database import db_manager
from src.core.userdb import userdb
from src.services.email_service import email_service
from src.services.user_service import user_service


class InviteService:
    def create_invitation(self, email, name, role, workspaces, created_by,
                          expiry_days=7) -> tuple[bool, str, str]:
        """
        Crea una invitación con token.
        Returns (success, message, token).
        """
        if not email or not email.strip():
            return False, "El email es obligatorio.", ""

        token = uuid.uuid4().hex
        expires_at = (datetime.utcnow() + timedelta(days=expiry_days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        try:
            db_manager.add_invitation(
                token=token,
                email=email.strip(),
                name=name or "",
                role=role or "viewer",
                workspaces=workspaces or ["general"],
                created_by=created_by,
                expires_at=expires_at,
            )
            return True, f"Invitación creada para {email}.", token
        except Exception as e:
            return False, f"Error al crear invitación: {e}", ""

    def send_invitation_email(self, token, email, name, app_url="") -> tuple[bool, str]:
        """Envía el email de invitación con el link."""
        if not email_service.is_configured():
            return False, "SMTP no configurado. Ve a Admin → Sistema → SMTP."

        try:
            product_name = userdb.get_setting("product_name", "Cortexa AI")
            invite_link = f"{app_url}?invite={token}" if app_url else f"?invite={token}"
            cfg = email_service._get_smtp_config()

            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import smtplib

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Invitación a {product_name}"
            msg["From"] = cfg["from"]
            msg["To"] = email

            html = f"""
            <html><body style="font-family:Arial,sans-serif; background:#f8fafc; padding:20px;">
            <div style="max-width:480px; margin:0 auto; background:white; border-radius:12px;
                        padding:32px; box-shadow:0 2px 16px rgba(0,0,0,0.08);">
                <h2 style="color:#1e1b4b; margin-bottom:8px;">Te han invitado a {product_name} 🎉</h2>
                <p style="color:#475569;">Hola <b>{name or 'usuario'}</b>,</p>
                <p style="color:#475569;">Has sido invitado/a a unirte. Haz clic en el enlace para crear tu cuenta:</p>
                <div style="text-align:center; margin:24px 0;">
                    <a href="{invite_link}" style="display:inline-block; padding:12px 32px;
                       background:linear-gradient(135deg,#6366f1,#8b5cf6); color:white;
                       text-decoration:none; border-radius:8px; font-weight:600;
                       box-shadow:0 4px 12px rgba(99,102,241,0.3);">
                        Aceptar invitación
                    </a>
                </div>
                <div style="background:#f1f5f9; border-radius:8px; padding:12px; margin:16px 0;">
                    <p style="margin:4px 0; color:#64748b; font-size:0.85em;">
                        Si el botón no funciona, copia y pega este enlace:<br>
                        <code style="word-break:break-all; font-size:0.8em;">{invite_link}</code>
                    </p>
                </div>
                <p style="color:#94a3b8; font-size:0.8em;">
                    ⏰ Esta invitación expira en 7 días.
                </p>
                <hr style="border:none; border-top:1px solid #e2e8f0; margin:24px 0;">
                <p style="color:#94a3b8; font-size:0.8em;">
                    Este email fue generado automáticamente por {product_name}.
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

            server.sendmail(cfg["from"], [email], msg.as_string())
            server.quit()
            return True, f"Invitación enviada a {email}"
        except Exception as e:
            return False, f"Error SMTP: {e}"

    def accept_invitation(self, token, username, password) -> tuple[bool, str]:
        """Acepta una invitación: valida el token y crea el usuario."""
        invite = db_manager.get_invitation(token)
        if not invite:
            return False, "Invitación no encontrada."
        if invite["used"]:
            return False, "Esta invitación ya fue utilizada."

        # Check expiry
        try:
            expires = datetime.strptime(invite["expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() > expires:
                return False, "Esta invitación ha expirado."
        except Exception:
            pass

        if not username or not password or len(password) < 8:
            return False, "Usuario y contraseña (mín. 8 caracteres) son obligatorios."

        # Create user
        ok, msg = user_service.add_user(
            username=username,
            name=invite["name"],
            email=invite["email"],
            password=password,
            role=invite["role"],
            workspaces=invite["workspaces"],
        )
        if not ok:
            return False, msg

        db_manager.mark_invitation_used(token)
        return True, f"Cuenta creada correctamente. Ya puedes iniciar sesión."


invite_service = InviteService()
