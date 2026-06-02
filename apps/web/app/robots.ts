import { MetadataRoute } from 'next';

export const dynamic = 'force-static';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/report/'],
    },
    sitemap: 'https://audita.zero2dev.es/sitemap.xml',
  };
}
