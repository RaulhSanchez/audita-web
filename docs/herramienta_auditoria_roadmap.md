# Herramienta de Auditoría Web — Roadmap Técnico

> Lead magnet construido como prueba pública de tu capacidad técnica. Diseñado para tu stack real (NestJS, Node, IA con Ollama/LangChain). Pensado para llegar a un MVP funcional en 1-2 fines de semana.

---

## 1. Visión del producto

**Qué es**: una web pública (`auditatuwebfuenlabrada.es` o similar) donde cualquier dueño de PYME pega la URL de su web, deja un email, y recibe un PDF profesional con:

- Una **nota global** (0-100) sobre 5 ejes (rendimiento, SEO, móvil, accesibilidad, seguridad/legal)
- **10-15 hallazgos concretos** ordenados por impacto en negocio
- **Explicación en lenguaje no técnico** de cada hallazgo (qué pasa, qué pierde por eso, cómo se arregla)
- Un **plan de acción priorizado** que termina con CTA hacia tu Calendly

**Qué NO es**: un Lighthouse glorificado. Lo que diferencia tu herramienta es la **capa de IA que traduce hallazgos técnicos a lenguaje de empresario**.

**Por qué funciona estratégicamente**:
- Demuestra tu stack en acción (NestJS + IA + arquitectura limpia)
- Es prueba pública de tu posicionamiento ("IA aplicada que entiende negocio")
- Genera leads cualificados que ya vieron lo que sabes hacer
- Se publica como repo en tu GitHub → portfolio activo

---

## 2. Flujos principales

### Flujo 1 — Auditoría pública (el principal)

```
Usuario llega a landing
   │
   ▼
Pega URL de su web + email
   │
   ▼
[Backend] Crea Audit en estado "pending"
   │
   ▼
[Backend] Encola job en BullMQ
   │
   ▼
[Worker] Ejecuta pipeline: Lighthouse + checks custom + scraping
   │
   ▼
[Worker] Pasa hallazgos a IA (LangChain) → narración business-friendly
   │
   ▼
[Worker] Renderiza PDF (Puppeteer + template)
   │
   ▼
[Worker] Sube PDF a Cloudflare R2, guarda URL pública
   │
   ▼
[Worker] Envía email con Resend + notifica a Raúl en Telegram
   │
   ▼
Usuario abre PDF en email + accede a URL pública compartible
```

Tiempo total objetivo: **< 90 segundos** desde envío hasta email recibido.

### Flujo 2 — Auditoría desde cold email (modo Raúl)

CLI interno (`pnpm audit https://gestoria-x.es`) que dispara el pipeline saltándose el formulario. Útil para enviar PDFs como gancho en tu prospección outbound.

### Flujo 3 — Compartir auditoría

Cada audit tiene URL pública `auditatuwebfuenlabrada.es/i/[uuid]` con:
- Preview HTML del informe (no solo el PDF)
- Open Graph tags personalizados → preview rico en WhatsApp/LinkedIn
- Botón "Audita la tuya" → tráfico viral

### Flujo 4 — Lead capture loop

```
Lead llega → guardado en DB
   ↓
Notif Telegram a Raúl con preview del informe
   ↓
Sync automático con Notion (CRM)
   ↓
Si en 48h no agenda → email follow-up automático
   ↓
Si en 7d no agenda → entra en secuencia drip mensual
```

---

## 3. Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                       CLOUDFLARE / DNS                       │
│                  auditatuwebfuenlabrada.es                   │
└──────────────────┬──────────────────────────┬───────────────┘
                   │                          │
                   ▼                          ▼
        ┌──────────────────────┐   ┌──────────────────────┐
        │   FRONTEND (Vercel)  │   │  BACKEND (Railway)   │
        │   Next.js App Router │◄──┤  NestJS + BullMQ     │
        │   Tailwind + shadcn  │   │  REST + WS opcional  │
        └──────────┬───────────┘   └──────────┬───────────┘
                   │                          │
                   │                          ├──► PostgreSQL (Neon)
                   │                          ├──► Redis (Upstash)
                   │                          ├──► Resend (email)
                   │                          ├──► Cloudflare R2 (PDFs)
                   │                          ├──► PageSpeed API
                   │                          └──► Claude/Gemini/Ollama
                   │
                   ▼
            Usuarios finales
