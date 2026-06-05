import { AuditForm } from './components/AuditForm';
import { ScrollReveal } from './components/ScrollReveal';

export const metadata = {
  title: 'AuditaWeb — Auditoría web gratis para PYMEs | zero2dev.es',
  description: 'Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90 segundos. Descubre por qué tu web está perdiendo clientes. Gratis, sin registro.',
};

const chips = [
  { icon: '⚡', label: 'Velocidad' },
  { icon: '🔍', label: 'SEO local' },
  { icon: '🔒', label: 'Seguridad' },
  { icon: '📋', label: 'RGPD' },
  { icon: '📱', label: 'Móvil' },
];

const stats = [
  { n: '4s',   sub: 'tarda de media una web PYME en cargar en móvil' },
  { n: '7/10', sub: 'webs tienen infracciones RGPD sin saberlo' },
  { n: '63%',  sub: 'de usuarios no vuelve si la experiencia es mala' },
];

export default function Home() {
  return (
    <main id="top" className="min-h-screen bg-[#f7f7f5] text-[#111111]">

      {/* ── NAV ── */}
      <nav className="mx-auto max-w-5xl px-6 py-5 lg:px-8 flex items-center justify-between">
        <span className="text-sm font-black tracking-tight">AuditaWeb</span>
        <a
          href="/informe-ejemplo.pdf"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-gray-400 hover:text-gray-900 transition-colors duration-200"
        >
          Ver ejemplo →
        </a>
      </nav>

      {/* ── HERO — Editorial Split ── */}
      <section className="mx-auto max-w-5xl px-6 pt-10 pb-16 lg:px-8">
        <div className="grid lg:grid-cols-[1fr_400px] gap-12 lg:gap-16 items-start">

          {/* Left — content */}
          <div>
            {/* Eyebrow pill — Skill: rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em] */}
            <div className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1.5 mb-8 shadow-sm">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">
                Gratis · Sin registro · 90 segundos
              </span>
            </div>

            {/* H1 — massive Grotesk, 2 lines */}
            <h1 className="text-[clamp(2.75rem,6vw,4.5rem)] font-black tracking-tight text-[#111111] leading-[0.93] mb-6">
              Tu web pierde<br />clientes.{' '}
              <span className="text-indigo-600">Descubre dónde.</span>
            </h1>

            <p className="text-[15px] text-gray-500 leading-relaxed max-w-md mb-8">
              Análisis de rendimiento, SEO, seguridad y RGPD en lenguaje de negocio,
              no de desarrollador. En 90 segundos. Gratis.
            </p>

            {/* Analysis chips */}
            <div className="flex flex-wrap gap-2">
              {chips.map(({ icon, label }) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-1.5 rounded-full bg-white border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 shadow-sm"
                >
                  <span className="text-sm">{icon}</span>
                  {label}
                </span>
              ))}
            </div>

            {/* Stats — inline, no cards */}
            <div className="mt-12 pt-10 border-t border-gray-200 grid grid-cols-3 gap-4">
              {stats.map(({ n, sub }) => (
                <div key={n}>
                  <p className="text-3xl font-black text-[#111111] tabular-nums leading-none mb-1">{n}</p>
                  <p className="text-xs text-gray-400 leading-snug">{sub}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Right — Double-bezel form card (Skill: outer shell + inner core) */}
          <div className="lg:sticky lg:top-8">
            {/* Outer shell */}
            <div className="rounded-[1.75rem] bg-gray-100 ring-1 ring-gray-200/80 p-2 shadow-[0_20px_60px_rgba(0,0,0,0.06)]">
              {/* Inner core */}
              <div className="rounded-[1.25rem] bg-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] p-6">
                <p className="text-base font-bold text-[#111111] mb-0.5">Analiza tu web gratis</p>
                <p className="text-xs text-gray-400 mb-5">Informe completo en 90 segundos</p>
                <AuditForm />
              </div>
            </div>

            <p className="mt-3 text-center text-xs text-gray-400">
              Sin tarjeta de crédito · Sin registro
            </p>
          </div>

        </div>
      </section>

      {/* ── BENTO FEATURES ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-20 lg:px-8">
          {/* Bento grid — asimétrico según skill */}
          <div className="grid lg:grid-cols-5 gap-3">

            {/* Featured — lg:col-span-3 */}
            <div className="lg:col-span-3 rounded-2xl bg-white ring-1 ring-gray-100 shadow-[0_4px_24px_rgba(0,0,0,0.05)] p-8">
              <p className="text-xs font-semibold uppercase tracking-[0.15em] text-gray-400 mb-4">Lo que analizamos</p>
              <ul className="space-y-3">
                {[
                  ['⚡', 'Velocidad de carga', 'Móvil y escritorio, Core Web Vitals'],
                  ['🔍', 'SEO local', 'Posicionamiento en búsquedas de tu zona'],
                  ['🔒', 'Seguridad HTTPS', 'Certificado SSL, cabeceras de seguridad'],
                  ['📋', 'Cumplimiento RGPD', 'Cookies, política de privacidad, formularios'],
                  ['📱', 'Experiencia móvil', 'Usabilidad, botones, accesibilidad'],
                ].map(([icon, title, desc]) => (
                  <li key={title} className="flex items-start gap-3">
                    <span className="text-base mt-0.5">{icon}</span>
                    <div>
                      <p className="text-sm font-semibold text-[#111]">{title}</p>
                      <p className="text-xs text-gray-400">{desc}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Right stack — lg:col-span-2 */}
            <div className="lg:col-span-2 flex flex-col gap-3">
              <div className="flex-1 rounded-2xl bg-indigo-600 p-7 text-white">
                <p className="text-4xl font-black tabular-nums mb-2">90s</p>
                <p className="text-sm font-semibold mb-1">Análisis completo</p>
                <p className="text-xs text-indigo-200 leading-relaxed">
                  En menos de 2 minutos tienes el diagnóstico completo de tu web.
                </p>
              </div>
              <div className="flex-1 rounded-2xl bg-white ring-1 ring-gray-100 shadow-[0_4px_24px_rgba(0,0,0,0.05)] p-7">
                <p className="text-4xl font-black tabular-nums text-[#111] mb-2">PDF</p>
                <p className="text-sm font-semibold mb-1">Informe completo</p>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Recibes el informe detallado en tu email, listo para enseñar a tu equipo.
                </p>
              </div>
            </div>

          </div>
        </section>
      </ScrollReveal>

      {/* ── AUTOR ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-20 lg:px-8">
          <div className="flex items-start gap-5 max-w-2xl">
            <div className="flex-shrink-0 h-11 w-11 rounded-xl bg-indigo-600 flex items-center justify-center text-sm font-black text-white shadow-md">
              R
            </div>
            <div>
              <p className="font-semibold text-[#111]">Raúl Huete</p>
              <p className="text-xs text-gray-400 mt-0.5 mb-3">Arquitecto de Software freelance · Madrid sur</p>
              <p className="text-sm text-gray-500 leading-relaxed">
                Creé AuditaWeb para que cada PYME pueda tener el diagnóstico web
                que normalmente solo se pueden permitir las empresas grandes.
                Sin agencias, sin presupuesto.
              </p>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── CTA FINAL ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-24 lg:px-8">
          <div className="rounded-2xl bg-[#111111] px-8 py-10 sm:px-12 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div>
              <p className="text-xl font-bold text-white mb-1">¿Tu web está perdiendo clientes?</p>
              <p className="text-sm text-gray-400">Descúbrelo en 90 segundos. Gratis.</p>
            </div>
            <a
              href="#top"
              className="inline-flex items-center gap-3 rounded-full bg-white px-6 py-3 text-sm font-semibold text-[#111] hover:bg-gray-100 active:scale-[0.97] transition-all duration-200 whitespace-nowrap shadow-sm"
            >
              Analizar mi web
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-black/8 text-xs">
                ↑
              </span>
            </a>
          </div>
        </section>
      </ScrollReveal>

      {/* ── FOOTER ── */}
      <footer className="border-t border-gray-100 py-8 px-6 bg-white">
        <div className="mx-auto max-w-5xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-400">
          <p>
            © 2026 AuditaWeb ·{' '}
            <a href="https://zero2dev.es" className="hover:text-gray-700 transition-colors">zero2dev.es</a>
            {' '}· Raúl Huete
          </p>
          <div className="flex gap-5">
            <a href="https://zero2dev.es/privacidad" className="hover:text-gray-700 transition-colors">Privacidad</a>
            <a href="https://zero2dev.es/aviso-legal" className="hover:text-gray-700 transition-colors">Aviso legal</a>
          </div>
        </div>
      </footer>

    </main>
  );
}
