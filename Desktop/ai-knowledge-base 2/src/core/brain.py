import os
import re
import contextvars
from typing import Any, List as TList, Optional
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_ollama import ChatOllama
from langchain_community.retrievers import BM25Retriever
from src.core.database import db_manager


# ─────────────────────────────────────────────────────────────────────────────
# POST-AUDITORÍA · Aislamiento per-request de fuentes y chunks
#
# La versión original guardaba self._last_sources / self._last_chunks como
# atributos del singleton CortexaBrain. Con dos usuarios concurrentes esto
# producía fuga cross-tenant: el usuario B podía ver las fuentes consultadas
# por el usuario A. Ahora usamos contextvars, que aísla los valores por
# contexto de ejecución (cada request en FastAPI / cada rerun de Streamlit
# corre en un contexto distinto cuando se respeta).
#
# Para Streamlit, el dashboard SIEMPRE crea un contexto nuevo por mensaje
# usando `with brain.scope():` antes de llamar a query_stream.
# ─────────────────────────────────────────────────────────────────────────────
_last_sources_var: contextvars.ContextVar[list] = contextvars.ContextVar(
    "cortexa_last_sources", default=[]
)
_last_chunks_var: contextvars.ContextVar[list] = contextvars.ContextVar(
    "cortexa_last_chunks", default=[]
)


def _ws_can_see(metadata, workspaces):
    """Comprueba si el usuario puede ver un chunk dado sus workspaces.
    El campo workspace puede ser un único valor o varios separados por coma.
    """
    if workspaces is None or "all" in workspaces:
        return True
    doc_ws = {w.strip() for w in str(metadata.get("workspace", "general")).split(",")}
    return bool(doc_ws & set(workspaces))


class _CortexaRetriever(BaseRetriever):
    """Envuelve cualquier retriever añadiendo post-filtrado por workspace y sanitización de texto."""
    base_retriever: Any
    workspaces: Optional[TList[str]] = None
    sanitizer_fn: Optional[Any] = None

    model_config = {"arbitrary_types_allowed": True}

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> TList[Document]:
        docs = self.base_retriever.invoke(query)
        filtered = []
        for d in docs:
            # 1. Post-filtrado por workspace
            if not _ws_can_see(d.metadata, self.workspaces):
                continue

            # 2. Sanitización (Eliminar ruido como "(14) ...." antes de llegar al LLM)
            if self.sanitizer_fn:
                d.page_content = self.sanitizer_fn(d.page_content)

            filtered.append(d)

        # 3. Re-ranking: reordena por relevancia semántica precisa antes del LLM
        if filtered:
            from src.core.reranker import rerank
            filtered = rerank(query, filtered, top_k=5)

        return filtered


