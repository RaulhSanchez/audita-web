"""
src/connectors/confluence.py
Conector Confluence Cloud + Server.

Configuración (prefijo connector_confluence_):
  base_url       — URL base, p.ej. https://miempresa.atlassian.net/wiki
                   o https://confluence.internal.com
  email          — Email del usuario (Cloud) o usuario (Server)
  api_token      — API Token (Cloud) o contraseña (Server)
  space_key      — Clave del espacio a sincronizar, p.ej. "DOCS"
                   (vacío = todos los espacios accesibles)
  workspace      — workspace de Cortexa
  include_children — "true" / "false" — incluir páginas hijas
  page_limit     — número máximo de páginas a sincronizar (default 500)

Las páginas se exportan como HTML y se indexan como texto plano.
No requiere dependencias extra (usa urllib).
"""

import base64
import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import List

from src.connectors.base import BaseConnector, ConnectorFile, register


@register
class ConfluenceConnector(BaseConnector):
    connector_type    = "confluence"
    display_name      = "Confluence"
    # Las páginas no tienen extensión — las tratamos como .html internamente
    supported_extensions = ["html", "pdf"]

    # ── Auth ───────────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return all([
            self._setting("base_url"),
            self._setting("email"),
            self._setting("api_token"),
        ])

    def _auth_header(self) -> str:
        creds = f"{self._setting('email')}:{self._setting('api_token')}"
        return "Basic " + base64.b64encode(creds.encode()).decode()

    def _get(self, path: str) -> dict:
        base = self._setting("base_url").rstrip("/")
        url  = base + path
        req  = urllib.request.Request(url)
        req.add_header("Authorization", self._auth_header())
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())

    def _get_bytes(self, path: str) -> bytes:
        base = self._setting("base_url").rstrip("/")
        url  = base + path
        req  = urllib.request.Request(url)
        req.add_header("Authorization", self._auth_header())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()

    # ── Test ───────────────────────────────────────────────────────────────

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._get("/rest/api/space?limit=1")
            return True, "✅ Conexión con Confluence establecida."
        except Exception as e:
            return False, f"❌ {e}"

    # ── Listar páginas ────────────────────────────────────────────────────

    def list_files(self) -> List[ConnectorFile]:
        space_key = self._setting("space_key", "")
        limit     = int(self._setting("page_limit", "500"))
        files: List[ConnectorFile] = []
        start = 0

        while len(files) < limit:
            params = urllib.parse.urlencode({
                "limit": min(50, limit - len(files)),
                "start": start,
                "expand": "version,space",
                **({"spaceKey": space_key} if space_key else {}),
            })
            data = self._get(f"/rest/api/content?type=page&{params}")
            results = data.get("results", [])
            if not results:
                break

            for page in results:
                try:
                    mod = datetime.fromisoformat(
                        page.get("version", {}).get("when", "").replace("Z", "+00:00")
                    )
                except Exception:
                    mod = datetime.utcnow()

                sp  = page.get("space", {})
                files.append(ConnectorFile(
                    file_id     = page["id"],
                    name        = f"{page['title']}.html",
                    modified_at = mod,
                    url         = self._setting("base_url").rstrip("/") + page.get("_links", {}).get("webui", ""),
                    extra       = {
                        "space_key":  sp.get("key", ""),
                        "space_name": sp.get("name", ""),
                        "title":      page["title"],
                    },
                ))

            size  = data.get("size", 0)
            start += size
            if size < 50:
                break

        return files

    # ── Descargar página como HTML ────────────────────────────────────────

    def fetch_file(self, file: ConnectorFile) -> bytes:
        page_id = file.file_id
        # Exportar como HTML con storage format (más limpio que view format)
        data = self._get(f"/rest/api/content/{page_id}?expand=body.export_view,version,space")
        html_body = data.get("body", {}).get("export_view", {}).get("value", "")
        title     = data.get("title", file.name)
        space     = data.get("space", {}).get("name", "")

        # Envolvemos en HTML básico para que el parser de ingest lo procese bien
        html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
{f'<p><em>Espacio: {space}</em></p>' if space else ''}
{html_body}
</body>
</html>"""
        return html.encode("utf-8")
