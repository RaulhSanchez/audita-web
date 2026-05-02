#!/usr/bin/env python3
"""
Migración one-shot: Chroma → Qdrant
Ejecutar UNA SOLA VEZ después de actualizar la app.

Uso:
    cd /ruta/a/ai-knowledge-base
    venv/bin/python scripts/migrate_chroma_to_qdrant.py

El script es seguro de re-ejecutar: no duplica documentos si Qdrant ya tiene datos.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 50)
    print("  Migración Chroma → Qdrant")
    print("=" * 50)

    # ── 1. Inicializar embeddings ────────────────────────────────────────────
    print("\n[1/4] Inicializando embeddings (nomic-embed-text)...")
    try:
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        embeddings.embed_query("test")
        print("      ✅ Embeddings listos")
    except Exception as e:
        print(f"      ❌ Error: {e}")
        print("      Asegúrate de que Ollama esté en ejecución con nomic-embed-text.")
        sys.exit(1)

    # ── 2. Leer datos de Chroma ──────────────────────────────────────────────
    print("\n[2/4] Leyendo datos de Chroma en ./db/ ...")
    chroma_path = "./db"
    if not os.path.exists(os.path.join(chroma_path, "chroma.sqlite3")):
        print("      ⚠️  No se encontró chroma.sqlite3. ¿Ya se migró o no hay datos?")
        print("      La app usará Qdrant desde cero.")
        return

    try:
        from langchain_chroma import Chroma
        chroma = Chroma(persist_directory=chroma_path, embedding_function=embeddings)
        data = chroma.get()
        total = len(data["ids"])
        print(f"      📦 {total} fragmentos encontrados en Chroma")
    except Exception as e:
        print(f"      ❌ Error leyendo Chroma: {e}")
        sys.exit(1)

    if total == 0:
        print("      ⚠️  Chroma está vacío. Nada que migrar.")
        return

    # ── 3. Escribir en Qdrant ────────────────────────────────────────────────
    print("\n[3/4] Escribiendo en Qdrant (./db/qdrant/)...")
    try:
        from src.core.vectorstore import CortexaVectorStore
        from langchain_core.documents import Document

        qdrant = CortexaVectorStore(embeddings=embeddings, path="./db/qdrant")

        # Comprobar si ya hay datos para evitar duplicados
        existing = qdrant.count()
        if existing > 0:
            print(f"      ⚠️  Qdrant ya tiene {existing} fragmentos.")
            resp = input("      ¿Continuar igualmente? (s/N): ").strip().lower()
            if resp != "s":
                print("      Migración cancelada.")
                return

        batch_size = 100
        migrated = 0
        for i in range(0, total, batch_size):
            batch_texts = data["documents"][i : i + batch_size]
            batch_metas = data["metadatas"][i : i + batch_size]
            docs = [
                Document(page_content=t, metadata=m)
                for t, m in zip(batch_texts, batch_metas)
                if t and t.strip()
            ]
            if docs:
                qdrant.add_documents(docs)
                migrated += len(docs)
            done = min(i + batch_size, total)
            print(f"      Procesados: {done}/{total} ({int(done/total*100)}%)", end="\r")

        print(f"\n      ✅ {migrated} fragmentos migrados")

    except Exception as e:
        print(f"\n      ❌ Error escribiendo en Qdrant: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ── 4. Verificar ─────────────────────────────────────────────────────────
    print("\n[4/4] Verificando migración...")
    try:
        final_count = qdrant.count()
        print(f"      📊 Fragmentos en Qdrant: {final_count}")

        if final_count >= migrated:
            print("\n✅ Migración completada con éxito.")
            print("\nPuedes eliminar los ficheros de Chroma (opcional):")
            print("  rm ./db/chroma.sqlite3")
            print("  rm -rf ./db/<uuid-directories>")
        else:
            print(f"\n⚠️  Solo {final_count}/{migrated} fragmentos en Qdrant. Revisa los logs.")
    except Exception as e:
        print(f"      Error en verificación: {e}")


if __name__ == "__main__":
    main()
