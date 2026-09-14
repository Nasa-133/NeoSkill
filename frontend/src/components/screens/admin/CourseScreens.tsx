'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { readApiError } from '@/lib/api';
import { categoryStore, courseStore, instructorStore, slugify } from '@/lib/admin-data';
import type { AdminCategory, AdminCourse, AdminInstructor } from '@/lib/types';
import { AdminShell } from '@/components/layout/Shells';
import { AdminTable, RowActions } from '@/components/domain/Admin';
import { Button, Checkbox, ConfirmDialog, ImagePicker, Input, PageHeader, Select, StatusBadge, Textarea } from '@/components/ui';
import { CurriculumEditor } from './CurriculumEditor';

const levels = [['BEGINNER', 'Boshlang‘ich'], ['INTERMEDIATE', 'O‘rta'], ['ADVANCED', 'Yuqori']] as const;
const statuses = [['DRAFT', 'Qoralama'], ['PUBLISHED', 'Nashr qilingan'], ['ARCHIVED', 'Arxivlangan']] as const;

function emptyCourse(): Omit<AdminCourse, 'id'> {
  return {
    category: null, instructor: null, title: '', slug: '', short_description: '', description: '',
    image_url: '', level: 'BEGINNER', language: 'O‘zbek', duration_minutes: 60,
    is_free: true, price: null, status: 'DRAFT', sequential_learning: true,
    what_you_will_learn: [], audience: [], requirements: [], telegram_group_url: '', support_url: '',
  };
}

/** Normalising on every keystroke would eat trailing spaces and blank lines, so the
 *  textareas keep their raw text and only split into items when the course is saved. */
function lines(value: string) { return value.split('\n').map(item => item.trim()).filter(Boolean); }
type ListText = { outcomes: string; audience: string; requirements: string };
const emptyListText: ListText = { outcomes: '', audience: '', requirements: '' };

/* --------------------------------- list ---------------------------------- */

