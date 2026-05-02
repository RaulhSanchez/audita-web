"""
api_server.py
Arranca el servidor FastAPI de Cortexa AI (reemplaza el servidor HTTP básico anterior).

Uso:
    python api_server.py                    # 0.0.0.0:8000
    PORT=9000 python api_server.py          # puerto personalizado
    python api_server.py --reload           # hot-reload para desarrollo

Documentación interactiva (Swagger):
    http://localhost:8000/api/docs

Autenticación:
    Bearer <api_key>   generada en Admin → Sistema → API Keys
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    port   = int(os.getenv("PORT", 8000))
    host   = os.getenv("HOST", "0.0.0.0")
    reload = "--reload" in sys.argv

    print(f"🚀 Cortexa AI API → http://{host}:{port}")
    print(f"📖 Swagger UI     → http://localhost:{port}/api/docs")

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=1,
        log_level="info",
    )
