import { Module } from '@nestjs/common';
import { AuditService } from './audit.service';
import { AuditController } from './audit.controller';
import { ChecksModule } from '../checks/checks.module';
import { PdfModule } from '../pdf/pdf.module';
import { NarrativeModule } from '../narrative/narrative.module';
import { QueueModule } from '../queue/queue.module';
import { TelegramModule } from '../telegram/telegram.module';
import { MailService } from '../notifications/mail.service';

@Module({
  imports: [ChecksModule, PdfModule, NarrativeModule, QueueModule, TelegramModule],
  controllers: [AuditController],
  providers: [AuditService, MailService],
})
export class AuditModule {}

