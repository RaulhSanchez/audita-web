"""
src/tools/document_ops.py
Operaciones sobre documentos: resumen, comparación, extracción de datos.

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


def _filter_by_workspace(result: dict, workspaces) -> list[str]:
    """Filtra los documentos de un resultado de vectorstore.get() por workspace."""
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])
    return [
        doc for doc, meta in zip(documents, metadatas)
        if _ws_can_see(meta, workspaces)
    ]


def make_document_ops_tools(workspaces=None):
    """
    Retorna herramientas de operaciones sobre documentos con el workspace
    del usuario inyectado. workspaces=None → acceso total (admin).
    """
    _ws = workspaces  # baked-in closure variable

    @tool
    def summarize_document(filename: str, focus: str = "") -> str:
        """
        Genera un resumen de un documento específico de la base de conocimiento.
        Usa esta herramienta cuando el usuario quiera un resumen de un documento
        concreto o cuando necesites entender el contenido de un fichero antes
        de responder.

        Args:
            filename: Nombre exacto del fichero a resumir (tal como aparece en list_available_documents).
            focus: Aspecto específico en el que enfocarse (opcional).
                   Ejemplo: "cláusulas de pago", "fechas clave", "personas mencionadas".

        Returns:
            Resumen estructurado del documento.
        """
        try:
            from src.core.database import db_manager
            vectorstore = db_manager.get_vectorstore()

            result = vectorstore.get(where={"source": filename})
            docs_content = _filter_by_workspace(result, _ws)

            if not docs_content:
                return f"No se encontró el documento '{filename}' o no tienes acceso a él."

            combined = "\n\n".join(docs_content)[:8000]

            from src.core.brain import get_brain
            brain, err = get_brain()
            if not brain:
                return f"Modelo no disponible: {err}"

            focus_instruction = f"\nEnfócate especialmente en: {focus}" if focus else ""
            prompt = (
                f"Eres un asistente experto. Resume el siguiente documento de forma clara y estructurada.{focus_instruction}\n\n"
                f"DOCUMENTO: {filename}\n\n{combined}\n\n"
                "Proporciona: 1) Resumen ejecutivo (2-3 frases), 2) Puntos clave, 3) Datos importantes."
            )
            response = brain.llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            return f"Error resumiendo documento: {e}"

    @tool
    def compare_documents(filename1: str, filename2: str, aspect: str = "") -> str:
        """
        Compara dos documentos de la base de conocimiento.
        Úsala cuando el usuario quiera comparar versiones, contratos, políticas
        u otros documentos entre sí.

        Args:
            filename1: Nombre del primer documento.
            filename2: Nombre del segundo documento.
            aspect: Aspecto específico a comparar (opcional).
                    Ejemplo: "precio", "condiciones", "fechas de vigencia".

        Returns:
            Análisis comparativo estructurado.
        """
        try:
            from src.core.database import db_manager
            vectorstore = db_manager.get_vectorstore()

            def _get_content(fname: str) -> str:
                res = vectorstore.get(where={"source": fname})
                docs = _filter_by_workspace(res, _ws)
                return "\n\n".join(docs)[:4000] if docs else ""

            content1 = _get_content(filename1)
            content2 = _get_content(filename2)

            if not content1:
                return f"No se encontró '{filename1}' o no tienes acceso a él."
            if not content2:
                return f"No se encontró '{filename2}' o no tienes acceso a él."

            from src.core.brain import get_brain
            brain, err = get_brain()
            if not brain:
                return f"Modelo no disponible: {err}"

            aspect_str = f" Enfócate en: {aspect}." if aspect else ""
            prompt = (
                f"Compara estos dos documentos de forma objetiva y estructurada.{aspect_str}\n\n"
                f"DOCUMENTO 1 ({filename1}):\n{content1}\n\n"
                f"DOCUMENTO 2 ({filename2}):\n{content2}\n\n"
                "Proporciona: 1) Similitudes principales, 2) Diferencias clave, 3) Conclusión."
            )
            response = brain.llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            return f"Error comparando documentos: {e}"

    @tool
    def extract_data_from_document(filename: str, data_to_extract: str) -> str:
        """
        Extrae información estructurada de un documento específico.
        Úsala para extraer datos concretos como fechas, importes, nombres,
        cláusulas, condiciones, KPIs, etc.

        Args:
            filename: Nombre del documento del que extraer datos.
            data_to_extract: Descripción de qué extraer.
                             Ejemplo: "todas las fechas y plazos mencionados",
                                      "importes y condiciones de pago",
                                      "nombres de personas y sus cargos".

        Returns:
            Datos extraídos en formato estructurado.
        """
        try:
            from src.core.database import db_manager
            vectorstore = db_manager.get_vectorstore()

            result = vectorstore.get(where={"source": filename})
            docs_content = _filter_by_workspace(result, _ws)

            if not docs_content:
                return f"No se encontró '{filename}' o no tienes acceso a él."

            combined = "\n\n".join(docs_content)[:8000]

            from src.core.brain import get_brain
            brain, err = get_brain()
            if not brain:
                return f"Modelo no disponible: {err}"

            prompt = (
                f"Extrae del siguiente documento: {data_to_extract}\n\n"
                f"Responde SOLO con los datos extraídos en formato claro y estructurado. "
                f"Si un dato no está presente, indícalo explícitamente.\n\n"
                f"DOCUMENTO: {filename}\n\n{combined}"
            )
            response = brain.llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            return f"Error extrayendo datos: {e}"

    return [summarize_document, compare_documents, extract_data_from_document]
