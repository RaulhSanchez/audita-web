# AuditaWeb

Herramienta de auditoría web automática orientada a PYMEs españolas. Analiza cualquier URL y genera un informe PDF profesional con hallazgos técnicos, impacto de negocio en lenguaje claro y un plan de acción priorizado. Diseñada como lead magnet para servicios de desarrollo web freelance.

**Demo:** https://raulhsanchez.github.io/audita-web  
**API:** https://audita-web-api.onrender.com

---

## Qué hace

1. El usuario introduce una URL y su email en el formulario
2. El API lanza el pipeline de análisis en segundo plano:
   - Descarga el HTML y mide TTFB y peso de página
   - Ejecuta 8 runners de comprobación en paralelo (SEO, seguridad, móvil, legal, rendimiento, social…)
   - Opcionalmente ejecuta Lighthouse para métricas de rendimiento y accesibilidad
   - Genera una narrativa de negocio en español con IA (Gemini 1.5 Flash)
   - Persiste el resultado en PostgreSQL
   - Genera un PDF de 4 páginas con Puppeteer
   - Envía el PDF por email al usuario (Resend)
   - Registra el lead en Formspree y notifica por Telegram
3. El resultado también es visible en la web en tiempo real

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Monorepo | pnpm workspaces + Turborepo |
| API | NestJS 11, TypeScript, Node 18 |
| Base de datos | PostgreSQL (Neon serverless) + Prisma 5 |
| IA narrativa | Google Gemini 1.5 Flash (fallback: Ollama llama3.2) vía LangChain |
| PDF | Puppeteer + @sparticuz/chromium-min + Handlebars |
| Auditoría | Lighthouse 13 + 8 runners custom |
| Email | Resend HTTP API |
| Frontend | Next.js 15, React 19, Tailwind CSS 4 (static export) |
| Despliegue API | Render (free tier) |
| Despliegue web | GitHub Pages |
| CI/CD | GitHub Actions |

---

## Estructura del proyecto

```
audita-web/
├── apps/
│   ├── api/                        # Backend NestJS
│   │   ├── prisma/
│   │   │   ├── schema.prisma       # Modelos: Audit, Lead, FindingCatalog
│   │   │   └── seed.ts             # 39 entradas del catálogo de hallazgos
│   │   └── src/
│   │       └── modules/
│   │           ├── audit/          # Controlador principal y pipeline
│   │           ├── checks/
│   │           │   ├── aggregator/ # Orquesta todos los runners
│   │           │   └── runners/    # 8 runners de comprobación
│   │           ├── narrative/      # Narrativa IA con LangChain
│   │           ├── pdf/            # Generación de PDF con Puppeteer
│   │           │   └── templates/report.hbs
│   │           ├── notifications/  # MailService (Resend)
│   │           ├── telegram/       # Notificaciones Telegram
│   │           └── queue/          # Cola local asíncrona
│   └── web/                        # Frontend Next.js
│       └── app/
│           ├── page.tsx            # Home con formulario de auditoría
│           └── report/             # Vista de resultados
├── packages/
│   ├── shared/                     # Tipos TypeScript compartidos
│   ├── ui/                         # Componentes React base
│   ├── eslint-config/
│   └── typescript-config/
├── .github/workflows/
│   ├── deploy-web.yml              # Build y deploy a GitHub Pages
│   └── ci-api.yml                  # Lint y build check del API
├── render.yaml                     # Configuración de despliegue en Render
└── turbo.json
```

---

## Runners de auditoría

Cada runner implementa la interfaz `CheckRunner` y devuelve un array de `Finding` con código, severidad y evidencia real extraída del HTML/cabeceras.

| Runner | Categoría | Qué comprueba |
|--------|-----------|---------------|
| `LighthouseRunner` | performance / seo / accessibility | Delega en Lighthouse 13; extrae scores y hallazgos |
| `SeoRunner` | seo | Title (texto y longitud), meta description, H1, idioma, imágenes sin alt |
| `SeoAdvancedRunner` | seo | Canonical, Schema.org, robots.txt, sitemap.xml |
| `SecurityRunner` | security | HTTPS, contenido mixto, cabeceras de seguridad (HSTS, CSP, XFO, XCTO), Server header expuesto |
| `MobileRunner` | mobile | Viewport, tel: links, WhatsApp, tamaños de fuente pequeños |
| `SocialRunner` | social | Open Graph (title, image), favicon, CTA, redes sociales, Google Maps, formulario de contacto |
| `LegalRunner` | legal | Banner de cookies (RGPD), política de privacidad, aviso legal |
| `PerformanceRunner` | performance | TTFB > 1500 ms, HTML > 500 KB, más de 15 scripts externos |

