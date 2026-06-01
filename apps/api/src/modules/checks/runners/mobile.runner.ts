import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

@Injectable()
export class MobileRunner implements CheckRunner {
  code = 'MOB_CORE';
  category = 'mobile';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    if (!ctx.html) return findings;

    const html = ctx.html;
    const lower = html.toLowerCase();

    // Viewport
    if (!/<meta[^>]+name=["']viewport["'][^>]*>/i.test(html)) {
      findings.push({ code: 'MOB_NO_VIEWPORT', severity: 'critical', evidence: {} });
    }

    // Clickable phone number
    const telLinks = (html.match(/<a[^>]+href=["']tel:[^"']+["']/gi) || []);
    if (telLinks.length === 0) {
      // Try to detect a phone number in text not linked
      const phoneInText = html.match(/\b(?:\+34\s?)?[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b/);
      findings.push({
        code: 'MOB_NO_TEL_LINK',
        severity: 'high',
        evidence: { telefono_detectado: phoneInText ? phoneInText[0] : null },
      });
    }

    // WhatsApp
    const hasWhatsapp = lower.includes('wa.me') || lower.includes('api.whatsapp.com') || lower.includes('whatsapp.com/send');
    if (!hasWhatsapp) {
      findings.push({ code: 'MOB_NO_WHATSAPP', severity: 'medium', evidence: {} });
    }

    // Small inline font sizes
    const tinyFont = html.match(/font-size\s*:\s*([0-9]+)px/gi) || [];
    const smallSizes = tinyFont
      .map(m => parseInt(m.replace(/[^0-9]/g, ''), 10))
      .filter(px => px > 0 && px < 12);
    if (smallSizes.length > 0) {
      findings.push({ code: 'MOB_FONT_SMALL', severity: 'medium', evidence: { tamanhos_pequenos: smallSizes } });
    }

    return findings;
  }
}
