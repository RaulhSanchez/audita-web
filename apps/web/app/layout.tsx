import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  verification: {
    google: 'KXEsjMuUk4SIg3fl5Xnki76B1DcJuw6k5Bi8G-UO0Zc',
  },
  title: "AuditaWeb — Auditoría web gratis para PYMEs | zero2dev.es",
  description: "Análisis profesional de rendimiento, SEO, seguridad y RGPD en 90 segundos. Descubre por qué tu web está perdiendo clientes. Informe en lenguaje de negocio, gratis.",
  openGraph: {
    title: "AuditaWeb — Auditoría web gratis para PYMEs",
    description: "Descubre en 90 segundos por qué tu web está perdiendo clientes. Informe de rendimiento, SEO, seguridad y RGPD. Gratis, sin registro.",
    url: "https://audita.zero2dev.es",
    siteName: "AuditaWeb · zero2dev.es",
    locale: "es_ES",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script defer data-domain="audita.zero2dev.es" src="https://plausible.io/js/script.js"></script>
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
