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
      <section className="mx-auto max-w-4xl px-6 pt-28 pb-16 sm:pt-36 lg:px-8">

        <p className="text-xs font-medium tracking-[0.2em] uppercase text-slate-600 mb-10">
          Gratis · Sin registro · 90 segundos
        </p>

        <h1 className="text-[clamp(3rem,8vw,5.5rem)] font-black tracking-tight text-white leading-[0.92] mb-8">
          Tu web está<br />
          <span className="text-indigo-400">perdiendo clientes.</span><br />
          Ya sé dónde.
        </h1>

        <p className="text-base text-slate-500 mb-10 max-w-md leading-relaxed">
          Rendimiento, SEO, seguridad y RGPD en lenguaje de negocio.
          Informe PDF en tu email, gratis.
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
            className="text-slate-500 underline underline-offset-4 decoration-slate-700 hover:text-slate-300 hover:decoration-slate-500 transition-all duration-200"
          >
            Ver informe de ejemplo
          </a>
        </p>
      </section>

      {/* ── STATS — sin cards, sólo números ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-20 lg:px-8">
          <div className="border-t border-white/[0.06] pt-12 flex flex-wrap gap-x-14 gap-y-8">
            {[
              { n: '4s', label: 'tarda de media una web PYME en cargar en móvil' },
              { n: '7/10', label: 'webs tienen infracciones RGPD sin saberlo' },
              { n: '63%', label: 'de usuarios no vuelve si la web es lenta o confusa' },
            ].map(({ n, label }) => (
              <div key={n} className="flex items-baseline gap-3">
                <span className="text-[2.5rem] font-black text-white tabular-nums leading-none">{n}</span>
                <span className="text-sm text-slate-600 max-w-[160px] leading-snug">{label}</span>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ── QUÉ ANALIZO / QUÉ RECIBES — texto, sin cards ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-24 lg:px-8">
          <div className="grid sm:grid-cols-2 gap-12">

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600 mb-5">
                Lo que analizo
              </p>
              <ul className="space-y-3">
                {[
                  'Velocidad de carga — móvil y escritorio',
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
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600 mb-5">
                Lo que recibes
              </p>
              <ul className="space-y-3">
                {[
                  'Puntuación 0–100 por cada categoría',
                  'Problemas ordenados por impacto real',
                  'Informe PDF completo en tu email',
                  'Sin tecnicismos — sólo lo que importa',
                  'Plan de acción con prioridades claras',
                ].map(item => (
                  <li key={item} className="flex items-center gap-3 text-sm text-slate-400">
                    <span className="h-px w-5 flex-shrink-0 bg-emerald-500/50" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

          </div>
        </section>
      </ScrollReveal>

      {/* ── AUTOR ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-24 lg:px-8">
          <div className="border-t border-white/[0.06] pt-12 flex items-start gap-5">
            <div className="flex-shrink-0 h-11 w-11 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-base font-black text-white">
              R
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Raúl Huete</p>
              <p className="text-xs text-slate-600 mt-0.5 mb-3">
                Arquitecto de Software freelance · Madrid sur · zero2dev.es
              </p>
              <p className="text-sm text-slate-500 leading-relaxed max-w-lg">
                Creé AuditaWeb porque cada PYME merece el mismo diagnóstico que normalmente
                sólo se pueden permitir las empresas grandes. Sin agencias, sin presupuesto.
              </p>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── CTA FINAL ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-4xl px-6 pb-28 lg:px-8">
          <div className="border-t border-white/[0.06] pt-12">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-2">
              Analiza tu web ahora.
            </h2>
            <p className="text-slate-600 text-sm mb-8">
              Gratis. Sin registro. Sin tarjeta de crédito.
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
            <a href="https://zero2dev.es/privacidad" className="hover:text-slate-400 transition-colors">
              Privacidad
            </a>
            <a href="https://zero2dev.es/aviso-legal" className="hover:text-slate-400 transition-colors">
              Aviso legal
            </a>
          </div>
        </div>
      </footer>

    </main>
  );
}
