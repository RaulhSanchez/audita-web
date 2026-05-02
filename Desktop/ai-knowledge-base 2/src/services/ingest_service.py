import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDoc
from src.core.database import db_manager
from src.services.plan_service import plan_service

MAX_FILE_SIZE_MB = 50


def _build_splitter(strategy: str = "semantic"):
    """
    Construye el splitter según la estrategia configurada.

    - "semantic": SemanticChunker con nomic-embed-text. Mejor calidad,
      más lento (~10-30s por documento). Recomendado para contratos y docs técnicos.
    - "recursive": RecursiveCharacterTextSplitter. Rápido, quality suficiente
      para documentos simples.

    Siempre devuelve un splitter válido — si SemanticChunker falla, usa recursive.
    """
    if strategy == "semantic":
        try:
            from langchain_experimental.text_splitter import SemanticChunker
            # Usamos los embeddings ya inicializados (evita re-cargar el modelo)
            embeddings = db_manager.embeddings
            return SemanticChunker(
                embeddings,
                breakpoint_threshold_type="percentile",   # corte en percentil 95 por defecto
                breakpoint_threshold_amount=95,
            )
        except Exception as e:
            print(f"[chunker] SemanticChunker no disponible, usando recursive: {e}")

    return RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150,
        add_start_index=True,
    )


def _load_pdf_pdfplumber(file_path: str):
    """
    Extrae texto + tablas de un PDF usando pdfplumber.
    Las tablas se convierten a Markdown para mejorar la calidad del RAG.
    Devuelve lista de LCDoc o None si falla (activa el fallback).
    """
    try:
        import pdfplumber
    except ImportError:
        return None

    filename = os.path.basename(file_path)
    docs = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                parts = []

                # ── Texto principal ───────────────────────────────────────
                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                if text.strip():
                    parts.append(text.strip())

                # ── Tablas → Markdown ────────────────────────────────────
                for table in (page.extract_tables() or []):
                    if not table:
                        continue
                    rows = []
                    for i, row in enumerate(table):
                        clean = [str(c or "").replace("\n", " ").strip() for c in row]
                        rows.append("| " + " | ".join(clean) + " |")
                        if i == 0:
                            rows.append("| " + " | ".join(["---"] * len(clean)) + " |")
                    if rows:
                        parts.append("\n".join(rows))

                combined = "\n\n".join(parts).strip()
                if combined:
                    docs.append(LCDoc(
                        page_content=combined,
                        metadata={"source": filename, "page": page_num + 1},
                    ))
    except Exception as e:
        print(f"[pdfplumber] Error en {filename}: {e}. Usando fallback PyPDF.")
        return None

    return docs if docs else None


def _load_pdf_fallback(file_path: str):
    """Fallback a PyPDFLoader si pdfplumber falla o no extrae texto."""
    from langchain_community.document_loaders import PyPDFLoader
    return PyPDFLoader(file_path).load()


