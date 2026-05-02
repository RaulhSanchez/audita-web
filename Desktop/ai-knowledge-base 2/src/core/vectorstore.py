"""
CortexaVectorStore — Qdrant-backed vector store con interfaz compatible con Chroma.

Almacena datos localmente en ./db/qdrant/ (sin Docker).
Para producción, apunta QDRANT_URL a un servidor Qdrant Docker:
    QDRANT_URL=http://localhost:6333
"""
import os
from typing import Dict, List, Optional, Any


def _detect_embedding_size(embeddings) -> int:
    vec = embeddings.embed_query("cortexa")
    return len(vec)


class CortexaVectorStore:
    """
    Wrapper sobre QdrantVectorStore que añade los métodos get()/delete()
    que usa el resto del código (diseñados originalmente para Chroma).
    """

    def __init__(
        self,
        embeddings,
        path: str = "./db/qdrant",
        collection: str = "cortexa_docs",
    ):
        from qdrant_client import QdrantClient, models
        from langchain_qdrant import QdrantVectorStore

        self._collection = collection
        self._embeddings = embeddings

        # Conexión: variable de entorno para Docker, fichero local para dev
        qdrant_url = os.getenv("QDRANT_URL", "")
        if qdrant_url:
            self._client = QdrantClient(url=qdrant_url)
        else:
            os.makedirs(path, exist_ok=True)
            self._client = QdrantClient(path=path)

        # Crear colección si no existe
        existing = {c.name for c in self._client.get_collections().collections}
        if collection not in existing:
            size = _detect_embedding_size(embeddings)
            self._client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(
                    size=size,
                    distance=models.Distance.COSINE,
                ),
            )
            # Índices de payload para filtros eficientes
            for field in ("metadata.source", "metadata.workspace"):
                try:
                    self._client.create_payload_index(
                        collection_name=collection,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    pass

        self._store = QdrantVectorStore(
            client=self._client,
            collection_name=collection,
            embedding=embeddings,
        )

    # ── Interfaz compatible con Chroma ──────────────────────────────────────

    def get(self, where: Optional[Dict[str, Any]] = None) -> Dict[str, List]:
        """
        Devuelve {"ids": [...], "documents": [...], "metadatas": [...]}.
        Filtro opcional: where={"source": "archivo.pdf"}
        """
        from qdrant_client import models as qm

        scroll_filter = None
        if where:
            conditions = [
                qm.FieldCondition(
                    key=f"metadata.{k}",
                    match=qm.MatchValue(value=v),
                )
                for k, v in where.items()
            ]
            scroll_filter = qm.Filter(must=conditions)

        ids, documents, metadatas = [], [], []
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=scroll_filter,
                with_payload=True,
                with_vectors=False,
                limit=500,
                offset=offset,
            )
            for pt in points:
                payload = pt.payload or {}
                ids.append(str(pt.id))
                documents.append(payload.get("page_content", ""))
                metadatas.append(payload.get("metadata", {}))
            if offset is None:
                break

        return {"ids": ids, "documents": documents, "metadatas": metadatas}

    def delete(self, ids: List[str]) -> None:
        """Elimina puntos por su lista de IDs (UUID strings)."""
        from qdrant_client import models as qm
        if not ids:
            return
        self._client.delete(
            collection_name=self._collection,
            points_selector=qm.PointIdsList(points=ids),
        )

    def add_documents(self, documents) -> List[str]:
        """Añade documentos LangChain y devuelve sus IDs."""
        return self._store.add_documents(documents)

    def as_retriever(self, search_type: str = "similarity", search_kwargs: Optional[Dict] = None):
        """Devuelve un BaseRetriever de LangChain respaldado por Qdrant."""
        kwargs = search_kwargs or {}
        try:
            return self._store.as_retriever(
                search_type=search_type,
                search_kwargs=kwargs,
            )
        except Exception:
            # Fallback a similarity si MMR no está disponible en esta versión
            return self._store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": kwargs.get("k", 8)},
            )

    def count(self) -> int:
        """Número total de puntos en la colección."""
        return self._client.count(collection_name=self._collection).count
