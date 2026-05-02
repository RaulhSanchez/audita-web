"""
src/core/agent.py
Agente LangGraph de Cortexa — flujos deterministas con tool calling nativo.

Arquitectura:
  [START] → nodo_llm → ¿tool_calls?
                      ├─ Sí → nodo_tools (paralelo) → nodo_llm
                      └─ No → [END]

Ventajas sobre el ReAct manual anterior:
- Tool calling nativo (sin regex frágil)
- Ejecución paralela de herramientas cuando el modelo lo decide
- Streaming token a token en la respuesta final
- Fallback automático al loop ReAct si el modelo no soporta function calling
"""

from __future__ import annotations
from typing import Iterator, List, Optional
import re

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AIMessageChunk
from langchain_core.tools import BaseTool


SYSTEM_PROMPT = """\
Eres Cortexa, un asistente corporativo experto. SIEMPRE respondes en ESPAÑOL.

Usa las herramientas disponibles antes de responder preguntas sobre documentos.
- Busca SIEMPRE en la base de conocimiento para preguntas sobre contenido corporativo.
- Si necesitas varios datos distintos a la vez, puedes usar múltiples herramientas.
- Sé conciso, cita las fuentes cuando uses documentos.
- Si no encuentras información, dilo claramente sin inventar datos.

Workspace activo: {workspaces}
"""


# ── ReAct fallback (para modelos sin function calling nativo) ────────────────