**Severidades:** `critical` → `high` → `medium` → `low`

El `AggregatorService` mide el TTFB real con `Date.now()`, pasa el contexto a todos los runners en paralelo con `Promise.all`, calcula las puntuaciones por área penalizando por hallazgos y devuelve `{ findings, scores, globalScore, pageStats }`.

---

## Pipeline de auditoría

```
POST /api/audits
       │
       ▼
  Crear registro en DB (status: pending)
  Notificar Telegram + registrar en Formspree
       │
       ▼ (cola asíncrona)
  [1] AggregatorService.runAll()
        ├─ fetch HTML + medir TTFB
        ├─ Lighthouse (opcional, omitido si PUPPETEER_SKIP_DOWNLOAD=true)
        └─ 8 runners en paralelo
       │
       ▼
  [2] NarrativeService.generate()
        ├─ Gemini 1.5 Flash (si GEMINI_API_KEY presente)
        └─ Ollama llama3.2 (fallback local)
       │
       ▼
  [3] Persistir en DB (status: done) ← resultado visible desde aquí
       │
       ▼
  [4] PdfService.generate()
        ├─ Handlebars → HTML
        └─ Puppeteer → PDF A4 (4 páginas)
       │
       ▼
  [5] MailService.send() — PDF adjunto vía Resend
```

---

## PDF generado

El informe tiene 4 páginas:

1. **Portada** — Puntuación global, tiempo de respuesta, peso de página y número de problemas
2. **Resumen ejecutivo** — Stats técnicas, contadores por severidad, puntuaciones por área y narrativa IA
3. **Hallazgos detallados** — Cada problema con chips de evidencia real (valores detectados), por qué importa para el negocio y cómo solucionarlo
4. **Plan de acción** — Lista priorizada de problemas críticos y altos numerados, más mejoras medias recomendadas
5. **CTA** — Página de cierre con contacto del desarrollador

---

## Variables de entorno

### API (`apps/api`)

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL` | Sí | Connection string de PostgreSQL (Neon) |
| `RESEND_API_KEY` | Sí | API key de Resend para envío de emails |
| `RESEND_FROM` | No | Dirección de envío. Default: `AuditaWeb <noreply@zero2dev.es>` |
| `FRONTEND_BASE_URL` | Sí | URL del frontend. Ej: `https://raulhsanchez.github.io/audita-web` |
| `GEMINI_API_KEY` | Recomendada | API key de Google Gemini para narrativa IA |
| `TELEGRAM_BOT_TOKEN` | No | Token del bot de Telegram para notificaciones |
| `TELEGRAM_CHAT_ID` | No | Chat ID de destino para las notificaciones |
| `FORMSPREE_FORM_ID` | No | ID del formulario Formspree. Default: `xykojvky` |
| `PUPPETEER_SKIP_DOWNLOAD` | Render | Usar `chromium-min` en lugar de Puppeteer completo. Poner `true` en Render |
| `PUPPETEER_CACHE_DIR` | Render | Directorio de caché de Chromium. Ej: `/opt/render/.cache/puppeteer` |
| `REPORTS_DIR` | No | Directorio donde se guardan los PDFs. Default: `./reports` |
| `OLLAMA_BASE_URL` | No | URL del servidor Ollama (fallback IA). Default: `http://localhost:11434` |
| `OLLAMA_MODEL` | No | Modelo Ollama a usar. Default: `llama3.2` |

### Frontend (`apps/web`)

| Variable | Descripción |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | URL base del API. Configura como secret en GitHub Actions |

---

## Desarrollo local

### Requisitos

