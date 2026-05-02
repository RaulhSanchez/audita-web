"""
src/services/scheduler_service.py
Sync programado para conectores ETL usando APScheduler.

Configuración por conector (guardada en settings):
  sync_schedule_{type}_enabled  = "true" / "false"
  sync_schedule_{type}_interval = horas entre ejecuciones (int, default 24)

El scheduler se inicia una sola vez por proceso (singleton thread-safe).
"""
from __future__ import annotations
import threading
import logging

log = logging.getLogger(__name__)

_scheduler = None
_scheduler_lock = threading.Lock()
_started = False


def _run_connector_sync(connector_type: str) -> None:
    """Ejecuta la sincronización de un conector en background."""
    try:
        import src.connectors.google_drive   # noqa: F401
        import src.connectors.sharepoint     # noqa: F401
        import src.connectors.confluence     # noqa: F401
        from src.connectors.base import all_connectors
        from src.services.sync_service import sync_service

        connectors = {c.connector_type: c for c in all_connectors()}
        conn = connectors.get(connector_type)
        if not conn:
            log.warning(f"[scheduler] Conector '{connector_type}' no encontrado.")
            return
        if not conn.is_configured():
            log.info(f"[scheduler] Conector '{connector_type}' no configurado, omitiendo.")
            return

        log.info(f"[scheduler] Iniciando sync automático: {connector_type}")
        result = sync_service.run(connector_type)
        sync_service.save_last_sync(connector_type)
        log.info(
            f"[scheduler] Sync '{connector_type}' completado — "
            f"+{result.added} nuevos, {result.updated} actualizados, {result.errors} errores"
        )
        try:
            from src.services.audit_service import audit_service
            audit_service.log_event(
                "scheduler", "system", "AUTO_SYNC",
                f"{connector_type}: +{result.added} upd:{result.updated} err:{result.errors}"
            )
        except Exception:
            pass
    except Exception as e:
        log.error(f"[scheduler] Error en sync '{connector_type}': {e}")


def _load_schedule_config() -> list[dict]:
    """Lee la configuración de schedules desde settings."""
    connector_types = ["gdrive", "sharepoint", "confluence"]
    configs = []
    try:
        from src.core.userdb import userdb
        for ct in connector_types:
            enabled  = userdb.get_setting(f"sync_schedule_{ct}_enabled", "false") == "true"
            interval = int(userdb.get_setting(f"sync_schedule_{ct}_interval", "24"))
            configs.append({"type": ct, "enabled": enabled, "interval_hours": max(1, interval)})
    except Exception as e:
        log.warning(f"[scheduler] No se pudo leer config: {e}")
    return configs


def start_scheduler() -> None:
    """Inicia el scheduler si no está ya corriendo. Seguro llamar múltiples veces."""
    global _scheduler, _started
    with _scheduler_lock:
        if _started:
            return
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger

            _scheduler = BackgroundScheduler(daemon=True)
            configs = _load_schedule_config()

            for cfg in configs:
                if cfg["enabled"]:
                    _scheduler.add_job(
                        _run_connector_sync,
                        trigger=IntervalTrigger(hours=cfg["interval_hours"]),
                        args=[cfg["type"]],
                        id=f"sync_{cfg['type']}",
                        replace_existing=True,
                        misfire_grace_time=300,
                    )
                    log.info(
                        f"[scheduler] Job registrado: {cfg['type']} cada {cfg['interval_hours']}h"
                    )

            _scheduler.start()
            _started = True
            log.info("[scheduler] APScheduler iniciado.")
        except Exception as e:
            log.error(f"[scheduler] No se pudo iniciar: {e}")


def reload_schedule() -> None:
    """Recarga la configuración de schedules sin reiniciar el scheduler."""
    global _scheduler
    if not _scheduler or not _started:
        start_scheduler()
        return
    try:
        from apscheduler.triggers.interval import IntervalTrigger
        configs = _load_schedule_config()
        connector_types = ["gdrive", "sharepoint", "confluence"]

        # Quitar todos los jobs de sync
        for ct in connector_types:
            try:
                _scheduler.remove_job(f"sync_{ct}")
            except Exception:
                pass

        # Re-añadir los que estén habilitados
        for cfg in configs:
            if cfg["enabled"]:
                _scheduler.add_job(
                    _run_connector_sync,
                    trigger=IntervalTrigger(hours=cfg["interval_hours"]),
                    args=[cfg["type"]],
                    id=f"sync_{cfg['type']}",
                    replace_existing=True,
                    misfire_grace_time=300,
                )
        log.info("[scheduler] Configuración de schedules recargada.")
    except Exception as e:
        log.error(f"[scheduler] Error recargando schedules: {e}")


def get_status() -> list[dict]:
    """Devuelve el estado actual de los jobs de sync."""
    if not _scheduler or not _started:
        return []
    status = []
    for job in _scheduler.get_jobs():
        if job.id.startswith("sync_"):
            status.append({
                "connector": job.id.replace("sync_", ""),
                "next_run": str(job.next_run_time)[:19] if job.next_run_time else "—",
            })
    return status


scheduler_service = type("SchedulerService", (), {
    "start": staticmethod(start_scheduler),
    "reload": staticmethod(reload_schedule),
    "status": staticmethod(get_status),
})()
