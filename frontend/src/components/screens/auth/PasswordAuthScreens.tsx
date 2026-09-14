'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { api, isDeviceLimit, readApiError } from '@/lib/api';
import { deviceId, deviceName, homePathFor, safeNext, useCurrentUser } from '@/lib/session';
import { forgetReferralCode, normalizeReferralCode, storedReferralCode } from '@/lib/referral';
import { AuthShell } from '@/components/layout/Shells';
import { Button, Checkbox, Input, Radio } from '@/components/ui';
import type { DeviceChoice } from '@/lib/types';

export function AuthScreen({ mode = 'login' }: { mode?: 'login' | 'register' }) {
  const router = useRouter();
  const search = useSearchParams();
  const { user, loading: sessionLoading } = useCurrentUser();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [consent, setConsent] = useState(mode === 'login');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [devices, setDevices] = useState<DeviceChoice[]>([]);
  const [release, setRelease] = useState('');
  const [referralCode, setReferralCode] = useState('');
  const [referralHint, setReferralHint] = useState('');

  const next = search.get('next');
  const switchQuery = next ? `?next=${encodeURIComponent(next)}` : '';
  const register = mode === 'register';

  useEffect(() => {
    if (!sessionLoading && user) router.replace(safeNext(next, homePathFor(user)));
  }, [sessionLoading, user, next, router]);

  useEffect(() => {
    if (!register) return;
    const code = storedReferralCode();
    if (!code) return;
    setReferralCode(code);
    let live = true;
    void api.referralOffer(code)
      .then(offer => {
        if (!live) return;
        setReferralHint(offer.discount_percent
          ? `Taklif qabul qilindi: pullik kurs arizalariga ${offer.discount_percent}% chegirma.`
          : 'Taklif kodi qabul qilindi.');
      })
      .catch(() => { if (live) setReferralHint('Taklif kodini tekshirib ko‘ring.'); });
    return () => { live = false; };
  }, [register]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (register && password !== repeat) { setError('Parollar bir xil emas.'); return; }
    if (register && !consent) { setError('Davom etish uchun foydalanish shartlariga rozilik bildiring.'); return; }
    if (devices.length && !release) { setError('Davom etish uchun chiqarib yuboriladigan qurilmani tanlang.'); return; }
    setBusy(true); setError('');
    const device = { device_id: deviceId(), device_name: deviceName() };
    try {
      const result = register
        ? await api.register({ email: email.trim(), password, first_name: firstName.trim(), last_name: lastName.trim(), ...device, ...(referralCode ? { referral_code: normalizeReferralCode(referralCode) } : {}) })
        : await api.login({ email: email.trim(), password, ...device, ...(release ? { revoke_device_session_id: release } : {}) });
      if (register) forgetReferralCode();
      router.push(safeNext(next, result.user.role === 'ADMIN' ? '/admin' : result.first_login ? '/courses' : '/dashboard'));
    } catch (reason) {
      if (isDeviceLimit(reason)) {
        setDevices(reason.body.devices);
        setRelease('');
        setError(reason.body.detail ?? 'Hisobda faol qurilmalar limiti to‘lgan.');
      } else {
        setError(readApiError(reason, register ? 'Ro‘yxatdan o‘tib bo‘lmadi.' : 'Email yoki parol noto‘g‘ri.'));
      }
    } finally { setBusy(false); }
  }

  return <AuthShell
    title={register ? 'NeoSkill’ga qo‘shiling' : 'Xush kelibsiz'}
    description={register ? 'Email va parol bilan hisob yarating.' : 'Email va parolingiz bilan kiring.'}
  >
    <form className="ns-auth-form" onSubmit={submit}>
      {register ? <div className="ns-form-grid">
        <Input id="first-name" label="Ism" autoComplete="given-name" value={firstName} onChange={event => setFirstName(event.target.value)} />
        <Input id="last-name" label="Familiya" autoComplete="family-name" value={lastName} onChange={event => setLastName(event.target.value)} />
      </div> : null}
      {register ? <Input
        id="referral-code"
        label="Taklif kodi (ixtiyoriy)"
        maxLength={12}
        value={referralCode}
        hint={referralHint || 'Taklif havolasi orqali kelgan bo‘lsangiz avtomatik to‘ldiriladi.'}
        onChange={event => { setReferralCode(normalizeReferralCode(event.target.value)); setReferralHint(''); }}
      /> : null}
      <Input id="email" label="Email" type="email" autoComplete="email" placeholder="siz@example.com" required requiredMark value={email} onChange={event => setEmail(event.target.value)} />
      <Input
        id="password"
        label="Parol"
        type="password"
        autoComplete={register ? 'new-password' : 'current-password'}
        required
        requiredMark
        minLength={8}
        value={password}
        onChange={event => setPassword(event.target.value)}
        {...(register ? { hint: 'Kamida 8 belgi, faqat raqamlardan bo‘lmasin.' } : {})}
      />
      {register ? <Input
        id="password-repeat"
        label="Parolni takrorlang"
        type="password"
        autoComplete="new-password"
        required
        requiredMark
        minLength={8}
        value={repeat}
        onChange={event => setRepeat(event.target.value)}
        {...(repeat && password !== repeat ? { error: 'Parollar bir xil emas.' } : {})}
      /> : null}
      {register ? <Checkbox id="policy" checked={consent} onChange={event => setConsent(event.target.checked)} label="Foydalanish shartlari va maxfiylik siyosatiga roziman." /> : null}
      {devices.length ? <fieldset className="ns-device-list">
        <legend>Qaysi qurilmani chiqaramiz?</legend>
        <p>Bitta hisobda ko‘pi bilan 2 ta qurilma bo‘lishi mumkin. Tanlangan qurilma tizimdan chiqariladi.</p>
        {devices.map(item => <Radio
          key={item.id}
          id={`release-${item.id}`}
          name="release-device"
          value={item.id}
          checked={release === item.id}
          onChange={() => { setRelease(item.id); setError(''); }}
          label={`${item.name} · oxirgi faollik ${new Date(item.last_seen_at).toLocaleString('uz-UZ')}`}
        />)}
      </fieldset> : null}
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
      <Button type="submit" loading={busy} size="lg" disabled={register && (password.length < 8 || password !== repeat)}>
        {devices.length ? 'Tanlangan qurilmani chiqarib kirish' : register ? 'Ro‘yxatdan o‘tish' : 'Kirish'}
      </Button>
    </form>
    <p className="ns-auth-switch">
      {register
        ? <>Avval ro‘yxatdan o‘tganmisiz? <Link href={`/login${switchQuery}`}>Kirish</Link></>
        : <>Hisobingiz yo‘qmi? <Link href={`/register${switchQuery}`}>Ro‘yxatdan o‘tish</Link></>}
    </p>
    {register ? null : <p className="ns-auth-recovery"><Link href="/forgot-password">Parolni unutdingizmi?</Link></p>}
  </AuthShell>;
}

