'use client';

import { useState } from 'react';
import { AuditRequestDto } from '@repo/shared';

const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const SEVERITY_LABEL: Record<string, string> = { critical: 'Crítico', high: 'Alto', medium: 'Medio', low: 'Bajo' };
const SCORE_LABEL: Record<string, string> = {
  performance: 'Rendimiento', seo: 'SEO', security: 'Seguridad',
  accessibility: 'Accesibilidad', mobile: 'Móvil',
};

function scoreColor(v: number) {
  if (v >= 80) return 'text-emerald-400';
  if (v >= 50) return 'text-amber-400';
  return 'text-red-400';
}

function badgeClass(severity: string) {
  if (severity === 'critical' || severity === 'high')
    return 'bg-red-500/20 text-red-400 border-red-500/30';
  if (severity === 'medium')
    return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
  return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
}

function borderClass(severity: string) {
  if (severity === 'critical' || severity === 'high') return 'border-l-red-500';
  if (severity === 'medium') return 'border-l-amber-500';
  return 'border-l-blue-500';
}

export function AuditForm() {
  const [url, setUrl] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [teaserEmail, setTeaserEmail] = useState('');
  const [teaserSent, setTeaserSent] = useState(false);
  const [teaserLoading, setTeaserLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setTeaserSent(false);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';
      const payload: AuditRequestDto = { url, email: email || undefined };
      const res = await fetch(`${apiBase}/api/audits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Error al iniciar la auditoría');
      const data = await res.json();
      pollResult(data.id);
    } catch (err: any) {
      setError(err.message || 'Error desconocido');
      setLoading(false);
    }
  };

  const pollResult = (id: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/api/audits/${id}`);
        const data = await res.json();
        if (data.status === 'done' || data.status === 'failed') {
          clearInterval(interval);
          setResult(data);
          setLoading(false);
        }
      } catch {
        clearInterval(interval);
        setError('Error al consultar el resultado');
        setLoading(false);
      }
    }, 1000);
  };

  const handleTeaserEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!teaserEmail || !result) return;
    setTeaserLoading(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';
      await fetch(`${apiBase}/api/audits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: result.url, email: teaserEmail }),
      });
      setTeaserSent(true);
    } catch {
      // silent — still show sent state
      setTeaserSent(true);
    } finally {
      setTeaserLoading(false);
    }
  };

  const sortedFindings = result?.findings
    ? [...result.findings].sort((a: any, b: any) =>
        (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
      )
    : [];

  const hasEmail = !!email;
  const previewFindings = hasEmail ? sortedFindings : sortedFindings.slice(0, 3);
  const hiddenCount = hasEmail ? 0 : sortedFindings.length - previewFindings.length;

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="url"
            required
            placeholder="https://tuweb.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 rounded-xl bg-white/5 border border-white/10 px-6 py-4 text-white placeholder-slate-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-lg shadow-inner"
          />
          <input
            type="email"
            placeholder="tu@email.com — recibe el informe completo en PDF"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 rounded-xl bg-white/5 border border-white/10 px-6 py-4 text-white placeholder-slate-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-lg shadow-inner"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-indigo-600 px-8 py-4 text-white font-semibold shadow-lg shadow-indigo-500/30 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-lg"
        >
          {loading ? 'Analizando tu web…' : 'Auditar mi web gratis'}
        </button>
      </form>

      {error && (
        <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-left">
          {error}
        </div>
      )}

      {result?.status === 'failed' && (
        <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-left">
          La auditoría de <strong>{result.url}</strong> no pudo completarse. Comprueba que la URL es accesible e inténtalo de nuevo.
        </div>
      )}

      {result?.status === 'done' && (
        <div className="mt-8 text-left space-y-6">

          {/* Score global + desglose */}
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-violet-500" />
            <h3 className="text-lg font-bold text-white mb-4">{result.url}</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
              <div className="p-3 rounded-xl bg-black/20 border border-white/5 text-center col-span-2 sm:col-span-1">
                <p className="text-xs text-slate-400 mb-1">Global</p>
                <p className={`text-3xl font-bold ${scoreColor(result.globalScore ?? 0)}`}>
                  {result.globalScore ?? '--'}
                </p>
              </div>
              {result.scores && Object.entries(result.scores).map(([key, value]) => (
                <div key={key} className="p-3 rounded-xl bg-black/20 border border-white/5 text-center">
                  <p className="text-xs text-slate-400 mb-1">{SCORE_LABEL[key] ?? key}</p>
                  <p className={`text-2xl font-bold ${scoreColor(value as number)}`}>{value as number}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Hallazgos preview */}
          {sortedFindings.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
                {hasEmail ? `${sortedFindings.length} problemas detectados` : 'Principales problemas detectados'}
              </h4>

              <div className="space-y-3">
                {previewFindings.map((finding: any, i: number) => (
                  <div key={i} className={`p-4 rounded-xl border-l-4 bg-white/5 border border-white/10 ${borderClass(finding.severity)}`}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded border ${badgeClass(finding.severity)}`}>
                        {SEVERITY_LABEL[finding.severity] ?? finding.severity}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-white leading-snug">
                      {finding.title ?? finding.code}
                    </p>
                    {finding.businessImpact && (
                      <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">{finding.businessImpact}</p>
                    )}
                  </div>
                ))}
              </div>

              {/* Teaser — solo si no hay email */}
              {!hasEmail && hiddenCount > 0 && (
                <div className="mt-4 rounded-2xl border border-indigo-500/30 bg-indigo-950/40 overflow-hidden">
                  {/* Blurred previews */}
                  <div className="relative px-4 pt-4 pb-2">
                    <div className="space-y-2 blur-sm pointer-events-none select-none" aria-hidden>
                      {sortedFindings.slice(3, 6).map((_: any, i: number) => (
                        <div key={i} className="h-14 rounded-lg bg-white/5 border border-white/10" />
                      ))}
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-indigo-950/60 to-indigo-950/90" />
                  </div>

                  {/* CTA */}
                  <div className="px-6 pb-6 pt-2 text-center">
                    <p className="text-white font-bold text-lg mb-1">
                      +{hiddenCount} problema{hiddenCount !== 1 ? 's' : ''} más en el análisis completo
                    </p>
                    <p className="text-slate-400 text-sm mb-5">
                      Recibe el informe PDF detallado en tu email — gratis, en menos de 2 minutos.
                    </p>

                    {teaserSent ? (
                      <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium">
                        ¡Listo! Revisa tu bandeja de entrada en unos minutos.
                      </div>
                    ) : (
                      <form onSubmit={handleTeaserEmail} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
                        <input
                          type="email"
                          required
                          placeholder="tu@email.com"
                          value={teaserEmail}
                          onChange={(e) => setTeaserEmail(e.target.value)}
                          className="flex-1 rounded-xl bg-white/5 border border-white/15 px-5 py-3 text-white placeholder-slate-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                        />
                        <button
                          type="submit"
                          disabled={teaserLoading}
                          className="rounded-xl bg-indigo-600 px-6 py-3 text-white font-semibold hover:bg-indigo-500 transition-all disabled:opacity-50 whitespace-nowrap"
                        >
                          {teaserLoading ? 'Enviando…' : 'Recibir PDF gratis'}
                        </button>
                      </form>
                    )}
                  </div>
                </div>
              )}

              {/* Confirmación si hay email */}
              {hasEmail && (
                <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm text-center">
                  El informe PDF completo se ha enviado a <strong>{email}</strong>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