class CortexaBrain:
    def __init__(self):
        import time
        max_retries = 3
        # Feature G: read model from settings first, then env var
        try:
            from src.core.userdb import userdb as _udb
            self.model_name = _udb.get_setting("ollama_model", "") or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        except Exception:
            self.model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

        for i in range(max_retries):
            try:
                self.llm = ChatOllama(
                    model=self.model_name,
                    base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    streaming=True,
                    temperature=0,
                    num_ctx=4096,
                    num_predict=1024,
                )
                break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"⏳ Esperando modelo {self.model_name}... (Intento {i+1}/{max_retries})")
                    import time as t
                    t.sleep(10)
                else:
                    raise e

        self.vectorstore = db_manager.get_vectorstore()
        # NOTA: _last_sources y _last_chunks ya NO son atributos del singleton.
        # Se exponen como properties que leen de contextvars (aislamiento per-request).
        
        # Regex para detectar referencias de pie de página seguidas de puntos suspensivos (Ruido de plantilla)
        # Ejemplo: "(14) ................." o "(1)  ....."
        self._footnote_pattern = re.compile(r"\(\d+\)\s*[\.]{3,}")

    def reload_model(self, model_name):
        """Feature G: cambiar modelo LLM en caliente."""
        self.model_name = model_name
        self.llm = ChatOllama(
            model=model_name,
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            streaming=True,
            temperature=0,
            num_ctx=4096,
            num_predict=1024,
        )

    @staticmethod
    def _can_see(metadata, workspaces):
        return _ws_can_see(metadata, workspaces)

    # ── BM25 corpus cache (post-auditoría: evita scroll completo por query) ──
    _bm25_cache: list = []           # Lista de Document
    _bm25_cache_count: int = -1      # nº de docs cuando se cacheó

    def _get_or_build_bm25_corpus(self):
        """Devuelve la lista cacheada de Documents para BM25, reconstruyendo solo si
        cambió el número total de chunks en el vectorstore. Llama a invalidate_bm25()
        al insertar/borrar para forzar reconstrucción.
        """
        try:
            data = self.vectorstore.get()
        except Exception:
            return None
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        current_count = len(docs)
        if current_count == 0:
            self._bm25_cache = []
            self._bm25_cache_count = 0
            return None
        if self._bm25_cache_count == current_count and self._bm25_cache:
            return self._bm25_cache
        # Reconstruir
        self._bm25_cache = [Document(page_content=t, metadata=m) for t, m in zip(docs, metas)]
        self._bm25_cache_count = current_count
        return self._bm25_cache

    def invalidate_bm25(self):
        """Fuerza reconstrucción del corpus BM25 en la próxima query."""
        self._bm25_cache = []
        self._bm25_cache_count = -1

    def _build_retriever(self, workspaces=None):
        """Retriever híbrido BM25 + semántico con post-filtrado por workspace.

        POST-AUDITORÍA · El BM25 ya NO se reconstruye en cada llamada (era el
        cuello de botella principal: scroll completo de la colección + creación
        del índice). Ahora se cachea junto con un fingerprint del vectorstore
        (count + revisión interna) y solo se reconstruye cuando cambia.
        """
        # None o ["all"] → sin restricción; [] lista vacía → sin acceso
        semantic = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 8, "fetch_k": 30, "lambda_mult": 0.2}
        )

        bm25_all = self._get_or_build_bm25_corpus()
        if bm25_all is None:
            return _CortexaRetriever(
                base_retriever=semantic,
                workspaces=workspaces,
                sanitizer_fn=self._sanitize_text,
            )

        # Filtramos los Documents en memoria por workspace (rápido, in-process)
        docs_for_bm25 = [d for d in bm25_all if _ws_can_see(d.metadata, workspaces)]
        if docs_for_bm25:
            bm25 = BM25Retriever.from_documents(docs_for_bm25, k=4)
            base = EnsembleRetriever(retrievers=[bm25, semantic], weights=[0.4, 0.6])
        else:
            base = semantic

        # Siempre devolvemos el retriever envuelto para aplicar sanitización y seguridad
        return _CortexaRetriever(
            base_retriever=base,
            workspaces=workspaces,
            sanitizer_fn=self._sanitize_text
        )

    def get_rag_chain(self, workspaces=None, system_prompt_override="", cite_only=False):
        retriever = self._build_retriever(workspaces=workspaces)

        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", "Re-escribe la pregunta para que sea independiente según el historial de conversación."),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, contextualize_q_prompt
        )

        document_prompt = PromptTemplate(
            input_variables=["page_content", "source"],
            template="[FUENTE: {source}]\n{page_content}"
        )

        # Feature H: modo cite-only
        if cite_only:
            system_prompt = (
                "Eres Cortexa. HABLA SIEMPRE EN ESPAÑOL.\n"
                "MODO CITA TEXTUAL: Tu ÚNICA función es citar textualmente los fragmentos "
                "relevantes de los documentos proporcionados. NO interpretes, NO resumas, "
                "NO añadas opiniones ni análisis.\n\n"
                "REGLAS:\n"
                "1. Cita TEXTUALMENTE los pasajes relevantes del contexto.\n"
                "2. Indica la fuente de cada cita entre corchetes.\n"
                "3. Si no hay información relevante, responde: "
                "'No hay contenido textual relevante en los documentos disponibles.'\n"
                "4. NUNCA parafrasees ni interpretes el contenido.\n\n"
            )
        else:
            system_prompt = (
                "Eres Cortexa. HABLA SIEMPRE EN ESPAÑOL.\n"
                "Responde basándote en el CONTEXTO proporcionado, combinándolo con tu conocimiento general "
                "para interpretar correctamente la información.\n\n"
                "REGLAS CRÍTICAS:\n"
                "1. Los HECHOS (nombres, fechas, condiciones, cláusulas) deben venir SIEMPRE del documento. No los inventes.\n\n"
                "2. RUIDO DE PLANTILLA (NOTAS AL PIÉ):\n"
                "   - Los números entre paréntesis como (1), (14) o (18) son simples referencias a NOTAS AL PIE legales.\n"
                "   - NO son números de cláusula, ni días, ni cantidades.\n"
                "   - EJEMPLO ERROR: Decir '14 días de prueba' o 'Cláusula 14' si el texto es 'prueba de (14) ....'. El campo está VACÍO.\n\n"
                "3. DIFERENCIA REMUNERACIÓN vs BONIFICACIÓN:\n"
                "   - Las 'Bonificaciones' (ej: 425€, 147€) son ayudas para la empresa. NUNCA las describas como el salario del trabajador.\n"
                "   - Si el campo de remuneración está vacío (......), declara que NO se ha especificado el salario. NUNCA lo inventes usando tablas de anexos.\n\n"
                "4. NO AÑADAS UNIDADES: No añadas 'días', 'horas' o 'euros' si no están literalmente vinculados a un dato rellenado.\n\n"
                "5. DETECCIÓN DE CAMPOS VACÍOS: Puntos suspensivos (....) significan que no hay información. Si el documento es una plantilla sin rellenar, adviértelo de forma prominente.\n\n"
                "6. Si la pregunta requiere información inexistente, responde: 'No tengo información específica sobre eso en los documentos disponibles.'\n"
                "7. Siempre verifica cálculos y fuentes antes de responder.\n\n"
            )

        # Feature C: system prompt personalizado por workspace
        if system_prompt_override:
            system_prompt = (
                system_prompt
                + f"INSTRUCCIONES ADICIONALES DEL WORKSPACE:\n{system_prompt_override}\n\n"
            )

        system_prompt += "Contexto:\n{context}"

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        question_answer_chain = create_stuff_documents_chain(
            self.llm,
            qa_prompt,
            document_variable_name="context",
            document_prompt=document_prompt
        )

        return create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def _sanitize_text(self, text: str) -> str:
        """Elimina ruido de plantillas (notas al pie vacías) para evitar alucinaciones."""
        if not text:
            return ""
        # Reemplaza "(14) ...." por "...."
        return self._footnote_pattern.sub("....", text)

    @property
    def _last_sources(self):
        """Backward-compat: lee desde contextvars. Mejor usar get_last_sources()."""
        return list(_last_sources_var.get([]))

    @property
    def _last_chunks(self):
        """Backward-compat: lee desde contextvars. Mejor usar get_last_chunks()."""
        return list(_last_chunks_var.get([]))

    @staticmethod
    def get_last_sources() -> list:
        """API recomendada para obtener las fuentes del último query del contexto actual."""
        return list(_last_sources_var.get([]))

    @staticmethod
    def get_last_chunks() -> list:
        """API recomendada para obtener los chunks del último query del contexto actual."""
        return list(_last_chunks_var.get([]))

    def query_stream(self, input_text, chat_history, workspaces=None,
                     system_prompt_override="", cite_only=False):
        """
        Stream RAG. Las fuentes y chunks se almacenan en contextvars locales al
        contexto actual; léelos con `CortexaBrain.get_last_sources()` /
        `CortexaBrain.get_last_chunks()` después de consumir el generador.

        Esto aísla los datos por request/usuario y evita la fuga cross-tenant
        que existía cuando se guardaban como atributos del singleton.
        """
        rag_chain = self.get_rag_chain(
            workspaces=workspaces,
            system_prompt_override=system_prompt_override,
            cite_only=cite_only,
        )
        sources: list = []
        chunks: list = []
        seen_sources: set = set()
        # Reset al inicio del request en este contexto
        _last_sources_var.set(sources)
        _last_chunks_var.set(chunks)
        for chunk in rag_chain.stream({"input": input_text, "chat_history": chat_history}):
            if "context" in chunk:
                for doc in chunk["context"]:
                    # Los documentos ya vienen sanitizados desde el retriever (_CortexaRetriever)
                    chunks.append(doc.page_content)
                    src = doc.metadata.get("source", "")
                    if src and src not in seen_sources:
                        seen_sources.add(src)
                        sources.append(src)
            if "answer" in chunk:
                yield chunk["answer"]


