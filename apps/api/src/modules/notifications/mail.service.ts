import { Injectable, Logger } from '@nestjs/common';
import * as nodemailer from 'nodemailer';

export interface MailOptions {
  from: string;
  to: string;
  subject: string;
  html: string;
  attachment?: {
    filename: string;
    content: Buffer;
    contentType: string;
  };
}

@Injectable()
export class MailService {
  private readonly logger = new Logger(MailService.name);

  async send(opts: MailOptions, user: string, pass: string): Promise<void> {
    const transporter = nodemailer.createTransport({
      host: 'smtp.gmail.com',
      port: 587,
      secure: false, // STARTTLS
      auth: { user, pass },
      connectionTimeout: 10_000,
      greetingTimeout: 10_000,
      socketTimeout: 15_000,
    });

    await transporter.sendMail({
      from: opts.from,
      to: opts.to,
      subject: opts.subject,
      html: opts.html,
      ...(opts.attachment ? {
        attachments: [{
          filename: opts.attachment.filename,
          content: opts.attachment.content,
          contentType: opts.attachment.contentType,
        }],
      } : {}),
    });

    this.logger.log(`✅ Email enviado a ${opts.to}`);
  }
}
