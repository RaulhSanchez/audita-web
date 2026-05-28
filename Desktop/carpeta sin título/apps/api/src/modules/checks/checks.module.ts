import { Module } from '@nestjs/common';
import { AggregatorService } from './aggregator/aggregator.service';
import { LighthouseRunner } from './runners/lighthouse.runner';
import { SeoRunner } from './runners/seo.runner';
import { SeoAdvancedRunner } from './runners/seo-advanced.runner';
import { SecurityRunner } from './runners/security.runner';
import { MobileRunner } from './runners/mobile.runner';
import { SocialRunner } from './runners/social.runner';
import { LegalRunner } from './runners/legal.runner';
import { ChecksSeeder } from './checks.seeder';

@Module({
  providers: [
    AggregatorService,
    LighthouseRunner,
    SeoRunner,
    SeoAdvancedRunner,
    SecurityRunner,
    MobileRunner,
    SocialRunner,
    LegalRunner,
    ChecksSeeder,
  ],
  exports: [AggregatorService],
})
export class ChecksModule {}
