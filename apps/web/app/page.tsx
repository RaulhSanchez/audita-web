import { AuditForm } from './components/AuditForm';
import { ScrollReveal } from './components/ScrollReveal';

export const metadata = {
  title: 'AuditaWeb — Auditoría web gratis para PYMEs | zero2dev.es',
  description: 'Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90 segundos. Descubre por qué tu web está perdiendo clientes. Gratis, sin registro.',
};

function IconSearch() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
  );
}

function IconTrendingUp() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22,7 13.5,15.5 8.5,10.5 2,17"/><polyline points="16,7 22,7 22,13"/>
    </svg>
  );
}

function IconTarget() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
    </svg>
  );
}

export default function Home() {
  return (
    <main className="grain relative min-h-screen overflow-hidden bg-[#020817] text-slate-50 selection:bg-indigo-500/20">

      {/* Ambient glow — muted, not screaming */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-600/10 blur-[120px]" />
      </div>

      {/* ══════════════ HERO ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pt-24 pb-20 sm:pt-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">

          {/* Badge */}
          <div className="mb-10 flex justify-center">
            <span className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium tracking-wide text-slate-400 ring-1 ring-white/10">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Gratis · Sin registro · 90 segundos
            </span>
          </div>

          {/* H1 — no AI gradient, solid accent on one word */}
          <h1 className="text-balance text-5xl font-extrabold tracking-tight text-white sm:text-6xl leading-[1.08]">
            ¿Tu web está{' '}
            <span className="text-indigo-400">perdiendo clientes</span>{' '}
            y no sabes por qué?
          </h1>

          <p className="text-balance mt-6 text-lg leading-8 text-slate-400 font-light">
            Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90&nbsp;segundos.
            Informe en lenguaje de negocio, gratis.
          </p>

          <div className="mt-10 max-w-xl mx-auto">
            <AuditForm />
          </div>

          {/* Sample report */}
          <p className="mt-6 text-sm text-slate-600">
            ¿Quieres ver el resultado antes de probar?{' '}
            <a
              href="/informe-ejemplo.pdf"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 underline underline-offset-4 decoration-slate-600 hover:text-white hover:decoration-white transition-colors duration-200"
            >
              Ver informe de ejemplo
            </a>
          </p>
        </div>
      </section>

      {/* ══════════════ PILARES — asymmetric, no equal 3-col ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-24 lg:px-8">
        <ScrollReveal>
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

            {/* Featured pilar — spans 3 cols */}
            <div className="lg:col-span-3 rounded-2xl border border-white/8 bg-white/[0.03] p-8 flex flex-col gap-4">
              <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-400">
                <IconSearch />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">Diagnóstico técnico completo</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Velocidad, SEO, seguridad, RGPD y experiencia móvil. Todo lo que afecta a cómo te encuentra Google y a si el cliente se queda o se va a la competencia.
                </p>
              </div>
              <div className="mt-auto pt-4 border-t border-white/6 grid grid-cols-3 gap-4 text-center">
                {[['Rendimiento', '0–100'], ['SEO', '0–100'], ['Seguridad', '0–100']].map(([label, range]) => (
                  <div key={label}>
                    <p className="text-xs text-slate-500 mb-1">{label}</p>
                    <p className="text-sm font-semibold text-slate-300">{range}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 2 smaller pilares stacked */}
            <div className="lg:col-span-2 flex flex-col gap-4">
              <div className="flex-1 rounded-2xl border border-white/8 bg-white/[0.03] p-6 flex flex-col gap-3">
                <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
                  <IconTrendingUp />
                </div>
                <h3 className="text-base font-semibold text-white">Impacto en negocio</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Sin tecnicismos. Cada problema se explica en lo que te cuesta: clientes que se van, posiciones que pierdes, multas que arriesgas.
                </p>
              </div>

              <div className="flex-1 rounded-2xl border border-white/8 bg-white/[0.03] p-6 flex flex-col gap-3">
                <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-violet-500/15 text-violet-400">
                  <IconTarget />
                </div>
                <h3 className="text-base font-semibold text-white">Plan de acción priorizado</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Los problemas ordenados por impacto. Sabrás exactamente qué arreglar primero.
                </p>
              </div>
            </div>

          </div>
        </ScrollReveal>
      </section>

      {/* ══════════════ PRUEBA SOCIAL ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-24 lg:px-8">
        <ScrollReveal>
          <div className="mb-10 text-center">
            <p className="text-sm text-slate-500 uppercase tracking-widest font-medium">Lo que dicen quienes ya lo probaron</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                quote: '"No sabía que mi web tardaba 4 segundos en cargar en el móvil. Con el informe lo vi claro."',
                who: 'Clínica dental · Fuenlabrada',
                delay: 1,
              },
              {
                quote: '"Lo del RGPD me asustó bastante. Mejor enterarme así que por una denuncia."',
                who: 'Gestoría · Móstoles',
                delay: 2,
              },
              {
                quote: '"El informe lo entiende cualquiera. Y eso que yo de tecnología no entiendo nada."',
                who: 'Restaurante · Leganés',
                delay: 3,
              },
            ].map(({ quote, who, delay }, i) => (
              <ScrollReveal key={i} delay={delay as 1 | 2 | 3}>
                <div className="h-full rounded-2xl border border-white/8 bg-white/[0.03] p-6 flex flex-col gap-4 hover:bg-white/[0.05] transition-colors duration-300">
                  <p className="text-sm text-slate-300 leading-relaxed italic flex-1">{quote}</p>
                  <p className="text-xs text-slate-500 font-medium">{who}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </ScrollReveal>
      </section>

      {/* ══════════════ AUTOR ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-24 lg:px-8">
        <ScrollReveal>
          <div className="mx-auto max-w-2xl rounded-2xl border border-white/8 bg-white/[0.03] p-8 flex flex-col sm:flex-row items-start gap-6">
            <div className="flex-shrink-0 h-14 w-14 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-xl font-black text-white">
              R
            </div>
            <div>
              <p className="text-xs font-medium text-indigo-400 tracking-widest uppercase mb-2">Quién está detrás</p>
              <h3 className="text-lg font-semibold text-white">Raúl Huete</h3>
              <p className="text-sm text-slate-500 mt-0.5 mb-3">Arquitecto de Software freelance · Madrid sur · zero2dev.es</p>
              <p className="text-sm text-slate-400 leading-relaxed">
                Llevo años construyendo y optimizando aplicaciones web. Creé AuditaWeb para darle a cada PYME el mismo diagnóstico que normalmente solo pueden permitirse las empresas grandes.
              </p>
            </div>
          </div>
        </ScrollReveal>
      </section>

      {/* ══════════════ CTA FINAL ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-28 lg:px-8">
        <ScrollReveal>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-balance text-3xl font-extrabold text-white sm:text-4xl">
              Analiza tu web ahora.{' '}
              <span className="text-indigo-400">Gratis.</span>
            </h2>
            <p className="mt-4 text-slate-400 text-base">
              90 segundos. Sin registro. Sin tarjeta. Recibes el informe en PDF si dejas tu email.
            </p>
            <div className="mt-8 max-w-xl mx-auto">
              <AuditForm />
            </div>
          </div>
        </ScrollReveal>
      </section>

      {/* ══════════════ FOOTER ══════════════ */}
      <footer className="relative z-10 border-t border-white/[0.06] py-8 px-6">
        <div className="mx-auto max-w-5xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
          <p>© 2026 AuditaWeb · <a href="https://zero2dev.es" className="hover:text-slate-400 transition-colors">zero2dev.es</a> · Raúl Huete</p>
          <div className="flex gap-4">
            <a href="https://zero2dev.es/privacidad" className="hover:text-slate-400 transition-colors">Privacidad</a>
            <a href="https://zero2dev.es/aviso-legal" className="hover:text-slate-400 transition-colors">Aviso legal</a>
          </div>
        </div>
      </footer>

    </main>
  );
}
