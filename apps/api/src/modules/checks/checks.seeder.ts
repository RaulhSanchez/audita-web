import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import { PrismaService } from '../../common/prisma/prisma.service';

const INITIAL_CATALOG = [
  // ─── Rendimiento ───────────────────────────────────────────────────────────
  {
    code: 'PERF_SCORE_LOW',
    category: 'performance',
    severity: 'critical',
    titleEs: 'Tu web carga demasiado despacio',
    descriptionEs: 'La puntuación de velocidad es muy baja. Los visitantes esperan más de 3 segundos para ver algo útil.',
    businessImpact: 'El 53% de los usuarios abandona una web que tarda más de 3 segundos. Estás perdiendo más de la mitad de tus visitas antes de que lean una sola línea.',
    fixSuggestion: 'Comprimir imágenes, activar caché y reducir el código JavaScript. Una hora de trabajo puede recuperar la mitad de esas visitas perdidas.',
  },
  {
    code: 'PERF_SCORE_MED',
    category: 'performance',
    severity: 'medium',
    titleEs: 'La velocidad de carga tiene margen de mejora',
    descriptionEs: 'La web carga en un tiempo aceptable pero por debajo de lo recomendado.',
    businessImpact: 'Google penaliza en resultados de búsqueda las webs lentas. Mejorar la velocidad puede subir tu posición en Google y traer más visitas orgánicas.',
    fixSuggestion: 'Optimizar el tamaño de las imágenes y activar la compresión del servidor.',
  },
  {
    code: 'PERF_LCP_HIGH',
    category: 'performance',
    severity: 'high',
    titleEs: 'El contenido principal tarda demasiado en aparecer',
    descriptionEs: 'El elemento más grande de la página (normalmente la imagen o título principal) tarda más de 2,5 segundos en mostrarse.',
    businessImpact: 'El cliente ve una pantalla en blanco o en construcción durante demasiado tiempo. La primera impresión es mala y muchos se van sin esperar. Google también lo penaliza directamente en su puntuación.',
    fixSuggestion: 'Comprimir la imagen principal, usar formatos modernos (WebP) y cargar el texto antes que las imágenes decorativas.',
  },
  // ─── SEO ───────────────────────────────────────────────────────────────────
  {
    code: 'SEO_NO_TITLE',
    category: 'seo',
    severity: 'critical',
    titleEs: 'Falta el título de la página',
    descriptionEs: 'La página no tiene etiqueta de título, lo que Google usa para mostrarla en los resultados de búsqueda.',
    businessImpact: 'Tu web es invisible para Google. No aparecerás cuando alguien busque tus servicios. Es como tener un negocio sin rótulo.',
    fixSuggestion: 'Añadir un título descriptivo de 50-60 caracteres que incluya tu servicio principal y tu localidad.',
  },
  {
    code: 'SEO_TITLE_LENGTH',
    category: 'seo',
    severity: 'low',
    titleEs: 'El título de la página no tiene la longitud ideal',
    descriptionEs: 'El título es demasiado corto o demasiado largo. Google muestra los títulos entre 50 y 60 caracteres.',
    businessImpact: 'Un título demasiado largo se corta en Google con "..." y pierde impacto. Uno muy corto no aprovecha el espacio para atraer clics. Ambos reducen el porcentaje de personas que entran a tu web.',
    fixSuggestion: 'Reescribir el título con entre 50 y 60 caracteres, incluyendo servicio + localidad + diferenciador.',
  },
  {
    code: 'SEO_NO_META_DESC',
    category: 'seo',
    severity: 'high',
    titleEs: 'Falta la descripción para Google',
    descriptionEs: 'No hay meta descripción. Es el texto de dos líneas que aparece bajo el título en los resultados de búsqueda.',
    businessImpact: 'Google inventará un texto aleatorio de tu web para mostrarlo. Ese texto suele ser irrelevante y hace que menos gente haga clic en tu resultado aunque aparezcas bien posicionado.',
    fixSuggestion: 'Añadir una descripción de 120-155 caracteres explicando qué haces, para quién y en qué zona.',
  },
  {
    code: 'SEO_NO_H1',
    category: 'seo',
    severity: 'high',
    titleEs: 'Falta el titular principal de la página',
    descriptionEs: 'La página no tiene ningún encabezado H1, que es el titular principal que Google usa para entender de qué trata la web.',
    businessImpact: 'Google no sabe qué servicio ofreces y te posiciona para búsquedas irrelevantes o no te posiciona para nada. Pierdes visibilidad frente a competidores que sí lo tienen.',
    fixSuggestion: 'Añadir un titular H1 único y claro que describa tu servicio principal, por ejemplo: "Gestoría en Fuenlabrada — Asesoría fiscal y laboral".',
  },
  {
    code: 'SEO_MULTIPLE_H1',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Hay varios titulares principales en la misma página',
    descriptionEs: 'La página tiene más de un H1. Solo debería haber uno para que Google entienda el tema principal.',
    businessImpact: 'Google recibe señales contradictorias sobre el tema de tu página y puede no posicionarla para ninguna búsqueda concreta.',
    fixSuggestion: 'Dejar un único H1 con el tema principal y usar H2 para los subtemas.',
  },
  {
    code: 'SEO_IMG_NO_ALT',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Imágenes sin descripción para Google',
    descriptionEs: 'Algunas imágenes no tienen texto alternativo (atributo alt). Google no puede "ver" las imágenes, solo leer su descripción.',
    businessImpact: 'Pierdes tráfico de Google Imágenes y puntos de accesibilidad. Los usuarios con lector de pantalla (personas con discapacidad visual) no pueden entender qué muestran las imágenes.',
    fixSuggestion: 'Añadir una descripción breve y descriptiva a cada imagen: qué muestra y en qué contexto.',
  },
  // ─── Seguridad y legal ────────────────────────────────────────────────────
  {
    code: 'SEC_NO_HTTPS',
    category: 'security',
    severity: 'critical',
    titleEs: 'La web no es segura',
    descriptionEs: 'La web no usa HTTPS. Los datos entre el visitante y el servidor viajan sin cifrar.',
    businessImpact: 'Chrome y Firefox muestran un aviso de "No seguro" a todos tus visitantes. Eso destruye la confianza al instante. Además, Google penaliza las webs sin HTTPS en el posicionamiento.',
    fixSuggestion: 'Activar el certificado SSL en tu alojamiento web. La mayoría de proveedores lo ofrecen gratis con Let\'s Encrypt.',
  },
  {
    code: 'SEC_NO_XCTO',
    category: 'security',
    severity: 'medium',
    titleEs: 'Falta una protección básica contra ataques de contenido',
    descriptionEs: 'No está configurada la cabecera X-Content-Type-Options. Esto permite ciertos ataques en los que el navegador malinterpreta archivos.',
    businessImpact: 'Aunque el riesgo para el usuario final es bajo, indica que la web no tiene las protecciones básicas configuradas. Puede ser un punto de entrada para ataques que inyecten código malicioso.',
    fixSuggestion: 'Añadir la cabecera "X-Content-Type-Options: nosniff" en la configuración del servidor. Es un cambio de una línea.',
  },
  {
    code: 'SEC_NO_XFO',
    category: 'security',
    severity: 'medium',
    titleEs: 'Tu web puede ser copiada dentro de otras páginas',
    descriptionEs: 'No está configurada la protección X-Frame-Options. Esto permite que alguien muestre tu web dentro de otra página maliciosa.',
    businessImpact: 'Un atacante puede crear una web falsa que muestre la tuya por encima, capturando clics de tus clientes (ataque "clickjacking"). Especialmente grave si tienes formularios de contacto o pago.',
    fixSuggestion: 'Añadir la cabecera "X-Frame-Options: SAMEORIGIN" en el servidor. Es una línea de configuración.',
  },
  {
    code: 'SEC_NO_CSP',
    category: 'security',
    severity: 'high',
    titleEs: 'Sin política de seguridad de contenido',
    descriptionEs: 'No hay cabecera Content-Security-Policy. Esta cabecera previene que código externo malicioso se ejecute en tu web.',
    businessImpact: 'Sin esta protección, si alguien consigue inyectar código en tu web (por ejemplo a través de un plugin o formulario vulnerable), puede robar datos de tus clientes o redirigirlos a sitios fraudulentos.',
    fixSuggestion: 'Configurar una política CSP básica en el servidor. Para webs simples, una configuración restrictiva se puede activar en 15 minutos.',
  },
  {
    code: 'SEC_NO_HSTS',
    category: 'security',
    severity: 'high',
    titleEs: 'La conexión segura no está forzada',
    descriptionEs: 'Falta la cabecera Strict-Transport-Security. Esto permite que alguien intercepte la conexión antes de que se establezca el cifrado.',
    businessImpact: 'Un atacante en la misma red WiFi que tu cliente (cafeterías, aeropuertos) puede interceptar la conexión inicial y ver o modificar los datos. Especialmente grave en formularios de contacto o datos personales.',
    fixSuggestion: 'Activar HSTS en el servidor con una duración mínima de 1 año. Es una sola línea de configuración en Apache o Nginx.',
  },
];

