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

    // HTTPS check
    if (!url.startsWith('https://')) {
      findings.push({ code: 'SEC_NO_HTTPS', severity: 'critical', evidence: { url } });
    }

    // Security headers
    const securityHeaders = [
      { key: 'x-content-type-options', code: 'SEC_NO_XCTO' },
      { key: 'x-frame-options', code: 'SEC_NO_XFO' },
      { key: 'content-security-policy', code: 'SEC_NO_CSP' },
      { key: 'strict-transport-security', code: 'SEC_NO_HSTS' },
    ];

    for (const { key, code } of securityHeaders) {
      const headerValue = headers[key] || headers[key.toLowerCase()];
      if (!headerValue) {
        findings.push({
          code,
          severity: code === 'SEC_NO_HSTS' || code === 'SEC_NO_CSP' ? 'high' : 'medium',
          evidence: { missing_header: key },
        });
      }
    }

    return findings;
  }
}
