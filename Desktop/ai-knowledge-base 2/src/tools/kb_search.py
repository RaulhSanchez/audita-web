"""
src/tools/kb_search.py
Herramienta de búsqueda en la base de conocimiento para el agente.

Los workspaces se inyectan en tiempo de construcción (closures), de modo que
el LLM nunca puede ver ni modificar el workspace del usuario.
"""
from langchain_core.tools import tool


def _ws_can_see(metadata, workspaces):
    """Comprueba si el usuario puede ver un chunk dado sus workspaces."""
    if workspaces is None or "all" in workspaces:
        return True
    doc_ws = {w.strip() for w in str(metadata.get("workspace", "general")).split(",")}
    return bool(doc_ws & set(workspaces))


def make_kb_tools(workspaces=None):
    """
    Retorna herramientas de búsqueda con el workspace del usuario inyectado.
    workspaces=None → acceso total (admin).
    """
    _ws = workspaces  # baked-in closure variable

    @tool
    def search_knowledge_base(query: str) -> str:
        """
        Busca información en la base de conocimiento corporativa.
        Usa esta herramienta cuando necesites responder preguntas sobre
        documentos internos, políticas, procedimientos o cualquier contenido
        que haya sido indexado en Cortexa.

        Args:
            query: La pregunta o términos a buscar.

        Returns:
            Fragmentos de documentos relevantes con su fuente.
        """
        try:
            from src.core.database import db_manager
            vectorstore = db_manager.get_vectorstore()

            retriever = vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.3}
            )
            docs = retriever.invoke(query)

            # Filtrado por workspace baked-in (el LLM no puede sobreescribir esto)
            filtered = [d for d in docs if _ws_can_see(d.metadata, _ws)]

            if not filtered:
                return "No se encontró información relevante en la base de conocimiento."

            results = []
            for i, doc in enumerate(filtered, 1):
                source = doc.metadata.get("source", "desconocido")
                results.append(f"[Fuente {i}: {source}]\n{doc.page_content.strip()}")

            return "\n\n---\n\n".join(results)

        except Exception as e:
            return f"Error buscando en la base de conocimiento: {e}"

    @tool
    def list_available_documents() -> str:
        """
        Lista todos los documentos disponibles en la base de conocimiento
        a los que el usuario tiene acceso.
        Usa esta herramienta cuando el usuario pregunte qué documentos hay
        disponibles o quiera saber el contenido de la biblioteca.

        Returns:
            Lista de documentos con nombre, workspace y fecha.
        """
        try:
            from src.core.database import db_manager
            workspace_filter = None if (_ws is None or "all" in _ws) else _ws
            docs_df = db_manager.get_all_documents(workspace_filter=workspace_filter)
            # POST-AUDITORÍA · get_all_documents devuelve un pandas.DataFrame, no una lista
            if docs_df is None or (hasattr(docs_df, "empty") and docs_df.empty):
                return "No hay documentos indexados en la base de conocimiento."

            records = docs_df.to_dict(orient="records") if hasattr(docs_df, "to_dict") else list(docs_df)
            lines = []
            for d in records:
                ws = d.get("workspace", "general") or "general"
                ts_raw = d.get("upload_date") or d.get("indexed_at") or ""
                ts = str(ts_raw)[:10] if ts_raw else "—"
                lines.append(f"• {d.get('filename','?')}  [grupo: {ws}]  [indexado: {ts}]")

            return f"{len(records)} documento(s) disponible(s):\n" + "\n".join(lines)

        except Exception as e:
            return f"Error listando documentos: {e}"

    return [search_knowledge_base, list_available_documents]
