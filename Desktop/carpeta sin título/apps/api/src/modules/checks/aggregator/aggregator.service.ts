import { Injectable, Logger } from '@nestjs/common';
import { CheckContext, Finding } from '../interfaces';
import { LighthouseRunner } from '../runners/lighthouse.runner';
import { SeoRunner } from '../runners/seo.runner';
import { SeoAdvancedRunner } from '../runners/seo-advanced.runner';
import { SecurityRunner } from '../runners/security.runner';
import { MobileRunner } from '../runners/mobile.runner';
import { SocialRunner } from '../runners/social.runner';
import { LegalRunner } from '../runners/legal.runner';

@Injectable()
export class AggregatorService {
  private readonly logger = new Logger(AggregatorService.name);

  constructor(
    private readonly lighthouseRunner: LighthouseRunner,
    private readonly seoRunner: SeoRunner,
    private readonly seoAdvancedRunner: SeoAdvancedRunner,
    private readonly securityRunner: SecurityRunner,
    private readonly mobileRunner: MobileRunner,
    private readonly socialRunner: SocialRunner,
    private readonly legalRunner: LegalRunner,
  ) {}

  async runAll(url: string): Promise<{ findings: Finding[]; scores: Record<string, number>; globalScore: number }> {
    const findings: Finding[] = [];
    const scores: Record<string, number> = {};

    // Fetch HTML and headers (shared across all custom runners)
    let html = '';
    let headers: Record<string, string> = {};
    try {
      const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 (compatible; AuditBot/1.0)' } });
      html = await res.text();
      res.headers.forEach((value, key) => { headers[key.toLowerCase()] = value; });
      this.logger.log(`Fetched HTML for ${url} (${html.length} bytes)`);
    } catch (e) {
      this.logger.warn(`Could not fetch HTML for ${url}: ${e}`);
    }

    const ctx: CheckContext = { url, html, headers };

    // 1. Lighthouse (optional)
    try {
      const lighthouse = (await import('lighthouse')).default;
      const chromeLauncher = await import('chrome-launcher');
      const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless', '--no-sandbox', '--disable-gpu'] });
      const runnerResult = await lighthouse(url, {
        logLevel: 'error' as const,
        output: 'json' as const,
        onlyCategories: ['performance', 'accessibility', 'seo'],
        port: chrome.port,
      });
      await chrome.kill();
      ctx.lighthouse = runnerResult?.lhr;
      if (runnerResult?.lhr?.categories) {
        scores.performance   = Math.round((runnerResult.lhr.categories.performance?.score   ?? 0) * 100);
        scores.seo           = Math.round((runnerResult.lhr.categories.seo?.score           ?? 0) * 100);
        scores.accessibility = Math.round((runnerResult.lhr.categories.accessibility?.score ?? 0) * 100);
      }
      this.logger.log(`Lighthouse done — perf=${scores.performance} seo=${scores.seo} a11y=${scores.accessibility}`);
    } catch (e) {
      this.logger.warn(`Lighthouse failed — continuing: ${e}`);
    }

    // 2. All custom runners in parallel
    const [lhFindings, seoFindings, seoAdvFindings, secFindings, mobFindings, socFindings, legFindings] =
      await Promise.all([
        this.lighthouseRunner.run(ctx),
        this.seoRunner.run(ctx),
        this.seoAdvancedRunner.run(ctx),
        this.securityRunner.run(ctx),
        this.mobileRunner.run(ctx),
        this.socialRunner.run(ctx),
        this.legalRunner.run(ctx),
      ]);

    findings.push(...lhFindings, ...seoFindings, ...seoAdvFindings, ...secFindings, ...mobFindings, ...socFindings, ...legFindings);

    // 3. Compute derived scores
    const severity = (arr: Finding[], s: string) => arr.filter((f) => f.severity === s).length;

    scores.security = Math.max(0, 100
      - severity(secFindings, 'critical') * 30
      - severity(secFindings, 'high') * 15
      - severity(secFindings, 'medium') * 8);

    scores.mobile = Math.max(0, 100
      - severity(mobFindings, 'critical') * 30
      - severity(mobFindings, 'high') * 15
      - severity(mobFindings, 'medium') * 8);

    // 4. Global score — average of all non-zero scores
    const available = Object.values(scores).filter((s) => s > 0);
    const globalScore = available.length > 0
      ? Math.round(available.reduce((a, b) => a + b, 0) / available.length)
      : 0;

    this.logger.log(`Scores: ${JSON.stringify(scores)} → global=${globalScore} findings=${findings.length}`);
    return { findings, scores, globalScore };
  }
}
