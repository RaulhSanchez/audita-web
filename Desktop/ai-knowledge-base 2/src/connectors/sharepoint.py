"""
src/connectors/sharepoint.py
Conector SharePoint / OneDrive — Microsoft Graph API con App Registration.

Configuración (prefijo connector_sharepoint_):
  tenant_id          — Azure Tenant ID
  client_id          — App Registration Client ID
  client_secret      — Client Secret de la app
  site_url           — URL del sitio SharePoint, p.ej. https://empresa.sharepoint.com/sites/MiSitio
                       (vacío = OneDrive del usuario de servicio)
  drive_path         — Ruta dentro del drive, p.ej. "Documentos/Contratos"  (vacío = raíz)
  workspace          — workspace de Cortexa
  include_subfolders — "true" / "false"
  file_extensions    — extensiones separadas por coma

Dependencias: solo urllib (stdlib) → sin pip install adicional.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import List, Optional

from src.connectors.base import BaseConnector, ConnectorFile, register

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@register
class SharePointConnector(BaseConnector):
    connector_type    = "sharepoint"
    display_name      = "SharePoint / OneDrive"
    supported_extensions = ["pdf", "docx", "doc", "txt", "md", "xlsx", "xls", "csv", "pptx", "ppt"]

    # ── Token ──────────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return all([
            self._setting("tenant_id"),
            self._setting("client_id"),
            self._setting("client_secret"),
        ])

    def _get_token(self) -> str:
        tenant = self._setting("tenant_id")
        url    = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data   = urllib.parse.urlencode({
            "grant_type":    "client_credentials",
            "client_id":     self._setting("client_id"),
            "client_secret": self._setting("client_secret"),
            "scope":         "https://graph.microsoft.com/.default",
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())["access_token"]

    def _graph_get(self, path: str, token: str) -> dict:
        req = urllib.request.Request(f"{GRAPH_BASE}{path}")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def _graph_bytes(self, url: str, token: str) -> bytes:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()

    # ── Resolver drive root ────────────────────────────────────────────────

    def _drive_root(self, token: str) -> str:
        """Devuelve el path base del drive en Graph API."""
        site_url = self._setting("site_url", "").rstrip("/")
        if site_url:
            # SharePoint site drive
            encoded = urllib.parse.quote(site_url, safe="")
            info    = self._graph_get(f"/sites/{encoded}?$select=id", token)
            site_id = info["id"]
            return f"/sites/{site_id}/drive"
        else:
            # OneDrive del tenant (primer drive del app)
            return "/me/drive"

    # ── Test ───────────────────────────────────────────────────────────────

    def test_connection(self) -> tuple[bool, str]:
        try:
            token = self._get_token()
            root  = self._drive_root(token)
            self._graph_get(f"{root}/root?$select=id,name", token)
            return True, "✅ Conexión con SharePoint/OneDrive establecida."
        except Exception as e:
            return False, f"❌ {e}"

    # ── Listar ficheros ────────────────────────────────────────────────────

    def list_files(self) -> List[ConnectorFile]:
        token   = self._get_token()
        root    = self._drive_root(token)
        path    = self._setting("drive_path", "").strip("/")
        recurse = self._setting("include_subfolders", "true") == "true"
        exts    = [e.strip().lower() for e in self._setting("file_extensions", "pdf,docx,txt,md").split(",") if e.strip()]

        if path:
            item_path = f"{root}/root:/{urllib.parse.quote(path)}"
        else:
            item_path = f"{root}/root"

        files: List[ConnectorFile] = []
        self._collect_items(token, f"{item_path}/children", exts, recurse, files)
        return files

    def _collect_items(self, token: str, children_url: str, exts: list,
                       recurse: bool, result: List[ConnectorFile], depth: int = 0):
        if depth > 10:
            return
        # children_url puede ser un path relativo o una @odata.nextLink absoluta
        url = children_url if children_url.startswith("http") else f"{GRAPH_BASE}{children_url}"

        while url:
            data = json.loads(self._graph_bytes(url, token))
            for item in data.get("value", []):
                if "folder" in item:
                    if recurse:
                        child_url = f"{GRAPH_BASE}/drives/{item.get('parentReference',{}).get('driveId','me/drive')}/items/{item['id']}/children"
                        self._collect_items(token, child_url, exts, recurse, result, depth + 1)
                    continue

                name = item.get("name", "")
                ext  = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                if exts and ext not in exts:
                    continue

                try:
                    mod = datetime.fromisoformat(
                        item.get("lastModifiedDateTime", "").replace("Z", "+00:00")
                    )
                except Exception:
                    mod = datetime.utcnow()

                result.append(ConnectorFile(
                    file_id     = item["id"],
                    name        = name,
                    modified_at = mod,
                    size_bytes  = item.get("size", 0),
                    url         = item.get("webUrl", ""),
                    extra       = {
                        "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                        "drive_id":     item.get("parentReference", {}).get("driveId", ""),
                    },
                ))
            url = data.get("@odata.nextLink")

    # ── Descargar fichero ─────────────────────────────────────────────────

    def fetch_file(self, file: ConnectorFile) -> bytes:
        token        = self._get_token()
        download_url = file.extra.get("download_url", "")
        if download_url:
            return self._graph_bytes(download_url, token)
        # Fallback via Graph
        drive_id = file.extra.get("drive_id", "")
        if drive_id:
            url = f"{GRAPH_BASE}/drives/{drive_id}/items/{file.file_id}/content"
        else:
            url = f"{GRAPH_BASE}/me/drive/items/{file.file_id}/content"
        return self._graph_bytes(url, token)
