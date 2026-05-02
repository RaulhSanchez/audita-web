# Runbook de Operaciones · Cortexa AI

Este documento detalla cómo poner en marcha y mantener Cortexa AI en producción.

## 1. Despliegue con Docker (Recomendado)

### Requisitos:
- Docker y Docker Compose instalados.
- Ollama corriendo en el host (o accesible via red).

### Pasos:
1.  **Configurar variables:** Crea un archivo `.env` (opcional) o usa las por defecto.
2.  **Lanzar:**
    ```bash
    docker-compose up -d --build
    ```
3.  **Acceder:** La app estará disponible en `http://localhost:8501`.

## 2. Gestión de Almacenamiento
Los datos se guardan en volúmenes locales dentro de la carpeta del proyecto:
- `./db`: Base de datos de usuarios y logs.
- `./data`: Documentos originales indexados.
- `./logs`: Logs del sistema en formato JSON.

## 3. Actualizaciones
Para actualizar a una nueva versión:
```bash
git pull
docker-compose up -d --build
```

## 4. Troubleshooting
- **Logs:** `docker logs -f cortexa-ai`
- **Reinicio:** `docker-compose restart cortexa`
