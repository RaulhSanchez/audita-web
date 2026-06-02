import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from '../../common/prisma/prisma.service';
import { AggregatorService } from '../checks/aggregator/aggregator.service';
import { PdfService } from '../pdf/pdf.service';
import { NarrativeService } from '../narrative/narrative.service';
import { QueueService } from '../queue/queue.service';
import { TelegramService } from '../telegram/telegram.service';
import { MailService } from '../notifications/mail.service';
import * as fs from 'fs/promises';
import * as path from 'path';

@Injectable()
export class AuditService {
  private readonly logger = new Logger(AuditService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly aggregator: AggregatorService,
    private readonly pdfService: PdfService,
    private readonly narrative: NarrativeService,
    private readonly queueService: QueueService,
    private readonly telegramService: TelegramService,
    private readonly mailService: MailService,
  ) {}

  async createAudit(url: string, email?: string) {
    let domain = '';
    try {
      domain = new URL(url).hostname;
    } catch (e) {
      domain = url;
    }

    const crypto = await import('crypto');
    const publicSlug = crypto.randomUUID().split('-')[0];
    const audit = await this.prisma.audit.create({
      data: {
        url,
        domain,
        status: 'pending',
        publicSlug,
        ...(email ? { email } : {}),
      },
    });

    this.telegramService.sendMessage(`🚀 <b>Nuevo lead</b>\nURL: ${url}\nEmail: ${email || 'No proporcionado'}`);

    // Register lead in Formspree (fire-and-forget)
    this.registerFormspree(url, email).catch((e) =>
      this.logger.warn(`Formspree registration failed: ${e?.message ?? e}`),
    );

    // Add to local queue
    this.queueService.add(() => this.processAudit(audit.id, url, email));

    return {
      id: audit.id,
      publicSlug: audit.publicSlug,
      status: audit.status,
    };
  }

  private async processAudit(auditId: string, url: string, email?: string) {
    try {
      this.logger.log(`[1/5] Starting audit ${auditId} — url=${url} email=${email ?? 'none'}`);

      // 1. Run all checks (Lighthouse + SEO + Security)
      const result = await this.aggregator.runAll(url);
      this.logger.log(`[2/5] Checks done — score=${result.globalScore} findings=${result.findings.length}`);

      // 2. Generate business narrative
      const narrativeText = await this.narrative.generate({
        url,
        globalScore: result.globalScore,
        scores: result.scores,
        findings: result.findings,
      });
      this.logger.log(`[3/5] Narrative generated (${narrativeText.length} chars)`);

      // 3. Persist to DB — audit is marked done here so results are visible even if PDF fails
      await this.prisma.audit.update({
        where: { id: auditId },
        data: {
          status: 'done',
          globalScore: result.globalScore,
          scores: JSON.stringify(result.scores),
          findings: JSON.stringify(result.findings),
          narrative: narrativeText,
        },
      });
      this.logger.log(`[3/5] Audit ${auditId} persisted as done`);

      // 4. Generate and save PDF (non-fatal — audit is already marked done above)
      let pdfBuffer: Buffer | null = null;
      try {
        this.logger.log(`[4/5] Generating PDF…`);
        const enrichedForPdf = await this.enrichFindings(result.findings);
        pdfBuffer = await this.pdfService.generate({
          url,
          globalScore: result.globalScore,
          scores: result.scores,
          findings: enrichedForPdf,
          narrative: narrativeText,
          pageStats: result.pageStats,
        });

        const reportsDir = path.resolve(process.env.REPORTS_DIR || path.join(process.cwd(), 'reports'));
        await fs.mkdir(reportsDir, { recursive: true });
        const pdfFilePath = path.join(reportsDir, `${auditId}.pdf`);
        await fs.writeFile(pdfFilePath, pdfBuffer);
        this.logger.log(`[4/5] PDF saved: ${pdfFilePath}`);
      } catch (pdfError) {
        this.logger.error(`[4/5] PDF generation failed — audit still done`, pdfError);
      }

      // 5. Send email if provided and PDF is available
      if (email) {
        this.logger.log(`[5/5] Sending email to ${email} (pdfReady=${pdfBuffer !== null})`);
        await this.sendReportEmail(email, url, auditId, pdfBuffer, result.globalScore);
      }

      this.telegramService.sendMessage(`✅ <b>Auditoría completada</b>\nURL: ${url}\nPuntuación: ${result.globalScore}/100\nLink: ${process.env.FRONTEND_BASE_URL || 'http://localhost:3000'}/report/?id=${auditId}`);
      this.logger.log(`Audit ${auditId} completed successfully.`);
    } catch (e) {
      this.logger.error(`Error processing audit ${auditId}`, e);
      await this.prisma.audit.update({
        where: { id: auditId },
        data: { status: 'failed' },
      }).catch(() => {}); // ignore secondary DB error
    }
  }

