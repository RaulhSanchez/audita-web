#!/usr/bin/env python3
"""
health_server.py — Servidor HTTP de health check para Cortexa AI (Feature D).

Endpoints:
    GET /health       → JSON con estado de todos los componentes
    GET /health/ready → 200 si todo OK, 503 si no
    GET /health/live  → 200 siempre (liveness probe)

Uso:
    python health_server.py              # Arranca en puerto 8502
    python health_server.py --port 9090  # Puerto personalizado

Docker:
    HEALTHCHECK CMD curl -f http://localhost:8502/health/ready || exit 1
"""
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from health_check import run_checks


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health/live":
            self._respond(200, {"status": "alive"})
        elif self.path == "/health/ready":
            checks, all_ok = run_checks()
            code = 200 if all_ok else 503
            self._respond(code, {
                "status": "ready" if all_ok else "not_ready",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        elif self.path == "/health" or self.path == "/health/":
            checks, all_ok = run_checks()
            self._respond(200, {
                "status": "healthy" if all_ok else "unhealthy",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "checks": checks,
            })
        else:
            self._respond(404, {"error": "Not found"})

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8"))

    def log_message(self, format, *args):
        # Silenciar logs excepto errores
        if args and "200" not in str(args[0]):
            super().log_message(format, *args)


if __name__ == "__main__":
    port = 8502
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i + 2 < len(sys.argv):
            port = int(sys.argv[i + 2])

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🏥 Health server listening on http://0.0.0.0:{port}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Health server stopped")
        server.server_close()
