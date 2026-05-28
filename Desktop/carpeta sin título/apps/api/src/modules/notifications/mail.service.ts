import { Injectable, Logger } from '@nestjs/common';
import * as tls from 'node:tls';
import * as crypto from 'node:crypto';

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
    const boundary = crypto.randomUUID().replace(/-/g, '');
    const mime = this.buildMime(opts, boundary);

    await this.smtp(mime, opts, user, pass);
    this.logger.log(`✅ Email enviado a ${opts.to}`);
  }

  // ─── MIME builder ──────────────────────────────────────────────────────────

  private buildMime(opts: MailOptions, boundary: string): string {
    const encodeSubject = (s: string) =>
      `=?UTF-8?B?${Buffer.from(s).toString('base64')}?=`;

    const lines: string[] = [
      `From: ${opts.from}`,
      `To: ${opts.to}`,
      `Subject: ${encodeSubject(opts.subject)}`,
      `MIME-Version: 1.0`,
      `Date: ${new Date().toUTCString()}`,
      `Content-Type: multipart/mixed; boundary="${boundary}"`,
      '',
      `--${boundary}`,
      'Content-Type: text/html; charset=utf-8',
      'Content-Transfer-Encoding: base64',
      '',
      Buffer.from(opts.html, 'utf8').toString('base64'),
      '',
    ];

    if (opts.attachment) {
      const b64 = opts.attachment.content.toString('base64');
      // RFC 2822: base64 lines max 76 chars
      const chunked = b64.match(/.{1,76}/g)?.join('\r\n') ?? b64;
      lines.push(
        `--${boundary}`,
        `Content-Type: ${opts.attachment.contentType}; name="${opts.attachment.filename}"`,
        `Content-Disposition: attachment; filename="${opts.attachment.filename}"`,
        'Content-Transfer-Encoding: base64',
        '',
        chunked,
        '',
      );
    }

    lines.push(`--${boundary}--`);
    return lines.join('\r\n');
  }

  // ─── SMTP client (node:tls, puerto 465 SSL) ────────────────────────────────

  private smtp(mime: string, opts: MailOptions, user: string, pass: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket = tls.connect({ host: 'smtp.gmail.com', port: 465 }, () => {
        this.logger.debug('TLS conectado a smtp.gmail.com:465');
      });

      type State =
        | 'GREETING' | 'EHLO' | 'AUTH_LOGIN'
        | 'AUTH_USER' | 'AUTH_PASS' | 'MAIL_FROM'
        | 'RCPT_TO' | 'DATA' | 'BODY' | 'QUIT';

      let state: State = 'GREETING';
      let buf = '';

      const write = (s: string) => socket.write(s + '\r\n');

      const fromAddr = opts.from.match(/<(.+)>/)?.[1] ?? opts.from;

      socket.on('data', (chunk: Buffer) => {
        buf += chunk.toString();
        const parts = buf.split('\r\n');
        buf = parts.pop() ?? '';

        for (const line of parts) {
          if (!line) continue;
          const code = parseInt(line.slice(0, 3), 10);
          const isLast = line[3] !== '-'; // '-' = más líneas; ' ' = última
          if (!isLast) continue;

          this.logger.debug(`[SMTP ${state}] ${line}`);

          switch (state) {
            case 'GREETING':
              if (code === 220) { write('EHLO auditaweb'); state = 'EHLO'; }
              else reject(new Error(`GREETING: ${line}`));
              break;

            case 'EHLO':
              if (code === 250) { write('AUTH LOGIN'); state = 'AUTH_LOGIN'; }
              else reject(new Error(`EHLO: ${line}`));
              break;

            case 'AUTH_LOGIN':
              if (code === 334) {
                write(Buffer.from(user).toString('base64'));
                state = 'AUTH_USER';
              } else reject(new Error(`AUTH LOGIN: ${line}`));
              break;

            case 'AUTH_USER':
              if (code === 334) {
                write(Buffer.from(pass).toString('base64'));
                state = 'AUTH_PASS';
              } else reject(new Error(`AUTH USER: ${line}`));
              break;

            case 'AUTH_PASS':
              if (code === 235) {
                write(`MAIL FROM:<${fromAddr}>`);
                state = 'MAIL_FROM';
              } else reject(new Error(`AUTH PASS: ${line} — comprueba GMAIL_APP_PASSWORD`));
              break;

            case 'MAIL_FROM':
              if (code === 250) { write(`RCPT TO:<${opts.to}>`); state = 'RCPT_TO'; }
              else reject(new Error(`MAIL FROM: ${line}`));
              break;

            case 'RCPT_TO':
              if (code === 250) { write('DATA'); state = 'DATA'; }
              else reject(new Error(`RCPT TO: ${line}`));
              break;

            case 'DATA':
              if (code === 354) {
                // El cuerpo termina con \r\n.\r\n (punto solo en línea)
                socket.write(mime + '\r\n.\r\n');
                state = 'BODY';
              } else reject(new Error(`DATA: ${line}`));
              break;

            case 'BODY':
              if (code === 250) { write('QUIT'); state = 'QUIT'; }
              else reject(new Error(`BODY: ${line}`));
              break;

            case 'QUIT':
              socket.end();
              resolve();
              break;
          }
        }
      });

      socket.on('error', (err) => reject(err));
      socket.on('close', () => {
        if (state !== 'QUIT') reject(new Error(`Conexión cerrada en estado ${state}`));
      });

      socket.setTimeout(15_000, () => {
        socket.destroy();
        reject(new Error('SMTP timeout'));
      });
    });
  }
}
