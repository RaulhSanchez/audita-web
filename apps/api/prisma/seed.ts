import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const catalog = [
  // ─── RENDIMIENTO ───────────────────────────────────────────────────────────
  {
    code: 'PERF_SCORE_LOW',
    category: 'performance',
    severity: 'critical',
    titleEs: 'Tu web carga demasiado lento',
    descriptionEs: 'La velocidad de carga de tu web es muy baja. Google penaliza las webs lentas en los resultados de búsqueda.',
    businessImpact: 'El 53% de los usuarios abandona una web si tarda más de 3 segundos en cargar. Cada segundo de retraso reduce las conversiones un 7%. Estás perdiendo clientes potenciales antes de que te conozcan.',
    fixSuggestion: 'Optimiza las imágenes, activa la compresión de archivos y usa un sistema de caché. Contacta con un desarrollador para una auditoría de rendimiento completa.',
  },
  {
    code: 'PERF_SCORE_MED',
    category: 'performance',
    severity: 'high',
    titleEs: 'Tu web podría cargar más rápido',
    descriptionEs: 'La velocidad de carga está por debajo de la media. Hay margen de mejora significativo.',
    businessImpact: 'Una web lenta genera desconfianza y aumenta la tasa de abandono. Tus competidores con webs más rápidas aparecen antes en Google y se llevan tus clientes potenciales.',
    fixSuggestion: 'Optimiza el tamaño de las imágenes, elimina plugins o scripts innecesarios y considera cambiar a un hosting más rápido.',
  },
  {
    code: 'PERF_LCP_HIGH',
    category: 'performance',
    severity: 'high',
    titleEs: 'El contenido principal tarda demasiado en aparecer',
    descriptionEs: 'El tiempo hasta que el usuario ve el contenido principal (imagen o texto destacado) es demasiado alto.',
    businessImpact: 'Los usuarios ven una pantalla en blanco o parcial demasiado tiempo. Esto genera frustración y abandono. Google mide este tiempo como factor de posicionamiento: estás perdiendo visibilidad en buscadores.',
    fixSuggestion: 'Optimiza la imagen o bloque principal de tu web. Usa formatos modernos como WebP y asegúrate de que el servidor responde rápido.',
  },

  // ─── SEO ───────────────────────────────────────────────────────────────────
  {
    code: 'SEO_NO_TITLE',
    category: 'seo',
    severity: 'critical',
    titleEs: 'Tu web no tiene título para Google',
    descriptionEs: 'La página no tiene etiqueta de título (title tag), que es lo que Google muestra en los resultados de búsqueda.',
    businessImpact: 'Sin título, Google no sabe de qué trata tu web y no te posiciona. Cuando alguien busca tus servicios, tu negocio es invisible. Estás regalando clientes a tu competencia.',
    fixSuggestion: 'Añade un título descriptivo de 50-60 caracteres que incluya tu servicio principal y tu localidad. Por ejemplo: "Gestoría García | Asesoría Fiscal en Madrid".',
  },
  {
    code: 'SEO_NO_META_DESC',
    category: 'seo',
    severity: 'high',
    titleEs: 'Sin descripción en Google',
    descriptionEs: 'Tu web no tiene meta descripción, el texto que aparece bajo el título en los resultados de búsqueda.',
    businessImpact: 'Google genera una descripción automática poco atractiva. Pierdes la oportunidad de convencer al usuario de que haga clic en tu web en lugar de la de un competidor. Menos clics = menos clientes.',
    fixSuggestion: 'Añade una descripción de 120-160 caracteres que explique qué haces, para quién y qué te diferencia. Incluye una llamada a la acción.',
  },
  {
    code: 'SEO_NO_H1',
    category: 'seo',
    severity: 'high',
    titleEs: 'Falta el título principal de la página',
    descriptionEs: 'Tu web no tiene un encabezado H1, que es el título principal que indica a Google el tema central de la página.',
    businessImpact: 'Google no entiende de qué trata tu página y no sabe para qué búsquedas posicionarte. Estás perdiendo visibilidad para los servicios que ofreces.',
    fixSuggestion: 'Añade un H1 claro que describa tu servicio principal. Solo debe haber uno por página.',
  },
  {
    code: 'SEO_MULTIPLE_H1',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Estructura de títulos confusa',
    descriptionEs: 'Tu página tiene más de un título principal (H1), lo que confunde a Google sobre el tema central.',
    businessImpact: 'Google distribuye la relevancia entre varios títulos en lugar de concentrarla en uno. Esto reduce tu posicionamiento para las búsquedas clave de tu negocio.',
    fixSuggestion: 'Deja solo un H1 por página con tu mensaje principal. El resto usa H2 y H3 para subtítulos.',
  },
  {
    code: 'SEO_TITLE_LENGTH',
    category: 'seo',
    severity: 'medium',
    titleEs: 'El título de tu web es demasiado largo o corto',
    descriptionEs: 'El título de la página no tiene la longitud óptima para aparecer completo en Google.',
    businessImpact: 'Un título demasiado largo se corta en los resultados de búsqueda y pierde impacto. Uno demasiado corto no aprovecha el espacio para convencer al usuario. Ambos reducen los clics que recibes.',
    fixSuggestion: 'Ajusta el título a entre 50 y 60 caracteres. Incluye tu palabra clave principal y el nombre de tu empresa.',
  },
  {
    code: 'SEO_IMG_NO_ALT',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Imágenes sin descripción para Google',
    descriptionEs: 'Varias imágenes de tu web no tienen texto alternativo (atributo alt).',
    businessImpact: 'Google no puede "ver" las imágenes, solo leer su descripción. Sin ella, pierdes oportunidades de aparecer en Google Imágenes y reduces la relevancia general de tu página.',
    fixSuggestion: 'Añade una descripción breve y descriptiva a cada imagen. Describe lo que muestra e incluye palabras clave cuando sea natural.',
  },
  {
    code: 'SEO_NO_CANONICAL',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Riesgo de contenido duplicado',
    descriptionEs: 'Tu web no tiene etiqueta canonical, que indica a Google cuál es la versión oficial de cada página.',
    businessImpact: 'Google puede penalizarte por contenido duplicado si tu web es accesible desde varias URLs. Esto divide tu posicionamiento y reduce tu visibilidad en buscadores.',
    fixSuggestion: 'Añade etiquetas canonical a todas tus páginas apuntando a la URL principal.',
  },
  {
    code: 'SEO_NO_SITEMAP',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Google no tiene el mapa de tu web',
    descriptionEs: 'Tu web no tiene un archivo sitemap.xml que ayude a Google a descubrir y indexar todas tus páginas.',
    businessImpact: 'Google tarda más en encontrar y actualizar tu contenido. Páginas importantes de tus servicios pueden no estar indexadas y no aparecer cuando alguien te busca.',
    fixSuggestion: 'Genera un sitemap.xml con todas tus páginas y regístralo en Google Search Console.',
  },
  {
    code: 'SEO_NO_ROBOTS',
    category: 'seo',
    severity: 'low',
    titleEs: 'Sin instrucciones para los buscadores',
    descriptionEs: 'Tu web no tiene un archivo robots.txt que guíe a los buscadores sobre qué páginas indexar.',
    businessImpact: 'Google puede indexar páginas que no quieres que aparezcan en resultados, como páginas de administración o duplicados. Esto diluye tu posicionamiento.',
    fixSuggestion: 'Crea un archivo robots.txt básico que permita la indexación de tu contenido público y bloquee las áreas privadas.',
  },
  {
    code: 'SEO_NO_SCHEMA',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Pierdes visibilidad en resultados enriquecidos de Google',
    descriptionEs: 'Tu web no tiene datos estructurados (Schema.org) que permiten a Google mostrar información especial en los resultados de búsqueda.',
    businessImpact: 'Tus competidores con datos estructurados aparecen en Google con estrellas de valoración, horarios, precios o preguntas frecuentes, ocupando más espacio y captando más clics. Tú apareces como un resultado genérico.',
    fixSuggestion: 'Implementa Schema.org para tu tipo de negocio: LocalBusiness, Organization o el específico de tu sector (dentista, taller, gestoría...).',
  },

  // ─── MÓVIL Y UX ────────────────────────────────────────────────────────────
  {
    code: 'MOB_NO_VIEWPORT',
    category: 'mobile',
    severity: 'critical',
    titleEs: 'Tu web no está adaptada al móvil',
    descriptionEs: 'Falta la configuración básica que hace que tu web se vea correctamente en smartphones.',
    businessImpact: 'Más del 60% de las búsquedas locales se hacen desde el móvil. Si tu web se ve mal en el móvil, los usuarios se van directamente y Google te penaliza en el posicionamiento. Estás perdiendo la mayoría de tus clientes potenciales.',
    fixSuggestion: 'Añade la etiqueta viewport en el encabezado de tu web y asegúrate de que el diseño sea responsive (adaptable a cualquier pantalla).',
  },
  {
    code: 'MOB_FONT_SMALL',
    category: 'mobile',
    severity: 'medium',
    titleEs: 'Texto demasiado pequeño en móvil',
    descriptionEs: 'El tamaño de letra de tu web es demasiado pequeño para leer cómodamente en un smartphone.',
    businessImpact: 'Los usuarios tienen que hacer zoom para leer, lo que es frustrante. La mayoría abandona la web en lugar de molestarse. Perdes la oportunidad de transmitir tu mensaje y generar confianza.',
    fixSuggestion: 'Aumenta el tamaño de fuente base a mínimo 16px para texto principal. El contenido tiene que leerse sin hacer zoom.',
  },
  {
    code: 'MOB_NO_TEL_LINK',
    category: 'mobile',
    severity: 'high',
    titleEs: 'El teléfono no es clicable en móvil',
    descriptionEs: 'El número de teléfono de tu web no está configurado como enlace clicable en dispositivos móviles.',
    businessImpact: 'Un usuario interesado ve tu teléfono pero tiene que copiarlo manualmente para llamarte, lo que es incómodo y muchos no lo hacen. Estás perdiendo llamadas de clientes potenciales que ya estaban listos para contactarte.',
    fixSuggestion: 'Convierte todos los números de teléfono en enlaces con formato tel:+34XXXXXXXXX para que al hacer clic se inicie la llamada directamente.',
  },
  {
    code: 'MOB_NO_WHATSAPP',
    category: 'mobile',
    severity: 'medium',
    titleEs: 'Sin botón de WhatsApp',
    descriptionEs: 'Tu web no tiene un enlace directo a WhatsApp para contactar fácilmente desde el móvil.',
    businessImpact: 'WhatsApp es el canal de comunicación preferido para contactar con negocios locales en España. Sin él, pones una barrera innecesaria entre tú y tus clientes potenciales. Tu competencia que sí lo tiene capta esos contactos.',
    fixSuggestion: 'Añade un botón flotante de WhatsApp en tu web con enlace directo a tu número de negocio. Es una de las mejoras con mejor retorno de inversión.',
  },

  // ─── SEGURIDAD Y LEGAL ─────────────────────────────────────────────────────
  {
    code: 'SEC_NO_HTTPS',
    category: 'security',
    severity: 'critical',
    titleEs: 'Tu web no es segura (sin HTTPS)',
    descriptionEs: 'Tu web no usa el protocolo seguro HTTPS. Los navegadores la marcan como "No segura".',
    businessImpact: 'Los navegadores muestran una advertencia de "No segura" a tus visitantes, lo que destruye la confianza inmediatamente. Google penaliza duramente estas webs en el posicionamiento. Además, cualquier dato que introduzca un cliente (formularios, emails) viaja sin protección.',
    fixSuggestion: 'Instala un certificado SSL en tu servidor. La mayoría de los hostings lo ofrecen gratis a través de Let\'s Encrypt.',
  },
  {
    code: 'SEC_NO_HSTS',
    category: 'security',
    severity: 'medium',
    titleEs: 'Protección incompleta contra ataques',
    descriptionEs: 'Tu web no tiene activada la política de seguridad HSTS que fuerza siempre conexiones seguras.',
    businessImpact: 'Un atacante podría interceptar la comunicación entre tu web y tus clientes en ciertos escenarios. Aunque tienes HTTPS, sin HSTS la protección no es completa, lo que puede suponer un riesgo de reputación y responsabilidad legal.',
    fixSuggestion: 'Activa el encabezado Strict-Transport-Security en tu servidor web. Tu proveedor de hosting o desarrollador puede hacerlo en minutos.',
  },
  {
    code: 'SEC_NO_XCTO',
    category: 'security',
    severity: 'low',
    titleEs: 'Configuración de seguridad básica pendiente',
    descriptionEs: 'Falta el encabezado X-Content-Type-Options que previene ciertos tipos de ataques.',
    businessImpact: 'Aunque el impacto directo en negocio es bajo, es una vulnerabilidad técnica que los auditores de seguridad detectan. Puede ser relevante si manejas datos de clientes.',
    fixSuggestion: 'Añade el encabezado X-Content-Type-Options: nosniff en la configuración de tu servidor.',
  },
  {
    code: 'SEC_NO_XFO',
    category: 'security',
    severity: 'low',
    titleEs: 'Tu web puede ser copiada en otras páginas',
    descriptionEs: 'Sin el encabezado X-Frame-Options, tu web puede ser incrustada en otras páginas para engañar a tus clientes (clickjacking).',
    businessImpact: 'Atacantes podrían mostrar tu web dentro de otra página maliciosa y engañar a tus clientes para que introduzcan datos o hagan clic donde no deben. Supone riesgo reputacional y legal.',
    fixSuggestion: 'Añade el encabezado X-Frame-Options: DENY o SAMEORIGIN en tu servidor.',
  },
  {
    code: 'SEC_NO_CSP',
    category: 'security',
    severity: 'medium',
    titleEs: 'Sin política de seguridad de contenido',
    descriptionEs: 'Tu web no tiene Content Security Policy (CSP), una capa de protección contra inyección de código malicioso.',
    businessImpact: 'Sin CSP, si tu web es comprometida, un atacante podría inyectar código para robar datos de tus clientes. Esto puede derivar en sanciones del RGPD de hasta el 4% de tu facturación anual.',
    fixSuggestion: 'Implementa una política CSP básica. Es una tarea técnica pero protege tanto a tu negocio como a tus clientes.',
  },

  // ─── LEGAL ─────────────────────────────────────────────────────────────────
  {
    code: 'LEG_NO_COOKIE_BANNER',
    category: 'legal',
    severity: 'critical',
    titleEs: 'Sin aviso de cookies: riesgo de multa',
    descriptionEs: 'Tu web no muestra el aviso de consentimiento de cookies requerido por la ley española y el RGPD europeo.',
    businessImpact: 'La Agencia Española de Protección de Datos (AEPD) sanciona con multas de hasta 20 millones de euros o el 4% de la facturación anual. Incluso para pequeños negocios, las multas son habituales. Además, daña la confianza de tus clientes.',
    fixSuggestion: 'Instala un banner de cookies que cumpla la normativa: explica qué cookies usas, para qué, y permite al usuario aceptar o rechazar. Existen soluciones gratuitas como Cookiebot o similares.',
  },
  {
    code: 'LEG_NO_LEGAL',
    category: 'legal',
    severity: 'critical',
    titleEs: 'Sin aviso legal: incumplimiento de la LSSI',
    descriptionEs: 'Tu web no tiene página de aviso legal, obligatoria por la Ley de Servicios de la Sociedad de la Información (LSSI).',
    businessImpact: 'Cualquier negocio con presencia online en España está obligado a tener aviso legal. Su ausencia puede suponer sanciones de hasta 150.000€. Además, sin aviso legal no puedes hacer valer tus condiciones de servicio ante conflictos con clientes.',
    fixSuggestion: 'Crea una página de aviso legal con: datos de la empresa, CIF/NIF, domicilio social, datos de contacto y condiciones de uso. Puedes usar plantillas gratuitas adaptadas a la normativa española.',
  },
  {
    code: 'LEG_NO_PRIVACY',
    category: 'legal',
    severity: 'critical',
    titleEs: 'Sin política de privacidad: violación del RGPD',
    descriptionEs: 'Tu web no tiene política de privacidad. Si recoges cualquier dato (emails, formularios de contacto), es obligatoria por el RGPD.',
    businessImpact: 'Recoger datos sin política de privacidad es una infracción grave del RGPD con multas de hasta 20 millones de euros. Si tienes formularios de contacto o newsletter, estás incumpliendo la ley ahora mismo.',
    fixSuggestion: 'Crea una política de privacidad que detalle: qué datos recoges, para qué, cuánto tiempo los guardas, con quién los compartes y cómo puede el usuario ejercer sus derechos. Existe ayuda gratuita en la web de la AEPD.',
  },

  // ─── CAPTACIÓN Y REDES SOCIALES ────────────────────────────────────────────
  {
    code: 'SOC_NO_OG_TITLE',
    category: 'social',
    severity: 'medium',
    titleEs: 'Tu web se ve mal cuando la comparten en redes',
    descriptionEs: 'Tu web no tiene configuradas las etiquetas Open Graph que controlan cómo se muestra cuando alguien comparte el enlace en WhatsApp, LinkedIn o Facebook.',
    businessImpact: 'Cuando un cliente satisfecho comparte tu web en WhatsApp o LinkedIn, aparece sin título, sin imagen y con una descripción genérica. En lugar de generar interés, pasa desapercibida. Pierdes el boca a boca digital.',
    fixSuggestion: 'Añade las etiquetas Open Graph básicas: og:title, og:description, og:image y og:url en el encabezado de tu web.',
  },
  {
    code: 'SOC_NO_OG_IMAGE',
    category: 'social',
    severity: 'medium',
    titleEs: 'Sin imagen al compartir en redes sociales',
    descriptionEs: 'Tu web no tiene imagen Open Graph configurada. Cuando se comparte el enlace, aparece sin imagen.',
    businessImpact: 'Los enlaces con imagen reciben hasta 3 veces más clics que los que aparecen sin ella. Cada vez que alguien comparte tu web, estás perdiendo ese impacto visual que genera confianza y curiosidad.',
    fixSuggestion: 'Añade una imagen og:image de al menos 1200x630 píxeles que represente tu negocio. Puede ser tu logo sobre un fondo de marca.',
  },
  {
    code: 'SOC_NO_FAVICON',
    category: 'social',
    severity: 'low',
    titleEs: 'Sin icono de negocio en el navegador',
    descriptionEs: 'Tu web no tiene favicon, el pequeño icono que aparece en las pestañas del navegador y marcadores.',
    businessImpact: 'Una web sin favicon transmite descuido y falta de profesionalidad. Los usuarios que tienen varias pestañas abiertas no pueden identificar la tuya fácilmente. Pequeño detalle que afecta la percepción de tu marca.',
    fixSuggestion: 'Crea un favicon con tu logo o inicial de empresa en formato .ico o .png (32x32 píxeles mínimo) y añádelo a tu web.',
  },
  {
    code: 'SOC_NO_CTA',
    category: 'social',
    severity: 'high',
    titleEs: 'Tu web no invita a contactarte',
    descriptionEs: 'No se detectan llamadas a la acción (CTA) claras que animen al usuario a contactar, llamar o contratar.',
    businessImpact: 'Un usuario interesado llega a tu web pero no sabe qué hacer a continuación. Sin botones o textos que le guíen ("Llámanos", "Pide presupuesto", "Contáctanos"), muchos se van sin contactarte. Estás atrayendo visitas pero no las conviertes en clientes.',
    fixSuggestion: 'Añade al menos un botón de acción visible en la parte superior de la página ("Solicitar presupuesto gratis", "Llamar ahora", "WhatsApp"). Repítelo al final de cada sección importante.',
  },

  // ─── SEGURIDAD (nuevos) ─────────────────────────────────────────────────────
  {
    code: 'SEC_MIXED_CONTENT',
    category: 'security',
    severity: 'high',
    titleEs: 'Recursos inseguros en una web segura',
    descriptionEs: 'Tu web usa HTTPS pero carga imágenes, scripts o estilos desde URLs sin cifrar (HTTP).',
    businessImpact: 'Los navegadores bloquean automáticamente estos recursos o muestran advertencias de seguridad visibles al usuario. Esto reduce la confianza, puede romper partes de tu web y afecta negativamente al posicionamiento en Google.',
    fixSuggestion: 'Cambia todas las URLs de recursos a HTTPS. Busca en el código fuente referencias a "http://" y actualízalas. Si usas un CMS como WordPress, el plugin "Better Search Replace" puede hacerlo automáticamente.',
  },
  {
    code: 'SEC_SERVER_EXPOSED',
    category: 'security',
    severity: 'low',
    titleEs: 'El servidor revela información técnica',
    descriptionEs: 'La cabecera Server del servidor web expone información sobre el software y versión utilizada.',
    businessImpact: 'Los atacantes usan esta información para buscar vulnerabilidades conocidas de esa versión concreta. Es información innecesaria que solo beneficia a quienes quieren comprometer tu web.',
    fixSuggestion: 'Configura tu servidor web (Apache, Nginx, etc.) para ocultar o minimizar la cabecera Server. Tu proveedor de hosting puede hacerlo en minutos.',
  },

  // ─── SEO (nuevos) ──────────────────────────────────────────────────────────
  {
    code: 'SEO_NO_LANG',
    category: 'seo',
    severity: 'medium',
    titleEs: 'Google no sabe en qué idioma está tu web',
    descriptionEs: 'Tu web no tiene declarado el idioma principal en el código HTML.',
    businessImpact: 'Google y otros buscadores usan el atributo de idioma para mostrar tu web a usuarios del idioma correcto. Sin él, puedes aparecer en búsquedas del idioma incorrecto o perder relevancia local. Los lectores de pantalla también dependen de esto para las personas con discapacidad.',
    fixSuggestion: 'Añade el atributo lang al elemento HTML principal. Para español: <html lang="es">. Si tienes contenido en varios idiomas, usa hreflang.',
  },
  {
    code: 'SEO_META_DESC_LENGTH',
    category: 'seo',
    severity: 'medium',
    titleEs: 'La descripción en Google no tiene el tamaño óptimo',
    descriptionEs: 'La meta descripción de tu web es demasiado corta o demasiado larga para aparecer completa en los resultados de búsqueda.',
    businessImpact: 'Una descripción demasiado larga se corta con "..." en Google, perdiendo parte del mensaje. Una muy corta no aprovecha el espacio para convencer al usuario. En ambos casos reduces los clics que recibes desde buscadores.',
    fixSuggestion: 'Ajusta la meta descripción a entre 120 y 158 caracteres. Incluye tu servicio principal, localidad y una llamada a la acción como "Solicita tu presupuesto gratis".',
  },

  // ─── SOCIAL (nuevos) ────────────────────────────────────────────────────────
  {
    code: 'SOC_NO_SOCIAL_PROFILES',
    category: 'social',
    severity: 'medium',
    titleEs: 'Sin enlaces a redes sociales',
    descriptionEs: 'Tu web no enlaza a ningún perfil en redes sociales (Facebook, Instagram, LinkedIn o Twitter/X).',
    businessImpact: 'Las redes sociales son una señal de confianza para los visitantes. Un negocio sin presencia en redes parece menos establecido. Además, pierdes la oportunidad de que los visitantes te sigan y reciban tus novedades.',
    fixSuggestion: 'Añade iconos con enlace a tus perfiles sociales activos en el footer o cabecera. Si no tienes redes sociales, considera crear al menos un perfil de Google Business y uno de Instagram o LinkedIn según tu sector.',
  },
  {
    code: 'SOC_NO_GOOGLE_MAPS',
    category: 'social',
    severity: 'low',
    titleEs: 'Sin ubicación en el mapa',
    descriptionEs: 'Tu web no muestra un mapa de Google con tu localización.',
    businessImpact: 'Los clientes que quieren visitar tu negocio tienen que buscar tu dirección por separado. Un mapa integrado genera confianza y facilita que lleguen a tu local, aumentando las visitas físicas.',
    fixSuggestion: 'Incrusta un Google Maps con la ubicación de tu negocio en la página de contacto. Además, da de alta o reclama tu ficha en Google Business Profile para aparecer en las búsquedas locales.',
  },
  {
    code: 'SOC_NO_CONTACT_FORM',
    category: 'social',
    severity: 'medium',
    titleEs: 'Sin formulario de contacto',
    descriptionEs: 'Tu web no tiene un formulario de contacto que permita a los visitantes enviarte un mensaje directamente.',
    businessImpact: 'Muchos usuarios prefieren enviar un mensaje por formulario antes que llamar o buscar tu email. Sin formulario, pierdes los contactos de personas interesadas pero que no dan el paso de llamar. Es una fuente de leads que estás dejando ir.',
    fixSuggestion: 'Añade un formulario de contacto sencillo (nombre, email, mensaje) en tu página de contacto. Existen soluciones gratuitas como Contact Form 7 para WordPress o Formspree para webs estáticas.',
  },

  // ─── RENDIMIENTO (nuevos) ──────────────────────────────────────────────────
  {
    code: 'PERF_TTFB_HIGH',
    category: 'performance',
    severity: 'high',
    titleEs: 'El servidor tarda demasiado en responder',
    descriptionEs: 'El tiempo hasta que el servidor empieza a enviar datos (TTFB) es superior a 1,5 segundos.',
    businessImpact: 'Google usa el tiempo de respuesta del servidor como factor de posicionamiento directo. Un servidor lento penaliza tu visibilidad en buscadores y aumenta el abandono antes de que el usuario vea nada. Parece que la web está caída aunque esté funcionando.',
    fixSuggestion: 'Contrata un hosting con mejor rendimiento, activa la caché del servidor o usa una CDN. Si usas WordPress, plugins como WP Rocket o W3 Total Cache pueden reducir drásticamente el tiempo de respuesta.',
  },
  {
    code: 'PERF_PAGE_HEAVY',
    category: 'performance',
    severity: 'medium',
    titleEs: 'La página pesa demasiado',
    descriptionEs: 'El HTML de la página principal supera los 500 KB, lo que indica un exceso de código o contenido incrustado.',
    businessImpact: 'Una página pesada tarda más en descargarse, especialmente en conexiones móviles lentas. Esto incrementa el tiempo de carga y dispara el abandono de usuarios antes de que vean tu oferta.',
    fixSuggestion: 'Revisa si hay código CSS o JavaScript incrustado directamente en la página que pueda moverse a archivos externos. Comprime el código HTML y elimina espacios y comentarios innecesarios en producción.',
  },
  {
    code: 'PERF_TOO_MANY_SCRIPTS',
    category: 'performance',
    severity: 'medium',
    titleEs: 'Demasiados scripts externos ralentizan la carga',
    descriptionEs: 'Tu web carga más de 15 archivos JavaScript externos, lo que aumenta significativamente el tiempo de carga.',
    businessImpact: 'Cada script externo es una petición adicional al servidor que retrasa la carga de la página. Con más de 15, la acumulación es notable en dispositivos lentos o conexiones móviles. Esto impacta directamente en la experiencia del usuario y en tu posicionamiento.',
    fixSuggestion: 'Combina y minimiza los scripts JavaScript. Elimina plugins o scripts que no uses activamente. Considera cargar scripts no críticos de forma diferida (lazy loading).',
  },
];

async function main() {
  console.log('🌱 Seeding FindingCatalog...');

  for (const entry of catalog) {
    await prisma.findingCatalog.upsert({
      where: { code: entry.code },
      update: entry,
      create: entry,
    });
  }

  console.log(`✅ ${catalog.length} finding catalog entries seeded.`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
