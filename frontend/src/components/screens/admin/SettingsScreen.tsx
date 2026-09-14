'use client';

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, readApiError } from '@/lib/api';
import { settingsChanged } from '@/lib/platform-settings';
import { useCurrentUser } from '@/lib/session';
import type { PlatformSettings } from '@/lib/types';
import { AdminShell } from '@/components/layout/Shells';
import { Button, Card, ErrorState, Input, PageHeader, Select, Textarea } from '@/components/ui';

export function SettingsScreen() {
  const [values, setValues] = useState<PlatformSettings | null>(null);
  const [password, setPassword] = useState('');
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [testRecipient, setTestRecipient] = useState('');
  const { user } = useCurrentUser();
  const load = useCallback(async () => {
    setError('');
    try { setValues(await api.adminSettings()); }
    catch (reason) { setError(readApiError(reason, 'Sozlamalarni yuklab bo‘lmadi.')); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { if (user?.email) setTestRecipient(user.email); }, [user?.email]);
  function patch(next: Partial<PlatformSettings>) {
    setValues(current => current ? { ...current, ...next } : current);
    setDirty(true); setMessage(''); setError('');
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!values) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const payload: Partial<PlatformSettings> & { smtp_password?: string } = { ...values };
      delete payload.smtp_password_set;
      delete payload.updated_at;
      const saved = await api.saveSettings({ ...payload, ...(password ? { smtp_password: password } : {}) });
      setValues(saved); setPassword(''); setDirty(false); settingsChanged();
      setMessage('Sozlamalar saqlandi. Sayt va email xizmati yangi qiymatlardan foydalanadi.');
    } catch (reason) { setError(readApiError(reason, 'Sozlamalarni saqlab bo‘lmadi.')); }
    finally { setBusy(false); }
  }
  async function testEmail(event: FormEvent) {
    event.preventDefault(); setTesting(true); setError(''); setMessage('');
    try { setMessage((await api.testEmail(testRecipient)).detail); }
    catch (reason) { setError(readApiError(reason, 'Test xatini yuborib bo‘lmadi.')); }
    finally { setTesting(false); }
  }
  return <AdminShell>
    <PageHeader eyebrow="Platforma" title="Sozlamalar" description="Kompaniya, aloqa va parolni tiklash emailini bir joydan boshqaring." />
    {!values ? error ? <ErrorState description={error} onRetry={load} /> : <p role="status">Sozlamalar yuklanmoqda…</p> : <>
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
      {message ? <p role="status">{message}</p> : null}
      <form className="ns-settings" onSubmit={save}>
        <fieldset disabled={busy || testing}>
          <Card><h2>Kompaniya haqida</h2>
            <div className="ns-form-grid">
              <Input id="platform-name" label="Platforma nomi" required maxLength={100} value={values.platform_name} onChange={e => patch({ platform_name: e.target.value })} />
              <Input id="company-name" label="Kompaniya nomi" required maxLength={200} value={values.company_name} onChange={e => patch({ company_name: e.target.value })} />
            </div>
            <Input id="about-title" label="Biz haqimizda sarlavhasi" required maxLength={200} value={values.about_title} onChange={e => patch({ about_title: e.target.value })} />
            <Textarea id="about-text" label="Kompaniya haqida ma’lumot" required maxLength={20000} rows={6} value={values.about_text} onChange={e => patch({ about_text: e.target.value })} />
            <Input id="company-address" label="Manzil" maxLength={500} value={values.company_address} onChange={e => patch({ company_address: e.target.value })} />
            <Textarea id="footer-text" label="Sayt pastidagi qisqa matn" required maxLength={300} value={values.footer_text} onChange={e => patch({ footer_text: e.target.value })} />
          </Card>
          <Card><h2>Aloqa va yordam</h2><div className="ns-form-grid">
            <Input id="support-email" label="Yordam emaili" type="email" value={values.support_email} onChange={e => patch({ support_email: e.target.value })} />
            <Input id="support-telegram" label="Telegram" placeholder="@username" value={values.support_telegram} onChange={e => patch({ support_telegram: e.target.value })} />
            <Input id="support-phone" label="Telefon" type="tel" placeholder="+998 …" value={values.support_phone} onChange={e => patch({ support_phone: e.target.value })} />
            <Input id="working-hours" label="Ish vaqti" maxLength={200} value={values.working_hours} onChange={e => patch({ working_hours: e.target.value })} />
          </div></Card>
          <Card><h2>Parolni tiklash emaili</h2>
            <Select id="smtp-source" label="Email sozlamalari" value={values.smtp_source} onChange={e => patch({ smtp_source: e.target.value as PlatformSettings['smtp_source'] })}>
              <option value="ENV">Serverdagi mavjud sozlamalar</option><option value="ADMIN">Shu paneldan boshqarish</option>
            </Select>
            <p className="ns-form-note">{values.smtp_source === 'ENV' ? 'Serverdagi mavjud email sozlamalari ishlatiladi. O‘zgartirish uchun paneldan boshqarishni tanlang.' : 'Email provayderingiz bergan SMTP ma’lumotlarini kiriting. Gmail uchun ilova paroli kerak bo‘lishi mumkin.'}</p>
            <div className="ns-form-grid">
              <Input id="smtp-host" label="SMTP server" disabled={values.smtp_source === 'ENV'} required={values.smtp_source === 'ADMIN'} value={values.smtp_host} onChange={e => patch({ smtp_host: e.target.value })} />
              <Input id="smtp-port" label="Port" type="number" min={1} max={65535} disabled={values.smtp_source === 'ENV'} value={values.smtp_port} onChange={e => patch({ smtp_port: Number(e.target.value) })} />
              <Input id="smtp-username" label="SMTP login" disabled={values.smtp_source === 'ENV'} value={values.smtp_username} onChange={e => patch({ smtp_username: e.target.value })} />
              <Input id="smtp-password" label="SMTP parol" type="password" autoComplete="new-password" disabled={values.smtp_source === 'ENV'} value={password} onChange={e => { setPassword(e.target.value); setDirty(true); setMessage(''); }} hint={values.smtp_password_set ? 'Parol saqlangan. Bo‘sh qoldirsangiz, mavjud parol saqlanadi.' : 'Email provayderining SMTP yoki ilova paroli.'} />
              <Select id="smtp-security" label="Ulanish himoyasi" disabled={values.smtp_source === 'ENV'} value={values.smtp_security} onChange={e => patch({ smtp_security: e.target.value as PlatformSettings['smtp_security'] })}>
                <option value="TLS">STARTTLS (odatda 587)</option><option value="SSL">SSL/TLS (odatda 465)</option><option value="NONE">Himoyasiz (mahalliy test)</option>
              </Select>
              <Input id="smtp-from" label="Xat yuboruvchi email" type="email" disabled={values.smtp_source === 'ENV'} value={values.smtp_from_email} onChange={e => patch({ smtp_from_email: e.target.value })} />
            </div>
          </Card>
          <div className="ns-profile-actions"><Button type="submit" disabled={!dirty} loading={busy}>Sozlamalarni saqlash</Button>{dirty ? <span>Saqlanmagan o‘zgarishlar bor</span> : null}</div>
        </fieldset>
      </form>
      <form className="ns-settings" onSubmit={testEmail}><Card><h2>Emailni tekshirish</h2><p>Saqlangan sozlamalar bilan test xati yuboring.</p>
        <Input id="test-email" label="Test xati qaysi emailga yuborilsin?" type="email" required value={testRecipient} onChange={e => setTestRecipient(e.target.value)} />
        <Button type="submit" variant="secondary" loading={testing} disabled={dirty || busy}>Test xatini yuborish</Button>
        {dirty ? <p>Test qilishdan oldin o‘zgarishlarni saqlang.</p> : null}
      </Card></form>
    </>}
  </AdminShell>;
}
