"""
src/tools/sql_query.py
Herramientas Text-to-SQL para el agente.

Los workspaces se inyectan en tiempo de construcción (closures), de modo que
el LLM nunca puede ver ni modificar el workspace del usuario.
"""
from langchain_core.tools import tool


_SQL_GENERATION_PROMPT = """\
Eres un experto en SQL. Genera UNA SOLA consulta SQL correcta para responder
la siguiente pregunta usando el esquema proporcionado.

REGLAS:
1. Solo SELECT — NUNCA INSERT, UPDATE, DELETE, DROP u otras operaciones de escritura.
2. Usa alias claros para columnas calculadas.
3. Limita siempre los resultados: añade LIMIT 50 si no hay otra restricción.
4. Si la pregunta es ambigua, elige la interpretación más útil.
5. Responde ÚNICAMENTE con la consulta SQL, sin explicaciones ni markdown.

ESQUEMA:
{schema}

PREGUNTA: {question}

SQL:"""


def make_sql_tools(workspaces=None):
    """
    Retorna herramientas Text-to-SQL con el workspace del usuario inyectado.
    workspaces=None → acceso total (admin).
    """
    _ws = workspaces  # baked-in closure variable

    @tool
    def list_sql_databases() -> str:
        """
        Lista las bases de datos SQL disponibles a las que tienes acceso.
        Úsala antes de query_database para conocer qué bases de datos hay
        y cuál elegir para responder la pregunta del usuario.

        Returns:
            Lista de bases de datos con nombre y descripción.
        """
        try:
            from src.core.sqldb import get_databases_for_workspaces
            dbs = get_databases_for_workspaces(_ws)
            if not dbs:
                return "No hay bases de datos SQL configuradas o accesibles."
            lines = []
            for db in dbs:
                lines.append(
                    f"• **{db['name']}** — {db['description'] or 'sin descripción'} "
                    f"[workspaces: {db['workspaces']}]"
                )
            return f"{len(dbs)} base(s) de datos disponible(s):\n" + "\n".join(lines)
        except Exception as e:
            return f"Error listando bases de datos: {e}"

    @tool
    def query_database(question: str, database_name: str) -> str:
        """
        Responde preguntas sobre datos estructurados consultando una base de datos SQL.
        Genera automáticamente la consulta SQL y devuelve los resultados.
        Úsala cuando el usuario pregunte por datos numéricos, estadísticas, listados
        o cualquier información que esté en una base de datos relacional.

        Args:
            question: La pregunta en lenguaje natural sobre los datos.
            database_name: Nombre exacto de la base de datos (usa list_sql_databases
                           para ver las disponibles).

        Returns:
            Resultados de la consulta en formato tabla.
        """
        try:
            from src.core.sqldb import get_schema, execute_readonly
            from src.core.brain import get_brain

            # 1. Obtener esquema (con comprobación de acceso)
            schema = get_schema(database_name, _ws)
            if "no encontrada" in schema or "sin acceso" in schema:
                return schema

            # 2. Generar SQL con el LLM
            brain, err = get_brain()
            if not brain:
                return f"Modelo no disponible: {err}"

            prompt = _SQL_GENERATION_PROMPT.format(
                schema=schema, question=question
            )
            sql_response = brain.llm.invoke(prompt)
            sql = sql_response.content.strip()

            # Limpiar posibles bloques markdown ```sql ... ```
            if sql.startswith("```"):
                sql = "\n".join(
                    line for line in sql.splitlines()
                    if not line.strip().startswith("```")
                ).strip()

            # 3. Ejecutar (solo lectura, validación de seguridad incluida)
            ok, result = execute_readonly(database_name, sql, _ws)
            if not ok:
                return f"Error ejecutando consulta: {result}\n\nSQL generado:\n```sql\n{sql}\n```"

            return (
                f"**Consulta ejecutada en `{database_name}`:**\n"
                f"```sql\n{sql}\n```\n\n"
                f"**Resultados:**\n{result}"
            )

        except Exception as e:
            return f"Error en Text-to-SQL: {e}"

    return [list_sql_databases, query_database]
