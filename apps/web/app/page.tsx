import { AuditForm } from './components/AuditForm';
import { ScrollReveal } from './components/ScrollReveal';

export const metadata = {
  title: 'AuditaWeb — Auditoría web gratis para PYMEs | zero2dev.es',
  description: 'Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90 segundos. Descubre por qué tu web está perdiendo clientes. Gratis, sin registro.',
};

const checks = [
  { icon: '⚡', label: 'Velocidad de carga' },
  { icon: '🔍', label: 'SEO local' },
  { icon: '🔒', label: 'Seguridad HTTPS' },
  { icon: '📋', label: 'Cumplimiento RGPD' },
  { icon: '📱', label: 'Experiencia móvil' },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#fafaf8] text-gray-900">

      {/* ── NAV ── */}
      <nav className="mx-auto max-w-5xl px-6 py-5 lg:px-8 flex items-center justify-between">
        <span className="text-sm font-bold text-gray-900 tracking-tight">AuditaWeb</span>
        <a
          href="/informe-ejemplo.pdf"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-gray-500 hover:text-gray-900 transition-colors duration-200"
        >
          Ver ejemplo →
        </a>
      </nav>

      {/* ── HERO ── */}
      <section className="mx-auto max-w-5xl px-6 pt-12 pb-16 lg:px-8">
        <div className="max-w-3xl">

          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-50 border border-indigo-100 px-3 py-1.5 mb-8">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500" />
            </span>
            <span className="text-xs font-medium text-indigo-700">Gratis · Sin registro · 90 segundos</span>
          </div>

          <h1 className="text-[clamp(2.5rem,6vw,4.25rem)] font-black tracking-tight text-gray-900 leading-[1.0] mb-6">
            Tu web pierde clientes.<br />
            <span className="text-indigo-600">Descubre exactamente dónde.</span>
          </h1>

          <p className="text-lg text-gray-500 mb-10 max-w-xl leading-relaxed">
            Análisis de rendimiento, SEO, seguridad y RGPD en 90 segundos.
            Informe en lenguaje de negocio, no de desarrollador. Gratis.
          </p>

          {/* Form en card elevada */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 max-w-xl">
            <AuditForm />
          </div>

        </div>
      </section>

      {/* ── QUÉ ANALIZO — chips visuales ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-16 lg:px-8">
          <div className="flex flex-wrap gap-3">
            {checks.map(({ icon, label }) => (
              <div
                key={label}
                className="flex items-center gap-2 rounded-full bg-white border border-gray-200 px-4 py-2 text-sm text-gray-700 shadow-sm"
              >
                <span>{icon}</span>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ── STATS ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-20 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { n: '4s',   label: 'tarda de media una web PYME en cargar en móvil' },
              { n: '7/10', label: 'webs tienen infracciones RGPD sin saberlo' },
              { n: '63%',  label: 'de usuarios no vuelve si la experiencia es mala' },
            ].map(({ n, label }) => (
              <div key={n} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <p className="text-4xl font-black text-indigo-600 tabular-nums mb-1">{n}</p>
                <p className="text-sm text-gray-500 leading-snug">{label}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ── CÓMO FUNCIONA ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-20 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-8">Cómo funciona</h2>
          <div className="grid sm:grid-cols-3 gap-6">
            {[
              { step: '1', title: 'Pega tu URL', desc: 'Introduce la dirección de tu web. No necesitas cuenta ni instalar nada.' },
              { step: '2', title: 'Análisis automático', desc: 'En 90 segundos analizamos velocidad, SEO, seguridad, RGPD y experiencia móvil.' },
              { step: '3', title: 'Recibe el informe', desc: 'Ves los resultados al instante. Si dejas tu email, recibes el PDF completo gratis.' },
            ].map(({ step, title, desc }) => (
              <div key={step} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <div className="h-8 w-8 rounded-lg bg-indigo-600 text-white text-sm font-black flex items-center justify-center mb-4">
                  {step}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ── AUTOR ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-20 lg:px-8">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 flex items-start gap-5 max-w-2xl">
            <div className="flex-shrink-0 h-12 w-12 rounded-xl bg-indigo-600 flex items-center justify-center text-lg font-black text-white">
              R
            </div>
            <div>
              <p className="font-semibold text-gray-900">Raúl Huete</p>
              <p className="text-xs text-gray-400 mt-0.5 mb-3">Arquitecto de Software freelance · Madrid sur · zero2dev.es</p>
              <p className="text-sm text-gray-600 leading-relaxed">
                Creé AuditaWeb para que cada PYME pueda tener el mismo diagnóstico web que normalmente solo se pueden permitir las empresas grandes. Sin agencias, sin presupuesto.
              </p>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ── CTA FINAL ── */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 pb-24 lg:px-8">
          <div className="bg-indigo-600 rounded-2xl p-8 sm:p-12">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-2">
              Analiza tu web ahora. Es gratis.
            </h2>
            <p className="text-indigo-200 mb-8 text-sm">
              Sin registro. Sin tarjeta de crédito. En 90 segundos.
            </p>
            <div className="max-w-xl bg-white rounded-xl p-4">
              <AuditForm ctaVariant="light" />
            </div>
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
