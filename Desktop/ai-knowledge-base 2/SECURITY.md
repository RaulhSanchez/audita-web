# Política de seguridad · Cortexa AI

Cortexa AI es un producto que procesa información sensible de empresa. La
seguridad es una promesa central: si se rompe, se rompe todo. Esta política
documenta cómo reportar problemas, qué cubrimos y nuestros compromisos.

## Alcance

Esta política cubre:

- El código fuente de Cortexa AI (este repositorio).
- Las imágenes Docker oficiales publicadas para clientes.
- La configuración de despliegue recomendada (Docker Compose + Nginx).

NO cubre:

- Despliegues personalizados modificados por el cliente.
- Integraciones de terceros (Ollama, Qdrant, Google Drive API, SharePoint API,
  Confluence API). Reporta esos a sus respectivos mantenedores.

## Reporte de vulnerabilidades

Si encuentras una vulnerabilidad **NO la publiques** en GitHub Issues, foros o
redes sociales. Envíanos el detalle a **security@cortexa.ai** (PGP disponible
bajo petición). Incluye:

- Descripción del problema.
- Pasos para reproducirlo (PoC mínimo).
- Versión de Cortexa AI afectada.
- Tu nombre o alias (si quieres aparecer en agradecimientos).

Compromisos:

- Acuse de recibo en **48 horas laborables**.
- Evaluación inicial en **5 días laborables**.
- Parche o mitigación en **30 días naturales** para CVSS ≥ 7.0; **90 días**
  para el resto.
- Coordinated disclosure: te avisamos antes de hacer público el parche.

No iniciaremos acciones legales contra investigadores que actúen de buena fe
y respeten esta política.

## Áreas críticas

Las siguientes áreas reciben revisión prioritaria por el impacto de un fallo:

- Autenticación, autorización, gestión de sesiones (SSO, 2FA, API keys).
- Aislamiento entre tenants (despliegue actual: un servidor por cliente).
- Protección frente a path traversal, SQL injection, command injection, SSRF
  en conectores.
- Cifrado de secretos en reposo (SMTP, SSO, conectores) y de backups.
- Cabeceras de seguridad HTTP, TLS y CORS.

## Buenas prácticas para el cliente

Si despliegas Cortexa AI:

1. **Genera todos los secretos** del `.env` con valores aleatorios. No reutilices
   ejemplos.
2. **Sustituye el certificado autofirmado** de `nginx/certs/` por uno de una CA
   reconocida (Let's Encrypt o tu CA corporativa) antes de exponer la app.
3. **Limita CORS_ORIGINS** a los dominios reales que vayan a consumir la API.
4. **Activa 2FA** para todas las cuentas con rol admin.
5. **Configura SMTP** para que el sistema pueda enviar resets de contraseña por
   email.
6. **Cifra el disco** del host donde residan los volúmenes (`db`, `data`,
   `logs`, `backups`).
7. **Revisa el log de auditoría** periódicamente y exporta a tu SIEM.
8. **Aplica updates** de imagen Docker dentro de los 30 días tras un release de
   seguridad.

## Versiones soportadas

Solo se aplican parches de seguridad a la versión actual y la inmediatamente
anterior. Versiones anteriores quedan sin soporte y se recomienda actualizar.

## Reconocimientos

Agradecemos a los investigadores que reporten vulnerabilidades responsablemente.
La lista pública de agradecimientos está en `SECURITY-HALL-OF-FAME.md` (con
permiso del investigador).
