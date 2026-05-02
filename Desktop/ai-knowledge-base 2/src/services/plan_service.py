"""
plan_service.py — Gestión de planes y límites por instancia.

Cada despliegue Docker tiene UN plan activo (starter / business / enterprise).
El plan se guarda en la tabla settings con la clave 'current_plan'.

Límites por plan:
  max_documents   : total de documentos indexados en el sistema (-1 = ilimitado)
  max_users       : número máximo de usuarios registrados   (-1 = ilimitado)
  max_queries_day : consultas diarias por usuario            (-1 = ilimitado)

Uso:
    from src.services.plan_service import plan_service

    ok, msg = plan_service.check_document_limit()
    ok, msg = plan_service.check_user_limit()
    info    = plan_service.get_plan_info()   # dict con nombre, límites y uso actual
"""

import sqlite3
from datetime import date
from src.core.userdb import userdb

SQLITE_PATH = "./db/cortexa_meta.db"

# ── Definición de planes ──────────────────────────────────────────────────────
# POST-AUDITORÍA · Pricing y límites alineados con la web pública
# (docs/pricing.html). Cualquier cambio aquí debe replicarse en la web.
PLANS = {
    "starter": {
        "label":           "Starter",
        "color":           "#64748b",
        "price":           "299 €/mes",
        "max_documents":   500,    # documentos totales indexados
        "max_users":       5,      # usuarios registrados
        "max_queries_day": 100,    # consultas/día por usuario
    },
    "business": {
        "label":           "Business",
        "color":           "#6366f1",
        "price":           "699 €/mes",
        "max_documents":   -1,     # ilimitado (alineado con web)
        "max_users":       25,
        "max_queries_day": 1000,
    },
    "enterprise": {
        "label":           "Enterprise",
        "color":           "#059669",
        "price":           "A consultar",
        "max_documents":   -1,
        "max_users":       -1,
        "max_queries_day": -1,
    },
}

DEFAULT_PLAN = "starter"


class PlanService:

    # ── Lectura del plan activo ───────────────────────────────────────────────

    def get_current_plan_name(self) -> str:
        name = userdb.get_setting("current_plan", DEFAULT_PLAN)
        return name if name in PLANS else DEFAULT_PLAN

    def get_plan_config(self, plan_name: str = None) -> dict:
        name = plan_name or self.get_current_plan_name()
        return PLANS.get(name, PLANS[DEFAULT_PLAN])

    def set_plan(self, plan_name: str, updated_by: str = "admin") -> bool:
        if plan_name not in PLANS:
            return False
        userdb.set_setting("current_plan", plan_name, updated_by=updated_by)
        # Sincronizar el rate limiter global con el nuevo límite de consultas
        new_limit = PLANS[plan_name]["max_queries_day"]
        if new_limit == -1:
            new_limit = 99999
        userdb.set_setting("daily_query_limit", str(new_limit), updated_by=updated_by)
        return True

    # ── Conteos actuales ──────────────────────────────────────────────────────

    def _count_documents(self) -> int:
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM documents")
            n = c.fetchone()[0]
            conn.close()
            return n
        except Exception:
            return 0

    def _count_users(self) -> int:
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            n = c.fetchone()[0]
            conn.close()
            return n
        except Exception:
            return 0

    def _count_queries_today(self, username: str) -> int:
        """Reutiliza la tabla rate_limits que ya existe."""
        try:
            today = date.today().isoformat()
            conn = sqlite3.connect(SQLITE_PATH)
            c = conn.cursor()
            c.execute(
                "SELECT count FROM rate_limits WHERE username=? AND date=?",
                (username, today)
            )
            row = c.fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception:
            return 0

    # ── Checks de límites ─────────────────────────────────────────────────────

    def check_document_limit(self) -> tuple[bool, str]:
        """
        Devuelve (True, "") si se puede indexar un documento más.
        Devuelve (False, mensaje) si se ha alcanzado el límite del plan.
        """
        cfg = self.get_plan_config()
        max_docs = cfg["max_documents"]
        if max_docs == -1:
            return True, ""

        current = self._count_documents()
        if current >= max_docs:
            plan_label = cfg["label"]
            return False, (
                f"Has alcanzado el límite de **{max_docs} documentos** del plan {plan_label}. "
                f"Actualmente tienes {current} documentos indexados. "
                f"Actualiza al plan Business para continuar."
            )
        return True, ""

    def check_user_limit(self) -> tuple[bool, str]:
        """
        Devuelve (True, "") si se puede crear un usuario más.
        Devuelve (False, mensaje) si se ha alcanzado el límite.
        """
        cfg = self.get_plan_config()
        max_users = cfg["max_users"]
        if max_users == -1:
            return True, ""

        current = self._count_users()
        if current >= max_users:
            plan_label = cfg["label"]
            return False, (
                f"Has alcanzado el límite de **{max_users} usuarios** del plan {plan_label}. "
                f"Actualmente tienes {current} usuarios registrados. "
                f"Actualiza al plan Business para continuar."
            )
        return True, ""

    # ── Info completa del plan (para el panel de admin) ───────────────────────

    def get_plan_info(self) -> dict:
        """
        Devuelve un dict con toda la info del plan actual + uso real.
        {
            "name":           "business",
            "label":          "Business",
            "color":          "#6366f1",
            "price":          "699 €/mes",
            "limits":         { max_documents, max_users, max_queries_day },
            "usage":          { documents, users },
            "pct_documents":  float (0-100),
            "pct_users":      float (0-100),
        }
        """
        name = self.get_current_plan_name()
        cfg  = self.get_plan_config(name)

        docs  = self._count_documents()
        users = self._count_users()

        def pct(current, limit):
            if limit == -1 or limit == 0:
                return 0.0
            return min(100.0, round(current / limit * 100, 1))

        return {
            "name":          name,
            "label":         cfg["label"],
            "color":         cfg["color"],
            "price":         cfg["price"],
            "limits": {
                "max_documents":   cfg["max_documents"],
                "max_users":       cfg["max_users"],
                "max_queries_day": cfg["max_queries_day"],
            },
            "usage": {
                "documents": docs,
                "users":     users,
            },
            "pct_documents": pct(docs,  cfg["max_documents"]),
            "pct_users":     pct(users, cfg["max_users"]),
        }

    def all_plans(self) -> dict:
        return PLANS


plan_service = PlanService()
