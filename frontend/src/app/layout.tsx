import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Cricket Commentary Website Analyzer',
  description: 'Get your website analyzed by legendary cricket commentators',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="cricket-pattern" />
        <div className="relative min-h-screen">
          {children}
        </div>
      </body>
    </html>
  )
}