```

**Por qué este stack** (decisiones razonadas):

| Decisión | Razón |
|----------|-------|
| **Next.js en lugar de Angular** | Vercel deploy gratis, App Router maduro, SEO server-side de fábrica, ecosistema masivo para landings |
| **NestJS backend** | Tu stack core, módulos limpios, BullMQ integración nativa, escalable cuando llegue tráfico |
| **PostgreSQL (Neon)** | Free tier real, branching para desarrollo, escala. Mongo no aporta aquí (datos relacionales) |
| **Redis (Upstash)** | Free tier, BullMQ necesita Redis, serverless = sin DevOps |
| **BullMQ vs ejecución sync** | Auditoría tarda 30-90s, no puedes bloquear HTTP. Queue es obligatoria. |
| **Cloudflare R2** | S3-compatible, 10GB gratis, sin egress fees |
| **Resend** | API limpia, 3000 mails/mes gratis, deliverability real |
| **Puppeteer para PDF** | Eres dev, HTML/CSS es lo más rápido para iterar diseño del informe |
| **Claude/Gemini API en MVP, Ollama en V3** | Empieza con API (rápido, barato), migra a local cuando el coste lo justifique y para reforzar tu posicionamiento "sin OpenAI" |
| **Plausible para analytics** | Sin cookies, sin GDPR, comparte públicamente las métricas (autoridad) |

---

## 4. Modelo de datos

```sql
-- Auditorías
CREATE TABLE audits (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url           TEXT NOT NULL,
  domain        TEXT NOT NULL,                -- extraído de url para agrupar
  sector        TEXT,                         -- detectado o seleccionado: gestoria, dental, taller...
  zona          TEXT,                         -- detectada o seleccionada
  status        TEXT NOT NULL,                -- pending | running | done | failed
  global_score  INTEGER,                      -- 0-100
  scores        JSONB,                        -- { performance: 67, seo: 42, mobile: 81, ... }
  findings      JSONB,                        -- array de hallazgos estructurados
  narrative     TEXT,                         -- texto generado por IA
  pdf_url       TEXT,                         -- URL pública en R2
  public_slug   TEXT UNIQUE,                  -- /i/[slug]
  created_at    TIMESTAMPTZ DEFAULT now(),
  completed_at  TIMESTAMPTZ,
  lead_id       UUID REFERENCES leads(id),
  source        TEXT                          -- 'web' | 'cli' | 'partner'
);