export function ForgotPasswordScreen() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError('');
    try { await api.requestPasswordReset(email.trim()); setSent(true); }
    catch (reason) { setError(readApiError(reason, 'So‘rovni yuborib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  if (sent) return <AuthShell title="Xatni tekshiring" description="Parolni tiklash havolasi yuborildi.">
    <div className="ns-recovery">
      <span className="ns-state__icon" aria-hidden="true">✓</span>
      <h2>Havola yuborildi</h2>
      <p className="ns-muted">Agar <strong>{email}</strong> manzilida hisob mavjud bo‘lsa, unga parolni tiklash havolasi keldi. Havola 2 soat amal qiladi.</p>
      <p className="ns-muted">Xat kelmadimi? Spam papkasini tekshiring yoki bir necha daqiqadan keyin qayta urinib ko‘ring.</p>
      <Link className="ns-link-button ns-link-button--secondary" href="/login">Kirish sahifasiga qaytish</Link>
    </div>
  </AuthShell>;

  return <AuthShell title="Parolni tiklash" description="Email manzilingizni kiriting — tiklash havolasini yuboramiz.">
    <form className="ns-auth-form" onSubmit={submit}>
      <Input id="reset-email" label="Email" type="email" autoComplete="email" required requiredMark value={email} onChange={event => setEmail(event.target.value)} />
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
      <Button type="submit" loading={busy} size="lg">Havola yuborish</Button>
    </form>
    <p className="ns-auth-switch">Parolingiz esingizdami? <Link href="/login">Kirish</Link></p>
  </AuthShell>;
}

export function ResetPasswordScreen() {
  const search = useSearchParams();
  const router = useRouter();
  const uid = search.get('uid') ?? '';
  const token = search.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (password !== repeat) { setError('Parollar bir xil emas.'); return; }
    setBusy(true); setError('');
    try { await api.confirmPasswordReset({ uid, token, password }); setDone(true); }
    catch (reason) { setError(readApiError(reason, 'Parolni yangilab bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  if (!uid || !token) return <AuthShell title="Havola yaroqsiz" description="Parolni tiklash havolasi to‘liq emas.">
    <div className="ns-recovery">
      <span className="ns-state__icon" aria-hidden="true">!</span>
      <h2>Havola ochilmadi</h2>
      <p className="ns-muted">Havolani email’dan to‘liq nusxalang yoki yangi havola so‘rang.</p>
      <Link className="ns-link-button" href="/forgot-password">Yangi havola so‘rash</Link>
    </div>
  </AuthShell>;

  if (done) return <AuthShell title="Parol yangilandi" description="Endi yangi parol bilan kirishingiz mumkin.">
    <div className="ns-recovery">
      <span className="ns-state__icon" aria-hidden="true">✓</span>
      <h2>Tayyor</h2>
      <p className="ns-muted">Parolingiz o‘zgartirildi. Barcha qurilmalarda eski havola ishlamaydi.</p>
      <Button size="lg" onClick={() => router.push('/login')}>Kirish sahifasiga o‘tish</Button>
    </div>
  </AuthShell>;

  return <AuthShell title="Yangi parol" description="Hisobingiz uchun yangi parol o‘rnating.">
    <form className="ns-auth-form" onSubmit={submit}>
      <Input id="new-password" label="Yangi parol" type="password" autoComplete="new-password" required requiredMark minLength={8} value={password} onChange={event => setPassword(event.target.value)} hint="Kamida 8 belgi, faqat raqamlardan bo‘lmasin." />
      <Input id="repeat-password" label="Parolni takrorlang" type="password" autoComplete="new-password" required requiredMark minLength={8} value={repeat} onChange={event => setRepeat(event.target.value)} {...(repeat && password !== repeat ? { error: 'Parollar bir xil emas.' } : {})} />
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
      <Button type="submit" loading={busy} size="lg" disabled={password.length < 8 || password !== repeat}>Parolni saqlash</Button>
    </form>
    <p className="ns-auth-switch">Havola eskirdimi? <Link href="/forgot-password">Yangi havola so‘rang</Link></p>
  </AuthShell>;
}
