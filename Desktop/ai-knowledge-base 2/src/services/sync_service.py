"""
src/services/sync_service.py
Motor de sincronización ETL.

Orquesta los conectores: lista ficheros, detecta cambios y
los indexa en ChromaDB a través del pipeline de ingest_service.

Persiste el estado de sincronización en userdb (último hash / fecha)
para evitar re-indexar ficheros que no han cambiado.

Uso:
    from src.services.sync_service import sync_service
    result = sync_service.run("gdrive")      # sincroniza un conector
    result = sync_service.run_all()          # sincroniza todos los activos
"""

import hashlib
import json
import tempfile
import os
from datetime import datetime, timezone
from typing import Optional

from src.connectors.base import ConnectorFile, SyncResult, all_connectors, get_connector


class SyncService:

    # ── Estado persistido ──────────────────────────────────────────────────

    def _state_key(self, connector_type: str, file_id: str) -> str:
        return f"sync_state_{connector_type}_{hashlib.md5(file_id.encode()).hexdigest()}"

    def _get_state(self, connector_type: str, file_id: str) -> Optional[dict]:
        from src.core.userdb import userdb
        raw = userdb.get_setting(self._state_key(connector_type, file_id), "")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def _save_state(self, connector_type: str, file_id: str, modified_at: datetime):
        from src.core.userdb import userdb
        userdb.set_setting(
            self._state_key(connector_type, file_id),
            json.dumps({"modified_at": modified_at.isoformat()}),
            updated_by="sync_service",
        )

    def _needs_update(self, connector_type: str, file: ConnectorFile) -> bool:
        state = self._get_state(connector_type, file.file_id)
        if not state:
            return True
        try:
            saved = datetime.fromisoformat(state["modified_at"])
            # Normalizar timezone
            if saved.tzinfo is None:
                saved = saved.replace(tzinfo=timezone.utc)
            mod = file.modified_at
            if mod.tzinfo is None:
                mod = mod.replace(tzinfo=timezone.utc)
            return mod > saved
        except Exception:
            return True

    # ── Indexar un fichero ─────────────────────────────────────────────────

    def _ingest_file(self, content: bytes, filename: str, workspace: str,
                     source_url: str) -> tuple[bool, str]:
        """
        Guarda content en un fichero temporal y lo pasa por ingest_service.
        Devuelve (ok, message).
        """
        from src.services.ingest_service import ingest_service

        suffix = os.path.splitext(filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix,
                                        prefix="cortexa_sync_") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # ingest_service.process_file(file_path, username, workspace)
            # Usamos "sync_service" como username para trazabilidad en auditoría
            ok, msg = ingest_service.process_file(
                file_path=tmp_path,
                username="sync_service",
                workspace=workspace,
            )
            return ok, msg
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # ── Sincronizar un conector ────────────────────────────────────────────

    def run(self, connector_type: str,
            on_progress=None) -> SyncResult:
        """
        Sincroniza un conector concreto.
        on_progress(msg: str) se llama con cada acción (opcional, para la UI).
        """
        started = datetime.now(timezone.utc)
        result  = SyncResult(connector=connector_type, started_at=started,
                             finished_at=started)

        connector = get_connector(connector_type)
        if connector is None:
            result.messages.append(f"Conector '{connector_type}' no registrado.")
            result.errors += 1
            result.finished_at = datetime.now(timezone.utc)
            return result

        if not connector.is_configured():
            result.messages.append(f"Conector '{connector_type}' no configurado.")
            result.errors += 1
            result.finished_at = datetime.now(timezone.utc)
            return result

        workspace = connector._setting("workspace", "general")

        # 1. Listar ficheros
        try:
            files = connector.list_files()
        except Exception as e:
            result.messages.append(f"Error listando ficheros: {e}")
            result.errors += 1
            result.finished_at = datetime.now(timezone.utc)
            return result

        msg0 = f"📋 {len(files)} ficheros encontrados en {connector.display_name}"
        result.messages.append(msg0)
        if on_progress:
            on_progress(msg0)

        # 2. Procesar cada fichero
        for file in files:
            try:
                if not self._needs_update(connector_type, file):
                    result.skipped += 1
                    continue

                if on_progress:
                    on_progress(f"⬇️ Descargando {file.name}…")

                content = connector.fetch_file(file)
                ok, msg = self._ingest_file(content, file.name, workspace, file.url)

                if ok:
                    was_known = self._get_state(connector_type, file.file_id) is not None
                    self._save_state(connector_type, file.file_id, file.modified_at)
                    if was_known:
                        result.updated += 1
                    else:
                        result.added += 1
                    if on_progress:
                        on_progress(f"✅ {file.name}")
                else:
                    result.errors += 1
                    result.messages.append(f"Error indexando {file.name}: {msg}")
                    if on_progress:
                        on_progress(f"❌ {file.name}: {msg}")

            except Exception as e:
                result.errors += 1
                result.messages.append(f"Excepción en {file.name}: {e}")
                if on_progress:
                    on_progress(f"❌ {file.name}: {e}")

        result.finished_at = datetime.now(timezone.utc)
        result.messages.append(result.summary())
        return result

    # ── Sincronizar todos los conectores activos ───────────────────────────

    def run_all(self, on_progress=None) -> list[SyncResult]:
        results = []
        for connector in all_connectors():
            if connector.is_configured():
                if on_progress:
                    on_progress(f"▶️ Sincronizando {connector.display_name}…")
                results.append(self.run(connector.connector_type, on_progress))
        return results

    # ── Limpiar estado de un conector (fuerza re-indexado completo) ─────────

    def reset_state(self, connector_type: str):
        from src.core.userdb import userdb
        connector = get_connector(connector_type)
        if not connector:
            return
        try:
            files = connector.list_files()
            for file in files:
                key = self._state_key(connector_type, file.file_id)
                userdb.set_setting(key, "", updated_by="sync_service")
        except Exception:
            pass

    # ── Última sincronización ─────────────────────────────────────────────

    def last_sync_info(self, connector_type: str) -> Optional[str]:
        from src.core.userdb import userdb
        return userdb.get_setting(f"sync_last_{connector_type}", "")

    def save_last_sync(self, connector_type: str):
        from src.core.userdb import userdb
        userdb.set_setting(
            f"sync_last_{connector_type}",
            datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
            updated_by="sync_service",
        )


sync_service = SyncService()