export function AdminCourses() {
  const [items, setItems] = useState<AdminCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [removing, setRemoving] = useState<AdminCourse | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    courseStore.list()
      .then(value => { if (live) setItems(value); })
      .catch(reason => { if (live) setError(readApiError(reason, 'Kurslarni yuklab bo‘lmadi.')); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  const shown = items.filter(item => (!search || item.title.toLowerCase().includes(search.toLowerCase())) && (!status || item.status === status));

  async function remove(course: AdminCourse) {
    setBusy(true); setError('');
    try { await courseStore.remove(course.id); setItems(await courseStore.list()); setRemoving(null); }
    catch (reason) { setError(readApiError(reason, 'Kursni o‘chirib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  return <AdminShell>
    <PageHeader eyebrow="Kontent" title="Kurslar" description="Kurs ma’lumotlari, narxi, holati va o‘quv dasturini boshqaring." actions={<Link className="ns-link-button" href="/admin/courses/new">+ Yangi kurs</Link>} />
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    <div className="ns-admin-filters">
      <Input id="admin-course-search" label="Qidirish" placeholder="Kurs nomi" value={search} onChange={event => setSearch(event.target.value)} />
      <Select id="admin-course-status" label="Holat" value={status} onChange={event => setStatus(event.target.value)}>
        <option value="">Barchasi</option>
        {statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </Select>
    </div>
    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : items.length === 0 ? <div className="ns-editor-empty"><h2>Hali kurs yo‘q</h2><p>Birinchi kursni yarating, so‘ng unga modul, dars va video qo‘shasiz.</p><Link className="ns-link-button" href="/admin/courses/new">+ Yangi kurs</Link></div>
      : <AdminTable columns={['Kurs', 'Daraja', 'Turi', 'Holat', 'Narx', 'Amallar']} caption="Kurslar ro‘yxati">
          {shown.map(item => <tr key={item.id}>
            <td><strong>{item.title}</strong><small>/{item.slug}</small></td>
            <td>{levels.find(([value]) => value === item.level)?.[1]}</td>
            <td>{item.is_free ? 'Bepul' : 'Pullik'}</td>
            <td><StatusBadge status={item.status} /></td>
            <td>{item.is_free ? '—' : `${Number(item.price ?? 0).toLocaleString('uz-UZ')} so‘m`}</td>
            <td><RowActions>
              {item.status === 'PUBLISHED' ? <Link href={`/courses/${item.slug}`}>Ko‘rish</Link> : null}
              <Link href={`/admin/courses/${item.id}/edit`}>Tahrirlash</Link>
              <button type="button" onClick={() => setRemoving(item)}>O‘chirish</button>
            </RowActions></td>
          </tr>)}
        </AdminTable>}
    <ConfirmDialog open={removing !== null} title="Kursni o‘chirasizmi?" description={removing ? `«${removing.title}» kursi, uning modullari, darslari va testlari o‘chiriladi.` : ''} confirmLabel="O‘chirish" danger busy={busy} onClose={() => setRemoving(null)} onConfirm={() => { if (removing) void remove(removing); }} />
  </AdminShell>;
}

/* -------------------------------- editor ---------------------------------- */

export function CourseEditor({ id }: { id?: string | undefined }) {
  const router = useRouter();
  const [draft, setDraft] = useState<Omit<AdminCourse, 'id'> | null>(id ? null : emptyCourse());
  const [listText, setListText] = useState<ListText>(emptyListText);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [instructors, setInstructors] = useState<AdminInstructor[]>([]);
  const [tab, setTab] = useState('basic');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    void Promise.all([categoryStore.list(), instructorStore.list()])
      .then(([nextCategories, nextInstructors]) => { if (live) { setCategories(nextCategories); setInstructors(nextInstructors); } })
      .catch(() => { /* the form still works; the selects stay empty */ });
    return () => { live = false; };
  }, []);

  useEffect(() => {
    if (!id) return;
    let live = true;
    courseStore.get(id)
      .then(value => {
        if (!live) return;
        setDraft({ ...value });
        setListText({
          outcomes: value.what_you_will_learn.join('\n'),
          audience: value.audience.join('\n'),
          requirements: value.requirements.join('\n'),
        });
      })
      .catch(reason => { if (live) setError(readApiError(reason, 'Kursni yuklab bo‘lmadi.')); });
    return () => { live = false; };
  }, [id]);

  const patch = useCallback((values: Partial<Omit<AdminCourse, 'id'>>) => { setDraft(current => current ? { ...current, ...values } : current); setSaved(false); }, []);

  async function save() {
    if (!draft) return;
    setSaving(true); setError(''); setSaved(false);
    const payload = {
      ...draft,
      price: draft.is_free ? null : draft.price,
      what_you_will_learn: lines(listText.outcomes),
      audience: lines(listText.audience),
      requirements: lines(listText.requirements),
    };
    try {
      if (id) { await courseStore.update(id, payload); setSaved(true); }
      else { const created = await courseStore.create(payload); router.replace(`/admin/courses/${created.id}/edit`); }
    } catch (reason) { setError(readApiError(reason, 'Kursni saqlab bo‘lmadi.')); }
    finally { setSaving(false); }
  }

  if (!draft) return <AdminShell><PageHeader eyebrow="Kurs muharriri" title="Kursni tahrirlash" />{error ? <p className="ns-field__error" role="alert">{error}</p> : <p className="ns-muted">Yuklanmoqda…</p>}</AdminShell>;

  const tabs = [['basic', 'Asosiy'], ['metadata', 'Metadata'], ['commercial', 'Narx'], ['landing', 'Landing'], ['curriculum', 'O‘quv dasturi'], ['publish', 'Nashr']] as const;
  const counts = { outcomes: lines(listText.outcomes).length, audience: lines(listText.audience).length, requirements: lines(listText.requirements).length };
  const readyToPublish = counts.outcomes >= 3 && counts.audience >= 3 && counts.requirements >= 1;

  return <AdminShell>
    <div>
      <PageHeader
        eyebrow="Kurs muharriri"
        title={id ? draft.title || 'Kursni tahrirlash' : 'Yangi kurs yaratish'}
        description={id ? 'O‘zgarishlar serverga saqlanadi.' : 'Kursni saqlaganingizdan keyin o‘quv dasturi bo‘limi ochiladi.'}
        actions={<><Link className="ns-link-button ns-link-button--secondary" href="/admin/courses">Bekor qilish</Link><Button onClick={save} loading={saving}>Saqlash</Button></>}
      />
      <div className="ns-editor">
        <nav className="ns-editor-tabs" aria-label="Kurs bo‘limlari">
          {tabs.map(([value, label]) => <button type="button" key={value} data-active={tab === value || undefined} onClick={() => setTab(value)}>{label}</button>)}
        </nav>
        <section className="ns-editor-panel">
          {error ? <p className="ns-field__error" role="alert">{error}</p> : null}

          {tab === 'basic' ? <>
            <h2>Asosiy ma’lumotlar</h2>
            <div className="ns-form-grid">
              <Input id="course-title" label="Kurs nomi" required requiredMark value={draft.title} onChange={event => patch({ title: event.target.value, ...(id ? {} : { slug: slugify(event.target.value) }) })} />
              <Input id="course-slug" label="Slug" required requiredMark value={draft.slug} hint="Manzil: /courses/<slug>" onChange={event => patch({ slug: event.target.value })} />
            </div>
            <Textarea id="course-summary" label="Qisqa tavsif" rows={3} required value={draft.short_description} onChange={event => patch({ short_description: event.target.value })} />
            <Textarea id="course-description" label="To‘liq tavsif" rows={6} value={draft.description} onChange={event => patch({ description: event.target.value })} />
            <ImagePicker label="Kurs muqovasi" recommended="1200×675" aspect="16 / 9" value={draft.image_url} onChange={url => patch({ image_url: url })} />
          </> : null}

          {tab === 'metadata' ? <>
            <h2>Metadata</h2>
            <div className="ns-form-grid">
              <Select id="course-category" label="Kategoriya" value={draft.category ?? ''} hint={categories.length ? undefined : 'Avval Kategoriyalar bo‘limida kategoriya qo‘shing.'} onChange={event => patch({ category: event.target.value || null })}>
                <option value="">Tanlanmagan</option>
                {categories.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
              </Select>
              <Select id="course-instructor" label="Ustoz" value={draft.instructor ?? ''} hint={instructors.length ? undefined : 'Avval Ustozlar bo‘limida ustoz qo‘shing.'} onChange={event => patch({ instructor: event.target.value || null })}>
                <option value="">Tanlanmagan</option>
                {instructors.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
              </Select>
              <Select id="course-level" label="Daraja" value={draft.level} onChange={event => patch({ level: event.target.value as AdminCourse['level'] })}>
                {levels.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </Select>
              <Input id="course-language" label="Til" value={draft.language} onChange={event => patch({ language: event.target.value })} />
              <Input id="course-duration" label="Davomiyligi (daqiqa)" type="number" min="1" value={draft.duration_minutes} onChange={event => patch({ duration_minutes: Number(event.target.value) || 0 })} />
              <Input id="support-url" label="Telegram/support URL" type="url" placeholder="https://t.me/..." value={draft.support_url} onChange={event => patch({ support_url: event.target.value })} />
            </div>
            <Checkbox id="sequential" label="Mavzular ketma-ket ochilsin (test topshirmaguncha keyingisi yopiq)" checked={draft.sequential_learning} onChange={event => patch({ sequential_learning: event.target.checked })} />
          </> : null}

          {tab === 'commercial' ? <>
            <h2>Kurs turi va narxi</h2>
            <Checkbox id="is-free" label="Bu kurs bepul" checked={draft.is_free} onChange={event => patch({ is_free: event.target.checked, price: event.target.checked ? null : (draft.price ?? '490000') })} />
            <Input id="course-price" label="Narx (so‘m)" type="number" min="1" disabled={draft.is_free} value={draft.price ?? ''} hint={draft.is_free ? 'Bepul kurs darhol ACTIVE enrollment beradi.' : 'Pullik kurs ariza va admin tasdig‘ini talab qiladi.'} onChange={event => patch({ price: event.target.value })} />
          </> : null}

          {tab === 'landing' ? <>
            <h2>Landing kontenti</h2>
            <Textarea id="outcomes" label="Nimalarni o‘rganadi? (har qatorda bittadan, 3–10 ta)" rows={6} value={listText.outcomes} onChange={event => { setListText({ ...listText, outcomes: event.target.value }); setSaved(false); }} hint={`Hozir ${counts.outcomes} ta`} />
            <Textarea id="audience" label="Kimlar uchun? (har qatorda bittadan, 3–8 ta)" rows={5} value={listText.audience} onChange={event => { setListText({ ...listText, audience: event.target.value }); setSaved(false); }} hint={`Hozir ${counts.audience} ta`} />
            <Textarea id="requirements" label="Talablar (har qatorda bittadan, kamida 1 ta)" rows={4} value={listText.requirements} onChange={event => { setListText({ ...listText, requirements: event.target.value }); setSaved(false); }} hint={`Hozir ${counts.requirements} ta`} />
          </> : null}

          {tab === 'curriculum' ? <CurriculumEditor courseId={id} /> : null}

          {tab === 'publish' ? <>
            <h2>Nashr holati</h2>
            <Select id="publish-status" label="Holat" value={draft.status} onChange={event => patch({ status: event.target.value as AdminCourse['status'] })}>
              {statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </Select>
            <div className="ns-publish-check">
              <strong>Nashr uchun server talablari</strong>
              <ul>
                <li>{counts.outcomes >= 3 && counts.outcomes <= 10 ? '✓' : '✗'} «Nimalarni o‘rganadi» — 3 tadan 10 tagacha ({counts.outcomes})</li>
                <li>{counts.audience >= 3 && counts.audience <= 8 ? '✓' : '✗'} «Kimlar uchun» — 3 tadan 8 tagacha ({counts.audience})</li>
                <li>{counts.requirements >= 1 ? '✓' : '✗'} Kamida bitta talab ({counts.requirements})</li>
                <li>{draft.is_free || Number(draft.price ?? 0) > 0 ? '✓' : '✗'} Pullik kursda narx noldan katta</li>
              </ul>
              {!readyToPublish ? <p className="ns-muted">Bu shartlar bajarilmasa server «Nashr qilingan» holatni rad etadi.</p> : null}
            </div>
          </> : null}

          {saved ? <p className="ns-save-message" role="status">✓ O‘zgarishlar saqlandi</p> : null}
        </section>
      </div>
    </div>
  </AdminShell>;
}
