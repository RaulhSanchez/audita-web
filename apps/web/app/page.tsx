import { AuditForm } from './components/AuditForm';
import { ScrollReveal } from './components/ScrollReveal';

export const metadata = {
  title: 'AuditaWeb — Auditoría web gratis para PYMEs | zero2dev.es',
  description: 'Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90 segundos. Descubre por qué tu web está perdiendo clientes. Gratis, sin registro.',
};

export default function Home() {
  return (
    <main className="relative min-h-screen bg-[#0a0a0a] text-slate-50">

      {/* ── HERO ── */}
      <section className="mx-auto max-w-4xl px-6 pt-20 pb-16 sm:pt-24 lg:px-8">

        {/* Eyebrow 1/2 */}
        <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-slate-600 mb-8">
          Auditoría web gratuita · Sin registro · 90 segundos
        </p>

        {/* Headline — máximo 2 líneas (taste-skill rule) */}
        <h1 className="text-[clamp(2.75rem,7vw,5rem)] font-black tracking-tight text-white leading-[0.93] mb-7">
          Tu web pierde clientes.<br />
          <span className="text-indigo-400">Ya sé exactamente dónde.</span>
        </h1>

        <p className="text-[15px] text-slate-500 mb-10 max-w-[400px] leading-relaxed">
          Rendimiento, SEO, seguridad y RGPD. Informe en lenguaje de negocio
          — no de desarrollador — en 90 segundos y gratis.
        </p>

        <div className="max-w-lg">
          <AuditForm />
        </div>

        <p className="mt-5 text-sm text-slate-700">
          ¿Quieres ver antes cómo queda?{' '}
          <a
            href="/informe-ejemplo.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-500 underline underline-offset-4 decoration-slate-700 hover:text-slate-300 transition-colors duration-200"
          >
            Ver informe de ejemplo
          </a>
        </p>
      </section>

      {/* ── STATS ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-20 lg:px-8">
          <div className="border-t border-white/[0.06] pt-12 flex flex-wrap gap-x-12 gap-y-8">
            {[
              { n: '4s',   label: 'tarda de media una web PYME en cargar en móvil' },
              { n: '7/10', label: 'webs tienen infracciones RGPD sin saberlo' },
              { n: '63%',  label: 'de usuarios no vuelve si la web es lenta' },
            ].map(({ n, label }) => (
              <div key={n} className="flex items-baseline gap-3">
                <span className="text-[2.5rem] font-black text-white tabular-nums leading-none">{n}</span>
                <span className="text-sm text-slate-500 max-w-[155px] leading-snug">{label}</span>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ── QUÉ ANALIZO / QUÉ RECIBES ──
           Eyebrow 2/2 — un único título de sección, sin eyebrow por columna */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-24 lg:px-8">

          <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-slate-600 mb-8">
            Qué incluye el análisis
          </p>

          <div className="grid sm:grid-cols-2 gap-10">
            <ul className="space-y-3">
              {[
                'Velocidad de carga, móvil y escritorio',
                'Posicionamiento SEO local',
                'Seguridad HTTPS y cabeceras HTTP',
                'Cumplimiento RGPD y política de cookies',
                'Experiencia móvil y accesibilidad',
              ].map(item => (
                <li key={item} className="flex items-center gap-3 text-sm text-slate-400">
                  <span className="h-px w-5 flex-shrink-0 bg-indigo-500/50" />
                  {item}
                </li>
              ))}
            </ul>

            <ul className="space-y-3">
              {[
                'Puntuación 0-100 por cada categoría',
                'Problemas ordenados por impacto real',
                'Informe PDF completo en tu email',
                'Sin tecnicismos, solo lo que importa',
                'Plan de acción con prioridades claras',
              ].map(item => (
                <li key={item} className="flex items-center gap-3 text-sm text-slate-400">
                  <span className="h-px w-5 flex-shrink-0 bg-indigo-500/50" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </ScrollReveal>

      {/* ── AUTOR ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-24 lg:px-8">
          <div className="border-t border-white/[0.06] pt-12 flex items-start gap-5">
            <div className="flex-shrink-0 h-10 w-10 rounded-lg bg-indigo-600 flex items-center justify-center text-sm font-black text-white">
              R
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Raúl Huete</p>
              <p className="text-xs text-slate-600 mt-0.5 mb-3">
                Arquitecto de Software freelance · Madrid sur · zero2dev.es
              </p>
              <p className="text-sm text-slate-500 leading-relaxed max-w-lg">
                Creé AuditaWeb porque cada PYME merece el mismo diagnóstico
                que normalmente solo se pueden permitir las empresas grandes.
              </p>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── CTA FINAL ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-28 lg:px-8">
          <div className="border-t border-white/[0.06] pt-12">
            <h2 className="text-3xl sm:text-[2.5rem] font-extrabold text-white tracking-tight leading-tight mb-2">
              Analiza tu web ahora.
            </h2>
            <p className="text-slate-600 text-sm mb-8">
              Gratis. Sin registro. Sin tarjeta.
            </p>
            <div className="max-w-lg">
              <AuditForm />
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── FOOTER ── */}
      <footer className="border-t border-white/[0.04] py-8 px-6">
        <div className="mx-auto max-w-4xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-700">
          <p>
            © 2026 AuditaWeb ·{' '}
            <a href="https://zero2dev.es" className="hover:text-slate-400 transition-colors">
              zero2dev.es
            </a>{' '}
            · Raúl Huete
          </p>
          <div className="flex gap-5">
            <a href="https://zero2dev.es/privacidad" className="hover:text-slate-400 transition-colors">Privacidad</a>
            <a href="https://zero2dev.es/aviso-legal" className="hover:text-slate-400 transition-colors">Aviso legal</a>
          </div>
        </div>
      </footer>

    </main>
  );
}
