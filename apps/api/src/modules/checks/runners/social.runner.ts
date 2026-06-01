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
    const lower = html.toLowerCase();

    // Open Graph: title
    const ogTitleMatch = html.match(/<meta[^>]+property=["']og:title["'][^>]*content=["']([^"']*?)["']/i)
      || html.match(/<meta[^>]+content=["']([^"']*?)["'][^>]*property=["']og:title["']/i);
    if (!ogTitleMatch) {
      findings.push({ code: 'SOC_NO_OG_TITLE', severity: 'medium', evidence: {} });
    }

    // Open Graph: image
    const ogImageMatch = html.match(/<meta[^>]+property=["']og:image["'][^>]*content=["']([^"']*?)["']/i)
      || html.match(/<meta[^>]+content=["']([^"']*?)["'][^>]*property=["']og:image["']/i);
    if (!ogImageMatch) {
      findings.push({ code: 'SOC_NO_OG_IMAGE', severity: 'high', evidence: {} });
    }

    // Favicon
    const hasFavicon = /<link[^>]+rel=["'][^"']*icon[^"']*["'][^>]*>/i.test(html);
    if (!hasFavicon) {
      findings.push({ code: 'SOC_NO_FAVICON', severity: 'low', evidence: {} });
    }

    // CTA
    const hasCta = /href=["']tel:/i.test(html) || lower.includes('wa.me')
      || lower.includes('presupuesto') || lower.includes('contacto') || lower.includes('cita');
    if (!hasCta) {
      findings.push({ code: 'SOC_NO_CTA', severity: 'high', evidence: {} });
    }

    // Social media profiles
    const socialNetworks: Record<string, string> = {
      facebook: 'facebook.com',
      instagram: 'instagram.com',
      linkedin: 'linkedin.com',
      twitter: 'twitter.com',
    };
    const foundSocial = Object.entries(socialNetworks)
      .filter(([, domain]) => lower.includes(domain))
      .map(([name]) => name);
    if (foundSocial.length === 0) {
      findings.push({ code: 'SOC_NO_SOCIAL_PROFILES', severity: 'medium', evidence: {} });
    }

    // Google Maps / location embed
    const hasMap = lower.includes('maps.google') || lower.includes('google.com/maps')
      || lower.includes('maps.googleapis') || lower.includes('goo.gl/maps');
    if (!hasMap) {
      findings.push({ code: 'SOC_NO_GOOGLE_MAPS', severity: 'low', evidence: {} });
    }

    // Contact form
    const hasForm = /<form[^>]*>/i.test(html);
    if (!hasForm) {
      findings.push({ code: 'SOC_NO_CONTACT_FORM', severity: 'medium', evidence: {} });
    }

    return findings;
  }
}
