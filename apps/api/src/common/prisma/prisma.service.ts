import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';
import { PrismaNeon } from '@prisma/adapter-neon';
import { Pool, neonConfig } from '@neondatabase/serverless';
import ws from 'ws';

// Required for Neon WebSocket driver in Node.js (non-edge) environments
neonConfig.webSocketConstructor = ws;

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit, OnModuleDestroy {
  constructor() {
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });
    const adapter = new PrismaNeon(pool);
    super({ adapter });
  }

  async onModuleInit() {
    await this.$connect().catch((e) => {
      console.error('Prisma connect failed:', e.message);
    });
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }
}
