import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class LegalRunner implements CheckRunner {
  code = 'LEG_CORE';
  category = 'legal';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    if (!ctx.html) return findings;

    const lower = ctx.html.toLowerCase();

    // Cookie banner
    const hasCookieBanner =
      lower.includes('cookie') &&
      (lower.includes('aceptar') ||
        lower.includes('accept') ||
        lower.includes('consent') ||
        lower.includes('consentimiento') ||
        lower.includes('cookie-banner') ||
        lower.includes('cookiebanner') ||
        lower.includes('cookie_banner') ||
        lower.includes('rgpd') ||
        lower.includes('gdpr'));
    if (!hasCookieBanner) {
      findings.push({ code: 'LEG_NO_COOKIE_BANNER', severity: 'high', evidence: {} });
    }

    // Privacy policy link
    const hasPrivacy =
      lower.includes('política de privacidad') ||
      lower.includes('politica de privacidad') ||
      lower.includes('privacy policy') ||
      lower.includes('privacidad') ||
      lower.includes('href') && lower.includes('privaci');
    if (!hasPrivacy) {
      findings.push({ code: 'LEG_NO_PRIVACY', severity: 'high', evidence: {} });
    }

    // Legal notice (aviso legal)
    const hasLegal =
      lower.includes('aviso legal') ||
      lower.includes('términos') ||
      lower.includes('terminos') ||
      lower.includes('condiciones de uso') ||
      lower.includes('términos y condiciones');
    if (!hasLegal) {
      findings.push({ code: 'LEG_NO_LEGAL', severity: 'medium', evidence: {} });
    }

    // SSL certificate check: detect expired/missing via HTTP-only URL
    const isHttps = ctx.url?.startsWith('https://');
    if (!isHttps) {
      findings.push({ code: 'LEG_NO_SSL_VALID', severity: 'critical', evidence: { url: ctx.url } });
    }

    return findings;
  }
}
