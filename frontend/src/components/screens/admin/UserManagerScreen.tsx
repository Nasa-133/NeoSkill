'use client';

import { useCallback, useEffect, useState } from 'react';

import { api, readApiError } from '@/lib/api';
import { courseStore } from '@/lib/admin-data';
import type { AdminAccount, AdminCourse, AdminCourseAccess } from '@/lib/types';
import { AdminShell } from '@/components/layout/Shells';
import { AdminTable, RowActions } from '@/components/domain/Admin';
import { Badge, Button, Checkbox, ConfirmDialog, Input, PageHeader, Select } from '@/components/ui';

type Draft = { id?: string; email: string; first_name: string; last_name: string; role: 'STUDENT' | 'ADMIN'; is_active: boolean; password: string };
const emptyDraft: Draft = { email: '', first_name: '', last_name: '', role: 'STUDENT', is_active: true, password: '' };


export function UserManagerScreen() {
  const [accounts, setAccounts] = useState<AdminAccount[]>([]);
  const [courses, setCourses] = useState<AdminCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const [draft, setDraft] = useState<Draft | null>(null);
  const [selected, setSelected] = useState<AdminAccount | null>(null);
  const [access, setAccess] = useState<AdminCourseAccess[]>([]);
  const [passwordFor, setPasswordFor] = useState<AdminAccount | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [removing, setRemoving] = useState<AdminAccount | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const reload = useCallback(async () => setAccounts(await api.adminAccounts()), []);

  useEffect(() => {
    let live = true;
    void Promise.all([api.adminAccounts(), courseStore.list()])
      .then(([nextAccounts, nextCourses]) => { if (live) { setAccounts(nextAccounts); setCourses(nextCourses); } })
      .catch(reason => { if (live) setError(readApiError(reason, 'Foydalanuvchilarni yuklab bo‘lmadi.')); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  useEffect(() => {
    if (!selected) { setAccess([]); return; }
    let live = true;
    api.adminAccountCourses(selected.id)
      .then(value => { if (live) setAccess(value); })
      .catch(() => { if (live) setAccess([]); });
    return () => { live = false; };
  }, [selected]);

  async function run(operation: () => Promise<unknown>, message = '') {
    setBusy(true); setError(''); setNotice('');
    try { await operation(); await reload(); if (message) setNotice(message); }
    catch (reason) { setError(readApiError(reason, 'Amalni bajarib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  const shown = accounts.filter(item =>
    (!role || item.role === role) &&
    (!search || `${item.email} ${item.full_name}`.toLowerCase().includes(search.toLowerCase())));

  async function saveDraft(event: React.FormEvent) {
    event.preventDefault();
    if (!draft) return;
    const base = { email: draft.email.trim(), first_name: draft.first_name.trim(), last_name: draft.last_name.trim(), role: draft.role, is_active: draft.is_active };
    await run(async () => {
      if (draft.id) await api.adminUpdate('users', draft.id, base);
      else await api.adminCreate('users', { ...base, password: draft.password });
      setDraft(null);
    }, draft.id ? 'Foydalanuvchi yangilandi.' : 'Foydalanuvchi yaratildi.');
  }

  async function grant(courseId: string) {
    if (!selected) return;
    await run(async () => { await api.adminGrantCourse(selected.id, courseId); setAccess(await api.adminAccountCourses(selected.id)); }, 'Kursga ruxsat berildi.');
  }

  async function revoke(courseId: string) {
    if (!selected) return;
    await run(async () => { await api.adminRevokeCourse(selected.id, courseId); setAccess(await api.adminAccountCourses(selected.id)); }, 'Ruxsat olib tashlandi.');
  }

  const grantedIds = new Set(access.map(item => item.course_id));
  const grantable = courses.filter(item => !grantedIds.has(item.id));

  return <AdminShell>
    <PageHeader
      eyebrow="Foydalanuvchilar"
      title="Hisoblar va ruxsatlar"
      description="Foydalanuvchi yarating, rolini o‘zgartiring, parolini almashtiring va kurslarga ruxsat bering."
      actions={<Button onClick={() => { setDraft({ ...emptyDraft }); setNotice(''); }}>+ Foydalanuvchi qo‘shish</Button>}
    />

    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    {notice ? <p className="ns-save-message" role="status">✓ {notice}</p> : null}

    <div className="ns-admin-filters">
      <Input id="user-search" label="Qidirish" placeholder="Email yoki ism" value={search} onChange={event => setSearch(event.target.value)} />
      <Select id="user-role" label="Rol" value={role} onChange={event => setRole(event.target.value)}>
        <option value="">Barchasi</option>
        <option value="STUDENT">Talaba</option>
        <option value="ADMIN">Administrator</option>
      </Select>
    </div>

    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : accounts.length === 0 ? <div className="ns-editor-empty"><h2>Hisob yo‘q</h2><p>Birinchi foydalanuvchini qo‘shing yoki odamlar o‘zlari ro‘yxatdan o‘tsin.</p></div>
      : <div className="ns-users-layout">
          <AdminTable columns={['Foydalanuvchi', 'Rol', 'Holat', 'Ro‘yxatdan o‘tgan', 'Amallar']} caption="Foydalanuvchilar">
            {shown.map(item => <tr key={item.id}>
              <td><strong>{item.full_name || '—'}</strong><small>{item.email}</small></td>
              <td><Badge tone={item.role === 'ADMIN' ? 'brand' : 'neutral'}>{item.role === 'ADMIN' ? 'Administrator' : 'Talaba'}</Badge></td>
              <td><Badge tone={item.is_active ? 'success' : 'danger'}>{item.is_active ? 'Faol' : 'Bloklangan'}</Badge></td>
              <td>{new Date(item.date_joined).toLocaleDateString('uz-UZ')}</td>
              <td><RowActions>
                <button type="button" onClick={() => { setSelected(item); setNotice(''); }}>Ruxsatlar</button>
                <button type="button" onClick={() => setDraft({ id: item.id, email: item.email, first_name: item.first_name, last_name: item.last_name, role: item.role, is_active: item.is_active, password: '' })}>Tahrirlash</button>
                <button type="button" onClick={() => { setPasswordFor(item); setNewPassword(''); }}>Parol</button>
                <button type="button" onClick={() => setRemoving(item)}>O‘chirish</button>
              </RowActions></td>
            </tr>)}
          </AdminTable>

          {selected ? <div className="ns-user-detail">
            <header className="ns-card-header">
              <div><h2>{selected.full_name || selected.email}</h2><p>{selected.email}</p></div>
              <button type="button" className="ns-table-link" onClick={() => setSelected(null)}>Yopish</button>
            </header>
            <h3>Kurslarga ruxsat</h3>
            {access.length === 0 ? <p className="ns-muted">Hech qanday kursga ruxsat berilmagan.</p>
              : <ul className="ns-access-list">
                  {access.map(item => <li key={item.id}>
                    <span>{item.course_title}</span>
                    <button type="button" className="ns-table-link" disabled={busy} onClick={() => void revoke(item.course_id)}>Olib tashlash</button>
                  </li>)}
                </ul>}
            {grantable.length ? <Select id="grant-course" label="Kurs qo‘shish" value="" disabled={busy} onChange={event => { if (event.target.value) void grant(event.target.value); }}>
              <option value="">Kursni tanlang…</option>
              {grantable.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
            </Select> : <p className="ns-muted">Barcha kurslarga ruxsat berilgan.</p>}
          </div> : null}
        </div>}

    {draft ? <div className="ns-inline-form" role="dialog" aria-modal="true" aria-label="Foydalanuvchi">
      <header><h2>{draft.id ? 'Foydalanuvchini tahrirlash' : 'Yangi foydalanuvchi'}</h2><button type="button" onClick={() => setDraft(null)} aria-label="Yopish">×</button></header>
      <form onSubmit={saveDraft}>
        <div className="ns-form-grid">
          <Input id="draft-first" label="Ism" value={draft.first_name} onChange={event => setDraft({ ...draft, first_name: event.target.value })} />
          <Input id="draft-last" label="Familiya" value={draft.last_name} onChange={event => setDraft({ ...draft, last_name: event.target.value })} />
        </div>
        <Input id="draft-email" label="Email" type="email" required requiredMark value={draft.email} onChange={event => setDraft({ ...draft, email: event.target.value })} />
        {draft.id ? null : <Input id="draft-password" label="Boshlang‘ich parol" type="password" required requiredMark minLength={8} value={draft.password} hint="Kamida 8 belgi. Foydalanuvchiga alohida yetkazing." onChange={event => setDraft({ ...draft, password: event.target.value })} />}
        <Select id="draft-role" label="Rol" value={draft.role} onChange={event => setDraft({ ...draft, role: event.target.value === 'ADMIN' ? 'ADMIN' : 'STUDENT' })}>
          <option value="STUDENT">Talaba</option>
          <option value="ADMIN">Administrator — butun admin panelga kirish</option>
        </Select>
        <Checkbox id="draft-active" label="Hisob faol (bloklanmagan)" checked={draft.is_active} onChange={event => setDraft({ ...draft, is_active: event.target.checked })} />
        <div className="ns-dialog-actions">
          <Button type="button" variant="secondary" onClick={() => setDraft(null)}>Bekor qilish</Button>
          <Button type="submit" loading={busy} disabled={!draft.email.trim() || (!draft.id && draft.password.length < 8)}>Saqlash</Button>
        </div>
      </form>
    </div> : null}

    {passwordFor ? <div className="ns-inline-form" role="dialog" aria-modal="true" aria-label="Parolni o‘zgartirish">
      <header><h2>Parolni o‘zgartirish</h2><button type="button" onClick={() => setPasswordFor(null)} aria-label="Yopish">×</button></header>
      <form onSubmit={event => { event.preventDefault(); const target = passwordFor; void run(async () => { await api.adminAccountPassword(target.id, newPassword); setPasswordFor(null); }, 'Parol yangilandi.'); }}>
        <p className="ns-muted">{passwordFor.full_name || passwordFor.email} uchun yangi parol. Foydalanuvchiga o‘zingiz yetkazasiz — email yuborilmaydi.</p>
        <Input id="admin-new-password" label="Yangi parol" type="password" required requiredMark minLength={8} value={newPassword} onChange={event => setNewPassword(event.target.value)} />
        <div className="ns-dialog-actions">
          <Button type="button" variant="secondary" onClick={() => setPasswordFor(null)}>Bekor qilish</Button>
          <Button type="submit" loading={busy} disabled={newPassword.length < 8}>Saqlash</Button>
        </div>
      </form>
    </div> : null}

    <ConfirmDialog
      open={removing !== null}
      title="Foydalanuvchini o‘chirasizmi?"
      description={removing ? `${removing.email} hisobi, uning enrollmentlari va progressi butunlay o‘chiriladi.` : ''}
      confirmLabel="O‘chirish"
      danger
      busy={busy}
      onClose={() => setRemoving(null)}
      onConfirm={() => { const target = removing; setRemoving(null); if (target) void run(() => api.adminDelete('users', target.id), 'Foydalanuvchi o‘chirildi.'); }}
    />
  </AdminShell>;
}
