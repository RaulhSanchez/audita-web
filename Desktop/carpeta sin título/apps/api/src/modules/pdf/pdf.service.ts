import { Injectable, Logger } from '@nestjs/common';
import * as handlebars from 'handlebars';
import * as fs from 'fs/promises';
import * as path from 'path';

handlebars.registerHelper('colorClass', (score: number) => {
  if (score >= 80) return 'green';
  if (score >= 50) return 'yellow';
  return 'red';
});

handlebars.registerHelper('scoreLabel', (score: number) => {
  if (score >= 80) return 'Excelente';
  if (score >= 60) return 'Aceptable';
  if (score >= 40) return 'Mejorable';
  return 'Crítico';
});

handlebars.registerHelper('severityLabel', (s: string) => {
  const map: Record<string, string> = { critical: 'CRÍTICO', high: 'ALTO', medium: 'MEDIO', low: 'BAJO' };
  return map[s] ?? s.toUpperCase();
});

handlebars.registerHelper('eq', (a: any, b: any) => a === b);
handlebars.registerHelper('gt', (a: number, b: number) => a > b);

// Strip markdown: ### Title → Title, **bold** → bold, - item → • item
handlebars.registerHelper('stripMd', (text: string) => {
  if (!text) return '';
  return text
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/^[-*+]\s+/gm, '• ')
    .replace(/`([^`]+)`/g, '$1')
    .trim();
});

// Format milliseconds: 4409.37 → "4.4 s"  |  890 → "890 ms"
handlebars.registerHelper('fmtMs', (ms: number) => {
  if (ms == null) return '';
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)} s`;
  return `${Math.round(ms)} ms`;
});

// Format any number: strips trailing decimals garbage
handlebars.registerHelper('fmtNum', (n: number) => {
  if (n == null) return '';
  return Number.isInteger(n) ? String(n) : parseFloat(n.toFixed(2)).toString();
});
handlebars.registerHelper('scoreAreaName', (key: string) => {
  const map: Record<string, string> = {
    performance: 'Rendimiento', seo: 'SEO', security: 'Seguridad', accessibility: 'Accesibilidad',
  };
  return map[key] ?? key;
});

@Injectable()
export class PdfService {
  private readonly logger = new Logger(PdfService.name);

  async generate(data: any): Promise<Buffer> {
    try {
      // Try compiled path first (production), fall back to source path (dev watch mode)
      const distPath = path.join(__dirname, 'templates', 'report.hbs');
      const srcPath = path.join(process.cwd(), 'src', 'modules', 'pdf', 'templates', 'report.hbs');
      const templatePath = await fs.access(distPath).then(() => distPath).catch(() => srcPath);
      const templateHtml = await fs.readFile(templatePath, 'utf8');

      const template = handlebars.compile(templateHtml);

      const findings: any[] = data.findings ?? [];
      const criticalFindings = findings.filter((f: any) => f.severity === 'critical');
      const highFindings = findings.filter((f: any) => f.severity === 'high');
      const mediumFindings = findings.filter((f: any) => f.severity === 'medium');
      const lowFindings = findings.filter((f: any) => f.severity === 'low');
      const urgentFindings = [...criticalFindings, ...highFindings];

      const html = template({
        ...data,
        date: new Date().toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' }),
        criticalFindings,
        highFindings,
        mediumFindings,
        lowFindings,
        urgentFindings,
        criticalCount: criticalFindings.length,
        highCount: highFindings.length,
        mediumCount: mediumFindings.length,
        lowCount: lowFindings.length,
        totalFindings: findings.length,
      });

      const puppeteer = (await import('puppeteer')).default;
      const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
      const page = await browser.newPage();
      
      await page.setContent(html, { waitUntil: 'domcontentloaded' });
      
      const pdf = await page.pdf({
        format: 'A4',
        printBackground: true,
        margin: { top: '20mm', right: '15mm', bottom: '20mm', left: '15mm' },
      });

      await browser.close();
      
      return Buffer.from(pdf);
    } catch (error) {
      this.logger.error('Error generating PDF', error);
      throw error;
    }
  }
}