  private async registerFormspree(url: string, email?: string) {
    const formId = process.env.FORMSPREE_FORM_ID ?? 'xykojvky';
    const body: Record<string, string> = {
      fuente: 'AuditaWeb',
      url_auditada: url,
      email: email ?? '(no proporcionado)',
      fecha: new Date().toISOString(),
    };
    const res = await fetch(`https://formspree.io/f/${formId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
    this.logger.log(`Formspree lead registered — email=${email ?? 'none'} url=${url}`);
  }

  private async sendReportEmail(email: string, url: string, auditId: string, pdfBuffer: Buffer | null, globalScore: number) {
    const resendApiKey = process.env.RESEND_API_KEY;

    if (!resendApiKey) {
      this.logger.warn('⚠️  RESEND_API_KEY vacío — email NO enviado.');
      return;
    }

    const hostname = new URL(url).hostname;
    const reportUrl = `${process.env.FRONTEND_BASE_URL || 'http://localhost:3000'}/report/?id=${auditId}`;
    const fromAddress = process.env.RESEND_FROM ?? 'AuditaWeb <onboarding@resend.dev>';

    try {
      await this.mailService.send(
        {
          from: fromAddress,
          to: email,
          subject: `Tu informe de auditoría para ${hostname} — Puntuación: ${globalScore}/100`,
          html: `
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
              <h2 style="color:#4f46e5">Tu informe está listo</h2>
              <p>Hemos analizado <strong>${url}</strong> y tu puntuación global es <strong style="font-size:1.4em">${globalScore}/100</strong>.</p>
              <p>Haz clic en el botón para ver todos los hallazgos y el plan de acción.</p>
              <a href="${reportUrl}" style="display:inline-block;margin:16px 0;background:#4f46e5;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">Ver resultado online</a>
              <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
              <p style="font-size:12px;color:#64748b">Raúl Huete · zero2dev.es</p>
            </div>
          `,
          ...(pdfBuffer ? {
            attachment: {
              filename: `informe-${hostname}.pdf`,
              content: pdfBuffer,
              contentType: 'application/pdf',
            },
          } : {}),
        },
        resendApiKey,
      );
    } catch (e) {
      this.logger.error(`Error enviando email a ${email}`, e);
    }
  }

  private async enrichFindings(rawFindings: any[] | null) {
    if (!rawFindings?.length) return rawFindings ?? [];
    const codes = rawFindings.map((f: any) => f.code);
    const catalog = await this.prisma.findingCatalog.findMany({ where: { code: { in: codes } } });
    const catalogMap = new Map(catalog.map((c) => [c.code, c]));
    return rawFindings.map((f: any) => {
      const entry = catalogMap.get(f.code);
      return {
        ...f,
        title: entry?.titleEs ?? f.code,
        description: entry?.descriptionEs ?? null,
        businessImpact: entry?.businessImpact ?? null,
        fixSuggestion: entry?.fixSuggestion ?? null,
      };
    });
  }

  async getAudit(id: string) {
    const audit = await this.prisma.audit.findUnique({ where: { id } });
    if (!audit) return null;
    const rawFindings = audit.findings ? JSON.parse(audit.findings) : null;
    return {
      id: audit.id,
      url: audit.url,
      status: audit.status,
      globalScore: audit.globalScore,
      scores: audit.scores ? JSON.parse(audit.scores) : null,
      findings: await this.enrichFindings(rawFindings),
      narrative: audit.narrative,
    };
  }

  async getAuditBySlug(publicSlug: string) {
    const audit = await this.prisma.audit.findUnique({ where: { publicSlug } });
    if (!audit) return null;
    const rawFindings = audit.findings ? JSON.parse(audit.findings) : null;
    return {
      id: audit.id,
      url: audit.url,
      status: audit.status,
      globalScore: audit.globalScore,
      scores: audit.scores ? JSON.parse(audit.scores) : null,
      findings: await this.enrichFindings(rawFindings),
      narrative: audit.narrative,
      createdAt: audit.createdAt,
    };
  }

  async getPdfPath(id: string): Promise<string | null> {
    const reportsDir = path.resolve(process.env.REPORTS_DIR ?? path.join(process.cwd(), 'reports'));
    const pdfPath = path.join(reportsDir, `${id}.pdf`);
    try {
      await fs.access(pdfPath);
      return pdfPath;
    } catch {
      return null;
    }
  }
}
