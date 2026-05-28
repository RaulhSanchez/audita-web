import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class SocialRunner implements CheckRunner {
  code = 'SOC_CORE';
  category = 'social';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    if (!ctx.html) return findings;

    const html = ctx.html;

    // Open Graph: title
    if (!/<meta[^>]+property=["']og:title["'][^>]*>/i.test(html)) {
      findings.push({ code: 'SOC_NO_OG_TITLE', severity: 'medium', evidence: {} });
    }

    // Open Graph: image
    if (!/<meta[^>]+property=["']og:image["'][^>]*>/i.test(html)) {
      findings.push({ code: 'SOC_NO_OG_IMAGE', severity: 'high', evidence: {} });
    }

    // Favicon
    const hasFavicon =
      /<link[^>]+rel=["'][^"']*icon[^"']*["'][^>]*>/i.test(html) ||
      /<link[^>]+rel=["']shortcut icon["'][^>]*>/i.test(html);
    if (!hasFavicon) {
      findings.push({ code: 'SOC_NO_FAVICON', severity: 'low', evidence: {} });
    }

    // CTA above-fold approximation: check for at least one prominent contact button
    const lower = html.toLowerCase();
    const hasCta =
      lower.includes('href="tel:') ||
      lower.includes("href='tel:") ||
      lower.includes('wa.me') ||
      lower.includes('contacto') ||
      lower.includes('presupuesto') ||
      lower.includes('llamar') ||
      lower.includes('cita');
    if (!hasCta) {
      findings.push({ code: 'SOC_NO_CTA', severity: 'high', evidence: {} });
    }

    return findings;
  }
}
