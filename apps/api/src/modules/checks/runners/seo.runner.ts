import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class SeoRunner implements CheckRunner {
  code = 'SEO_CORE';
  category = 'seo';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    if (!ctx.html) return findings;

    const html = ctx.html;

    // H1 check
    const h1Matches = html.match(/<h1[^>]*>/gi);
    if (!h1Matches || h1Matches.length === 0) {
      findings.push({ code: 'SEO_NO_H1', severity: 'high', evidence: {} });
    } else if (h1Matches.length > 1) {
      findings.push({ code: 'SEO_MULTIPLE_H1', severity: 'medium', evidence: { count: h1Matches.length } });
    }

    // Meta description
    const metaDesc = html.match(/<meta[^>]+name=["']description["'][^>]*>/i);
    if (!metaDesc) {
      findings.push({ code: 'SEO_NO_META_DESC', severity: 'high', evidence: {} });
    }

    // Title
    const title = html.match(/<title[^>]*>(.*?)<\/title>/i);
    if (!title) {
      findings.push({ code: 'SEO_NO_TITLE', severity: 'critical', evidence: {} });
    } else if (title[1].length < 30 || title[1].length > 60) {
      findings.push({
        code: 'SEO_TITLE_LENGTH',
        severity: 'low',
        evidence: { length: title[1].length },
      });
    }

    // Images without alt
    const imgMatches = html.match(/<img[^>]*>/gi) || [];
    const imgsWithoutAlt = imgMatches.filter((img) => !img.includes('alt='));
    if (imgsWithoutAlt.length > 0) {
      findings.push({
        code: 'SEO_IMG_NO_ALT',
        severity: 'medium',
        evidence: { count: imgsWithoutAlt.length },
      });
    }

    return findings;
  }
}