- Node 18+
- pnpm 9
- PostgreSQL (o cuenta en [Neon](https://neon.tech))
- Opcional: cuenta Gemini, Resend, Telegram

### Instalación

```bash
git clone https://github.com/RaulhSanchez/audita-web.git
cd audita-web
pnpm install
```

### Configuración

Crea `apps/api/.env` con el siguiente contenido:

```env
DATABASE_URL=postgresql://user:password@host/dbname
RESEND_API_KEY=re_xxxxx
GEMINI_API_KEY=AIzaSy_xxxxx
FRONTEND_BASE_URL=http://localhost:3000
```

Aplica las migraciones y carga el catálogo de hallazgos:

```bash
cd apps/api
npx prisma migrate deploy
npx ts-node prisma/seed.ts
```

### Arrancar en desarrollo

```bash
# Desde la raíz — arranca API (puerto 3001) y web (puerto 3000) en paralelo
pnpm dev

# Solo el API
pnpm --filter api dev

# Solo la web
pnpm --filter web dev
```

---

## Despliegue

### API — Render

El fichero `render.yaml` configura el servicio automáticamente. Las variables marcadas como `sync: false` hay que añadirlas manualmente en el dashboard de Render:

- `DATABASE_URL`
- `RESEND_API_KEY`
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
- `FRONTEND_BASE_URL`

> **Nota:** En Render free tier Lighthouse está deshabilitado (`PUPPETEER_SKIP_DOWNLOAD=true`). El PDF se genera con `@sparticuz/chromium-min` que descarga Chromium comprimido (~50 MB) en runtime desde GitHub Releases.

### Web — GitHub Pages

1. Activa GitHub Pages en el repositorio (Settings → Pages → GitHub Actions)
2. Añade el secret `NEXT_PUBLIC_API_URL` en Settings → Secrets → Actions con la URL de tu API en Render
3. Cada push a `main` que toque `apps/web/**` lanza el workflow `deploy-web.yml` automáticamente

---

## Modelos de base de datos

```prisma
model Audit {
  id          String   @id @default(cuid())
  url         String
  domain      String
  email       String?
  status      String   @default("pending")  // pending | running | done | failed
  globalScore Int?
  scores      String?  // JSON: { performance, seo, security, accessibility, mobile }
  findings    String?  // JSON: Finding[]
  narrative   String?
  publicSlug  String   @unique
  createdAt   DateTime @default(now())
}

model FindingCatalog {
  code           String @id   // Ej: SEO_NO_TITLE, SEC_NO_HTTPS
  category       String       // seo | security | mobile | legal | social | performance
  severity       String       // critical | high | medium | low
  titleEs        String
  descriptionEs  String
  businessImpact String
  fixSuggestion  String
}
```

---

## Catálogo de hallazgos (39 códigos)

| Área | Códigos |
|------|---------|
| **Rendimiento** | `PERF_SCORE_LOW`, `PERF_SCORE_MED`, `PERF_LCP_HIGH`, `PERF_TTFB_HIGH`, `PERF_PAGE_HEAVY`, `PERF_TOO_MANY_SCRIPTS` |
| **SEO** | `SEO_NO_TITLE`, `SEO_NO_META_DESC`, `SEO_NO_H1`, `SEO_MULTIPLE_H1`, `SEO_TITLE_LENGTH`, `SEO_IMG_NO_ALT`, `SEO_NO_CANONICAL`, `SEO_NO_SITEMAP`, `SEO_NO_ROBOTS`, `SEO_NO_SCHEMA`, `SEO_NO_LANG`, `SEO_META_DESC_LENGTH` |
| **Seguridad** | `SEC_NO_HTTPS`, `SEC_NO_HSTS`, `SEC_NO_CSP`, `SEC_NO_XCTO`, `SEC_NO_XFO`, `SEC_MIXED_CONTENT`, `SEC_SERVER_EXPOSED` |
| **Móvil** | `MOB_NO_VIEWPORT`, `MOB_NO_TEL_LINK`, `MOB_NO_WHATSAPP`, `MOB_FONT_SMALL` |
| **Legal** | `LEG_NO_COOKIE_BANNER`, `LEG_NO_LEGAL`, `LEG_NO_PRIVACY` |
| **Social / Captación** | `SOC_NO_OG_TITLE`, `SOC_NO_OG_IMAGE`, `SOC_NO_FAVICON`, `SOC_NO_CTA`, `SOC_NO_SOCIAL_PROFILES`, `SOC_NO_GOOGLE_MAPS`, `SOC_NO_CONTACT_FORM` |

Cada código tiene en base de datos: título en español, descripción técnica, impacto de negocio y sugerencia de corrección.

---

## Autor

**Raúl Huete** — Arquitecto de Software freelance  
[zero2dev.es](https://zero2dev.es) · 92sanchez.raul@gmail.com
