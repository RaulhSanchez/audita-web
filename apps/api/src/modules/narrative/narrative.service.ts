import { Injectable, Logger } from '@nestjs/common';
import { ChatOllama } from '@langchain/ollama';
import { PromptTemplate } from '@langchain/core/prompts';
import { StringOutputParser } from '@langchain/core/output_parsers';
import { PrismaService } from '../../common/prisma/prisma.service';
import type { Finding } from '../checks/interfaces';

export interface NarrativeInput {
  url: string;
  globalScore: number;
  scores: Record<string, number>;
  findings: Finding[];
}

@Injectable()
export class NarrativeService {
  private readonly logger = new Logger(NarrativeService.name);
  private llm: ChatOllama;

  constructor(private prisma: PrismaService) {
    this.llm = new ChatOllama({
      baseUrl: process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434',
      model: process.env.OLLAMA_MODEL ?? 'llama3.2',
      temperature: 0.3,
    });
  }

  async generate(params: NarrativeInput): Promise<string> {
    this.logger.log(`Generando narrativa con Ollama para ${params.url}`);
    
    // Fetch catalog entries for findings
    const codes = params.findings.map(f => f.code);
    const catalogEntries = await this.prisma.findingCatalog.findMany({
      where: { code: { in: codes } }
    });

    const catalogMap = new Map(catalogEntries.map(e => [e.code, e]));

    const enrichedFindings = params.findings.map(f => {
      const cat = catalogMap.get(f.code);
      if (cat) {
        return `- [${f.severity.toUpperCase()}] ${cat.titleEs}: ${cat.businessImpact}`;
      }
      return `- [${f.severity.toUpperCase()}] ${f.code}: Problema técnico que afecta a la experiencia del usuario.`;
    }).join('\n');

    const prompt = PromptTemplate.fromTemplate(`
Eres un consultor de negocio experto en marketing digital y desarrollo web.
Tu objetivo es redactar un resumen ejecutivo de una auditoría web para el dueño de la empresa (que NO es técnico).

Datos de la auditoría:
- URL: {url}
- Puntuación global: {globalScore}/100

Hallazgos principales (con impacto en negocio):
{findings}

Escribe un texto en formato Markdown persuasivo, directo y profesional (español de España) con la siguiente estructura:
1. Un breve diagnóstico general sobre la puntuación obtenida.
2. "¿Qué te está haciendo perder dinero?": Explica en 2-3 viñetas los problemas más graves traduciéndolos a clientes perdidos, ineficiencia o riesgo legal.
3. "Siguiente paso": Un Call To Action animando a agendar una llamada de valoración.

No uses tecnicismos como "DOM", "CSS", "Headers" o similares sin explicarlos en lenguaje llano.
`);

    const chain = prompt.pipe(this.llm).pipe(new StringOutputParser());

    try {
      const response = await chain.invoke({
        url: params.url,
        globalScore: params.globalScore.toString(),
        findings: enrichedFindings,
      });
      return response;
    } catch (e) {
      this.logger.error('Error llamando a Ollama, usando fallback', e);
      return this.generateFallback(params);
    }
  }

  private generateFallback(params: NarrativeInput): string {
    const qualifier =
      params.globalScore >= 80 ? 'buena forma, aunque con margen de mejora'
      : params.globalScore >= 50 ? 'un nivel aceptable pero con problemas que frenan su rendimiento'
      : 'un estado que requiere atención urgente';

    let text = `Tu web ha obtenido una puntuación global de ${params.globalScore}/100, lo que indica que está en ${qualifier}.\n\n`;

    const urgent = params.findings.filter(f => f.severity === 'critical' || f.severity === 'high').slice(0, 3);
    if (urgent.length > 0) {
      text += 'Los problemas más importantes detectados afectan directamente a cómo te encuentran tus clientes y a la confianza que genera tu web. Resolverlos puede marcar la diferencia entre perder o ganar un cliente potencial.\n\n';
      text += 'Si quieres que me encargue de solucionarlo todo, escríbeme a raaul9212@gmail.com o visita zero2dev.es.';
    } else {
      text += 'Tu web está en buena forma. Aun así, hay mejoras puntuales que pueden aumentar tu visibilidad en Google y mejorar la experiencia de tus clientes.\n\n';
      text += 'Si quieres exprimir al máximo el potencial de tu web, puedo ayudarte. Escríbeme a raaul9212@gmail.com.';
    }

    return text;
  }
}