_ACTION_RE = re.compile(r"Action\s*:\s*(.+)", re.IGNORECASE)
_INPUT_RE  = re.compile(r"Action Input\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)
_FINAL_RE  = re.compile(r"Final Answer\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)

REACT_FALLBACK_PROMPT = """\
Eres Cortexa. SIEMPRE en ESPAÑOL. Workspaces: {workspaces}

Herramientas disponibles:
{tool_descriptions}

Formato OBLIGATORIO:
Thought: [razonamiento]
Action: [nombre_herramienta]
Action Input: [texto de entrada]
Observation: [resultado — lo da el sistema]
... (repite según necesites)
Thought: Ya tengo suficiente información.
Final Answer: [respuesta completa en español]
"""


def _react_stream(llm, tools_dict, question, history, workspaces, max_iter=8) -> Iterator[str]:
    """Loop ReAct manual — usado como fallback si el modelo no soporta tool calling."""
    tool_descs = "\n".join(
        f"- {n}: {(t.description or '').split(chr(10))[0]}"
        for n, t in tools_dict.items()
    )
    system = REACT_FALLBACK_PROMPT.format(
        workspaces=", ".join(workspaces or ["all"]),
        tool_descriptions=tool_descs,
    )
    msgs = [SystemMessage(content=system)]
    for role, content in (history or [])[-6:]:
        msgs.append(HumanMessage(content=content) if role == "human" else AIMessage(content=content))

    scratchpad = ""
    seen: dict[str, int] = {}

    for _ in range(max_iter):
        user_content = question + (f"\n\n{scratchpad}" if scratchpad else "")
        current_msgs = msgs + [HumanMessage(content=user_content)]
        raw = "".join(
            c.content for c in llm.stream(current_msgs) if hasattr(c, "content")
        )
        final = _FINAL_RE.search(raw)
        if final:
            yield final.group(1).strip()
            return
        am, im = _ACTION_RE.search(raw), _INPUT_RE.search(raw)
        if am and im:
            tname = am.group(1).strip().replace(" ", "_").replace("-", "_").lower()
            tinput = im.group(1).strip()
            key = f"{tname}::{tinput}"
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 2:
                scratchpad += f"\n{raw}\nObservation: Acción repetida. Usando información disponible.\n"
                continue
            tool = tools_dict.get(tname)
            obs = str(tool.invoke(tinput)) if tool else f"Herramienta '{tname}' no encontrada."
            scratchpad += f"\n{raw}\nObservation: {obs}\n"
        else:
            yield raw.strip()
            return

    yield "He alcanzado el límite de razonamiento. " + scratchpad.split("Observation:")[-1].strip()


# ── Agente principal ─────────────────────────────────────────────────────────

class CortexaAgent:
    """
    Agente LangGraph con fallback ReAct.
    Los grafos se construyen bajo demanda y se cachean por conjunto de workspaces,
    de modo que las herramientas nunca exponen el workspace al LLM.

    Interfaz pública:
        agent.stream(question, history, workspaces) → Iterator[str]
        agent.run(question, history, workspaces)    → str
    """

    def __init__(self):
        from src.core.brain import get_brain
        brain, err = get_brain()
        if not brain:
            raise RuntimeError(f"Modelo no disponible: {err}")
        self.llm = brain.llm

        # Cache: frozenset(workspaces) → (graph | None, tools_dict)
        self._cache: dict = {}
        self._langgraph_ok: bool | None = None  # None = untested

    @staticmethod
    def _build_tools(workspaces) -> List[BaseTool]:
        """Construye herramientas con workspace baked-in (el LLM no puede sobreescribirlo)."""
        from src.tools.kb_search    import make_kb_tools
        from src.tools.document_ops import make_document_ops_tools
        from src.tools.sql_query    import make_sql_tools
        from src.tools.calculator   import calculator, statistics_summary
        from src.tools.web_search   import web_search
        return [
            *make_kb_tools(workspaces),
            *make_document_ops_tools(workspaces),
            *make_sql_tools(workspaces),
            calculator,
            statistics_summary,
            web_search,
        ]

    def _get_graph_and_tools(self, workspaces: list):
        """Retorna (graph_or_None, tools_dict) para el conjunto de workspaces dado."""
        key = frozenset(workspaces)
        if key in self._cache:
            return self._cache[key]

        tools = self._build_tools(workspaces)
        tools_dict = {t.name: t for t in tools}
        graph = None

        # Solo intentar LangGraph si la primera vez funcionó (o aún no se ha probado)
        if self._langgraph_ok is not False:
            try:
                from langgraph.prebuilt import create_react_agent
                graph = create_react_agent(model=self.llm, tools=tools)
                self._langgraph_ok = True
            except Exception as e:
                print(f"[agent] LangGraph no disponible, usando ReAct: {e}")
                self._langgraph_ok = False

        self._cache[key] = (graph, tools_dict)
        return graph, tools_dict

    # ── API pública ──────────────────────────────────────────────────────────

    def run(self, question: str, history: list | None = None,
            workspaces: list | None = None) -> str:
        return "".join(self.stream(question, history, workspaces))

    def stream(self, question: str, history: list | None = None,
               workspaces: list | None = None,
               on_tool_call: "callable | None" = None) -> Iterator[str]:
        """
        Genera tokens de la respuesta final.
        on_tool_call(tool_name): callback opcional llamado cuando el agente
        invoca una herramienta (útil para mostrar estado en el UI).
        """
        workspaces = workspaces or ["all"]
        history    = history or []

        graph, tools_dict = self._get_graph_and_tools(workspaces)

        if graph is not None:
            yield from self._stream_langgraph(
                graph, tools_dict, question, history, workspaces, on_tool_call
            )
        else:
            yield from _react_stream(self.llm, tools_dict, question, history, workspaces)

    def _stream_langgraph(self, graph, tools_dict: dict, question: str,
                          history: list, workspaces: list,
                          on_tool_call=None) -> Iterator[str]:
        system = SystemMessage(content=SYSTEM_PROMPT.format(
            workspaces=", ".join(workspaces)
        ))
        msgs = [system]
        for role, content in history[-6:]:
            msgs.append(
                HumanMessage(content=content) if role == "human"
                else AIMessage(content=content)
            )
        msgs.append(HumanMessage(content=question))

        try:
            for chunk, metadata in graph.stream(
                {"messages": msgs},
                stream_mode="messages",
            ):
                if isinstance(chunk, AIMessageChunk):
                    # Notificar al UI qué herramienta se va a llamar
                    tool_calls = getattr(chunk, "tool_call_chunks", [])
                    if on_tool_call and tool_calls:
                        for tc in tool_calls:
                            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                            if name:
                                on_tool_call(name)

                    # Emitir solo tokens de respuesta final (sin tool_calls)
                    if (
                        chunk.content
                        and not tool_calls
                        and metadata.get("langgraph_node") == "agent"
                    ):
                        yield chunk.content
        except Exception as e:
            # Si falla en runtime (ej: modelo sin tool calling), caer a ReAct
            print(f"[agent] Error LangGraph en runtime, fallback ReAct: {e}")
            yield from _react_stream(
                self.llm, tools_dict, question, history, workspaces
            )


# ── Singleton ────────────────────────────────────────────────────────────────

_agent_instance: Optional[CortexaAgent] = None


def get_agent() -> tuple[Optional[CortexaAgent], Optional[str]]:
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance, None
    try:
        _agent_instance = CortexaAgent()
        return _agent_instance, None
    except Exception as e:
        return None, str(e)


def reset_agent():
    """Fuerza recreación del agente (útil al cambiar modelo en caliente)."""
    global _agent_instance
    _agent_instance = None
