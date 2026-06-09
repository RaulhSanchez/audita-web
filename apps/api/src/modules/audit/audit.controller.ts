import { BadRequestException, Body, Controller, Get, Headers, InternalServerErrorException, Logger, Param, Post, Res, NotFoundException, UnauthorizedException } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { AuditService } from './audit.service';
import type { Response } from 'express';
import * as fs from 'fs';

@Controller('api/audits')
export class AuditController {
  private readonly logger = new Logger(AuditController.name);

  constructor(private readonly auditService: AuditService) {}

  @Post()
  async create(@Body() body: any) {
    // ── URL validation ──────────────────────────────────────
    const BLOCKED_HOSTS = [
      'example.com', 'example.org', 'example.net',
      'localhost', '127.0.0.1', '0.0.0.0',
      'test.com', 'test.org', 'test.net',
      'domain.com', 'yourwebsite.com', 'mywebsite.com',
      'placeholder.com', 'website.com',
    ];
    try {
      const hostname = new URL(body.url).hostname.toLowerCase().replace(/^www\./, '');
      if (BLOCKED_HOSTS.includes(hostname)) {
        throw new BadRequestException('Introduce la URL real de tu web para analizarla.');
      }
    } catch (e) {
      if (e instanceof BadRequestException) throw e;
      throw new BadRequestException('URL no válida. Asegúrate de incluir https://');
    }

    // ── Email validation ────────────────────────────────────
    if (body.email) {
      const BLOCKED_EMAIL_DOMAINS = [
        'test.com', 'example.com', 'fake.com', 'fake.es',
        'mailinator.com', 'guerrillamail.com', 'tempmail.com',
        'throwam.com', 'yopmail.com', 'trashmail.com',
        'sharklasers.com', 'dispostable.com',
      ];
      const BLOCKED_EMAIL_USERS = ['test', 'fake', 'noreply', 'no-reply', 'admin@test', 'user@test'];
      const emailLower = body.email.toLowerCase().trim();
      const [user, domain] = emailLower.split('@');
      if (
        BLOCKED_EMAIL_DOMAINS.includes(domain) ||
        BLOCKED_EMAIL_USERS.some(u => emailLower.startsWith(u + '@')) ||
        emailLower === 'test@test.com' ||
        emailLower === 'a@a.com'
      ) {
        throw new BadRequestException('Introduce tu email real para recibir el informe.');
      }
    }

    try {
      return await this.auditService.createAudit(body.url, body.email, body.phone, body.sector);
    } catch (e) {
      if (e instanceof BadRequestException) throw e;
      this.logger.error('createAudit failed', e);
      throw new InternalServerErrorException((e as Error).message ?? 'Unexpected error');
    }
  }

  /**
   * Endpoint interno para auditoría en lote (outreach).
   * No envía email, no registra en Formspree, no notifica en Telegram.
   * Requiere header x-api-key con el valor de INTERNAL_API_KEY env var.
   */
  @Post('internal')
  async createInternal(
    @Headers('x-api-key') apiKey: string,
    @Body() body: { url: string },
  ) {
    const expected = process.env.INTERNAL_API_KEY;
    if (!expected || apiKey !== expected) {
      throw new UnauthorizedException('Invalid or missing x-api-key');
    }
    if (!body?.url) {
      throw new InternalServerErrorException('url is required');
    }
    try {
      return await this.auditService.createInternalAudit(body.url);
    } catch (e) {
      this.logger.error('createInternalAudit failed', e);
      throw new InternalServerErrorException((e as Error).message ?? 'Unexpected error');
    }
  }

  // Specific routes must come before the generic :id route
  @Get('public/:slug')
  async findBySlug(@Param('slug') slug: string) {
    const audit = await this.auditService.getAuditBySlug(slug);
    if (!audit) throw new NotFoundException('Audit not found');
    return audit;
  }

  @Get(':id/pdf')
  async downloadPdf(@Param('id') id: string, @Res() res: Response) {
    const pdfPath = await this.auditService.getPdfPath(id);
    if (!pdfPath) throw new NotFoundException('PDF not generated yet');
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="informe-${id}.pdf"`);
    fs.createReadStream(pdfPath).pipe(res);
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    const audit = await this.auditService.getAudit(id);
    if (!audit) throw new NotFoundException('Audit not found');
    return audit;
  }

  /** Cron diario a las 10:00 — envía follow-ups a leads de hace ~48h */
  @Cron('0 10 * * *')
  async dailyFollowUp() {
    this.logger.log('Cron dailyFollowUp: iniciando...');
    const result = await this.auditService.sendFollowUpEmails();
    this.logger.log(`Cron dailyFollowUp: enviados=${result.sent} saltados=${result.skipped}`);
  }
}
