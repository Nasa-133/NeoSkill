'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { AdminTable } from '@/components/domain/Admin';
import { AdminShell } from '@/components/layout/Shells';
import { Badge, Button, Input, PageHeader } from '@/components/ui';
import { api, readApiError } from '@/lib/api';
import type { AdminReferralDetail, ReferralSummary } from '@/lib/types';

export function ReferralScreen() {
  const [items, setItems] = useState<ReferralSummary[]>([]);
  const [selected, setSelected] = useState<AdminReferralDetail | null>(null);
  const [search, setSearch] = useState('');
  const [discount, setDiscount] = useState('0');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setError('');
    try { setItems(await api.adminReferrals()); }
    catch (reason) { setError(readApiError(reason, 'Referral hisobotini yuklab bo‘lmadi.')); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const shown = useMemo(() => {
    const query = search.trim().toLowerCase();
    return query ? items.filter(item => `${item.full_name} ${item.email} ${item.referral_code}`.toLowerCase().includes(query)) : items;
  }, [items, search]);

  async function open(item: ReferralSummary) {
    setError(''); setNotice(''); setBusy(true);
    try {
      const detail = await api.adminReferral(item.user_id);
      setSelected(detail); setDiscount(String(detail.discount_percent));
    } catch (reason) { setError(readApiError(reason, 'Referral tafsilotini yuklab bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  async function saveDiscount(event: React.FormEvent) {
    event.preventDefault();
    if (!selected) return;
    const value = Number(discount);
    setBusy(true); setError(''); setNotice('');
    try {
      await api.adminReferralDiscount(selected.user_id, value);
      const detail = await api.adminReferral(selected.user_id);
      setSelected(detail); setDiscount(String(detail.discount_percent));
      await load(); setNotice('Chegirma saqlandi. U keyingi yangi referral hisoblariga qo‘llanadi.');
    } catch (reason) { setError(readApiError(reason, 'Chegirmani saqlab bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  return <AdminShell>
    <PageHeader eyebrow="Referral" title="Takliflar va chegirmalar" description="Har bir foydalanuvchining taklif havolasi, kelgan odamlar va ularning kurs ruxsatlarini kuzating." />
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    {notice ? <p className="ns-save-message" role="status">✓ {notice}</p> : null}
    <div className="ns-admin-filters ns-admin-filters--single"><Input id="referral-search" type="search" label="Qidirish" placeholder="Ism, email yoki kod" value={search} onChange={event => setSearch(event.target.value)} /></div>
    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : shown.length === 0 ? <div className="ns-editor-empty"><h2>Natija topilmadi</h2><p>Qidiruvni o‘zgartirib ko‘ring.</p></div>
      : <AdminTable className="ns-statistics-table" columns={['Foydalanuvchi', 'Kod', 'Chegirma', 'Takliflar', 'Ruxsat olgan', 'Bepul', 'Pullik', 'Amal']} caption="Referral statistikasi">
          {shown.map(item => <tr key={item.user_id}>
            <td data-label="Foydalanuvchi"><strong>{item.full_name || '—'}</strong><small>{item.email}</small></td>
            <td data-label="Kod"><code>{item.referral_code}</code></td>
            <td data-label="Chegirma">{item.discount_percent}%</td>
            <td data-label="Takliflar">{item.referred_count}</td>
            <td data-label="Ruxsat olgan">{item.referred_with_access}</td>
            <td data-label="Bepul">{item.free_access_count}</td>
            <td data-label="Pullik">{item.paid_access_count}</td>
            <td data-label="Amal"><Button size="sm" variant="secondary" loading={busy && !selected} onClick={() => void open(item)}>Batafsil</Button></td>
          </tr>)}
        </AdminTable>}

    {selected ? <aside className="ns-detail-drawer ns-referral-drawer">
      <header><div><small>REFERRAL TAFSILOTI</small><h2>{selected.full_name || selected.email}</h2></div><button type="button" onClick={() => setSelected(null)} aria-label="Yopish">×</button></header>
      <dl>
        <div><dt>Taklif kodi</dt><dd><code>{selected.referral_code}</code></dd></div>
        <div><dt>Taklif bilan kirgan</dt><dd>{selected.referred_count}</dd></div>
        <div><dt>Kursga ruxsat olgan</dt><dd>{selected.referred_with_access}</dd></div>
        <div><dt>Kurs ruxsatlari</dt><dd>{selected.free_access_count} bepul · {selected.paid_access_count} pullik</dd></div>
      </dl>
      <form className="ns-referral-discount" onSubmit={saveDiscount}>
        <Input id="referral-discount" label="Yangi referral uchun chegirma (%)" type="number" min="0" max="100" required value={discount} hint="O‘zgarish faqat keyin ro‘yxatdan o‘tadigan hisoblar uchun snapshot qilinadi." onChange={event => setDiscount(event.target.value)} />
        <Button type="submit" loading={busy} disabled={!Number.isInteger(Number(discount)) || Number(discount) < 0 || Number(discount) > 100}>Chegirmani saqlash</Button>
      </form>
      <section className="ns-referral-people"><h3>Taklif orqali kelganlar</h3>
        {selected.referred_users.length === 0 ? <p className="ns-muted">Hali hech kim ro‘yxatdan o‘tmagan.</p> : <ul>
          {selected.referred_users.map(user => <li key={user.id}><div><strong>{user.full_name || '—'}</strong><small>{user.email} · {new Date(user.joined_at).toLocaleDateString('uz-UZ')} · {user.discount_percent}%</small></div>
            {user.course_access.length ? <ul>{user.course_access.map(access => <li key={access.id}><span>{access.course_title}</span><Badge tone={access.access_type === 'FREE' ? 'success' : 'brand'}>{access.access_type === 'FREE' ? 'Bepul' : 'Pullik kurs'}</Badge></li>)}</ul> : <small className="ns-muted">Kursga ruxsat olmagan</small>}
          </li>)}
        </ul>}
      </section>
    </aside> : null}
  </AdminShell>;
}
