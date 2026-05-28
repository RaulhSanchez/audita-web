'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

const SCORE_LABEL: Record<string, string> = {
  performance: 'Rendimiento', seo: 'SEO', security: 'Seguridad',
  accessibility: 'Accesibilidad', mobile: 'Móvil',
};

function scoreColor(v: number) {
  if (v >= 80) return 'text-emerald-400';
  if (v >= 50) return 'text-amber-400';
  return 'text-red-400';
}

function ReportContent() {
  const searchParams = useSearchParams();
  const slug = searchParams.get('id');
  const [audit, setAudit] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!slug) { setNotFound(true); setLoading(false); return; }
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';
    fetch(`${apiBase}/api/audits/public/${slug}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) setNotFound(true);
        else setAudit(data);
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-400 text-lg animate-pulse">Cargando informe…</p>
      </main>
    );
  }

  if (notFound) {
    return (
      <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4">
        <p className="text-white text-2xl font-bold">Informe no encontrado</p>
        <a href="/" className="text-indigo-400 hover:text-indigo-300 text-sm">← Audita tu web</a>
      </main>
    );
  }

  const severityLabel: Record<string, string> = { critical: 'Crítico', high: 'Alto', medium: 'Medio', low: 'Bajo' };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 py-20 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <a href="/" className="text-indigo-400 hover:text-indigo-300 text-sm font-medium">← Volver a AuditaWeb</a>
        </div>

        <header className="mb-12 border-b border-white/10 pb-8">
          <h1 className="text-4xl font-bold mb-4">Resultados de Auditoría</h1>
          <p className="text-xl text-slate-400">{audit.url}</p>
          {audit.createdAt && (
            <p className="text-sm text-slate-500 mt-2">
              {new Date(audit.createdAt).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          )}
        </header>

        <div className="grid md:grid-cols-2 gap-6 mb-12">
          <div className="bg-white/5 rounded-2xl p-8 border border-white/10 text-center flex flex-col justify-center items-center">
            <p className="text-slate-400 uppercase tracking-widest text-xs mb-4">Puntuación Global</p>
            <p className={`text-7xl font-black ${scoreColor(audit.globalScore)}`}>{audit.globalScore}</p>
            <p className="text-slate-500 mt-2 text-sm">sobre 100</p>
          </div>

          <div className="bg-white/5 rounded-2xl p-8 border border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-5">Desglose por área</h3>
            <div className="space-y-3">
              {audit.scores && Object.entries(audit.scores).map(([key, value]: [string, any]) => (
                <div key={key} className="flex justify-between items-center">
                  <span className="text-slate-300 text-sm">{SCORE_LABEL[key] ?? key}</span>
                  <span className={`font-bold text-sm ${scoreColor(value)}`}>{value}/100</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {audit.narrative && (
          <div className="mb-12 bg-indigo-950/30 rounded-2xl p-8 border border-indigo-500/30">
            <h2 className="text-xl font-bold mb-4 text-indigo-300">Diagnóstico de negocio</h2>
            <p className="text-slate-300 whitespace-pre-wrap text-sm leading-relaxed">
              {audit.narrative.replace(/^#{1,6}\s+/gm, '').replace(/\*\*(.+?)\*\*/g, '$1').trim()}
            </p>
          </div>
        )}

        {audit.findings?.length > 0 && (
          <div>
            <h2 className="text-xl font-bold mb-6">Principales problemas detectados</h2>
            <div className="space-y-4 mb-8">
              {[...audit.findings]
                .sort((a: any, b: any) => {
                  const o: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
                  return (o[a.severity] ?? 9) - (o[b.severity] ?? 9);
                })
                .slice(0, 3)
                .map((finding: any, i: number) => {
                  const isUrgent = finding.severity === 'critical' || finding.severity === 'high';
                  return (
                    <div key={i} className={`bg-white/5 rounded-xl p-5 border border-white/10 border-l-4 ${isUrgent ? 'border-l-red-500' : finding.severity === 'medium' ? 'border-l-amber-500' : 'border-l-blue-500'}`}>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${isUrgent ? 'bg-red-500/20 text-red-400' : finding.severity === 'medium' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
                        {severityLabel[finding.severity] ?? finding.severity}
                      </span>
                      <h3 className="font-semibold text-white mt-2 mb-1">{finding.title ?? finding.code}</h3>
                      {finding.businessImpact && (
                        <p className="text-sm text-slate-400">{finding.businessImpact}</p>
                      )}
                    </div>
                  );
                })}
            </div>

            <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/40 p-8 text-center">
              <p className="text-white font-bold text-xl mb-2">
                {audit.findings.length > 3
                  ? `+${audit.findings.length - 3} problemas más en el informe completo`
                  : '¿Quieres que lo resuelva todo?'}
              </p>
              <p className="text-slate-400 text-sm mb-6">
                El informe PDF completo con todos los hallazgos y su impacto en tu negocio — o escríbeme directamente.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <a href="/" className="rounded-xl bg-indigo-600 px-6 py-3 text-white font-semibold hover:bg-indigo-500 transition-all text-sm">
                  Audita otra web
                </a>
                <a href="mailto:raaul9212@gmail.com" className="rounded-xl bg-white/10 border border-white/15 px-6 py-3 text-white font-semibold hover:bg-white/15 transition-all text-sm">
                  Contactar con Raúl
                </a>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default function PublicReportPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-400 text-lg animate-pulse">Cargando informe…</p>
      </main>
    }>
      <ReportContent />
    </Suspense>
  );
}
