import { Module } from '@nestjs/common';
import { NarrativeService } from './narrative.service';

@Module({
  providers: [NarrativeService],
  exports: [NarrativeService],
})
export class NarrativeModule {}
