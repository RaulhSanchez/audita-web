import { Body, Controller, Get, InternalServerErrorException, Logger, Param, Post, Res, NotFoundException } from '@nestjs/common';
import { AuditService } from './audit.service';
import type { Response } from 'express';
import * as fs from 'fs';

@Controller('api/audits')
export class AuditController {
  private readonly logger = new Logger(AuditController.name);

  constructor(private readonly auditService: AuditService) {}

  @Post()
  async create(@Body() body: any) {
    try {
      return await this.auditService.createAudit(body.url, body.email);
    } catch (e) {
      this.logger.error('createAudit failed', e);
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
}
