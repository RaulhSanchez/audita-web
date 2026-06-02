import { Injectable, Logger } from '@nestjs/common';

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

  async send(opts: MailOptions, apiKey: string): Promise<void> {
    const body: Record<string, unknown> = {
      from: opts.from,
      to: [opts.to],
      subject: opts.subject,
      html: opts.html,
    };

    if (opts.attachment) {
      body.attachments = [{
        filename: opts.attachment.filename,
        content: opts.attachment.content.toString('base64'),
      }];
    }

    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Resend error ${res.status}: ${text}`);
    }

    this.logger.log(`✅ Email enviado a ${opts.to}`);
  }
}
