import { Injectable } from '@nestjs/common';
import { CheckContext, CheckRunner, Finding } from '../interfaces';

function extractText(html: string): string {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

@Injectable()
export class SeoRunner implements CheckRunner {
  code = 'SEO_CORE';
  category = 'seo';

  async run(ctx: CheckContext): Promise<Finding[]> {
    const findings: Finding[] = [];
    if (!ctx.html) return findings;

    const html = ctx.html;

    // Title
    const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    if (!titleMatch) {
      findings.push({ code: 'SEO_NO_TITLE', severity: 'critical', evidence: {} });
    } else {
      const titleText = titleMatch[1].replace(/\s+/g, ' ').trim();
      if (titleText.length < 30 || titleText.length > 65) {
        findings.push({ code: 'SEO_TITLE_LENGTH', severity: 'low', evidence: { longitud: titleText.length, titulo: titleText.substring(0, 80) } });
      }
    }

    // Meta description
    const metaDescMatch = html.match(/<meta[^>]+name=["']description["'][^>]*content=["']([^"']*?)["']/i)
      || html.match(/<meta[^>]+content=["']([^"']*?)["'][^>]*name=["']description["']/i);
    if (!metaDescMatch) {
      findings.push({ code: 'SEO_NO_META_DESC', severity: 'high', evidence: {} });
    } else {
      const desc = metaDescMatch[1].trim();
      if (desc.length < 70 || desc.length > 160) {
        findings.push({ code: 'SEO_META_DESC_LENGTH', severity: 'low', evidence: { longitud: desc.length, texto: desc.substring(0, 100) } });
      }
    }

    // H1
    const h1Full = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/gi) || [];
    const h1Texts = h1Full.map(h => extractText(h)).filter(Boolean);
    if (h1Texts.length === 0) {
      findings.push({ code: 'SEO_NO_H1', severity: 'high', evidence: {} });
    } else if (h1Texts.length > 1) {
      findings.push({ code: 'SEO_MULTIPLE_H1', severity: 'medium', evidence: { cantidad: h1Texts.length, titulos: h1Texts.slice(0, 3) } });
    }

    // Images without alt
    const imgMatches = html.match(/<img[^>]*>/gi) || [];
    const imgsWithoutAlt = imgMatches.filter(img => !/\balt=["'][^"']*["']/i.test(img));
    if (imgsWithoutAlt.length > 0) {
      findings.push({ code: 'SEO_IMG_NO_ALT', severity: 'medium', evidence: { sin_alt: imgsWithoutAlt.length, total_imagenes: imgMatches.length } });
    }

    // Lang attribute
    if (!/<html[^>]+lang=["'][^"']+["']/i.test(html)) {
      findings.push({ code: 'SEO_NO_LANG', severity: 'low', evidence: {} });
    }

    return findings;
  }
}
