import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Script from 'next/script'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'TEN x Minimax - experience the latest Minimax TTS with human like voices',
    description: 'TEN x Minimax Live2D assistant: experience the latest Minimax TTS with human-like voices, powered by TEN.',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <head>
                <Script src="/lib/live2dcubismcore.min.js" strategy="beforeInteractive" />
            </head>
            <body className={inter.className}>
                {children}
            </body>
        </html>
    )
}