_brain_instance = None
_brain_error = None
_brain_error_ts = 0.0          # timestamp del último fallo
_BRAIN_RETRY_SECS = 30         # reintenta si Ollama vuelve a estar disponible
_brain_lock = __import__("threading").Lock()


def get_brain():
    """Returns (brain_instance, error_message). On failure: (None, str). Thread-safe.
    Si hubo un error previo, reintenta pasados _BRAIN_RETRY_SECS segundos."""
    import time
    global _brain_instance, _brain_error, _brain_error_ts
    if _brain_instance is not None:
        return _brain_instance, None
    # Devolver error cacheado solo si aún no ha pasado el TTL
    if _brain_error is not None and (time.monotonic() - _brain_error_ts) < _BRAIN_RETRY_SECS:
        return None, _brain_error
    with _brain_lock:
        if _brain_instance is not None:
            return _brain_instance, None
        if _brain_error is not None and (time.monotonic() - _brain_error_ts) < _BRAIN_RETRY_SECS:
            return None, _brain_error
        try:
            _brain_instance = CortexaBrain()
            _brain_error = None   # limpiar error anterior si ahora funciona
            _brain_error_ts = 0.0
            return _brain_instance, None
        except Exception as e:
            _brain_error = str(e)
            _brain_error_ts = time.monotonic()
            return None, _brain_error


# Keep backward-compat alias (used in ingest_service)
class _LazyBrain:
    """Proxy that lazily initializes CortexaBrain on first use."""
    def __getattr__(self, name):
        instance, err = get_brain()
        if instance is None:
            raise RuntimeError(f"Ollama no disponible: {err}")
        return getattr(instance, name)


brain = _LazyBrain()
