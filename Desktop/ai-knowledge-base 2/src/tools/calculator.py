"""
src/tools/calculator.py
Calculadora segura para el agente: operaciones matemáticas y estadísticas.
"""
import ast
import operator
import math
from langchain_core.tools import tool

# Operaciones permitidas (whitelist)
_SAFE_OPS = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Pow:  operator.pow,
    ast.Mod:  operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "len": len, "sqrt": math.sqrt,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
    "ceil": math.ceil, "floor": math.floor,
    "pow": pow, "int": int, "float": float,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Tipo no permitido: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        op = type(node.op)
        if op not in _SAFE_OPS:
            raise ValueError(f"Operación no permitida: {op}")
        left  = _safe_eval(node.left)
        right = _safe_eval(node.right)
        # POST-AUDITORÍA · Anti-DoS: limitar exponentes catastróficos
        # Sin esto el LLM podría pedir "2 ** (10 ** 9)" y reventar la CPU/RAM.
        if op is ast.Pow:
            try:
                if abs(float(right)) > 1024:
                    raise ValueError("Exponente demasiado grande (límite 1024).")
            except (TypeError, OverflowError):
                raise ValueError("Exponente inválido.")
        return _SAFE_OPS[op](left, right)
    elif isinstance(node, ast.UnaryOp):
        op = type(node.op)
        if op not in _SAFE_OPS:
            raise ValueError(f"Operación unaria no permitida: {op}")
        return _SAFE_OPS[op](_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Llamada a función no permitida.")
        fname = node.func.id
        if fname not in _SAFE_FUNCS:
            raise ValueError(f"Función no permitida: {fname}")
        args = [_safe_eval(a) for a in node.args]
        return _SAFE_FUNCS[fname](*args)
    elif isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCS:
            return _SAFE_FUNCS[node.id]
        raise ValueError(f"Variable no permitida: {node.id}")
    elif isinstance(node, ast.List):
        return [_safe_eval(e) for e in node.elts]
    else:
        raise ValueError(f"Expresión no soportada: {type(node)}")


@tool
def calculator(expression: str) -> str:
    """
    Evalúa expresiones matemáticas de forma segura.
    Úsala para cualquier cálculo numérico: aritmética, porcentajes,
    estadísticas básicas, operaciones financieras simples.

    Funciones disponibles: abs, round, min, max, sum, len, sqrt,
    log, log10, log2, sin, cos, tan, ceil, floor, pow, int, float.
    Constantes: pi, e.

    Args:
        expression: Expresión matemática a evaluar.
                    Ejemplos: "1500 * 0.21", "sqrt(144)", "sum([10,20,30]) / 3"

    Returns:
        Resultado numérico o mensaje de error.
    """
    try:
        expr = expression.strip()
        # Reemplazar ^ por ** para usuarios que usen notación matemática
        expr = expr.replace("^", "**")
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval(tree)
        # Formatear resultado
        if isinstance(result, float):
            if result == int(result):
                return str(int(result))
            return f"{result:.6g}"
        return str(result)
    except ZeroDivisionError:
        return "Error: división por cero."
    except Exception as e:
        return f"Error en el cálculo: {e}"


@tool
def statistics_summary(numbers: str) -> str:
    """
    Calcula estadísticas descriptivas de una lista de números.
    Úsala cuando tengas datos numéricos y necesites media, mediana,
    mínimo, máximo, desviación estándar, etc.

    Args:
        numbers: Números separados por comas o espacios.
                 Ejemplo: "10, 20, 30, 40, 50"  o  "1.5 2.3 4.1 3.8"

    Returns:
        Resumen estadístico completo.
    """
    try:
        import statistics as stats
        # Parsear números
        raw = numbers.replace(",", " ").split()
        vals = [float(x) for x in raw if x.strip()]
        if not vals:
            return "No se proporcionaron números válidos."
        n = len(vals)
        mean   = stats.mean(vals)
        median = stats.median(vals)
        mn, mx = min(vals), max(vals)
        total  = sum(vals)
        stdev  = stats.stdev(vals) if n > 1 else 0

        return (
            f"N = {n}\n"
            f"Total  = {total:g}\n"
            f"Media  = {mean:.4g}\n"
            f"Mediana = {median:.4g}\n"
            f"Mín    = {mn:g}\n"
            f"Máx    = {mx:g}\n"
            f"Rango  = {mx - mn:g}\n"
            f"Desv. estándar = {stdev:.4g}"
        )
    except Exception as e:
        return f"Error: {e}"
