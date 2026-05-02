import os
import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.core.brain import get_brain

class VerifierService:
    def __init__(self):
        # Evitar inicialización inmediata para no bloquear el arranque de Streamlit
        self.brain = None

    def _ensure_brain(self):
        """Inicializa el cerebro bajo demanda."""
        if self.brain is None:
            self.brain, _ = get_brain()
        return self.brain

    def verify_answer(self, question: str, answer: str, chunks: List[str]) -> Dict[str, Any]:
        """
        Verifica la fidelidad de la respuesta frente al contexto.
        Retorna un dict con: {status: 'VERIFIED'|'WARNING'|'FAILED', reasoning: str}
        """
        brain = self._ensure_brain()
        if not brain or not chunks:
            return {"status": "UNKNOWN", "reasoning": "No hay contexto o cerebro disponible para verificar."}

        context_text = "\n---\n".join(chunks)

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "Eres un Auditor de Veracidad de IA especializado en contratos legales.\n\n"
                "CRITERIOS DE FALLO CRÍTICOS (FAILED):\n"
                "1. CONFUSIÓN SALARIO-BONO: Si la respuesta describe 'Bonificaciones' (ej: 425€, 147€) como si fueran el sueldo del trabajador, marca como FAILED. Las bonificaciones son ayudas para la empresa, no salario.\n"
                "2. ALUCINACIÓN DE REFERENCIA: Si usa números entre paréntesis (ej: '(14)') para inventar días o números de cláusula, marca como FAILED.\n"
                "3. CAMPOS VACÍOS: Si el contexto tiene puntos suspensivos (....) y la respuesta afirma que hay un dato real, marca como FAILED.\n\n"
                "ESTADOS:\n"
                "- VERIFIED: Fiel y distingue correctamente bonos de salarios.\n"
                "- WARNING: Inferencias con riesgo medio.\n"
                "- FAILED: Mentiras, datos inventados o confusión de términos técnicos.\n\n"
                "CONTEXTO:\n{context}\n\n"
                "PREGUNTA: {question}\n\n"
                "RESPUESTA: {answer}\n\n"
                "Responde ÚNICAMENTE en JSON:\n"
                '{ "status": "VERIFIED" | "WARNING" | "FAILED", "reasoning": "Explicación breve del fallo o éxito" }'
            ))
        ])

        try:
            # Usamos el mismo LLM pero con temperatura 0 para máxima consistencia
            raw_response = brain.llm.invoke(prompt.format(
                context=context_text[:8000], # Limitamos para no exceder contexto
                question=question,
                answer=answer
            ))
            
            # Intentar limpiar si el LLM devuelve markdown
            clean_content = raw_response.content.strip()
            if "```json" in clean_content:
                clean_content = clean_content.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_content:
                clean_content = clean_content.split("```")[1].split("```")[0].strip()
                
            return json.loads(clean_content)
        except Exception as e:
            return {"status": "ERROR", "reasoning": f"Error en la verificación: {str(e)}"}

verifier_service = VerifierService()