class IngestionService:
    def __init__(self):
        self._splitter_cache: dict = {}   # strategy → splitter instance

    def _get_splitter(self):
        """Devuelve el splitter según la configuración activa."""
        try:
            from src.core.userdb import userdb
            strategy = userdb.get_setting("chunking_strategy", "semantic")
        except Exception:
            strategy = "semantic"
        if strategy not in self._splitter_cache:
            self._splitter_cache[strategy] = _build_splitter(strategy)
        return self._splitter_cache[strategy]

    def _get_loader(self, file_path):
        """Devuelve la lista de documentos según el tipo de fichero."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            # Intentar pdfplumber primero (tablas + layout), fallback a PyPDF
            docs = _load_pdf_pdfplumber(file_path)
            if docs is None:
                docs = _load_pdf_fallback(file_path)
            return docs  # lista de LCDoc, no un loader
        elif ext in [".docx", ".doc"]:
            try:
                from langchain_community.document_loaders import Docx2txtLoader
                return Docx2txtLoader(file_path).load()
            except ImportError:
                raise ImportError("Instala docx2txt: pip install docx2txt")
        else:
            raise ValueError(f"Formato no soportado: {ext}. Usa PDF o DOCX.")

    def check_size(self, file_path):
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return False, f"El archivo supera el límite de {MAX_FILE_SIZE_MB}MB ({size_mb:.1f}MB)."
        return True, ""

    def _generate_summary(self, splits):
        """Genera un resumen breve del documento usando el LLM local."""
        try:
            from src.core.brain import brain as _brain
            sample = " ".join([s.page_content for s in splits[:6]])[:2500]
            resp = _brain.llm.invoke(
                f"Resume en 2-3 frases cortas y en español este fragmento de documento. "
                f"Solo el resumen, sin introducciones:\n\n{sample}"
            )
            return resp.content.strip()[:500]
        except Exception:
            return ""

    def reindex_file(self, file_path, username, workspace=None):
        """Feature F: Reindexar documento existente (eliminar chunks + volver a indexar)."""
        filename = os.path.basename(file_path)

        # Guardar versión anterior
        try:
            old_doc_df = db_manager.get_all_documents()
            if not old_doc_df.empty:
                old_row = old_doc_df[old_doc_df['filename'] == filename]
                if not old_row.empty:
                    old_chunks = int(old_row.iloc[0].get('chunk_count', 0))
                    old_user = old_row.iloc[0].get('user', username)
                    version = db_manager.get_document_version_count(filename) + 1
                    db_manager.add_document_version(filename, version, old_user, old_chunks)
        except Exception:
            pass

        # Eliminar documento existente (chunks + metadata)
        try:
            db_manager.delete_document(filename)
        except Exception:
            pass

        # Re-indexar
        return self.process_file(file_path, username, workspace)

    def process_file(self, file_path, username, workspace=None):
        filename = os.path.basename(file_path)

        # Normalizar workspace a string (puede venir como lista)
        if isinstance(workspace, list):
            workspace_str = ",".join(sorted(set(w for w in workspace if w)))
        else:
            workspace_str = workspace or "general"

        # Validar tamaño
        ok, msg = self.check_size(file_path)
        if not ok:
            return False, msg

        # ── Verificar límite de documentos del plan ───────────────────────────
        ok, msg = plan_service.check_document_limit()
        if not ok:
            return False, msg

        # Detectar duplicado
        if db_manager.document_exists(filename):
            return False, f"'{filename}' ya está indexado. Usa 'Reindexar' para actualizarlo."

        try:
            docs = self._get_loader(file_path)
            splits = self._get_splitter().split_documents(docs)

            for split in splits:
                split.metadata["source"] = filename
                split.metadata["workspace"] = workspace_str

            splits = [d for d in splits if len(d.page_content.strip()) > 20]

            if not splits:
                return False, "No se extrajo texto válido del archivo."

            vectorstore = db_manager.get_vectorstore()
            ids = vectorstore.add_documents(documents=splits)

            db_manager.add_document_meta(
                doc_id=filename,
                filename=filename,
                user=username,
                chunks=len(ids),
                workspace=workspace_str
            )

            # Registrar como versión 1 en el historial
            try:
                version = db_manager.get_document_version_count(filename) + 1
                db_manager.add_document_version(filename, version, username, len(ids))
            except Exception:
                pass

            # Resumen automático (no bloquea si falla)
            summary = self._generate_summary(splits)
            if summary:
                db_manager.update_document_summary(filename, summary)

            # POST-AUDITORÍA · invalidar cache BM25 tras añadir documentos
            try:
                from src.core.brain import get_brain
                _b, _ = get_brain()
                if _b is not None:
                    _b.invalidate_bm25()
            except Exception:
                pass

            # Feature M: notificación por email de nuevo doc
            try:
                self._notify_new_doc(filename, workspace_str, username)
            except Exception:
                pass

            return True, f"✅ {filename} — {len(ids)} fragmentos indexados en '{workspace_str}'"
        except Exception as e:
            return False, f"❌ Error al procesar {filename}: {str(e)}"

    def _notify_new_doc(self, filename, workspace_str, uploader):
        """Feature M: Envía notificación por email a los usuarios del workspace."""
        from src.core.userdb import userdb
        if userdb.get_setting("notify_new_docs", "false") != "true":
            return
        from src.services.email_service import email_service
        if not email_service.is_configured():
            return

        product_name = userdb.get_setting("product_name", "Cortexa AI")
        ws_list = [w.strip() for w in workspace_str.split(",") if w.strip()]

        # Get users that belong to those workspaces
        all_users = userdb.get_all_users()
        recipients = []
        for u in all_users:
            if u["username"] == uploader:
                continue  # Don't notify the uploader
            email = u.get("email", "")
            if not email:
                continue
            user_ws = u.get("workspaces", ["general"])
            if "all" in user_ws or any(w in user_ws for w in ws_list):
                recipients.append(email)

        if not recipients:
            return

        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import smtplib

            cfg = email_service._get_smtp_config()
            for recipient_email in recipients[:20]:  # Limit to avoid spam
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"📄 Nuevo documento en {product_name}"
                msg["From"] = cfg["from"]
                msg["To"] = recipient_email

                html = f"""
                <html><body style="font-family:Arial,sans-serif; background:#f8fafc; padding:20px;">
                <div style="max-width:480px; margin:0 auto; background:white; border-radius:12px;
                            padding:32px; box-shadow:0 2px 16px rgba(0,0,0,0.08);">
                    <h3 style="color:#1e1b4b;">📄 Nuevo documento disponible</h3>
                    <p style="color:#475569;">Se ha subido un nuevo documento a <b>{product_name}</b>:</p>
                    <div style="background:#f1f5f9; border-radius:8px; padding:16px; margin:16px 0;">
                        <p style="margin:4px 0; color:#334155;"><b>📄 {filename}</b></p>
                        <p style="margin:4px 0; color:#64748b;">Grupo: {workspace_str}</p>
                        <p style="margin:4px 0; color:#64748b;">Subido por: {uploader}</p>
                    </div>
                    <p style="color:#94a3b8; font-size:0.8em;">
                        Inicia sesión para consultarlo.
                    </p>
                </div>
                </body></html>
                """
                msg.attach(MIMEText(html, "html"))

                if cfg["tls"]:
                    server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10)
                if cfg["user"] and cfg["password"]:
                    server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["from"], [recipient_email], msg.as_string())
                server.quit()
        except Exception as e:
            print(f"[notify_new_doc] Error enviando notificación: {e}")

    # Alias para compatibilidad con código anterior
    def process_pdf(self, file_path, username, workspace="general"):
        return self.process_file(file_path, username, workspace)

ingest_service = IngestionService()
