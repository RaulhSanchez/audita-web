"""
src/core/reranker.py
Re-ranking de chunks con cross-encoder antes de enviárselos al LLM.

Modelo: cross-encoder/ms-marco-MiniLM-L-6-v2 (~80 MB, descarga automática).
Si el modelo no está disponible, devuelve los documentos sin reordenar (fallback seguro).
"""
from __future__ import annotations
from typing import List
from langchain_core.documents import Document

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None
_reranker_error: str | None = None


def _get_reranker():
    global _reranker, _reranker_error
    if _reranker is not None:
        return _reranker
    if _reranker_error is not None:
        return None
    try:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(_MODEL_NAME)
        return _reranker
    except Exception as e:
        _reranker_error = str(e)
        print(f"[reranker] No disponible, se usarán los docs sin reordenar: {e}")
        return None


def rerank(query: str, docs: List[Document], top_k: int = 5) -> List[Document]:
    """
    Reordena docs por relevancia respecto a query usando un cross-encoder.
    Devuelve los top_k más relevantes. Si el modelo no está disponible,
    devuelve los primeros top_k sin cambios.
    """
    if not docs:
        return docs

    model = _get_reranker()
    if model is None:
        return docs[:top_k]

    try:
        pairs = [(query, doc.page_content) for doc in docs]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in ranked[:top_k]]
    except Exception as e:
        print(f"[reranker] Error al reordenar, devolviendo sin cambios: {e}")
        return docs[:top_k]
