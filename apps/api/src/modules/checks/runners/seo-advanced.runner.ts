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

    // Broken internal links (sample check: up to 5 internal hrefs)
    if (html) {
      try {
        const base = new URL(ctx.url).origin;
        const internalLinks = [...html.matchAll(/href=["'](\/[^"'#?][^"']*?)["']/gi)]
          .map(m => m[1])
          .filter(href => !href.startsWith('//') && !href.endsWith('.pdf') && !href.endsWith('.zip'))
          .slice(0, 5);

        const brokenLinks: string[] = [];
        await Promise.allSettled(
          internalLinks.map(async (href) => {
            try {
              const res = await fetch(`${base}${href}`, { method: 'HEAD', signal: AbortSignal.timeout(4000) });
              if (res.status === 404) brokenLinks.push(href);
            } catch {
              // timeout / network error — skip
            }
          })
        );

        if (brokenLinks.length > 0) {
          findings.push({
            code: 'SEO_BROKEN_LINKS',
            severity: 'high',
            evidence: { enlaces_rotos: brokenLinks },
          });
        }
      } catch (e) {
        this.logger.warn(`Broken links check failed: ${e}`);
      }
    }

    return findings;
  }
}
