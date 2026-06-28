import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PoliceOSINT — Cyber Crime Investigation Platform',
  description: 'AI-Powered OSINT Platform for Law Enforcement — GPCSSI',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.4.0/dist/tabler-icons.min.css"
        />
      </head>
      <body>{children}</body>
    </html>
  )
}
