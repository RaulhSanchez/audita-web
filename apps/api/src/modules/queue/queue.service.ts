import { Injectable, Logger } from '@nestjs/common';

@Injectable()
export class QueueService {
  private queue: Array<() => Promise<void>> = [];
  private isProcessing = false;
  private readonly logger = new Logger(QueueService.name);

  add(job: () => Promise<void>) {
    this.queue.push(job);
    this.processNext();
  }

  private async processNext() {
    if (this.isProcessing || this.queue.length === 0) return;
    this.isProcessing = true;
    const job = this.queue.shift();
    if (job) {
      try {
        await job();
      } catch (err) {
        this.logger.error('Job failed', err);
      }
    }
    this.isProcessing = false;
    this.processNext();
  }
}
