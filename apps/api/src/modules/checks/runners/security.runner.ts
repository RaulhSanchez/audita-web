import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class SecurityRunner implements CheckRunner {
  code = 'SEC_CORE';
  category = 'security';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    const headers = ctx.headers || {};
    const url = ctx.url;
    const isHttps = url.startsWith('https://');

    // HTTPS
    if (!isHttps) {
      findings.push({ code: 'SEC_NO_HTTPS', severity: 'critical', evidence: { url } });
    }

    // Mixed content (HTTP resources on HTTPS page)
    if (isHttps && ctx.html) {
      const httpSrcs = (ctx.html.match(/(?:src|href)=["']http:\/\/[^"']+["']/gi) || [])
        .filter(m => !m.includes('http://localhost'))
        .slice(0, 5);
      if (httpSrcs.length > 0) {
        findings.push({ code: 'SEC_MIXED_CONTENT', severity: 'high', evidence: { ejemplos: httpSrcs.length, recursos: httpSrcs.slice(0, 3) } });
      }
    }

    // Security headers
    const secHeaders = [
      { key: 'strict-transport-security', code: 'SEC_NO_HSTS', severity: 'high' as const },
      { key: 'content-security-policy', code: 'SEC_NO_CSP', severity: 'medium' as const },
      { key: 'x-content-type-options', code: 'SEC_NO_XCTO', severity: 'low' as const },
      { key: 'x-frame-options', code: 'SEC_NO_XFO', severity: 'low' as const },
    ];

    for (const h of secHeaders) {
      if (!headers[h.key]) {
        findings.push({ code: h.code, severity: h.severity, evidence: { header: h.key } });
      }
    }

    // Server header exposed (info leak)
    if (headers['server'] && headers['server'].length > 5) {
      findings.push({ code: 'SEC_SERVER_EXPOSED', severity: 'low', evidence: { server: headers['server'] } });
    }

    return findings;
  }
}