-- Leads
CREATE TABLE leads (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL,
  name            TEXT,
  phone           TEXT,
  company         TEXT,
  first_audit_id  UUID,
  audit_count     INTEGER DEFAULT 0,
  source_channel  TEXT,                       -- 'linkedin' | 'direct' | 'partner_x' | 'cold_email'
  status          TEXT DEFAULT 'new',         -- new | contacted | meeting_booked | client | lost
  notes           TEXT,
  notion_id       TEXT,                       -- sync con tu CRM
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audits_domain ON audits(domain);
CREATE INDEX idx_audits_sector_score ON audits(sector, global_score);
CREATE INDEX idx_leads_email ON leads(email);

-- Hallazgos individuales (denormalizado para SEO programmatic)
CREATE TABLE finding_catalog (
  code              TEXT PRIMARY KEY,         -- e.g. 'OG_IMAGE_BROKEN'
  category          TEXT NOT NULL,            -- seo | perf | mobile | a11y | legal
  severity          TEXT NOT NULL,            -- critical | high | medium | low
  title_es          TEXT NOT NULL,
  description_es    TEXT NOT NULL,
  business_impact   TEXT NOT NULL,            -- "Pierdes X clics cuando se comparte por WhatsApp"
  fix_suggestion    TEXT NOT NULL
);
```

El **catálogo de hallazgos** es central: cada chequeo del pipeline mapea a un `code`. La IA narra usando los textos del catálogo + contexto específico de esa web.

---

## 5. Backend NestJS — módulos

```
apps/api/src/
├── app.module.ts
├── main.ts
├── modules/
│   ├── audit/
│   │   ├── audit.module.ts
│   │   ├── audit.controller.ts        # POST /api/audits, GET /api/audits/:id
│   │   ├── audit.service.ts           # crea, encola, consulta
│   │   ├── audit.processor.ts         # @Processor BullMQ
│   │   ├── dto/
│   │   │   ├── create-audit.dto.ts
│   │   │   └── audit-result.dto.ts
│   │   └── audit.entity.ts
│   ├── checks/
│   │   ├── checks.module.ts
│   │   ├── lighthouse.runner.ts       # ejecuta Lighthouse
│   │   ├── pagespeed.runner.ts        # PageSpeed API fallback
│   │   ├── seo.runner.ts              # meta tags, OG, structured data
│   │   ├── legal.runner.ts            # GDPR, cookies, aviso legal
│   │   ├── security.runner.ts         # HTTPS, headers, CSP
│   │   ├── content.runner.ts          # textos, lang, alt images
│   │   └── aggregator.service.ts      # consolida findings
│   ├── narrative/
│   │   ├── narrative.module.ts
│   │   ├── narrative.service.ts       # orquesta LangChain
│   │   ├── prompts/
│   │   │   ├── system.prompt.ts
│   │   │   └── finding.prompt.ts
│   │   └── providers/
│   │       ├── claude.provider.ts     # MVP
│   │       ├── gemini.provider.ts     # alternativa
│   │       └── ollama.provider.ts     # V3
│   ├── pdf/
│   │   ├── pdf.module.ts
│   │   ├── pdf.service.ts             # Puppeteer
│   │   └── templates/
│   │       └── report.hbs             # Handlebars HTML template
│   ├── storage/
│   │   └── r2.service.ts              # upload + signed URLs
│   ├── leads/
│   │   ├── leads.module.ts
│   │   ├── leads.service.ts           # dedupe, scoring, sync Notion
│   │   └── notion.service.ts
│   ├── notifications/
│   │   ├── notifications.module.ts
│   │   ├── email.service.ts           # Resend wrapper
│   │   └── telegram.service.ts        # tu notif personal
│   └── public/
│       ├── public.controller.ts       # GET /i/:slug
│       └── public.service.ts
└── common/
    ├── guards/
    ├── interceptors/
    └── filters/
```

**Endpoints expuestos**:

| Método | Ruta | Propósito |
|--------|------|-----------|
| `POST` | `/api/audits` | Crea audit, devuelve `{id, slug, status}` |
| `GET`  | `/api/audits/:id` | Polling de estado (o usar SSE en V2) |
| `GET`  | `/api/audits/:id/pdf` | Redirige al PDF en R2 |
| `GET`  | `/i/:slug` | Página HTML pública del informe |
| `POST` | `/api/audits/:id/share` | Genera link de compartir |
| `GET`  | `/api/stats/sectors` | Datos públicos por sector (programmatic SEO) |
| `POST` | `/api/webhooks/resend` | Tracking de aperturas |

---

## 6. Pipeline de auditoría — qué se evalúa exactamente

El valor del producto está aquí. **40+ checks** organizados en 5 categorías. Cada check produce un finding con `code`, `severity` y `evidence`.

### A. Rendimiento (10 checks)
- Lighthouse Performance score
- LCP (Largest Contentful Paint) < 2.5s
- CLS (Cumulative Layout Shift) < 0.1
- TBT (Total Blocking Time) < 200ms
- Tamaño total del HTML
- Número de requests
- Imágenes sin optimizar (peso > 200KB sin webp/avif)
- Imágenes sin lazy loading
- Fuentes sin `font-display: swap`
- CDN detectado (Cloudflare, Fastly, etc.) o ausencia

### B. SEO (10 checks)
- Title tag presente, longitud 30-60 chars
- Meta description 120-160 chars
- H1 único en la página
- Estructura jerárquica H1 > H2 > H3
- Atributos `alt` en imágenes
- URL en formato amigable
- Sitemap.xml presente
- robots.txt presente y válido
- Schema.org structured data (LocalBusiness, Organization)
- Canonical tag

### C. Móvil y UX (8 checks)
- Viewport meta tag
- Tamaño de fuente legible (>= 16px)
- Touch targets >= 48px
- Sin scroll horizontal en móvil
- Lighthouse Mobile-Friendly
- WhatsApp/Tel links clicables en móvil
- Formularios usables en móvil (inputmode, autocomplete)
- Imagen hero adaptada a móvil

### D. Seguridad y legal (7 checks)
- HTTPS obligatorio (cero links http)
- Certificado válido y no próximo a expirar
- Headers: `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`
- Cookie banner GDPR-compliant detectado
- Aviso legal accesible
- Política de privacidad accesible
- Formularios con consentimiento explícito

### E. Captación y redes sociales (7 checks)
- Open Graph tags completos y válidos
- Open Graph image accesible (URL no rota)
- Twitter Card tags
- Favicon presente y de calidad
- Botones de contacto destacados (teléfono, WhatsApp)
- Formulario de contacto funcional
- CTAs por encima del fold

### F. Específicos por sector (V2)
Cuando el sector está detectado, se añaden checks de nicho:

- **Gestorías**: área cliente, formulario de cita, descarga de docs, calculadoras
- **Dentales**: reservas online, urgencias 24h funcional, fotos antes/después
- **Restaurantes**: menú actualizado, reservas online, mapa, horarios visibles
- **Talleres**: presupuesto online, WhatsApp Business, especialidades

### Implementación técnica de los checks

```typescript
// Cada check implementa esta interfaz
export interface CheckRunner {
  code: string;                  // referencia al catálogo
  category: Category;
  run(ctx: CheckContext): Promise<Finding | null>;
}

export interface CheckContext {
  url: string;
  html: string;                  // HTML completo
  dom: Document;                 // DOM parseado (jsdom)
  lighthouse: LighthouseResult;  // resultado completo Lighthouse
  headers: Headers;              // headers HTTP
  screenshots: Screenshots;      // desktop + mobile
}

export interface Finding {
  code: string;
  severity: Severity;
  evidence: Record<string, unknown>;  // datos específicos para narración
}
```

El `AggregatorService` ejecuta todos los runners en paralelo (Promise.all con timeout individual), recoge findings y calcula scores ponderados por categoría.

---

## 7. La capa IA — narración business-friendly

Esto es **el diferencial real** del producto. Sin esta capa eres un Lighthouse más.

### Diseño

Por cada finding del catálogo, la IA genera 3 piezas:
1. **Title**: titular gancho ("Estás perdiendo clientes en WhatsApp sin saberlo")
2. **Story**: 2-3 frases explicando el problema en lenguaje de dueño de PYME
3. **Action**: qué hacer concretamente, traducido a esfuerzo + impacto

### Prompt arquitectónico

```
SYSTEM:
Eres un consultor que explica problemas técnicos de webs a dueños de PYMES
españolas que NO son técnicos. Tu trabajo es traducir hallazgos de Lighthouse
y auditoría SEO a impacto concreto en negocio. Hablas claro, sin tecnicismos,
en castellano de España. Cada hallazgo se traduce en términos de:
- Clientes perdidos / oportunidades perdidas
- Tiempo perdido / ineficiencia
- Riesgo legal o reputacional

NUNCA uses palabras como "stack", "framework", "CDN", "viewport". Si tienes
que mencionar algo técnico, lo describes en español llano.

USER:
Web auditada: {url}
Sector detectado: {sector}
Hallazgo: {finding_code}
Evidencia técnica: {evidence_json}
Catálogo: {catalog_entry}

Genera JSON con:
{
  "title": "...",          // máx 60 chars
  "story": "...",          // 2-3 frases, máx 200 chars
  "action": "...",         // 1 frase, qué hacer
  "effort": "low|med|high",
  "impact": "low|med|high"
}
```

### Estrategia multimodelo

```typescript
// providers intercambiables
interface NarrativeProvider {
  generate(finding: Finding, ctx: AuditContext): Promise<Narrative>;
}

// MVP: Claude Haiku (rápido + barato)
// Backup: Gemini Flash (más barato aún)
// V3: Ollama local (qwen2.5:14b o llama3.1:8b) - tu posicionamiento

@Injectable()
export class NarrativeService {
  constructor(
    @Inject(NARRATIVE_PROVIDER) private provider: NarrativeProvider,
  ) {}
  // ...
}
```

**Coste estimado MVP**: ~0,02€ por auditoría completa con Claude Haiku (15 findings × ~500 tokens output). 1000 auditorías = 20€/mes. Asumible.

**Razón para migrar a Ollama en V3**: no por coste sino por **mensaje**. Cuando vendas a una gestoría, demostrar la herramienta funcionando 100% en local refuerza tu pitch "sin filtrar datos a OpenAI". Tu producto se convierte en demo de tu servicio.

---

## 8. El PDF — el activo viral

### Diseño del informe

8-12 páginas:

1. **Portada**: logo del cliente + URL + score grande + fecha
2. **Resumen ejecutivo**: 5 puntos clave en lenguaje claro
3. **Score por categoría**: gráfico radar
4. **Top 3 problemas críticos**: 1 página cada uno con story + action + estimación de impacto
5. **El resto de hallazgos**: tabla compacta
6. **Plan de acción priorizado**: matriz esfuerzo vs impacto
7. **Próximo paso**: CTA grande hacia tu Calendly + QR

### Implementación

```typescript
@Injectable()
export class PdfService {
  async generate(audit: Audit): Promise<Buffer> {
    const html = await this.renderTemplate('report', audit);
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle0' });
    const pdf = await page.pdf({
      format: 'A4',
      printBackground: true,
      margin: { top: '20mm', right: '15mm', bottom: '20mm', left: '15mm' },
      displayHeaderFooter: true,
      footerTemplate: this.footerHtml(audit),
    });
    await browser.close();
    return pdf;
  }
}
```

**Branding** en footer de cada página:
```
Auditoría generada el {{date}} por Raúl Huete · raulhuete.es · +34 XXX XXX XXX
[QR pequeño a la derecha → tu Calendly]
```

---

## 9. Frontend Next.js — qué se construye

### Páginas

```
app/
├── (marketing)/
│   ├── page.tsx                       # Landing principal
│   ├── sectores/
│   │   └── [sector]/page.tsx          # SSG por sector (programmatic SEO)
│   ├── zonas/
│   │   └── [zona]/page.tsx            # SSG por zona
│   ├── como-funciona/page.tsx
│   ├── blog/
│   │   ├── page.tsx
│   │   └── [slug]/page.tsx
│   └── precios/page.tsx               # opcional, V2
├── i/
│   └── [slug]/page.tsx                # Informe público con OG dinámico
├── api/
│   └── (proxy a backend)
└── layout.tsx
```

### Landing — secciones

1. **Hero**: 1 input grande (URL) + botón "Audita gratis"
2. **Cómo funciona**: 3 pasos visuales
3. **Qué encontramos**: muestra 3-4 ejemplos de hallazgos reales (anonimizados)
4. **Por qué confiar**: tu foto + breve bio + GitHub link
5. **Casos**: 2-3 informes públicos como ejemplos
6. **FAQ**
7. **CTA final**

### Página de informe público (`/i/[slug]`)

- SSR con `generateMetadata` para OG image dinámico
- Misma información que el PDF pero en HTML interactivo
- Botón "Audita la tuya" siempre visible
- Botón "Compartir" con link prefijado

### Programmatic SEO

```typescript
// app/sectores/[sector]/page.tsx
export async function generateStaticParams() {
  return ['gestorias', 'clinicas-dentales', 'talleres-mecanicos', ...]
    .map(sector => ({ sector }));
}

export default async function SectorPage({ params }) {
  const stats = await api.getSectorStats(params.sector);
  // Copy específico del sector + 5 hallazgos top de ese sector +
  // formulario de auditoría con sector pre-seleccionado
}
```

**Resultado**: 1 URL por sector × 1 URL por zona = 20-30 landings indexables sin escribir 30 páginas a mano.

---

## 10. Roadmap por fases

### Fase 0 — Setup (3-4 horas)
- Comprar dominio `.es` (10€/año)
- Setup repos GitHub público (apps/api, apps/web — monorepo Turbo)
- Cuentas: Vercel, Railway, Neon, Upstash, Resend, Cloudflare R2
- Variables de entorno y CI básico
- DNS y subdominios

### Fase 1 — MVP (1-2 fines de semana, ~20-30 horas)

**Objetivo: una auditoría real entregada por email**

- Landing minimalista (1 hero + form + footer)
- Backend NestJS con 1 endpoint POST `/api/audits`
- 1 worker con Lighthouse + 10 checks custom (los más impactantes)
- Generación de PDF simple (sin IA todavía, solo plantilla con findings)
- Resend para enviar PDF
- Telegram bot para notificarte
- Deploy: Vercel + Railway

**Validación**: 5 amigos prueban + tú haces 10 auditorías reales de gestorías.

### Fase 2 — Capa IA + viralidad (1 fin de semana)

- Integración LangChain + Claude/Gemini
- Catálogo de hallazgos completo (40 codes)
- Plantilla PDF con branding cuidado
- URL pública del informe (`/i/[slug]`) con OG dinámico
- Botón "compartir"
- Plausible Analytics

**Validación**: tasa de compartir > 10% (lo medimos)

### Fase 3 — Multiplicadores (semanas 3-4)

- Sectores y zonas: programmatic SEO landings
- BullMQ + Redis (queue real, no procesamiento sync)
- CLI interno `pnpm audit <url>` para tu prospección outbound
- Sync con Notion (CRM personal)
- Email follow-up automation (Resend + cron)
- Newsletter mensual con stats de hallazgos

**Validación**: 50 auditorías ejecutadas, 5 leads cualificados, 1 reunión.

### Fase 4 — Posicionamiento estratégico (mes 2)

- Migración a **Ollama local** para narración (en tu servidor o Mac mini)
- Página "cómo está construido" con tu stack y decisiones (refuerza tu marca técnica)
- Repo público en GitHub con README detallado (no el código completo, solo lo necesario para mostrar arquitectura)
- 1-2 artículos en dev.to/Medium narrando la construcción (backlinks)
- API tokens para partners (mode white-label)

### Fase 5 — Producto recurrente (mes 3+)

- Monitorización continua: las webs registradas se auditan semanal/mensualmente
- Email de alerta cuando algo empeora ("tu LCP ha pasado de 1.8s a 3.2s")
- Comparativa con sector ("estás en el percentil 60 de gestorías")
- Detector de oportunidades IA específicas por sector
- Generación de propuesta de presupuesto automática (la herramienta ya hace pre-venta sola)

---

## 11. Decisiones arquitectónicas clave (ADRs)

### ADR-001: Monorepo Turbo

**Decisión**: monorepo `apps/api` (NestJS) + `apps/web` (Next.js) + `packages/shared` (tipos y DTOs)

**Razón**: tipos compartidos entre frontend y backend sin duplicación. Deploy independiente. Tooling unificado.

### ADR-002: Queue obligatoria desde día 1

**Decisión**: incluso en MVP, las auditorías van por BullMQ.

**Razón**: una auditoría tarda 30-90s. Bloquear HTTP es no-go. Mejor pagar la complejidad inicial que reescribir en V2.

### ADR-003: Findings como catálogo, no strings hardcoded

**Decisión**: cada hallazgo tiene un `code` (`OG_IMAGE_BROKEN`, etc.) que mapea a una entrada de catálogo en DB.

**Razón**: traducciones, ajustes de mensaje, mejora de copy sin redeploy. Catálogo se vuelve un activo en sí mismo.

### ADR-004: Provider pattern para IA

**Decisión**: `NarrativeProvider` como interfaz, implementaciones intercambiables.

**Razón**: hoy Claude API, mañana Ollama local. Permite migrar sin tocar el resto del código.

### ADR-005: PDF como Puppeteer + HTML

**Decisión**: NO pdf-lib ni reportlab. Sí Puppeteer renderizando HTML.

**Razón**: iteración del diseño 10x más rápida. Reusas el mismo template HTML para la página pública.

### ADR-006: Privacidad por defecto

**Decisión**: no se publica nada sin consentimiento explícito del lead.

**Razón**: el leaderboard público solo incluye webs cuyo dueño marca "Sí, publica mi auditoría" (con descuento u otra contraprestación).

### ADR-007: Open source parcial

**Decisión**: repo público en GitHub con los runners de auditoría y la arquitectura. **NO** publicas los prompts de la IA ni los plantillas de PDF.

**Razón**: portfolio + autoridad técnica + backlinks SEO. Los prompts y diseño son tu salsa, esos no.

---

## 12. Observabilidad y métricas técnicas

Necesitas saber qué pasa sin tener que ir a logs:

- **Sentry** (free tier) → errores frontend + backend
- **Logtail** o **Axiom** → logs centralizados
- **Plausible** → analytics de producto
- **Dashboard propio** en `/admin` (protegido) con:
  - Auditorías hoy / esta semana
  - Tiempo medio de ejecución
  - Tasa de finalización
  - Leads capturados / contactados / convertidos
  - Top hallazgos del mes
  - Distribución por sector

Métricas técnicas a alertar:
- Auditorías fallidas > 5% en 1h → Telegram
- Tiempo de auditoría P95 > 120s → Telegram
- Cola con > 50 jobs pendientes → Telegram

---

## 13. Coste mensual operativo estimado

| Servicio | Plan | Coste/mes |
|----------|------|-----------|
| Dominio .es | anual | ~1€ |
| Vercel (frontend) | Free | 0€ |
| Railway (backend NestJS) | Hobby | 5€ |
| Neon (Postgres) | Free | 0€ |
| Upstash (Redis) | Free | 0€ |
| Cloudflare R2 | <10GB | 0€ |
| Resend | Free 3k mails | 0€ |
| Claude API (Haiku) | uso real | 5-20€ |
| Plausible | self-host | 0€ |
| **Total mes 1-3** | | **~10-30€** |

Cuando escales (>1000 auditorías/mes) sube a ~60-80€. Sigue siendo un negocio sano.

---

## 14. Lo primero que abrirías este sábado

Si abres el editor el sábado a las 10:00, este es el orden:

1. **30 min** — `pnpm create turbo@latest`, crear apps/api (NestJS) + apps/web (Next.js)
2. **1h** — Schema Prisma + migrations + conexión a Neon
3. **1h** — Endpoint POST /api/audits + entidad Audit + DTO
4. **2h** — Primer runner: Lighthouse con `lighthouse` npm package, devuelve JSON
5. **1h** — 3 runners custom (SEO basic, OG, viewport)
6. **1h** — Aggregator + cálculo de score global
7. **1h** — Endpoint GET /api/audits/:id
8. **2h** — Frontend Next.js: 1 página, form, polling al backend, mostrar resultado JSON

**Estado al final del sábado**: una web localhost donde pegas URL y devuelve JSON con findings reales.

**El domingo**: PDF con Puppeteer + Resend + deploy a Vercel/Railway.

**Lunes por la mañana**: primera auditoría real lanzada a un lead de tu spreadsheet.

---

## 15. Errores a evitar

1. **Empezar con la IA**. No. La IA es la capa final. Sin findings reales primero, la IA narra el vacío.
2. **Diseñar el PDF antes que el pipeline**. El PDF es output, no input. Cuando tengas findings, decides cómo presentarlos.
3. **Sobrediseñar la arquitectura del MVP**. Microservicios, K8s, gRPC — todo eso te lo guardas. Monolito modular NestJS + queue es más que suficiente hasta 10k auditorías/mes.
4. **No medir desde el día 1**. Plausible y Sentry desde el deploy inicial. Lo que no mides, no mejoras.
5. **Lanzar sin ningún caso real**. Lanza con 5-10 auditorías hechas a mano de webs locales. La landing tiene que mostrar trabajo real, no copy.
6. **Olvidar que es lead magnet**, no SaaS. No te pierdas refinando features. El objetivo es conseguir reuniones, no usuarios DAU.
