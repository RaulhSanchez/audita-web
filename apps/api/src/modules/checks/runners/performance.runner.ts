import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class PerformanceRunner implements CheckRunner {
  code = 'PERF_CORE';
  category = 'performance';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];

    // Response time (TTFB)
    if (ctx.responseTimeMs !== undefined) {
      if (ctx.responseTimeMs > 1500) {
        findings.push({
          code: 'PERF_TTFB_HIGH',
          severity: ctx.responseTimeMs > 3000 ? 'critical' : 'high',
          evidence: { tiempo_ms: Math.round(ctx.responseTimeMs), umbral_ms: 1500 },
        });
      }
    }

    // Page weight (HTML size as proxy)
    if (ctx.htmlSizeBytes !== undefined) {
      const sizeKb = Math.round(ctx.htmlSizeBytes / 1024);
      if (ctx.htmlSizeBytes > 500_000) {
        findings.push({
          code: 'PERF_PAGE_HEAVY',
          severity: ctx.htmlSizeBytes > 1_000_000 ? 'high' : 'medium',
          evidence: { tamanho_kb: sizeKb, umbral_kb: 500 },
        });
      }
    }

    // Inline scripts count (render blocking)
    if (ctx.html) {
      const inlineScripts = (ctx.html.match(/<script(?![^>]*src=)[^>]*>[\s\S]*?<\/script>/gi) || []).length;
      const externalScripts = (ctx.html.match(/<script[^>]+src=/gi) || []).length;
      if (externalScripts > 15) {
        findings.push({
          code: 'PERF_TOO_MANY_SCRIPTS',
          severity: 'medium',
          evidence: { scripts_externos: externalScripts, scripts_inline: inlineScripts },
        });
      }
    }

    // No Cache-Control headers
    const headers = ctx.headers || {};
    const hasCacheControl = !!(headers['cache-control'] || headers['etag'] || headers['last-modified']);
    if (!hasCacheControl) {
      findings.push({
        code: 'PERF_NO_CACHE',
        severity: 'medium',
        evidence: {},
      });
    }

    // No compression (gzip/brotli)
    const contentEncoding = headers['content-encoding'] ?? '';
    const hasCompression = contentEncoding.includes('gzip') || contentEncoding.includes('br') || contentEncoding.includes('deflate');
    if (!hasCompression) {
      findings.push({
        code: 'PERF_NO_COMPRESSION',
        severity: 'medium',
        evidence: { content_encoding: contentEncoding || '(none)' },
      });
    }

    return findings;
  }
}
