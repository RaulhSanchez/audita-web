import { AuditForm } from './components/AuditForm';

export const metadata = {
  title: 'Audita Tu Web - Descubre por qué pierdes clientes',
  description: 'Auditoría web profesional en menos de 90 segundos.',
};

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-50 selection:bg-indigo-500/30">
      <div className="absolute top-0 z-[-1] h-screen w-screen bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.3),rgba(255,255,255,0))]"></div>
      
      <div className="relative z-10 mx-auto max-w-5xl px-6 pt-32 pb-20 sm:pt-40 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mb-8 flex justify-center">
            <span className="relative rounded-full px-3 py-1 text-sm leading-6 text-indigo-300 ring-1 ring-white/10 hover:ring-white/20 transition-all cursor-pointer backdrop-blur-sm">
              Lanzamiento MVP. <span className="font-semibold text-indigo-400">Pruébalo gratis</span>
            </span>
          </div>
          <h1 className="text-5xl font-extrabold tracking-tight text-white sm:text-7xl drop-shadow-sm">
            ¿Tu web está <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">perdiendo ventas</span>?
          </h1>
          <p className="mt-6 text-lg leading-8 text-slate-300 font-light">
            Analizamos rendimiento, SEO, seguridad y accesibilidad. Recibe un informe en lenguaje de negocio para saber exactamente qué te está costando dinero.
          </p>
          
          <div className="mt-10 max-w-xl mx-auto">
            <AuditForm />
          </div>
        </div>
      </div>
    </main>
  );
}
