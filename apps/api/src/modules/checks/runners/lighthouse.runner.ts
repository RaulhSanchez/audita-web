import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class LighthouseRunner implements CheckRunner {
  code = 'LH_CORE';
  category = 'performance';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    if (!ctx.lighthouse) return findings;

    const categories = ctx.lighthouse.categories;
    if (categories?.performance?.score !== null) {
      const score = categories.performance.score * 100;
      if (score < 50) {
        findings.push({
          code: 'PERF_SCORE_LOW',
          severity: 'critical',
          evidence: { score },
        });
      } else if (score < 90) {
        findings.push({
          code: 'PERF_SCORE_MED',
          severity: 'medium',
          evidence: { score },
        });
      }
    }

    // LCP check
    const lcp = ctx.lighthouse.audits?.['largest-contentful-paint']?.numericValue;
    if (lcp && lcp > 2500) {
      findings.push({
        code: 'PERF_LCP_HIGH',
        severity: lcp > 4000 ? 'critical' : 'medium',
        evidence: { lcp_ms: lcp },
      });
    }

    return findings;
  }
}
