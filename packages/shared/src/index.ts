export interface AuditRequestDto {
  url: string;
  email?: string;
  phone?: string;
  sector?: string;
}

export interface AuditResponseDto {
  id: string;
  publicSlug: string | null;
  status: string;
}

export interface AuditResultDto {
  id: string;
  url: string;
  status: string;
  globalScore: number | null;
  scores: any;
  findings: any;
  narrative: string | null;
}
