"""
demo/seed_demo.py
─────────────────
Popula el entorno Cortexa AI con datos de demostración:
  • 4 usuarios precreados con distintos roles y grupos
  • 3 grupos de trabajo: general, ventas, rrhh
  • Documentos PDF/TXT de muestra en cada grupo
  • Historial de chat simulado en la base de datos

Uso:
    cd /ruta/del/proyecto
    python demo/seed_demo.py

Requisitos: la app debe haberse ejecutado al menos una vez para crear las tablas.
"""

import os, sys, sqlite3, hashlib, textwrap
from pathlib import Path
from datetime import datetime, timedelta
import random

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH   = ROOT / "db" / "users.db"
MAIN_DB   = ROOT / "db" / "knowledge_base.db"
DATA_DIR  = ROOT / "data"

# ── Colores de consola ────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def log(msg, color=GREEN):
    print(f"{color}{msg}{RESET}")

# ── Helpers ───────────────────────────────────────────────────────────────────
def bcrypt_hash(password: str) -> str:
    """
    Genera hash bcrypt compatible con streamlit-authenticator.

    POST-AUDITORÍA · Eliminado el fallback SHA-256 sin salt: si bcrypt no está
    instalado, abortamos. Permitirlo dejaba contraseñas crackeables en
    milisegundos y, peor, hashes incompatibles con el resto de la app.
    """
    try:
        import bcrypt
    except ImportError:
        log("❌ bcrypt no instalado. Aborta el seed: instala las dependencias antes (pip install -r requirements.txt).", RED)
        sys.exit(2)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def ensure_tables():
    """Verifica que las tablas existan (la app debe haberse ejecutado antes)."""
    if not DB_PATH.exists():
        log(f"⚠️  {DB_PATH} no existe. Ejecuta la app primero para crear las tablas.", YELLOW)
        sys.exit(1)
    if not MAIN_DB.exists():
        log(f"⚠️  {MAIN_DB} no existe. Ejecuta la app primero para crear las tablas.", YELLOW)
        sys.exit(1)

# ── Demo users ────────────────────────────────────────────────────────────────
DEMO_USERS = [
    {
        "username":      "demo_admin",
        "name":          "Admin Demo",
        "email":         "admin@demo.cortexa",
        "password":      "Demo1234!",
        "role":          "admin",
        "workspaces":    "all",
        "can_upload":    1,
        "upload_groups": "all",
        "can_delete":    1,
        "delete_groups": "all",
        "temp_password": 0,
    },
    {
        "username":      "ana.ventas",
        "name":          "Ana García (Ventas)",
        "email":         "ana@demo.cortexa",
        "password":      "Ventas2024!",
        "role":          "editor",
        "workspaces":    "general,ventas",
        "can_upload":    1,
        "upload_groups": "ventas",
        "can_delete":    0,
        "delete_groups": "",
        "temp_password": 0,
    },
    {
        "username":      "carlos.rrhh",
        "name":          "Carlos López (RRHH)",
        "email":         "carlos@demo.cortexa",
        "password":      "RRHH2024!",
        "role":          "editor",
        "workspaces":    "general,rrhh",
        "can_upload":    1,
        "upload_groups": "rrhh",
        "can_delete":    0,
        "delete_groups": "",
        "temp_password": 0,
    },
    {
        "username":      "lucia.viewer",
        "name":          "Lucía Martínez",
        "email":         "lucia@demo.cortexa",
        "password":      "Viewer2024!",
        "role":          "viewer",
        "workspaces":    "general",
        "can_upload":    0,
        "upload_groups": "",
        "can_delete":    0,
        "delete_groups": "",
        "temp_password": 0,
    },
]

DEMO_GROUPS = ["general", "ventas", "rrhh"]

