export interface CheckContext {
  url: string;
  html: string;
  lighthouse?: any;
  headers?: Record<string, string>;
  responseTimeMs?: number;
  htmlSizeBytes?: number;
}

export interface Finding {
  code: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  evidence: Record<string, unknown>;
}

export interface CheckRunner {
  code: string;
  category: string;
  run(ctx: CheckContext): Promise<Finding[]>;
}
