# Manual de Instalación · Cortexa AI

Este documento describe el despliegue de Cortexa AI en un servidor on-premise o
máquina local. Siguelo en orden — cada paso aporta una capa de seguridad.

---

## 1. Requisitos

- **Sistema operativo:** Linux (recomendado), Windows 10/11 con WSL2 o macOS.
- **Hardware:** 16 GB de RAM (mínimo 8), CPU 4 núcleos o más, 30 GB de disco.
- **Software:**
  - [Docker Engine](https://docs.docker.com/engine/install/) ≥ 24.x con Compose v2.
  - `openssl` y `python3` para generar claves iniciales.

---

## 2. Configuración inicial (obligatoria)

Antes del primer arranque debes generar y configurar los secretos. La aplicación
**no** funcionará con valores por defecto.

```bash
# 1) Copia la plantilla de variables de entorno
cp .env.example .env

# 2) Genera valores aleatorios para los campos marcados [GENERAR]
echo "COOKIE_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env
echo "SETTINGS_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" >> .env
echo "ADMIN_INITIAL_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(20))')" >> .env

# 3) Edita .env y revisa CORS_ORIGINS, SMTP_*, OLLAMA_*
nano .env
```

> Guarda la contraseña que ha quedado en `ADMIN_INITIAL_PASSWORD`: la usarás en el
> primer login. La aplicación te obligará a cambiarla en ese mismo momento.

---

## 3. Despliegue

```bash
docker compose up -d
docker compose logs -f app   # observa el primer arranque
```

El primer arranque tarda 5–10 minutos: se construye la imagen, se inicializa la
base de datos y, si tienes el servicio Ollama habilitado en `docker-compose.yml`,
se descarga el modelo. Pasados unos minutos, abre `https://cortexa.local` (ver
sección 6 si el DNS no resuelve).

---

## 4. Credenciales

No hay credenciales predefinidas. El usuario `admin` se crea en el primer
arranque a partir de `ADMIN_INITIAL_PASSWORD`. Si esa variable está vacía, la
app genera una temporal y la imprime en `docker compose logs app` — búscala con
`grep "Contraseña temporal admin"`.

En el primer login Cortexa AI exige cambiar la contraseña. Crea el resto de
usuarios desde **Admin → Usuarios**.

---

## 5. Gestión de archivos y auditoría

- **Ingesta:** sube PDFs y DOCX desde **Biblioteca**. El sistema los indexa en
  segundo plano.
- **Auditoría:** todas las preguntas y acciones quedan en `./logs/audit.log`.
  Desde **Admin → Auditoría** puedes descargar CSV o JSON SIEM.
- **Persistencia:** los volúmenes Docker (`./db`, `./data`, `./logs`,
  `./backups`) sobreviven a reinicios. Cifra el disco si manejas datos sensibles.
- **Backups:** programa backups automáticos desde **Admin → Sistema → Backups**.
  Los ZIP se cifran con AES-GCM usando `SETTINGS_ENCRYPTION_KEY`.

---

## 6. Configuración de red (DNS local)

Para acceder desde otros ordenadores con el nombre `cortexa.local`:

- **Manual (pruebas):** añade en cada equipo `IP_DEL_SERVIDOR cortexa.local` en
  `/etc/hosts` (Linux/macOS) o `C:\Windows\System32\drivers\etc\hosts`.
- **Corporativa:** registro DNS tipo A o CNAME apuntando `cortexa.local` a la IP
  del servidor.

Para producción real, sustituye el certificado autofirmado de
`nginx/certs/` por uno emitido por una CA reconocida (Let's Encrypt o la CA
corporativa interna).

---

## 7. Soporte

Para soporte técnico contacta con **soporte@cortexa.ai**.