# ── Sample document texts ─────────────────────────────────────────────────────
SAMPLE_DOCS = [
    {
        "filename":   "politica_corporativa.txt",
        "workspace":  "general",
        "user":       "demo_admin",
        "summary":    "Política corporativa general de la empresa. Normas de conducta, uso de recursos y confidencialidad.",
        "content":    textwrap.dedent("""\
            POLÍTICA CORPORATIVA — VERSIÓN 2024
            ====================================

            1. CÓDIGO DE CONDUCTA
            Todos los empleados deben actuar con integridad, respeto y profesionalismo
            en sus relaciones con compañeros, clientes y proveedores.

            2. USO DE RECURSOS TECNOLÓGICOS
            Los sistemas informáticos de la empresa son para uso profesional.
            Queda prohibido el acceso a contenidos no relacionados con el trabajo.

            3. CONFIDENCIALIDAD
            Toda información de clientes, proyectos y estrategia es confidencial.
            Su divulgación sin autorización puede tener consecuencias disciplinarias.

            4. PROTECCIÓN DE DATOS (RGPD)
            La empresa cumple con el Reglamento General de Protección de Datos.
            Cualquier duda sobre tratamiento de datos personales debe dirigirse al DPO.

            5. POLÍTICA DE TELETRABAJO
            El teletrabajo está autorizado hasta 2 días semanales previa aprobación
            del responsable directo.
        """),
    },
    {
        "filename":   "manual_ventas_2024.txt",
        "workspace":  "ventas",
        "user":       "ana.ventas",
        "summary":    "Manual del equipo de ventas: proceso comercial, herramientas CRM y objetivos 2024.",
        "content":    textwrap.dedent("""\
            MANUAL DE VENTAS — 2024
            =======================

            PROCESO COMERCIAL
            -----------------
            1. Prospección: identificar leads cualificados en LinkedIn y ferias sectoriales.
            2. Primer contacto: llamada de 15 min para detectar necesidades.
            3. Demo del producto: máximo 45 min, centrada en el ROI del cliente.
            4. Propuesta: enviar en 48h tras la demo, personalizada por sector.
            5. Cierre: seguimiento semanal hasta decisión.

            HERRAMIENTAS
            ------------
            • CRM: Salesforce (registro obligatorio de todas las interacciones)
            • Email de ventas: plantillas en SharePoint > Ventas > Plantillas
            • Demos: Loom para grabaciones asíncronas

            OBJETIVOS 2024
            --------------
            • MRR objetivo: 150.000 € / mes (crecimiento 40% vs 2023)
            • CAC objetivo: < 1.200 €
            • Tasa de cierre: > 22%
            • NPS post-venta: > 45
        """),
    },
    {
        "filename":   "guia_onboarding_rrhh.txt",
        "workspace":  "rrhh",
        "user":       "carlos.rrhh",
        "summary":    "Guía de incorporación para nuevos empleados. Pasos del primer día, beneficios y formación.",
        "content":    textwrap.dedent("""\
            GUÍA DE ONBOARDING — NUEVOS EMPLEADOS
            ======================================

            ANTES DEL PRIMER DÍA
            • El manager envía email de bienvenida con accesos provisionales.
            • IT prepara el equipo y credenciales corporativas.
            • RRHH envía contrato y documentación por DocuSign.

            PRIMER DÍA
            • 09:00 – Recepción y tour por las instalaciones.
            • 10:00 – Reunión con RRHH: beneficios, políticas, herramientas.
            • 12:00 – Almuerzo con el equipo.
            • 14:00 – Configuración del entorno de trabajo con IT.
            • 16:00 – Primera reunión 1:1 con el manager.

            BENEFICIOS
            • Seguro médico privado (desde el mes 3).
            • Ticket restaurante: 11 €/día.
            • Formación: presupuesto de 1.500 €/año por empleado.
            • Horario flexible: entrada entre 8:00 y 10:00.
            • 23 días de vacaciones + festivos locales.

            FORMACIÓN OBLIGATORIA (primeros 30 días)
            1. Seguridad de la información (e-learning, 2h).
            2. Protección de datos RGPD (e-learning, 1h).
            3. Código de conducta (presencial, 3h).
        """),
    },
]

