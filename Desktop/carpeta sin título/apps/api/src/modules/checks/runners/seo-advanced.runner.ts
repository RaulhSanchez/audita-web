import { Injectable, Logger } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class SeoAdvancedRunner implements CheckRunner {
  code = 'SEO_ADV_CORE';
  category = 'seo';
  private readonly logger = new Logger(SeoAdvancedRunner.name);

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    if (!ctx.html) return findings;

    const html = ctx.html;

    // Canonical tag
    if (!/<link[^>]+rel=["']canonical["'][^>]*>/i.test(html)) {
      findings.push({ code: 'SEO_NO_CANONICAL', severity: 'medium', evidence: {} });
    }

    // Schema.org structured data
    const hasSchema =
      html.includes('application/ld+json') ||
      /itemtype=["']https?:\/\/schema\.org/i.test(html);
    if (!hasSchema) {
      findings.push({ code: 'SEO_NO_SCHEMA', severity: 'medium', evidence: {} });
    }

    // robots.txt & sitemap.xml — fetch from root of domain
    try {
      const base = new URL(ctx.url).origin;

      const [robotsRes, sitemapRes] = await Promise.allSettled([
        fetch(`${base}/robots.txt`, { signal: AbortSignal.timeout(5000) }),
        fetch(`${base}/sitemap.xml`, { signal: AbortSignal.timeout(5000) }),
      ]);

      if (robotsRes.status === 'rejected' || (robotsRes.status === 'fulfilled' && !robotsRes.value.ok)) {
        findings.push({ code: 'SEO_NO_ROBOTS', severity: 'medium', evidence: { url: `${base}/robots.txt` } });
      }

      if (sitemapRes.status === 'rejected' || (sitemapRes.status === 'fulfilled' && !sitemapRes.value.ok)) {
        findings.push({ code: 'SEO_NO_SITEMAP', severity: 'medium', evidence: { url: `${base}/sitemap.xml` } });
      }
    } catch (e) {
      this.logger.warn(`Could not check robots.txt / sitemap.xml: ${e}`);
    }

    return findings;
  }
}
