import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { PlatformSettingsProvider } from '@/lib/platform-settings';
import { ReferralCapture } from '@/lib/referral';

import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'),
  title: { default: 'NeoSkill', template: '%s | NeoSkill' },
  description: 'NeoSkill amaliy online kurslari orqali yangi ko‘nikmalarni bosqichma-bosqich o‘rganing.',
  openGraph: {
    type: 'website', locale: 'uz_UZ', siteName: 'NeoSkill', title: 'NeoSkill',
    description: 'Amaliy kurslar, mashqlar va bilimni tekshiruvchi mavzu testlari.',
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="uz">
      <body><a className="ns-skip" href="#main-content">Asosiy kontentga o‘tish</a><ReferralCapture /><PlatformSettingsProvider>{children}</PlatformSettingsProvider></body>
    </html>
  );
}
