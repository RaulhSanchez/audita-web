import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit, OnModuleDestroy {
  async onModuleInit() {
    await this.$connect().catch((e) => {
      console.error('Prisma connect failed (DB unreachable?):', e.message);
    });
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }
}
