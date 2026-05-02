"""
src/services/ragas_service.py
Evaluación de calidad del RAG con RAGAS (v0.4+).

Métricas implementadas:
  - Faithfulness:       ¿La respuesta solo afirma cosas que están en los documentos?
  - Answer Relevancy:   ¿La respuesta responde realmente a la pregunta?
  - Context Precision:  ¿Los chunks recuperados son relevantes para la pregunta?

Las métricas usan el LLM local (Ollama) y los embeddings (nomic-embed-text),
sin enviar datos fuera de la organización.

Uso:
    from src.services.ragas_service import ragas_service
    results = ragas_service.evaluate(samples)   # lista de dicts
    score   = ragas_service.quick_score(question, answer, contexts)
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from typing import Any


_SQLITE_PATH = "./db/cortexa_meta.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ragas_evaluations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_name    TEXT DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by  TEXT DEFAULT 'system',
    num_samples INTEGER DEFAULT 0,
    scores_json TEXT DEFAULT '{}',
    samples_json TEXT DEFAULT '[]'
)
"""


class RagasService:

    def _ensure_table(self):
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.execute(_CREATE_TABLE)
        conn.commit()
        conn.close()

    # ── LLM / Embeddings wrappers para RAGAS ────────────────────────────────

    def _get_ragas_llm(self):
        from ragas.llms import LangchainLLMWrapper
        from src.core.brain import get_brain
        brain, err = get_brain()
        if not brain:
            raise RuntimeError(f"LLM no disponible: {err}")
        return LangchainLLMWrapper(brain.llm)

    def _get_ragas_embeddings(self):
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from src.core.database import db_manager
        return LangchainEmbeddingsWrapper(db_manager.embeddings)

    # ── Evaluación completa ──────────────────────────────────────────────────

    def evaluate(
        self,
        samples: list[dict],
        run_name: str = "",
        created_by: str = "system",
    ) -> dict[str, Any]:
        """
        Evalúa una lista de muestras con RAGAS.

        Cada muestra debe tener:
          - user_input (str):         la pregunta del usuario
          - response (str):           la respuesta generada
          - retrieved_contexts (list[str]): los chunks recuperados

        Devuelve un dict con:
          - scores: {faithfulness, answer_relevancy, context_precision}
          - samples: lista de muestras con scores individuales
          - run_id: ID de la evaluación guardada en BD
        """
        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.metrics.collections import (
            Faithfulness, AnswerRelevancy, ContextPrecisionWithoutReference,
        )

        if not samples:
            return {"error": "No hay muestras para evaluar."}

        try:
            llm        = self._get_ragas_llm()
            embeddings = self._get_ragas_embeddings()
        except Exception as e:
            return {"error": f"No se pudo inicializar LLM/embeddings: {e}"}

        # Construir dataset
        ragas_samples = []
        for s in samples:
            ragas_samples.append(SingleTurnSample(
                user_input=s.get("user_input", ""),
                response=s.get("response", ""),
                retrieved_contexts=s.get("retrieved_contexts", []),
            ))
        dataset = EvaluationDataset(samples=ragas_samples)

        # Métricas a calcular
        metrics = [
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm, embeddings=embeddings),
            ContextPrecisionWithoutReference(llm=llm),
        ]

        try:
            result = evaluate(dataset=dataset, metrics=metrics)
        except Exception as e:
            return {"error": f"Error durante la evaluación: {e}"}

        # Extraer scores agregados
        scores = {}
        try:
            df = result.to_pandas()
            for col in ["faithfulness", "answer_relevancy", "context_precision"]:
                if col in df.columns:
                    scores[col] = round(float(df[col].mean()), 4)

            # Scores por muestra
            sample_scores = []
            for i, s in enumerate(samples):
                row = df.iloc[i] if i < len(df) else {}
                sample_scores.append({
                    "question": s.get("user_input", "")[:120],
                    "faithfulness":       round(float(row.get("faithfulness", 0)), 4),
                    "answer_relevancy":   round(float(row.get("answer_relevancy", 0)), 4),
                    "context_precision":  round(float(row.get("context_precision", 0)), 4),
                })
        except Exception as e:
            print(f"[ragas] Error extrayendo scores: {e}")
            sample_scores = []

        # Guardar en BD
        run_id = self._save_run(run_name, created_by, len(samples), scores, sample_scores)

        return {
            "run_id":  run_id,
            "scores":  scores,
            "samples": sample_scores,
        }

    # ── Evaluación rápida (una sola pregunta) ────────────────────────────────

    def quick_score(
        self, question: str, answer: str, contexts: list[str]
    ) -> dict[str, float]:
        """
        Evalúa una sola respuesta. Devuelve scores individuales o {} si falla.
        """
        result = self.evaluate(
            samples=[{
                "user_input":          question,
                "response":            answer,
                "retrieved_contexts":  contexts,
            }],
            run_name="quick_eval",
        )
        return result.get("scores", {})

    # ── Persistencia ─────────────────────────────────────────────────────────

    def _save_run(self, run_name, created_by, num_samples, scores, sample_scores) -> int:
        self._ensure_table()
        conn = sqlite3.connect(_SQLITE_PATH)
        cur = conn.execute(
            "INSERT INTO ragas_evaluations "
            "(run_name, created_by, num_samples, scores_json, samples_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_by,
                num_samples,
                json.dumps(scores, ensure_ascii=False),
                json.dumps(sample_scores, ensure_ascii=False),
            ),
        )
        run_id = cur.lastrowid
        conn.commit()
        conn.close()
        return run_id

    def get_all_runs(self) -> list[dict]:
        self._ensure_table()
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, run_name, created_at, created_by, num_samples, scores_json "
            "FROM ragas_evaluations ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            scores = json.loads(r["scores_json"] or "{}")
            result.append({
                "id":          r["id"],
                "run_name":    r["run_name"],
                "created_at":  r["created_at"],
                "created_by":  r["created_by"],
                "num_samples": r["num_samples"],
                "scores":      scores,
            })
        return result

    def get_run_detail(self, run_id: int) -> dict | None:
        self._ensure_table()
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        r = conn.execute(
            "SELECT * FROM ragas_evaluations WHERE id=?", (run_id,)
        ).fetchone()
        conn.close()
        if not r:
            return None
        return {
            "id":          r["id"],
            "run_name":    r["run_name"],
            "created_at":  r["created_at"],
            "created_by":  r["created_by"],
            "num_samples": r["num_samples"],
            "scores":      json.loads(r["scores_json"] or "{}"),
            "samples":     json.loads(r["samples_json"] or "[]"),
        }

    def delete_run(self, run_id: int):
        self._ensure_table()
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.execute("DELETE FROM ragas_evaluations WHERE id=?", (run_id,))
        conn.commit()
        conn.close()


ragas_service = RagasService()
