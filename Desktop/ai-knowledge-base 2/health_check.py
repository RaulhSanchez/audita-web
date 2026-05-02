#!/usr/bin/env python3
"""
health_check.py — Verifica el estado del sistema Cortexa AI.

Uso:
    python health_check.py            # salida human-readable
    python health_check.py --json     # salida JSON (para monitorización)
    python health_check.py --quiet    # exit 0 si OK, exit 1 si falla

Integración con Docker/systemd:
    HEALTHCHECK CMD python health_check.py --quiet
"""
import sys
import os
import json
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def check_sqlite(path: str, label: str) -> dict:
    try:
        conn = sqlite3.connect(path, timeout=5)
        conn.execute("SELECT 1")
        conn.close()
        return {"name": label, "status": "ok", "detail": path}
    except Exception as e:
        return {"name": label, "status": "error", "detail": str(e)}


def check_ollama() -> dict:
    try:
        import httpx
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        r = httpx.get(f"{host}/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return {"name": "Ollama", "status": "ok", "detail": f"{len(models)} modelo(s) disponibles"}
        return {"name": "Ollama", "status": "error", "detail": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"name": "Ollama", "status": "error", "detail": str(e)}


def check_qdrant() -> dict:
    """POST-AUDITORÍA · Sustituye check_chroma. La app migró a Qdrant; el
    healthcheck antiguo siempre fallaba en deploys nuevos."""
    try:
        from qdrant_client import QdrantClient
        qdrant_path = ROOT / "db" / "qdrant"
        client = QdrantClient(path=str(qdrant_path))
        cols = [c.name for c in client.get_collections().collections]
        return {"name": "Qdrant", "status": "ok",
                "detail": f"{len(cols)} colección(es) en {qdrant_path}"}
    except Exception as e:
        return {"name": "Qdrant", "status": "error", "detail": str(e)}


def check_disk() -> dict:
    try:
        import shutil
        usage = shutil.disk_usage(ROOT)
        free_gb = usage.free / (1024 ** 3)
        pct_used = int(usage.used / usage.total * 100)
        status = "ok" if free_gb > 1 else "warning"
        return {"name": "Disco", "status": status, "detail": f"{free_gb:.1f} GB libres ({pct_used}% usado)"}
    except Exception as e:
        return {"name": "Disco", "status": "error", "detail": str(e)}


def run_checks():
    checks = [
        # POST-AUDITORÍA · Eliminado users.db (no existía en producción).
        # La tabla de usuarios vive en cortexa_meta.db.
        check_sqlite(str(ROOT / "db" / "cortexa_meta.db"), "SQLite metadatos"),
        check_qdrant(),
        check_ollama(),
        check_disk(),
    ]
    all_ok = all(c["status"] == "ok" for c in checks)
    return checks, all_ok


if __name__ == "__main__":
    args = sys.argv[1:]
    checks, all_ok = run_checks()

    if "--json" in args:
        print(json.dumps({
            "status": "healthy" if all_ok else "unhealthy",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checks": checks
        }, ensure_ascii=False, indent=2))
    elif "--quiet" in args:
        sys.exit(0 if all_ok else 1)
    else:
        icons = {"ok": "✅", "warning": "⚠️", "error": "❌"}
        print(f"\n{'='*45}")
        print(f"  Cortexa AI — Health Check")
        print(f"{'='*45}")
        for c in checks:
            print(f"  {icons.get(c['status'], '?')}  {c['name']:<22} {c['detail']}")
        print(f"{'='*45}")
        print(f"  Estado global: {'✅ HEALTHY' if all_ok else '❌ UNHEALTHY'}")
        print(f"{'='*45}\n")

    sys.exit(0 if all_ok else 1)
