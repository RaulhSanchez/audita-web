#!/usr/bin/env node
/**
 * batch-audit.js
 *
 * Lee la columna "Web" de scripts/leads.csv, audita cada URL via el endpoint
 * interno de la API y rellena Score, Hallazgo_1-3 y PDF_URL.
 *
 * Uso:
 *   node scripts/batch-audit.js
 *
 * Requisitos:
 *   - API corriendo en localhost:3001 (pnpm --filter api dev)
 *   - INTERNAL_API_KEY en apps/api/.env
 *   - leads.csv con columna "Web" rellena
 *
 * Opciones de entorno:
 *   API_BASE   URL base de la API  (default: http://localhost:3001)
 *   API_KEY    clave interna       (default: auditaweb-local-2026)
 *   CONCURRENCY auditorías en paralelo (default: 2)
 */

const fs = require('fs');
const path = require('path');

const API_BASE    = process.env.API_BASE  || 'http://localhost:3001';
const API_KEY     = process.env.API_KEY   || 'auditaweb-local-2026';
const CONCURRENCY = parseInt(process.env.CONCURRENCY || '2', 10);
const CSV_PATH    = path.join(__dirname, 'leads.csv');
const POLL_MS     = 3000;
const TIMEOUT_MS  = 5 * 60 * 1000;

// ── CSV helpers ──────────────────────────────────────────────────────────────

function parseCsv(text) {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const vals = splitCsvLine(line);
    const row = {};
    headers.forEach((h, i) => { row[h] = (vals[i] ?? '').trim(); });
    return row;
  });
}

function splitCsvLine(line) {
  const result = [];
  let cur = '';
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') { inQuote = !inQuote; continue; }
    if (ch === ',' && !inQuote) { result.push(cur); cur = ''; continue; }
    cur += ch;
  }
  result.push(cur);
  return result;
}

function toCsv(rows) {
  if (!rows.length) return '';
  const headers = Object.keys(rows[0]);
  const escape = v => {
    const s = String(v ?? '');
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [
    headers.join(','),
    ...rows.map(r => headers.map(h => escape(r[h])).join(','))
  ].join('\n') + '\n';
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function startAudit(url) {
  const res = await fetch(`${API_BASE}/api/audits/internal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return await res.json();
}

async function pollAudit(id) {
  const deadline = Date.now() + TIMEOUT_MS;
  while (Date.now() < deadline) {
    await sleep(POLL_MS);
    const res = await fetch(`${API_BASE}/api/audits/${id}`);
    if (!res.ok) continue;
    const data = await res.json();
    if (data.status === 'done' || data.status === 'failed') return data;
  }
  throw new Error('Timeout esperando resultado');
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// ── Audit one row ─────────────────────────────────────────────────────────────

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

async function auditRow(row, index, total) {
  const url = row['Web'];
  if (!url || url === '-' || !url.startsWith('http')) {
    console.log(`[${index}/${total}] SKIP — sin URL: ${row['Empresa']}`);
    return row;
  }

  console.log(`[${index}/${total}] Auditando: ${url}`);

  try {
    const { id } = await startAudit(url);
    const result  = await pollAudit(id);

    if (result.status === 'failed') {
      console.log(`  ✗ Falló: ${url}`);
      row['Score'] = 'ERROR';
      row['Estado'] = row['Estado'] || 'Pendiente';
      return row;
    }

    const findings = Array.isArray(result.findings) ? result.findings : [];
    const sorted = findings.sort((a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
    );

    const fmt = f => f ? `[${f.severity?.toUpperCase()}] ${f.title ?? f.code}` : '';

    row['Score']      = result.globalScore ?? '--';
    row['Hallazgo_1'] = fmt(sorted[0]);
    row['Hallazgo_2'] = fmt(sorted[1]);
    row['Hallazgo_3'] = fmt(sorted[2]);
    row['PDF_URL']    = `${API_BASE}/api/audits/${id}/pdf`;

    const score = result.globalScore ?? 100;
    const stars = score < 50 ? '🔴' : score < 75 ? '🟡' : '🟢';
    console.log(`  ${stars} Score ${score} | ${findings.length} hallazgos`);

  } catch (err) {
    console.error(`  ✗ Error en ${url}:`, err.message);
    row['Score'] = 'ERROR';
    row['Notas'] = err.message;
  }

  return row;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  if (!fs.existsSync(CSV_PATH)) {
    console.error('No se encuentra scripts/leads.csv');
    process.exit(1);
  }

  // Check API is up
  try {
    const check = await fetch(`${API_BASE}/api/audits/health-check-fake`).catch(() => null);
    if (!check) throw new Error('no responde');
  } catch {
    console.error(`\n⚠️  La API no responde en ${API_BASE}`);
    console.error('   Arranca la API primero: pnpm --filter api dev\n');
    process.exit(1);
  }

  const text = fs.readFileSync(CSV_PATH, 'utf8');
  const rows = parseCsv(text);

  const pending = rows.filter(r => {
    const web = r['Web'];
    return web && web.startsWith('http') && (!r['Score'] || r['Score'] === '-' || r['Score'] === '');
  });

  console.log(`\n🔍 ${pending.length} URLs pendientes de auditar (total filas: ${rows.length})\n`);

  if (pending.length === 0) {
    console.log('Nada que auditar. Rellena la columna "Web" en leads.csv y vuelve a ejecutar.\n');
    process.exit(0);
  }

  // Process in batches of CONCURRENCY
  let done = 0;
  for (let i = 0; i < rows.length; i += CONCURRENCY) {
    const batch = rows.slice(i, i + CONCURRENCY);
    await Promise.all(
      batch.map((row, j) => {
        const idx = i + j + 1;
        return auditRow(row, idx, rows.length);
      })
    );
    // Write after each batch so progress is saved even if interrupted
    fs.writeFileSync(CSV_PATH, toCsv(rows), 'utf8');
    done += batch.filter(r => r['Score'] && r['Score'] !== '-').length;
  }

  console.log(`\n✅ Hecho. ${done} auditorías completadas.`);
  console.log(`📄 Resultados guardados en: scripts/leads.csv\n`);

  // Print summary sorted by score
  const auditados = rows
    .filter(r => r['Score'] && !isNaN(Number(r['Score'])))
    .sort((a, b) => Number(a['Score']) - Number(b['Score']));

  if (auditados.length) {
    console.log('━━━ RANKING (peores primero) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    auditados.forEach(r => {
      const s = Number(r['Score']);
      const star = s < 50 ? '🔴' : s < 75 ? '🟡' : '🟢';
      console.log(`${star} ${String(s).padStart(3)}  ${r['Empresa'] || r['Web']}`);
      if (r['Hallazgo_1']) console.log(`      ${r['Hallazgo_1']}`);
    });
    console.log('');
  }
}

main().catch(err => { console.error(err); process.exit(1); });
