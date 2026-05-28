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

    // Viewport meta tag
    if (!/<meta[^>]+name=["']viewport["'][^>]*>/i.test(html)) {
      findings.push({ code: 'MOB_NO_VIEWPORT', severity: 'critical', evidence: {} });
    }

    // Clickable phone number
    if (!/<a[^>]+href=["']tel:/i.test(html)) {
      findings.push({ code: 'MOB_NO_TEL_LINK', severity: 'medium', evidence: {} });
    }

    // WhatsApp link
    if (!lower.includes('wa.me') && !lower.includes('api.whatsapp.com') && !lower.includes('whatsapp.com/send')) {
      findings.push({ code: 'MOB_NO_WHATSAPP', severity: 'medium', evidence: {} });
    }

    // Touch-friendly buttons: check for suspiciously small inline font sizes
    const tinyFont = html.match(/font-size\s*:\s*([0-9]+)px/gi) || [];
    const hasSmallText = tinyFont.some((m) => {
      const px = parseInt(m.replace(/[^0-9]/g, ''), 10);
      return px > 0 && px < 12;
    });
    if (hasSmallText) {
      findings.push({ code: 'MOB_FONT_SMALL', severity: 'medium', evidence: {} });
    }

    return findings;
  }
}
