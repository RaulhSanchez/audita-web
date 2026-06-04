import { Metadata } from 'next';
import { AuditForm } from '../../components/AuditForm';

interface PageProps {
  params: Promise<{ sector: string }>;
}

const SECTOR_DATA: Record<string, {
  name: string;
  pain: string;
  hook: string;
  stats: { label: string; value: string }[];
  findings: string[];
}> = {
  'clinicas-dentales': {
    name: 'clínicas dentales',
    pain: 'Pacientes que buscan dentista en Google y acaban en la clínica de al lado',
    hook: '¿Tu clínica dental aparece cuando alguien busca "dentista" en tu ciudad?',
    stats: [
      { value: '73%', label: 'de pacientes buscan dentista en Google antes de llamar' },
      { value: '53%', label: 'abandonan si la web tarda más de 3 segundos en móvil' },
      { value: '8/10', label: 'clínicas dentales analizadas fallan en SEO local' },
    ],
    findings: [
      'Web no aparece en "dentista cerca de mí"',
      'Carga en +4 segundos en móvil',
      'Sin política de privacidad visible',
      'Teléfono no es clickable desde el móvil',
      'Sin reseñas de Google enlazadas',
    ],
  },
  'gestorias': {
    name: 'gestorías y asesorías',
    pain: 'Tu web no cumple la normativa RGPD que tú mismo aplicas a tus clientes',
    hook: '¿Tu gestoría tiene los mismos problemas legales en su web que detectas en tus clientes?',
    stats: [
      { value: '6/10', label: 'gestorías tienen infracciones RGPD en su propia web' },
      { value: '40%', label: 'de búsquedas de gestoría son locales con intención inmediata' },
      { value: '3x', label: 'más conversiones tienen webs con certificado SSL correcto' },
    ],
    findings: [
      'Sin banner de cookies conforme a RGPD',
      'Política de privacidad desactualizada o inexistente',
      'Sin HTTPS o certificado caducado',
      'No aparece en búsquedas locales "gestoría [ciudad]"',
      'Formulario de contacto sin aviso legal',
    ],
  },
  'talleres-mecanicos': {
    name: 'talleres mecánicos',
    pain: 'Conductores que buscan taller en Google Maps y llaman al primero que aparece (que no eres tú)',
    hook: '¿Cuántos conductores buscan taller en tu zona y encuentran a la competencia?',
    stats: [
      { value: '68%', label: 'de búsquedas de taller se hacen desde el móvil' },
      { value: '4x', label: 'más llamadas reciben talleres con web optimizada para móvil' },
      { value: '9/10', label: 'talleres analizados tienen el teléfono no clickable en móvil' },
    ],
    findings: [
      'Teléfono no clickable desde el móvil',
      'Sin ficha de Google Business optimizada',
      'Web no carga en conexiones 4G lentas',
      'Sin metadatos de localización SEO',
      'Sin botón WhatsApp visible',
    ],
  },
  'restaurantes': {
    name: 'restaurantes y hostelería',
    pain: 'Comensales que buscan restaurante en Google y reservan en el que tiene mejor web',
    hook: '¿Tu restaurante aparece cuando alguien busca dónde comer en tu zona?',
    stats: [
      { value: '80%', label: 'de reservas de restaurante se inician en Google' },
      { value: '2.1s', label: 'es el tiempo máximo antes de que el usuario abandone en móvil' },
      { value: '70%', label: 'de restaurantes no tiene la carta accesible desde móvil en <2 clics' },
    ],
    findings: [
      'Carta en PDF no indexable por Google',
      'Sin schema.org de restaurante (horario, precio, reservas)',
      'Fotos sin optimizar que ralentizan la carga',
      'Sin botón de reserva visible en móvil',
      'Página de inicio tarda +5s en cargar',
    ],
  },
};

export async function generateStaticParams() {
  return Object.keys(SECTOR_DATA).map((sector) => ({ sector }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { sector } = await params;
  const data = SECTOR_DATA[sector];
  if (!data) return { title: 'AuditaWeb' };
  return {
    title: `Auditoría web gratis para ${data.name} | AuditaWeb`,
    description: `${data.pain}. Analiza tu web en 90 segundos y descubre por qué pierdes clientes. Gratis, sin registro.`,
  };
}

export default async function SectorPage({ params }: PageProps) {
  const { sector } = await params;
  const data = SECTOR_DATA[sector];

  if (!data) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-400">Sector no encontrado</p>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-50">
      <div className="absolute top-0 z-[-1] h-screen w-screen bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.3),rgba(255,255,255,0))]" />

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pt-24 pb-16 sm:pt-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mb-6 flex justify-center">
            <span className="rounded-full px-4 py-1.5 text-sm font-medium text-indigo-300 ring-1 ring-indigo-500/30 bg-indigo-500/10">
              Auditoría gratuita para {data.name}
            </span>
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl leading-tight mb-6">
            {data.hook}
          </h1>

          <p className="text-lg text-slate-300 font-light mb-10">
            {data.pain}. Descúbrelo en 90 segundos, gratis.
          </p>

          <div className="max-w-xl mx-auto">
            <AuditForm />
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-16 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {data.stats.map((stat, i) => (
            <div key={i} className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
              <p className="text-4xl font-black text-indigo-400 mb-2">{stat.value}</p>
              <p className="text-sm text-slate-400 leading-snug">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Findings preview */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-16 lg:px-8">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-8">
          <h2 className="text-xl font-bold text-white mb-6 text-center">
            Problemas más frecuentes en {data.name}
          </h2>
          <ul className="space-y-3">
            {data.findings.map((f, i) => (
              <li key={i} className="flex items-center gap-3 text-sm text-slate-300">
                <span className="flex-shrink-0 h-5 w-5 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center text-xs font-bold">✕</span>
                {f}
              </li>
            ))}
          </ul>
          <p className="mt-6 text-center text-sm text-slate-500">
            ¿Cuántos tiene tu web?{' '}
            <a href="#top" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">
              Compruébalo gratis →
            </a>
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 py-8 px-6">
        <div className="mx-auto max-w-5xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
          <p>© 2026 AuditaWeb · <a href="https://zero2dev.es" className="hover:text-slate-400 transition-colors">zero2dev.es</a> · Raúl Huete</p>
          <div className="flex gap-4">
            <a href="https://audita.zero2dev.es" className="hover:text-slate-400 transition-colors">← Inicio</a>
            <a href="https://zero2dev.es/privacidad" className="hover:text-slate-400 transition-colors">Privacidad</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
