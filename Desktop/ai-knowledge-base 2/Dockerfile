# Usa una imagen de Python ligera y estable
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y permite ver logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema necesarias (para compilación de algunos paquetes y PDF/DOCX)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copia los requerimientos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt
# Instalamos pytest explícitamente para el entorno de test
RUN pip install --no-cache-dir pytest

# Copia el resto de la aplicación
COPY . .

# Crea los directorios necesarios si no existen y asigna permisos
RUN mkdir -p db data assets logs backups

# Expone el puerto por defecto de Streamlit
EXPOSE 8501

# Salud del contenedor (opcional pero recomendado)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando de arranque
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
