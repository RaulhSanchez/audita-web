'use client';

import { useState } from 'react';
import { AuditRequestDto } from '@repo/shared';

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:3001'
    : 'https://audita-web.onrender.com')
).trim();

const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const SEVERITY_LABEL: Record<string, string> = { critical: 'Crítico', high: 'Alto', medium: 'Medio', low: 'Bajo' };
const SCORE_LABEL: Record<string, string> = {
  performance: 'Rendimiento', seo: 'SEO', security: 'Seguridad',
  accessibility: 'Accesibilidad', mobile: 'Móvil',
};

const SECTORS = [
  'Clínica dental / Fisio / Estética',
  'Hostelería / Restaurante / Bar',
  'Gestoría / Asesoría / Abogado',
  'Comercio local / Tienda',
  'Taller mecánico / Automoción',
  'Inmobiliaria',
  'Otro',
];

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
  const [phone, setPhone] = useState('');
  const [sector, setSector] = useState('');
  const [loading, setLoading] = useState(false);
  const [warming, setWarming] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [teaserEmail, setTeaserEmail] = useState('');
  const [teaserSent, setTeaserSent] = useState(false);
  const [teaserLoading, setTeaserLoading] = useState(false);

  // Retry with exponential backoff — handles Render cold start
  const postWithRetry = async (payload: AuditRequestDto, retries = 4): Promise<any> => {
    for (let i = 0; i < retries; i++) {
      try {
        const res = await fetch(`${API_BASE}/api/audits`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (res.ok) return await res.json();
        if (res.status >= 500 || res.status === 404) {
          if (i === 0) setWarming(true);
          await new Promise(r => setTimeout(r, (i + 1) * 8000));
          continue;
        }
        throw new Error(`Error ${res.status}`);
      } catch (e: any) {
        // CORS / network error = service sleeping
        if (i === 0) setWarming(true);
        if (i < retries - 1) {
          await new Promise(r => setTimeout(r, (i + 1) * 8000));
          continue;
        }
        throw e;
      }
    }
    throw new Error('El servidor no respondió tras varios intentos.');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    setLoading(true);
    setWarming(false);
    setError(null);
    setResult(null);
    setTeaserSent(false);

    try {
      const payload: AuditRequestDto = {
        url,
        email: email || undefined,
        phone: phone || undefined,
        sector: sector || undefined,
      };
      const data = await postWithRetry(payload);
      setWarming(false);
      pollResult(data.id);
    } catch (err: any) {
      setWarming(false);
      setError('No se pudo conectar con el servidor. Espera unos segundos y vuelve a intentarlo.');
      setLoading(false);
    }
  };

  const pollResult = (id: string) => {
    const apiBase = API_BASE;
    const deadline = Date.now() + 5 * 60 * 1000;
    const interval = setInterval(async () => {
      if (Date.now() > deadline) {
        clearInterval(interval);
        setError('La auditoría tardó demasiado. El servidor puede estar arrancando (plan gratuito). Inténtalo de nuevo en 30 segundos.');
        setLoading(false);
        return;
      }
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
        setError('Error al consultar el resultado. Comprueba tu conexión e inténtalo de nuevo.');
        setLoading(false);
      }
    }, 2000);
  };

  const handleTeaserEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!teaserEmail || !result) return;
    setTeaserLoading(true);
    try {
      const apiBase = API_BASE;
      await fetch(`${apiBase}/api/audits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: result.url, email: teaserEmail }),
      });
      setTeaserSent(true);
    } catch {
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
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 w-full">
        {/* URL — full width */}
        <input
          type="url"
          required
          placeholder="https://tuweb.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full rounded-xl bg-white/5 border border-white/10 px-5 py-4 text-white placeholder-slate-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-base shadow-inner"
        />

        {/* Email + teléfono */}
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            placeholder="tu@email.com — recibe el PDF completo"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 rounded-xl bg-white/5 border border-white/10 px-5 py-3.5 text-white placeholder-slate-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-sm shadow-inner"
          />
          <input
            type="tel"
            placeholder="Teléfono (opcional)"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="flex-1 sm:max-w-[180px] rounded-xl bg-white/5 border border-white/10 px-5 py-3.5 text-white placeholder-slate-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-sm shadow-inner"
          />
        </div>

        {/* Sector — dropdown */}
        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="w-full rounded-xl bg-white/5 border border-white/10 px-5 py-3.5 text-sm text-slate-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all shadow-inner appearance-none"
          style={{ colorScheme: 'dark' }}
        >
          <option value="" className="bg-slate-900 text-slate-400">Sector de tu negocio (opcional)</option>
          {SECTORS.map((s) => (
            <option key={s} value={s} className="bg-slate-900 text-white">{s}</option>
          ))}
        </select>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-indigo-600 px-8 py-4 text-white font-semibold hover:bg-indigo-500 active:scale-[0.98] active:bg-indigo-700 transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              {warming ? 'Arrancando servidor (puede tardar ~30s)…' : 'Analizando tu web…'}
            </span>
          ) : 'Auditar mi web gratis →'}
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

          {/* Share bar */}
          {result.publicSlug && (
            <div className="flex items-center justify-between gap-3 rounded-xl bg-white/5 border border-white/10 px-4 py-3">
              <span className="text-xs text-slate-400 truncate hidden sm:block">
                {typeof window !== 'undefined' ? `${window.location.origin}/report?id=${result.publicSlug}` : ''}
              </span>
              <div className="flex gap-2 ml-auto">
                <a
                  href={`/report?id=${result.publicSlug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors whitespace-nowrap"
                >
                  Ver informe completo →
                </a>
                <button
                  onClick={() => navigator.clipboard.writeText(`${window.location.origin}/report?id=${result.publicSlug}`)}
                  className="text-xs font-medium text-slate-400 hover:text-white transition-colors whitespace-nowrap"
                >
                  Copiar enlace
                </button>
              </div>
            </div>
          )}

          {/* Score global + desglose */}
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-violet-500" />
            <h3 className="text-base font-bold text-white mb-4">{result.url}</h3>
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

          {/* Hallazgos */}
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
                  <div className="relative px-4 pt-4 pb-2">
                    <div className="space-y-2 blur-sm pointer-events-none select-none" aria-hidden>
                      {sortedFindings.slice(3, 6).map((_: any, i: number) => (
                        <div key={i} className="h-14 rounded-lg bg-white/5 border border-white/10" />
                      ))}
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-indigo-950/60 to-indigo-950/90" />
                  </div>

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

