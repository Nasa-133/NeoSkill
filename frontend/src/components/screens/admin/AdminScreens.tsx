'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

import { api, readApiError } from '@/lib/api';
import type { AdminEnrollmentRequest, AdminStats, EnrollmentRequestStatus } from '@/lib/types';
import { AdminShell } from '@/components/layout/Shells';
import { AdminTable, KpiCard } from '@/components/domain/Admin';
import { Button, Card, ConfirmDialog, PageHeader, ProgressBar, StatusBadge } from '@/components/ui';

export { SimpleManager, TestimonialsManager } from './ContentManagers';
export { AdminCourses, CourseEditor } from './CourseScreens';
export { UserManagerScreen } from './UserManagerScreen';
export { TestBuilderScreen } from './TestBuilderScreen';


/* ------------------------------- dashboard -------------------------------- */

export function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [pending, setPending] = useState<AdminEnrollmentRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    void Promise.all([api.adminStats(), api.adminEnrollmentRequests('PENDING')])
      .then(([nextStats, nextPending]) => { if (live) { setStats(nextStats); setPending(nextPending); } })
      .catch(reason => { if (live) setError(readApiError(reason, 'Ko‘rsatkichlarni yuklab bo‘lmadi.')); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  const attempts = (stats?.passed_attempts ?? 0) + (stats?.failed_attempts ?? 0);

  return <AdminShell>
    <PageHeader eyebrow="Umumiy ko‘rinish" title="Boshqaruv paneli" description="Platformaning asosiy ko‘rsatkichlari va yangi arizalar." />
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    {loading || !stats ? <p className="ns-muted">Yuklanmoqda…</p> : <>
      <div className="ns-kpi-grid">
        <KpiCard label="Foydalanuvchilar" value={stats.total_users} note="Jami hisoblar" mark="♙" href="/admin/users" />
        <KpiCard label="Faol kurs ruxsatlari" value={stats.active_enrollments} note="Bepul va pullik kurslar" mark="✓" href="/admin/statistics?view=enrollments" />
        <KpiCard label="Kurslar" value={stats.total_courses} note={`${stats.free_courses} bepul · ${stats.paid_courses} pullik`} mark="▤" href="/admin/courses" />
        <KpiCard label="Kutilayotgan arizalar" value={stats.pending_requests} note="Ko‘rib chiqish kerak" mark="!" href="/admin/enrollment-requests?status=PENDING" />
      </div>
      <div className="ns-admin-dashboard-grid">
        <Card>
          <header className="ns-card-header">
            <div><h2>Yangi arizalar</h2><p>Eng so‘nggi pullik kurs arizalari</p></div>
            <Link href="/admin/enrollment-requests">Barchasi →</Link>
          </header>
          {pending.length === 0 ? <p className="ns-muted">Kutilayotgan ariza yo‘q.</p>
            : <AdminTable columns={['Talaba', 'Kurs', 'Sana', 'Holat']} caption="Yangi enrollment arizalari">
                {pending.slice(0, 3).map(item => <tr key={item.id}>
                  <td><strong>{item.user_name || '—'}</strong><small>{item.user_email}</small></td>
                  <td>{item.course_title}</td>
                  <td>{new Date(item.requested_at).toLocaleDateString('uz-UZ')}</td>
                  <td><StatusBadge status={item.status} /></td>
                </tr>)}
              </AdminTable>}
        </Card>
        <Card>
          <header className="ns-card-header"><div><h2>Test natijalari</h2><p>Barcha topshirishlar</p></div><Link href="/admin/statistics?view=attempts">Batafsil →</Link></header>
          <div className="ns-test-stats">
            <span><strong>{stats.passed_attempts}</strong><small>Muvaffaqiyatli</small><i data-tone="success" /></span>
            <span><strong>{stats.failed_attempts}</strong><small>Qayta urinish kerak</small><i data-tone="danger" /></span>
          </div>
          <ProgressBar value={attempts ? Math.round(stats.passed_attempts / attempts * 100) : 0} label="Muvaffaqiyat ulushi" />
        </Card>
      </div>
    </>}
  </AdminShell>;
}

/* ----------------------------- enrollment queue --------------------------- */

const queueTabs: { value: EnrollmentRequestStatus; label: string }[] = [
  { value: 'PENDING', label: 'Kutilmoqda' },
  { value: 'APPROVED', label: 'Tasdiqlangan' },
  { value: 'REJECTED', label: 'Rad etilgan' },
];

export function EnrollmentQueue() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const requested = searchParams.get('status');
  const initial = queueTabs.some(item => item.value === requested) ? requested as EnrollmentRequestStatus : 'PENDING';
  const [filter, setFilter] = useState<EnrollmentRequestStatus>(initial);
  const [items, setItems] = useState<AdminEnrollmentRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<AdminEnrollmentRequest | null>(null);
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (status: EnrollmentRequestStatus) => {
    setLoading(true); setError('');
    try { setItems(await api.adminEnrollmentRequests(status)); }
    catch (reason) { setError(readApiError(reason, 'Arizalarni yuklab bo‘lmadi.')); setItems([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(filter); }, [filter, load]);
  useEffect(() => { router.replace(`/admin/enrollment-requests?status=${filter}`, { scroll: false }); }, [filter, router]);

  async function apply() {
    if (!selected || !decision) return;
    setBusy(true); setError('');
    try { await api.adminReviewEnrollment(selected.id, decision); setSelected(null); setDecision(null); await load(filter); }
    catch (reason) { setError(readApiError(reason, 'Qarorni saqlab bo‘lmadi.')); setDecision(null); }
    finally { setBusy(false); }
  }

  return <AdminShell>
    <PageHeader eyebrow="Enrollment" title="Kursga yozilish arizalari" description="Pullik kurslar uchun arizalarni ko‘rib chiqing va yakuniy qaror bering." />
    <div className="ns-segment-buttons">
      {queueTabs.map(tab => <button key={tab.value} type="button" data-active={filter === tab.value || undefined} onClick={() => setFilter(tab.value)}>{tab.label}</button>)}
    </div>
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : items.length === 0 ? <div className="ns-editor-empty"><h2>Ariza yo‘q</h2><p>Bu holatda hech qanday ariza topilmadi.</p></div>
      : <AdminTable columns={['Talaba', 'Kurs', 'Narx', 'Email', 'Sana', 'Holat', 'Amal']} caption="Enrollment arizalari">
          {items.map(item => <tr key={item.id}>
            <td><strong>{item.user_name || '—'}</strong></td>
            <td>{item.course_title}</td>
            <td>{item.requested_price ? `${Number(item.requested_price).toLocaleString('uz-UZ')} so‘m` : '—'}</td>
            <td>{item.user_email}</td>
            <td>{new Date(item.requested_at).toLocaleDateString('uz-UZ')}</td>
            <td><StatusBadge status={item.status} /></td>
            <td><Button size="sm" variant="secondary" onClick={() => setSelected(item)}>Ko‘rish</Button></td>
          </tr>)}
        </AdminTable>}

    {selected ? <aside className="ns-detail-drawer">
      <header><div><small>ARIZA TAFSILOTI</small><h2>{selected.user_name || selected.user_email}</h2></div><button type="button" onClick={() => setSelected(null)} aria-label="Yopish">×</button></header>
      <dl>
        <div><dt>Kurs</dt><dd>{selected.course_title}</dd></div>
        <div><dt>Email</dt><dd>{selected.user_email}</dd></div>
        <div><dt>Yuborilgan</dt><dd>{new Date(selected.requested_at).toLocaleString('uz-UZ')}</dd></div>
        <div><dt>Izoh</dt><dd>{selected.note || 'Izoh qoldirilmagan'}</dd></div>
        <div><dt>Asl narx</dt><dd>{selected.list_price ? `${Number(selected.list_price).toLocaleString('uz-UZ')} so‘m` : '—'}</dd></div>
        <div><dt>Referral chegirma</dt><dd>{selected.referral_discount_percent}%</dd></div>
        <div><dt>Arizadagi narx</dt><dd>{selected.requested_price ? `${Number(selected.requested_price).toLocaleString('uz-UZ')} so‘m` : '—'}</dd></div>
        <div><dt>Holat</dt><dd><StatusBadge status={selected.status} /></dd></div>
      </dl>
      {selected.status === 'PENDING'
        ? <footer><Button variant="danger" onClick={() => setDecision('reject')}>Rad etish</Button><Button onClick={() => setDecision('approve')}>Tasdiqlash</Button></footer>
        : <p className="ns-muted">Bu ariza yakunlangan. Qayta tasdiqlash mumkin emas.</p>}
    </aside> : null}

    <ConfirmDialog
      open={decision !== null}
      title={decision === 'approve' ? 'Arizani tasdiqlaysizmi?' : 'Arizani rad etasizmi?'}
      description={decision === 'approve' ? 'Talabaga faol enrollment beriladi va kurs darhol ochiladi.' : 'Talabaga kurs uchun kirish berilmaydi.'}
      confirmLabel={decision === 'approve' ? 'Tasdiqlash' : 'Rad etish'}
      danger={decision === 'reject'}
      busy={busy}
      onClose={() => setDecision(null)}
      onConfirm={apply}
    />
  </AdminShell>;
}

export { SettingsScreen } from './SettingsScreen';
