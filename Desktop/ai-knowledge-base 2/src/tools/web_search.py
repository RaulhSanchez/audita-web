"""
src/tools/web_search.py
Búsqueda web usando DuckDuckGo (sin API key, solo urllib).
Solo activa si el admin habilita "web_search_enabled" en settings.
"""
import json
import urllib.request
import urllib.parse
from langchain_core.tools import tool


def _is_enabled() -> bool:
    try:
        from src.core.userdb import userdb
        return userdb.get_setting("web_search_enabled", "false") == "true"
    except Exception:
        return False


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Busca información actualizada en internet usando DuckDuckGo.
    Úsala SOLO cuando la información solicitada NO esté en la base de
    conocimiento corporativa o cuando el usuario pida explícitamente
    información externa o actualizada.

    Esta herramienta requiere que el administrador haya habilitado
    la búsqueda web en la configuración del sistema.

    Args:
        query: Términos de búsqueda.
        max_results: Número máximo de resultados (1-10, default 5).

    Returns:
        Resultados de búsqueda con título, URL y extracto.
    """
    if not _is_enabled():
        return (
            "La búsqueda web está desactivada. "
            "Un administrador puede activarla en Sistema → Búsqueda web."
        )

    try:
        params = urllib.parse.urlencode({
            "q":      query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        })
        url = f"https://api.duckduckgo.com/?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "CortexaAI/1.0")

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        results = []

        # Abstract (respuesta directa si existe)
        if data.get("AbstractText"):
            results.append(
                f"📌 Respuesta directa ({data.get('AbstractSource', 'Wikipedia')}):\n"
                f"{data['AbstractText']}\n"
                f"🔗 {data.get('AbstractURL', '')}"
            )

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                url_t = topic.get("FirstURL", "")
                results.append(f"• {topic['Text']}\n  🔗 {url_t}")

        if not results:
            return f"No se encontraron resultados para: '{query}'"

        return f"Resultados web para '{query}':\n\n" + "\n\n".join(results)

    except Exception as e:
        return f"Error en búsqueda web: {e}"
