import { Injectable, Logger } from '@nestjs/common';
import { CheckContext, Finding } from '../interfaces';
import { LighthouseRunner } from '../runners/lighthouse.runner';
import { SeoRunner } from '../runners/seo.runner';
import { SeoAdvancedRunner } from '../runners/seo-advanced.runner';
import { SecurityRunner } from '../runners/security.runner';
import { MobileRunner } from '../runners/mobile.runner';
import { SocialRunner } from '../runners/social.runner';
import { LegalRunner } from '../runners/legal.runner';
import { PerformanceRunner } from '../runners/performance.runner';

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
    private readonly performanceRunner: PerformanceRunner,
  ) {}

  async runAll(url: string): Promise<{ findings: Finding[]; scores: Record<string, number>; globalScore: number; pageStats: Record<string, number> }> {
    const findings: Finding[] = [];
    const scores: Record<string, number> = {};

    // Fetch HTML + measure TTFB
    let html = '';
    let headers: Record<string, string> = {};
    let responseTimeMs = 0;
    let htmlSizeBytes = 0;
    try {
      const t0 = Date.now();
      const res = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0 (compatible; AuditBot/1.0)' },
        signal: AbortSignal.timeout(15000),
      });
      html = await res.text();
      responseTimeMs = Date.now() - t0;
      htmlSizeBytes = Buffer.byteLength(html, 'utf8');
      res.headers.forEach((value, key) => { headers[key.toLowerCase()] = value; });
      this.logger.log(`Fetched HTML for ${url} (${htmlSizeBytes} bytes, ${responseTimeMs}ms)`);
    } catch (e) {
      this.logger.warn(`Could not fetch HTML for ${url}: ${e}`);
    }

    const ctx: CheckContext = { url, html, headers, responseTimeMs, htmlSizeBytes };

    // 1. Lighthouse (optional)
    try {
      if (process.env.PUPPETEER_SKIP_DOWNLOAD === 'true') {
        throw new Error('Lighthouse skipped: PUPPETEER_SKIP_DOWNLOAD=true');
      }
      const lighthouse = (await import('lighthouse')).default;
      const chromeLauncher = await import('chrome-launcher');
      const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--no-zygote'] });
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
    const [lhFindings, seoFindings, seoAdvFindings, secFindings, mobFindings, socFindings, legFindings, perfFindings] =
      await Promise.all([
        this.lighthouseRunner.run(ctx),
        this.seoRunner.run(ctx),
        this.seoAdvancedRunner.run(ctx),
        this.securityRunner.run(ctx),
        this.mobileRunner.run(ctx),
        this.socialRunner.run(ctx),
        this.legalRunner.run(ctx),
        this.performanceRunner.run(ctx),
      ]);

    findings.push(...lhFindings, ...seoFindings, ...seoAdvFindings, ...secFindings, ...mobFindings, ...socFindings, ...legFindings, ...perfFindings);

    // 3. Derived scores (penalización por findings)
    const pen = (arr: Finding[]) =>
      arr.filter(f => f.severity === 'critical').length * 25 +
      arr.filter(f => f.severity === 'high').length * 12 +
      arr.filter(f => f.severity === 'medium').length * 6;

    if (!scores.security) scores.security = Math.max(0, 100 - pen(secFindings));
    if (!scores.mobile)   scores.mobile   = Math.max(0, 100 - pen(mobFindings));
    if (!scores.seo)      scores.seo      = Math.max(0, 100 - pen([...seoFindings, ...seoAdvFindings]));

    // 4. Global score
    const available = Object.values(scores).filter(s => s > 0);
    const globalScore = available.length > 0
      ? Math.round(available.reduce((a, b) => a + b, 0) / available.length)
      : 50;

    const pageStats = { responseTimeMs: Math.round(responseTimeMs), htmlSizeKb: Math.round(htmlSizeBytes / 1024) };

    this.logger.log(`Scores: ${JSON.stringify(scores)} → global=${globalScore} findings=${findings.length}`);
    return { findings, scores, globalScore, pageStats };
  }
}