const EXTENDED_CATALOG = [
  // ─── Móvil ────────────────────────────────────────────────────────────────
  {
    code: 'MOB_NO_VIEWPORT',
    category: 'mobile',
    severity: 'critical',
    titleEs: 'Tu web no está adaptada para móviles',
    descriptionEs: 'Falta la etiqueta de viewport. El navegador muestra la web a escala de escritorio en pantallas pequeñas.',
    businessImpact: 'Más del 70% de tus visitas llegan desde el móvil. Si la web se ve mal, se van en segundos. Google también penaliza las webs no adaptadas a móvil y te baja en los resultados de búsqueda.',
    fixSuggestion: 'Añadir la etiqueta <meta name="viewport" content="width=device-width, initial-scale=1"> en el head de todas las páginas.',
  },
  {
    code: 'MOB_NO_TEL_LINK',
    category: 'mobile',
    severity: 'medium',
    titleEs: 'El teléfono no es clickable desde el móvil',
    descriptionEs: 'El número de teléfono aparece como texto, no como enlace. En móvil no se puede llamar con un toque.',
    businessImpact: 'Un cliente potencial que ve tu número en el móvil tiene que memorizarlo, salir, abrir el marcador y marcarlo. La mayoría no lo hace. Estás perdiendo llamadas por una fricción innecesaria.',
    fixSuggestion: 'Envolver el número en un enlace tel: — por ejemplo <a href="tel:+34600000000">600 000 000</a>.',
  },
  {
    code: 'MOB_NO_WHATSAPP',
    category: 'mobile',
    severity: 'medium',
    titleEs: 'No hay botón de contacto por WhatsApp',
    descriptionEs: 'No se detecta ningún enlace ni botón de WhatsApp en la web.',
    businessImpact: 'WhatsApp es el canal de comunicación preferido de las PYMEs españolas. Sin él, pierdes a todos los clientes que prefieren escribir antes que llamar, que son la mayoría de los menores de 50 años.',
    fixSuggestion: 'Añadir un botón flotante o un enlace wa.me/34XXXXXXXXX con un mensaje de bienvenida predefinido.',
  },
  {
    code: 'MOB_FONT_SMALL',
    category: 'mobile',
    severity: 'medium',
    titleEs: 'Texto demasiado pequeño para leer en móvil',
    descriptionEs: 'Se detectan tamaños de fuente por debajo de 12px que dificultan la lectura en pantallas pequeñas.',
    businessImpact: 'Si el cliente tiene que hacer zoom para leer, la experiencia es mala y suele abandonar. Google mide esto y penaliza la web en móvil.',
    fixSuggestion: 'Establecer un tamaño de fuente base de mínimo 16px para el cuerpo del texto.',
  },
  // ─── Social / Captación ───────────────────────────────────────────────────
  {
    code: 'SOC_NO_OG_TITLE',
    category: 'social',
    severity: 'medium',
    titleEs: 'Tu web no se previsualiza bien al compartirla',
    descriptionEs: 'Faltan las etiquetas Open Graph. Cuando alguien comparte tu web en WhatsApp o redes sociales, no se genera un preview atractivo.',
    businessImpact: 'Cuando un cliente satisfecho comparte tu web, el enlace aparece sin título ni imagen. La gente no hace clic en un enlace vacío. Pierdes tráfico de referidos, que suele ser el más cualificado.',
    fixSuggestion: 'Añadir las etiquetas <meta property="og:title">, <meta property="og:description"> y <meta property="og:image"> en el head.',
  },
  {
    code: 'SOC_NO_OG_IMAGE',
    category: 'social',
    severity: 'high',
    titleEs: 'Sin imagen al compartir en redes sociales',
    descriptionEs: 'No hay etiqueta og:image. Los enlaces compartidos en WhatsApp, LinkedIn o Facebook aparecen sin imagen.',
    businessImpact: 'Los posts con imagen generan entre 3 y 5 veces más clics que los que no la tienen. Cada vez que alguien comparte tu web sin imagen, pierdes la mitad del potencial de ese contacto.',
    fixSuggestion: 'Añadir una imagen de 1200x630px optimizada con <meta property="og:image"> apuntando a una URL absoluta.',
  },
  {
    code: 'SOC_NO_FAVICON',
    category: 'social',
    severity: 'low',
    titleEs: 'Tu web no tiene icono en el navegador',
    descriptionEs: 'No se detecta favicon. Las pestañas del navegador y los marcadores muestran un icono genérico.',
    businessImpact: 'Es un detalle pequeño pero muy visible. Un cliente que tiene tu web entre sus favoritos o en varias pestañas abiertas no puede identificarla de un vistazo. Da una impresión de web descuidada.',
    fixSuggestion: 'Crear un favicon de 32x32px (ICO o PNG) y referenciarlo con <link rel="icon" href="/favicon.ico">.',
  },
  {
    code: 'SOC_NO_CTA',
    category: 'social',
    severity: 'high',
    titleEs: 'No hay ninguna llamada a la acción visible',
    descriptionEs: 'No se detecta ningún botón o enlace que invite al visitante a contactar, llamar, pedir presupuesto o reservar cita.',
    businessImpact: 'Una web sin CTA es como una tienda donde nadie te atiende. El visitante no sabe qué hacer a continuación y se va. Puedes tener buen posicionamiento y perder el 80% de los leads por no guiarles.',
    fixSuggestion: 'Añadir un botón de acción claro y visible en la parte superior: "Llámanos", "Pide presupuesto" o "Reserva cita". Repetirlo al final de cada sección.',
  },
  // ─── SEO Avanzado ─────────────────────────────────────────────────────────
  {
    code: 'SEO_NO_CANONICAL',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Google puede estar indexando versiones duplicadas de tu web',
    descriptionEs: 'No hay etiqueta canonical. Si tu web es accesible por varias URLs (con www y sin www, con http y https), Google puede penalizarte por contenido duplicado.',
    businessImpact: 'Google reparte la "autoridad" de tu web entre todas las versiones duplicadas. Resultado: ninguna versión llega a lo alto de los resultados. Pierdes posicionamiento frente a competidores que sí lo tienen configurado.',
    fixSuggestion: 'Añadir <link rel="canonical" href="URL-principal"> en todas las páginas apuntando siempre a la versión principal.',
  },
  {
    code: 'SEO_NO_SCHEMA',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Google no conoce los datos de tu negocio',
    descriptionEs: 'No se detectan datos estructurados Schema.org. Google usa estos datos para mostrar información enriquecida en los resultados de búsqueda.',
    businessImpact: 'Tus competidores con Schema.org aparecen en Google con sus horarios, valoraciones, dirección y teléfono directamente en los resultados de búsqueda. Tú apareces como un texto genérico. El clic va a ellos.',
    fixSuggestion: 'Añadir un bloque JSON-LD con Schema.org LocalBusiness incluyendo nombre, dirección, teléfono, horario y tipo de negocio.',
  },
  {
    code: 'SEO_NO_ROBOTS',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Google no tiene instrucciones para rastrear tu web',
    descriptionEs: 'No se encuentra el archivo robots.txt. Este archivo le dice a los buscadores qué páginas pueden o no indexar.',
    businessImpact: 'Sin robots.txt, Google puede indexar páginas que no quieres que aparezcan en los resultados (páginas de administración, duplicados, etc.), diluyendo tu posicionamiento y confundiendo al buscador.',
    fixSuggestion: 'Crear un archivo robots.txt en la raíz del dominio con al menos "User-agent: *" y "Disallow: /admin".',
  },
  {
    code: 'SEO_NO_SITEMAP',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Google no tiene un mapa de tu web',
    descriptionEs: 'No se encuentra el archivo sitemap.xml. Este archivo lista todas las páginas de tu web para que Google las indexe.',
    businessImpact: 'Sin sitemap, Google puede tardar semanas en descubrir páginas nuevas o actualizadas. Si añades un nuevo servicio o una página de oferta, Google tardará en mostrarla en los resultados.',
    fixSuggestion: 'Generar un sitemap.xml con la lista de todas las URLs importantes y subirlo a Google Search Console.',
  },
  // ─── Legal ────────────────────────────────────────────────────────────────
  {
    code: 'LEG_NO_COOKIE_BANNER',
    category: 'legal',
    severity: 'high',
    titleEs: 'Tu web puede estar incumpliendo la Ley de Cookies',
    descriptionEs: 'No se detecta ningún banner de consentimiento de cookies. La normativa europea exige informar y pedir permiso antes de instalar cookies.',
    businessImpact: 'La AEPD (Agencia Española de Protección de Datos) impone multas de hasta 20.000€ por webs que instalan cookies sin consentimiento. No es una amenaza teórica: llevan años sancionando a PYMEs.',
    fixSuggestion: 'Instalar un banner de cookies con opciones de aceptar/rechazar y una política de cookies detallada. Herramientas como Cookiebot o Usercentrics lo simplifican.',
  },
  {
    code: 'LEG_NO_PRIVACY',
    category: 'legal',
    severity: 'high',
    titleEs: 'Falta la política de privacidad',
    descriptionEs: 'No se detecta enlace a política de privacidad. Es obligatoria para cualquier web que recoja datos personales (incluido un formulario de contacto).',
    businessImpact: 'Si tienes cualquier formulario en tu web, estás recogiendo datos personales y estás obligado por el RGPD a tener una política de privacidad. Sin ella, puedes recibir multas y reclamaciones de usuarios.',
    fixSuggestion: 'Crear una página de política de privacidad que explique qué datos se recogen, para qué y durante cuánto tiempo. Enlazarla desde el footer y desde todos los formularios.',
  },
  {
    code: 'LEG_NO_LEGAL',
    category: 'legal',
    severity: 'medium',
    titleEs: 'Falta el aviso legal',
    descriptionEs: 'No se detecta enlace a aviso legal. La Ley de Servicios de la Sociedad de la Información (LSSI) lo exige para webs de empresas y autónomos.',
    businessImpact: 'El aviso legal es obligatorio en España para cualquier web con actividad económica. Su ausencia puede derivar en sanciones administrativas y, sobre todo, genera desconfianza en clientes que buscan referencias legales antes de contratar.',
    fixSuggestion: 'Crear una página de aviso legal con los datos identificativos del titular (nombre, NIF, dirección, email) y enlazarla desde el footer.',
  },
];

@Injectable()
export class ChecksSeeder implements OnModuleInit {
  private readonly logger = new Logger(ChecksSeeder.name);

  constructor(private prisma: PrismaService) {}

  async onModuleInit() {
    try {
      this.logger.log('Seeding FindingCatalog...');
      for (const item of [...INITIAL_CATALOG, ...EXTENDED_CATALOG]) {
        await this.prisma.findingCatalog.upsert({
          where: { code: item.code },
          update: item,
          create: item,
        });
      }
      this.logger.log('Seeding completed.');
    } catch (e) {
      this.logger.error('Seeding failed (DB unavailable?): ' + (e as Error).message);
    }
  }
}
