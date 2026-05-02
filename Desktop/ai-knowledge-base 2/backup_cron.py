#!/usr/bin/env python3
"""
backup_cron.py — Script de backup automático para Cortexa AI.

Uso:
    python backup_cron.py                 # Ejecuta backup una vez
    python backup_cron.py --daemon        # Ejecuta en loop según configuración

Integración con crontab:
    0 2 * * * cd /app && python backup_cron.py >> logs/backup.log 2>&1

Integración con Docker (daemon mode):
    El Dockerfile arranca este script en background con --daemon.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def run_backup():
    from src.services.backup_service import backup_service
    from src.services.audit_service import audit_service

    ok, result = backup_service.create_backup(triggered_by="cron")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    if ok:
        print(f"[{ts}] ✅ Backup creado: {result}")
        try:
            audit_service.log_event("system", "system", "BACKUP_AUTO", result)
        except Exception:
            pass
    else:
        print(f"[{ts}] ❌ Error en backup: {result}")
    return ok


def get_interval_hours():
    """Lee el intervalo de backup desde settings (default 24h)."""
    try:
        from src.core.userdb import userdb
        return float(userdb.get_setting("backup_interval_hours", "24"))
    except Exception:
        return 24.0


def is_enabled():
    """Comprueba si el backup automático está activado."""
    try:
        from src.core.userdb import userdb
        return userdb.get_setting("backup_enabled", "true") == "true"
    except Exception:
        return True


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        print(f"🔄 Backup daemon iniciado")
        while True:
            if is_enabled():
                run_backup()
            else:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⏸️ Backup desactivado")
            hours = get_interval_hours()
            print(f"   Próximo backup en {hours}h")
            time.sleep(hours * 3600)
    else:
        ok = run_backup()
        sys.exit(0 if ok else 1)