# ── Sample chat sessions ──────────────────────────────────────────────────────
SAMPLE_CHATS = [
    {
        "username": "ana.ventas",
        "title":    "Objetivos de ventas 2024",
        "messages": [
            ("user",      "¿Cuáles son los objetivos de MRR para 2024?"),
            ("assistant", "Según el Manual de Ventas 2024, el objetivo de MRR es **150.000 €/mes**, "
                          "lo que representa un crecimiento del **40%** respecto a 2023. "
                          "También se establece una tasa de cierre objetivo superior al 22% "
                          "y un CAC inferior a 1.200 €."),
            ("user",      "¿Qué herramientas CRM usamos?"),
            ("assistant", "El CRM corporativo es **Salesforce**. Es obligatorio registrar todas las "
                          "interacciones comerciales. Para grabaciones de demos asíncronas se usa Loom, "
                          "y las plantillas de email están disponibles en SharePoint > Ventas > Plantillas."),
        ]
    },
    {
        "username": "lucia.viewer",
        "title":    "Política de teletrabajo",
        "messages": [
            ("user",      "¿Cuántos días puedo teletrabajar a la semana?"),
            ("assistant", "Según la Política Corporativa 2024, el **teletrabajo está autorizado hasta "
                          "2 días semanales**, previa aprobación de tu responsable directo."),
        ]
    },
]

