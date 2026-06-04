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
  if (v >= 80) return 'text-emerald-600';
  if (v >= 50) return 'text-amber-600';
  return 'text-red-600';
}

function badgeClass(severity: string) {
  if (severity === 'critical' || severity === 'high')
    return 'bg-red-50 text-red-700 border-red-200';
  if (severity === 'medium')
    return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-blue-50 text-blue-700 border-blue-200';
}

function borderClass(severity: string) {
  if (severity === 'critical' || severity === 'high') return 'border-l-red-500';
  if (severity === 'medium') return 'border-l-amber-500';
  return 'border-l-blue-400';
}

export function AuditForm({ ctaVariant }: { ctaVariant?: 'light' } = {}) {
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

  const inputCls = "w-full rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 text-gray-900 placeholder-gray-400 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all duration-200 text-sm";

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 w-full">
        <input
          type="url"
          required
          placeholder="https://tuweb.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className={inputCls}
        />

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            placeholder="tu@email.com — recibe el PDF"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={`flex-1 ${inputCls}`}
          />
          <input
            type="tel"
            placeholder="Teléfono (opcional)"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className={`flex-1 sm:max-w-[170px] ${inputCls}`}
          />
        </div>

        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className={`${inputCls} text-gray-500`}
        >
          <option value="">Sector de tu negocio (opcional)</option>
          {SECTORS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-indigo-600 px-6 py-3.5 text-white text-sm font-semibold hover:bg-indigo-700 active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 shadow-sm"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              {warming ? 'Arrancando servidor (~30s)…' : 'Analizando tu web…'}
            </span>
          ) : 'Auditar mi web gratis →'}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {result?.status === 'failed' && (
        <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          La auditoría de <strong>{result.url}</strong> no pudo completarse. Comprueba que la URL es accesible e inténtalo de nuevo.
        </div>
      )}

      {result?.status === 'done' && (
        <div className="mt-6 text-left space-y-5">

          {/* Share bar */}
          {result.publicSlug && (
            <div className="flex items-center justify-between gap-3 rounded-lg bg-gray-50 border border-gray-200 px-4 py-2.5">
              <span className="text-xs text-gray-400 truncate hidden sm:block">
                {typeof window !== 'undefined' ? `${window.location.origin}/report?id=${result.publicSlug}` : ''}
              </span>
              <div className="flex gap-3 ml-auto">
                <a
                  href={`/report?id=${result.publicSlug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors whitespace-nowrap"
                >
                  Ver informe completo →
                </a>
                <button
                  onClick={() => navigator.clipboard.writeText(`${window.location.origin}/report?id=${result.publicSlug}`)}
                  className="text-xs font-medium text-gray-400 hover:text-gray-700 transition-colors whitespace-nowrap"
                >
                  Copiar enlace
                </button>
              </div>
            </div>
          )}

          {/* Score global + desglose */}
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm overflow-hidden">
            <div className="h-1 bg-indigo-600 w-full" />
            <div className="p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-4 truncate">{result.url}</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                <div className="p-3 rounded-lg bg-gray-50 border border-gray-100 text-center col-span-2 sm:col-span-1">
                  <p className="text-[10px] text-gray-400 mb-1 uppercase tracking-wider font-medium">Global</p>
                  <p className={`text-4xl font-black tabular-nums ${scoreColor(result.globalScore ?? 0)}`}>
                    {result.globalScore ?? '--'}
                  </p>
                </div>
                {result.scores && Object.entries(result.scores).map(([key, value]) => (
                  <div key={key} className="p-3 rounded-lg bg-gray-50 border border-gray-100 text-center">
                    <p className="text-[10px] text-gray-400 mb-1">{SCORE_LABEL[key] ?? key}</p>
                    <p className={`text-2xl font-bold ${scoreColor(value as number)}`}>{value as number}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Hallazgos */}
          {sortedFindings.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                {hasEmail ? `${sortedFindings.length} problemas detectados` : 'Principales problemas detectados'}
              </h4>

              <div className="space-y-2">
                {previewFindings.map((finding: any, i: number) => (
                  <div key={i} className={`p-4 rounded-xl border-l-4 bg-white border border-gray-100 shadow-sm hover:-translate-y-px transition-all duration-200 ${borderClass(finding.severity)}`}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${badgeClass(finding.severity)}`}>
                        {SEVERITY_LABEL[finding.severity] ?? finding.severity}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 leading-snug">
                      {finding.title ?? finding.code}
                    </p>
                    {finding.businessImpact && (
                      <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">{finding.businessImpact}</p>
                    )}
                  </div>
                ))}
              </div>

              {/* Teaser — solo si no hay email */}
              {!hasEmail && hiddenCount > 0 && (
                <div className="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50 overflow-hidden">
                  <div className="relative px-4 pt-4 pb-2">
                    <div className="space-y-2 blur-sm pointer-events-none select-none" aria-hidden>
                      {sortedFindings.slice(3, 6).map((_: any, i: number) => (
                        <div key={i} className="h-14 rounded-lg bg-white border border-gray-100" />
                      ))}
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-indigo-50/60 to-indigo-50" />
                  </div>

                  <div className="px-6 pb-6 pt-2 text-center">
                    <p className="text-gray-900 font-bold text-lg mb-1">
                      +{hiddenCount} problema{hiddenCount !== 1 ? 's' : ''} más en el análisis completo
                    </p>
                    <p className="text-gray-500 text-sm mb-5">
                      Recibe el informe PDF detallado en tu email, gratis, en menos de 2 minutos.
                    </p>

                    {teaserSent ? (
                      <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm font-medium">
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
                          className="flex-1 rounded-lg bg-white border border-gray-200 px-4 py-3 text-gray-900 placeholder-gray-400 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all text-sm"
                        />
                        <button
                          type="submit"
                          disabled={teaserLoading}
                          className="rounded-lg bg-indigo-600 px-6 py-3 text-white text-sm font-semibold hover:bg-indigo-700 active:scale-[0.98] transition-all disabled:opacity-50 whitespace-nowrap"
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
                <div className="mt-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm text-center">
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

