import { Metadata } from 'next';
import { AuditForm } from '../../components/AuditForm';

interface PageProps {
  params: Promise<{ sector: string }>;
}

export async function generateStaticParams() {
  return [
    { sector: 'gestorias' },
    { sector: 'clinicas-dentales' },
    { sector: 'talleres-mecanicos' },
    { sector: 'restaurantes' }
  ];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { sector } = await params;
  const sectorName = sector.replace('-', ' ');
  return {
    title: `Auditoría Web Gratis para ${sectorName.charAt(0).toUpperCase() + sectorName.slice(1)}`,
    description: `Descubre por qué tu ${sectorName} está perdiendo clientes en Google y cómo solucionarlo gratis en 60 segundos.`,
  };
}

export default async function SectorPage({ params }: PageProps) {
  const { sector } = await params;
  const sectorName = sector.replace('-', ' ');

  return (
    <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-4xl w-full space-y-12 py-20">
        <header className="space-y-6">
          <div className="inline-block px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm font-semibold tracking-wide uppercase mb-4">
            Especial para {sectorName}
          </div>
          <h1 className="text-5xl sm:text-7xl font-black text-white tracking-tight">
            ¿Por qué tu <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">{sectorName}</span> no recibe más clientes de Google?
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Pega la URL de tu web. En 60 segundos, nuestra IA te dirá exactamente qué problemas técnicos te están haciendo invisible para tus clientes locales.
          </p>
        </header>

        <div className="max-w-2xl mx-auto w-full bg-white/5 p-2 rounded-3xl border border-white/10 shadow-2xl backdrop-blur-sm">
          <AuditForm />
        </div>
      </div>
    </main>
  );
}
