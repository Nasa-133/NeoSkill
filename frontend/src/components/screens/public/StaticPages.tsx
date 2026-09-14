'use client';

import { PublicShell } from '@/components/layout/Shells';
import { ErrorState } from '@/components/ui';
import { usePlatformSettings } from '@/lib/platform-settings';

export function AboutScreen() {
  const { settings, loading, error, retry } = usePlatformSettings();
  return <PublicShell><section className="ns-page-hero"><div className="ns-container"><p className="ns-eyebrow">Biz haqimizda</p><h1>{settings.about_title}</h1><p>{settings.company_name}</p></div></section>
    <section className="ns-section"><div className="ns-container ns-legal">
      {loading ? <p role="status">Yuklanmoqda…</p> : error ? <ErrorState description={error} onRetry={retry} /> : <>
        {settings.about_text.split(/\n\s*\n/).map((paragraph, index) => <p key={index} style={{ whiteSpace: 'pre-line' }}>{paragraph}</p>)}
        {settings.company_address ? <p><strong>Manzil:</strong> {settings.company_address}</p> : null}
      </>}
    </div></section></PublicShell>;
}

export function ContactScreen() {
  const { settings, loading, error, retry } = usePlatformSettings();
  const telegram = settings.support_telegram ? `https://t.me/${settings.support_telegram}` : '';
  const phone = settings.support_phone.replace(/[^+0-9]/g, '');
  const hasContact = Boolean(settings.support_email || telegram || phone);
  return <PublicShell><section className="ns-page-hero"><div className="ns-container"><p className="ns-eyebrow">Aloqa</p><h1>Savolingiz bormi? Biz yordam beramiz</h1><p>Kurs, ariza yoki o‘qish jarayoni bo‘yicha murojaatingizni yuboring.</p></div></section>
    <section className="ns-section"><div className="ns-container">
      {loading ? <p role="status">Yuklanmoqda…</p> : error ? <ErrorState description={error} onRetry={retry} /> : <div className="ns-contact-grid">
        <div><h2>{settings.company_name}</h2><dl>
          {settings.support_email ? <div><dt>Email</dt><dd><a href={`mailto:${settings.support_email}`}>{settings.support_email}</a></dd></div> : null}
          {telegram ? <div><dt>Telegram</dt><dd><a href={telegram} target="_blank" rel="noreferrer">@{settings.support_telegram}</a></dd></div> : null}
          {phone ? <div><dt>Telefon</dt><dd><a href={`tel:${phone}`}>{settings.support_phone}</a></dd></div> : null}
          {settings.company_address ? <div><dt>Manzil</dt><dd>{settings.company_address}</dd></div> : null}
          {settings.working_hours ? <div><dt>Ish vaqti</dt><dd>{settings.working_hours}</dd></div> : null}
        </dl>{!hasContact ? <p>Aloqa ma’lumotlari hozircha kiritilmagan.</p> : null}</div>
        {hasContact ? <div className="ns-form-card"><h2>Biz bilan bog‘laning</h2><p className="ns-muted">Quyidagi tugma orqali yozing yoki qo‘ng‘iroq qiling.</p>
          {settings.support_email ? <a className="ns-link-button" href={`mailto:${settings.support_email}`}>Email yozish</a> : null}
          {telegram ? <a className="ns-link-button ns-link-button--secondary" href={telegram} target="_blank" rel="noreferrer">Telegramda yozish ↗</a> : null}
          {phone ? <a className="ns-link-button ns-link-button--secondary" href={`tel:${phone}`}>Qo‘ng‘iroq qilish</a> : null}
        </div> : null}
      </div>}
    </div></section></PublicShell>;
}
