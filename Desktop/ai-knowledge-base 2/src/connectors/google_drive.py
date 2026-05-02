"""
src/connectors/google_drive.py
Conector Google Drive — usa la API REST v3 con OAuth2 Service Account.

Configuración (guardada en userdb con prefijo connector_gdrive_):
  service_account_json   — JSON completo de la Service Account (pegado como texto)
  folder_id              — ID de la carpeta raíz a sincronizar (vacío = My Drive)
  workspace              — workspace de Cortexa donde se indexan los docs
  include_subfolders     — "true" / "false"
  file_extensions        — extensiones a sincronizar, separadas por coma
                           p.ej. "pdf,docx,txt,md"

Dependencias (ya en requirements.txt o stdlib):
  google-auth            → pip install google-auth
  google-api-python-client → pip install google-api-python-client
  (se importan de forma lazy para no romper el arranque si no están)
"""

import json
import io
from datetime import datetime
from typing import List

from src.connectors.base import BaseConnector, ConnectorFile, register

SUPPORTED_MIME_EXPORT = {
    # Google Docs → PDF
    "application/vnd.google-apps.document":     ("application/pdf", ".pdf"),
    # Google Sheets → xlsx
    "application/vnd.google-apps.spreadsheet":  (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    # Google Slides → PDF
    "application/vnd.google-apps.presentation": ("application/pdf", ".pdf"),
}


@register
class GoogleDriveConnector(BaseConnector):
    connector_type    = "gdrive"
    display_name      = "Google Drive"
    supported_extensions = ["pdf", "docx", "doc", "txt", "md", "xlsx", "xls", "csv", "pptx"]

    # ── Configuración ──────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return bool(self._setting("service_account_json"))

    def _get_service(self):
        """Crea el cliente de Drive usando la Service Account."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "Faltan dependencias de Google Drive. "
                "Ejecuta: pip install google-auth google-api-python-client"
            )
        sa_json = self._setting("service_account_json")
        if not sa_json:
            raise ValueError("Falta la Service Account JSON.")
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    # ── Test ───────────────────────────────────────────────────────────────

    def test_connection(self) -> tuple[bool, str]:
        try:
            svc = self._get_service()
            svc.about().get(fields="user").execute()
            return True, "✅ Conexión con Google Drive establecida."
        except Exception as e:
            return False, f"❌ {e}"

    # ── Listar ficheros ────────────────────────────────────────────────────

    def list_files(self) -> List[ConnectorFile]:
        svc    = self._get_service()
        folder = self._setting("folder_id", "")
        exts   = [e.strip().lower() for e in self._setting("file_extensions", "pdf,docx,txt,md").split(",") if e.strip()]
        recurse = self._setting("include_subfolders", "true") == "true"

        files: List[ConnectorFile] = []
        self._collect_files(svc, folder or "root", exts, recurse, files)
        return files

    def _collect_files(self, svc, folder_id: str, exts: list, recurse: bool,
                       result: List[ConnectorFile], depth: int = 0):
        if depth > 10:
            return
        page_token = None
        q_parts = [f"'{folder_id}' in parents", "trashed = false"]
        q = " and ".join(q_parts)

        while True:
            resp = svc.files().list(
                q=q,
                fields="nextPageToken, files(id,name,mimeType,modifiedTime,size,webViewLink)",
                pageSize=200,
                pageToken=page_token or "",
            ).execute()

            for f in resp.get("files", []):
                mime = f.get("mimeType", "")
                name = f.get("name", "")

                if mime == "application/vnd.google-apps.folder":
                    if recurse:
                        self._collect_files(svc, f["id"], exts, recurse, result, depth + 1)
                    continue

                # Google Workspace docs (exportar)
                if mime in SUPPORTED_MIME_EXPORT:
                    _, export_ext = SUPPORTED_MIME_EXPORT[mime]
                    effective_name = name + export_ext
                else:
                    effective_name = name

                file_ext = effective_name.rsplit(".", 1)[-1].lower() if "." in effective_name else ""
                if exts and file_ext not in exts:
                    continue

                try:
                    mod = datetime.fromisoformat(f.get("modifiedTime", "").replace("Z", "+00:00"))
                except Exception:
                    mod = datetime.utcnow()

                result.append(ConnectorFile(
                    file_id     = f["id"],
                    name        = effective_name,
                    modified_at = mod,
                    size_bytes  = int(f.get("size", 0) or 0),
                    mime_type   = mime,
                    url         = f.get("webViewLink", ""),
                    extra       = {"original_name": name, "gdrive_mime": mime},
                ))

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    # ── Descargar fichero ─────────────────────────────────────────────────

    def fetch_file(self, file: ConnectorFile) -> bytes:
        svc  = self._get_service()
        mime = file.extra.get("gdrive_mime", "")

        if mime in SUPPORTED_MIME_EXPORT:
            export_mime, _ = SUPPORTED_MIME_EXPORT[mime]
            req = svc.files().export_media(fileId=file.file_id, mimeType=export_mime)
        else:
            req = svc.files().get_media(fileId=file.file_id)

        from googleapiclient.http import MediaIoBaseDownload
        buf = io.BytesIO()
        dl  = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()
