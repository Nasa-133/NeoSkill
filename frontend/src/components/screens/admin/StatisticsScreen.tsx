'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { api, readApiError } from '@/lib/api';
import type { AdminAttemptStat, AdminEnrollmentStat } from '@/lib/types';
import { AdminShell } from '@/components/layout/Shells';
import { AdminTable } from '@/components/domain/Admin';
import { Badge, EmptyState, ErrorState, Input, PageHeader, Select, StatusBadge } from '@/components/ui';

type View = 'enrollments' | 'attempts';

export function StatisticsScreen() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const view: View = params.get('view') === 'attempts' ? 'attempts' : 'enrollments';
  const [search, setSearch] = useState(params.get('q') ?? '');
  const requestedType = params.get('type');
  const requestedResult = params.get('result');
  const [type, setType] = useState(requestedType === 'FREE' || requestedType === 'PAID' ? requestedType : 'ALL');
  const [result, setResult] = useState(requestedResult === 'PASSED' || requestedResult === 'FAILED' ? requestedResult : 'ALL');
  const [enrollments, setEnrollments] = useState<AdminEnrollmentStat[]>([]);
  const [attempts, setAttempts] = useState<AdminAttemptStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const next = new URLSearchParams({ view });
    if (search) next.set('q', search);
    if (view === 'enrollments' && type !== 'ALL') next.set('type', type);
    if (view === 'attempts' && result !== 'ALL') next.set('result', result);
    const timer = window.setTimeout(() => router.replace(`${pathname}?${next}`, { scroll: false }), 250);
    return () => window.clearTimeout(timer);
  }, [view, search, type, result, pathname, router]);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    const query = new URLSearchParams();
    if (search) query.set('search', search);
    if (view === 'enrollments') query.set('type', type);
    else query.set('result', result);
    try {
      if (view === 'enrollments') setEnrollments(await api.adminEnrollmentStats(`?${query}`));
      else setAttempts(await api.adminAttemptStats(`?${query}`));
    } catch (reason) { setError(readApiError(reason, 'Statistika tafsilotlarini yuklab bo‘lmadi.')); }
    finally { setLoading(false); }
  }, [view, search, type, result]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  return <AdminShell>
    <PageHeader eyebrow="Hisobot" title="Batafsil statistika" description="Kurs ruxsatlari va test natijalarini foydalanuvchi kesimida ko‘ring." />
    <nav className="ns-segment-buttons" aria-label="Statistika turi">
      <Link data-active={view === 'enrollments' || undefined} href="/admin/statistics?view=enrollments">Kurs ruxsatlari</Link>
      <Link data-active={view === 'attempts' || undefined} href="/admin/statistics?view=attempts">Test natijalari</Link>
    </nav>
    <div className="ns-admin-filters">
      <Input id="statistics-search" type="search" label="Qidirish" placeholder="Ism, email, kurs yoki mavzu" value={search} onChange={event => setSearch(event.target.value)} />
      {view === 'enrollments' ? <Select id="statistics-type" label="Kurs turi" value={type} onChange={event => setType(event.target.value)}>
        <option value="ALL">Barcha ruxsatlar</option><option value="FREE">Bepul kurslar</option><option value="PAID">Pullik kurslar</option>
      </Select> : <Select id="statistics-result" label="Natija" value={result} onChange={event => setResult(event.target.value)}>
        <option value="ALL">Barcha natijalar</option><option value="PASSED">O‘tgan</option><option value="FAILED">O‘tmagan</option>
      </Select>}
    </div>
    {error ? <ErrorState description={error} onRetry={load} /> : loading ? <p role="status">Yuklanmoqda…</p>
      : view === 'enrollments' ? enrollments.length ? <>
        <p className="ns-results-head" aria-live="polite"><strong>{enrollments.length} ta kurs ruxsati</strong></p>
        <AdminTable className="ns-statistics-table" columns={['Foydalanuvchi', 'Kurs', 'Turi', 'Holat', 'Berilgan sana']} caption="Kurs ruxsatlari statistikasi">
          {enrollments.map(item => <tr key={item.id}><td data-label="Foydalanuvchi"><strong>{item.user_name || '—'}</strong><small>{item.user_email}</small></td><td data-label="Kurs"><Link href={`/courses/${item.course_slug}`}>{item.course_title}</Link></td><td data-label="Turi"><Badge tone={item.access_type === 'FREE' ? 'success' : 'brand'}>{item.access_type === 'FREE' ? 'Bepul' : 'Pullik kurs'}</Badge></td><td data-label="Holat"><StatusBadge status={item.status} /></td><td data-label="Berilgan sana">{new Date(item.activated_at).toLocaleString('uz-UZ')}</td></tr>)}
        </AdminTable></> : <EmptyState title="Kurs ruxsati topilmadi" description="Filterlarni o‘zgartirib ko‘ring." />
      : attempts.length ? <>
        <p className="ns-results-head" aria-live="polite"><strong>{attempts.length} ta test natijasi</strong></p>
        <AdminTable className="ns-statistics-table" columns={['Foydalanuvchi', 'Kurs va mavzu', 'Ball', 'Natija', 'Sana']} caption="Test natijalari statistikasi">
          {attempts.map(item => <tr key={item.id}><td data-label="Foydalanuvchi"><strong>{item.user_name || '—'}</strong><small>{item.user_email}</small></td><td data-label="Kurs va mavzu"><strong>{item.course_title}</strong><small>{item.topic_title}</small></td><td data-label="Ball">{item.score}%</td><td data-label="Natija"><StatusBadge status={item.result} /></td><td data-label="Sana">{new Date(item.completed_at).toLocaleString('uz-UZ')}</td></tr>)}
        </AdminTable></> : <EmptyState title="Test natijasi topilmadi" description="Filterlarni o‘zgartirib ko‘ring." />}
  </AdminShell>;
}
