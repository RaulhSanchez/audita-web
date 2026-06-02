import { AuditForm } from './components/AuditForm';

export const metadata = {
  title: 'AuditaWeb — Auditoría web gratis para PYMEs | zero2dev.es',
  description: 'Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90 segundos. Descubre por qué tu web está perdiendo clientes. Gratis, sin registro.',
};

export default function Home() {

  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-50 selection:bg-indigo-500/30">
      {/* Background glow */}
      <div className="absolute top-0 z-[-1] h-screen w-screen bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.3),rgba(255,255,255,0))]" />

      {/* ══════════════ HERO ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pt-24 pb-16 sm:pt-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          {/* Badge */}
          <div className="mb-8 flex justify-center">
            <span className="rounded-full px-4 py-1.5 text-sm font-medium text-indigo-300 ring-1 ring-indigo-500/30 bg-indigo-500/10 backdrop-blur-sm">
              Gratis · Sin registro · 90 segundos
            </span>
          </div>

          {/* H1 */}
          <h1 className="text-5xl font-extrabold tracking-tight text-white sm:text-6xl drop-shadow-sm leading-tight">
            ¿Tu web está{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
              perdiendo clientes
            </span>{' '}
            y no sabes por qué?
          </h1>

          {/* Subtítulo */}
          <p className="mt-6 text-lg leading-8 text-slate-300 font-light">
            Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90 segundos.
            Informe en lenguaje de negocio, gratis.
          </p>

          {/* Form */}
          <div className="mt-10 max-w-xl mx-auto">
            <AuditForm />
          </div>

          {/* Sample report link */}
          <p className="mt-5 text-sm text-slate-500">
            ¿Quieres ver el informe antes de probar?{' '}
            <a
              href="/informe-ejemplo.pdf"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
            >
              Ver informe de ejemplo →
            </a>
          </p>
        </div>
      </section>

      {/* ══════════════ 3 PILARES ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-16 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {/* Pilar 1 */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 text-xl">
              🔍
            </div>
            <h3 className="text-base font-bold text-white mb-2">Diagnóstico técnico completo</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Velocidad, SEO, seguridad, RGPD y experiencia móvil. Todo lo que afecta a cómo te encuentra Google y a si el cliente se queda.
            </p>
          </div>

          {/* Pilar 2 */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400 text-xl">
              💶
            </div>
            <h3 className="text-base font-bold text-white mb-2">Impacto traducido a negocio</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Sin tecnicismos. Cada problema se explica en lo que te cuesta: clientes que se van, posiciones que pierdes, multas que arriesgas.
            </p>
          </div>

          {/* Pilar 3 */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/20 text-violet-400 text-xl">
              🎯
            </div>
            <h3 className="text-base font-bold text-white mb-2">Plan de acción priorizado</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Los problemas ordenados por impacto. Sabrás exactamente qué arreglar primero para notar los resultados antes.
            </p>
          </div>
        </div>
      </section>

      {/* ══════════════ PRUEBA SOCIAL ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-16 lg:px-8">
        <div className="text-center">
          <p className="text-4xl font-extrabold text-white">+50</p>
          <p className="mt-1 text-slate-400 text-sm">webs de PYMEs madrileñas ya auditadas</p>
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-left">
              <p className="text-sm text-slate-300 leading-relaxed italic">
                "No sabía que mi web tardaba 4 segundos en cargar en el móvil. Con el informe lo vi claro."
              </p>
              <p className="mt-3 text-xs text-slate-500 font-medium">Clínica dental · Fuenlabrada</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-left">
              <p className="text-sm text-slate-300 leading-relaxed italic">
                "Lo del RGPD me asustó bastante. Mejor enterarme así que por una denuncia."
              </p>
              <p className="mt-3 text-xs text-slate-500 font-medium">Gestoría · Móstoles</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-left">
              <p className="text-sm text-slate-300 leading-relaxed italic">
                "El informe lo entiende cualquiera. Y eso que yo de tecnología no entiendo nada."
              </p>
              <p className="mt-3 text-xs text-slate-500 font-medium">Restaurante · Leganés</p>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════ QUIÉN ESTÁ DETRÁS ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-16 lg:px-8">
        <div className="mx-auto max-w-2xl rounded-2xl border border-white/10 bg-white/5 p-8 backdrop-blur-sm flex flex-col sm:flex-row items-center sm:items-start gap-6">
          <div className="flex-shrink-0">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-2xl font-black text-white shadow-lg shadow-indigo-500/30">
              R
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-indigo-400 uppercase tracking-widest mb-1">Quién está detrás</p>
            <h3 className="text-lg font-bold text-white">Raúl Huete</h3>
            <p className="text-sm text-slate-400 mt-0.5">Arquitecto de Software freelance · Madrid sur · zero2dev.es</p>
            <p className="mt-3 text-sm text-slate-400 leading-relaxed">
              Llevo años construyendo y optimizando aplicaciones web. Creé AuditaWeb para darle a cada PYME el mismo diagnóstico que normalmente solo pueden permitirse las empresas grandes.
            </p>
          </div>
        </div>
      </section>

      {/* ══════════════ CTA FINAL ══════════════ */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-24 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
            Analiza tu web ahora.{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
              Gratis.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 text-base">
            90 segundos. Sin registro. Sin tarjeta. Recibes el informe en PDF si dejas tu email.
          </p>
          <div className="mt-8 max-w-xl mx-auto">
            <AuditForm />
          </div>
        </div>
      </section>

      {/* ══════════════ FOOTER ══════════════ */}
      <footer className="relative z-10 border-t border-white/5 py-8 px-6">
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