# ── Main seeder ───────────────────────────────────────────────────────────────
def seed():
    log(f"\n{BOLD}═══ Cortexa AI — Demo Seeder ═══{RESET}")
    ensure_tables()

    # 1. Users
    log("\n📦 Creando usuarios demo…", CYAN)
    conn_u = sqlite3.connect(DB_PATH)
    cur_u  = conn_u.cursor()
    for u in DEMO_USERS:
        existing = cur_u.execute("SELECT username FROM users WHERE username=?", (u["username"],)).fetchone()
        if existing:
            log(f"   ⏭  @{u['username']} ya existe — omitido", YELLOW)
            continue
        pwd_hash = bcrypt_hash(u["password"])
        cur_u.execute("""
            INSERT INTO users
              (username, name, email, password_hash, role, workspaces,
               can_upload, upload_groups, can_delete, delete_groups,
               created_at, temp_password)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            u["username"], u["name"], u["email"], pwd_hash, u["role"],
            u["workspaces"], u["can_upload"], u["upload_groups"],
            u["can_delete"], u["delete_groups"],
            datetime.now().isoformat(), u["temp_password"]
        ))
        log(f"   ✅ @{u['username']}  ({u['role']})  pwd: {u['password']}")
    conn_u.commit()
    conn_u.close()

    # 2. Groups / workspaces
    log("\n🗂️  Creando grupos demo…", CYAN)
    conn_m = sqlite3.connect(MAIN_DB)
    cur_m  = conn_m.cursor()
    # Ensure workspaces table exists (may not if app never ran fully)
    cur_m.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_by TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    """)
    for grp in DEMO_GROUPS:
        existing_grp = cur_m.execute("SELECT name FROM workspaces WHERE name=?", (grp,)).fetchone()
        if existing_grp:
            log(f"   ⏭  Grupo '{grp}' ya existe — omitido", YELLOW)
        else:
            cur_m.execute("INSERT INTO workspaces (name, created_by, created_at) VALUES (?,?,?)",
                          (grp, "demo_admin", datetime.now().isoformat()))
            log(f"   ✅ Grupo '{grp}' creado")
    conn_m.commit()

    # 3. Sample documents (text files + DB records)
    log("\n📄 Creando documentos de muestra…", CYAN)
    DATA_DIR.mkdir(exist_ok=True)
    cur_m.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            user TEXT,
            upload_date TEXT,
            chunk_count INTEGER DEFAULT 0,
            query_count INTEGER DEFAULT 0,
            workspace TEXT DEFAULT 'general',
            summary TEXT DEFAULT ''
        )
    """)
    for doc in SAMPLE_DOCS:
        # Write text file to data/
        fpath = DATA_DIR / doc["filename"]
        fpath.write_text(doc["content"], encoding="utf-8")

        # Insert into documents table
        existing_doc = cur_m.execute("SELECT filename FROM documents WHERE filename=?", (doc["filename"],)).fetchone()
        if existing_doc:
            log(f"   ⏭  '{doc['filename']}' ya existe en DB — omitido", YELLOW)
        else:
            qcount = random.randint(3, 25)
            cur_m.execute("""
                INSERT INTO documents (filename, user, upload_date, chunk_count, query_count, workspace, summary)
                VALUES (?,?,?,?,?,?,?)
            """, (
                doc["filename"], doc["user"],
                (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                random.randint(4, 18), qcount,
                doc["workspace"], doc["summary"]
            ))
            log(f"   ✅ '{doc['filename']}' → grupo '{doc['workspace']}'")
    conn_m.commit()

    # 4. Sample chat history
    log("\n💬 Creando historial de chat de muestra…", CYAN)
    cur_m.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            title TEXT DEFAULT 'Conversación',
            created_at TEXT
        )
    """)
    cur_m.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            username TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)
    for chat in SAMPLE_CHATS:
        cur_m.execute(
            "INSERT INTO chat_sessions (username, title, created_at) VALUES (?,?,?)",
            (chat["username"], chat["title"],
             (datetime.now() - timedelta(days=random.randint(1, 7))).isoformat())
        )
        session_id = cur_m.lastrowid
        base_ts = datetime.now() - timedelta(hours=random.randint(1, 48))
        for j, (role, content) in enumerate(chat["messages"]):
            msg_ts = (base_ts + timedelta(minutes=j * 2)).isoformat()
            cur_m.execute(
                "INSERT INTO chat_history (session_id, username, role, content, timestamp) VALUES (?,?,?,?,?)",
                (session_id, chat["username"], role, content, msg_ts)
            )
        log(f"   ✅ Sesión '{chat['title']}' para @{chat['username']} ({len(chat['messages'])} mensajes)")
    conn_m.commit()
    conn_m.close()

    # 5. Brand settings
    log("\n🎨 Configurando marca demo…", CYAN)
    conn_s = sqlite3.connect(DB_PATH)
    cur_s  = conn_s.cursor()
    cur_s.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_by TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)
    demo_settings = {
        "product_name":     "Cortexa AI",
        "company_name":     "Acme Corp (Demo)",
        "welcome_title":    "Base de conocimiento corporativo",
        "welcome_subtitle": "100% local. Tus datos no salen de tu organización.",
    }
    for k, v in demo_settings.items():
        cur_s.execute("""
            INSERT INTO settings (key, value, updated_by, updated_at)
            VALUES (?,?,?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (k, v, "demo_admin", datetime.now().isoformat()))
    conn_s.commit()
    conn_s.close()
    log("   ✅ Ajustes de marca configurados")

    # ── Summary ───────────────────────────────────────────────────────────────
    log(f"\n{BOLD}{'═'*45}", CYAN)
    log("✅  Demo seeded correctamente!", GREEN)
    log(f"{'═'*45}{RESET}", CYAN)
    print()
    print("  Usuarios creados:")
    for u in DEMO_USERS:
        print(f"    {'🔐' if u['role'] == 'admin' else '👤'}  @{u['username']:<20} pwd: {u['password']}")
    print()
    print("  Grupos: " + ", ".join(DEMO_GROUPS))
    print("  Documentos: " + ", ".join(d["filename"] for d in SAMPLE_DOCS))
    print()
    log("  ▶  Arranca la app:  streamlit run app.py", CYAN)
    print()


if __name__ == "__main__":
    seed()
