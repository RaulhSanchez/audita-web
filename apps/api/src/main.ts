import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({
    origin: [
      'https://audita.zero2dev.es',
      'https://zero2dev.es',
      'http://localhost:3000',
      'http://localhost:3001',
    ],
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'x-api-key'],
    credentials: false,
  });
  await app.listen(process.env.PORT ?? 3001);
}
bootstrap();
