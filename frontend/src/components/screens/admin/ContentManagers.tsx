'use client';

import { readApiError } from '@/lib/api';
import { useCallback, useEffect, useState, type ReactNode } from 'react';

import { categoryStore, instructorStore, slugify, testimonialStore, type AdminTestimonial } from '@/lib/admin-data';
import type { AdminCategory, AdminInstructor } from '@/lib/types';
import { AdminShell } from '@/components/layout/Shells';
import { AdminTable, RowActions } from '@/components/domain/Admin';
import { Badge, Button, Card, Checkbox, ConfirmDialog, ImagePicker, Input, PageHeader, Textarea } from '@/components/ui';

/** Load-once list state shared by every flat admin collection screen. */
function useCollection<T>(load: () => Promise<T[]>) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    load()
      .then(value => { if (live) setItems(value); })
      .catch(reason => { if (live) setError(readApiError(reason, 'Ro‘yxatni yuklab bo‘lmadi.')); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [load]);
  return { items, setItems, loading, error, setError };
}

function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return <div className="ns-inline-form" role="dialog" aria-modal="true" aria-label={title}>
    <header><h2>{title}</h2><button type="button" onClick={onClose} aria-label="Yopish">×</button></header>
    {children}
  </div>;
}

export type ManagerKind = 'category' | 'instructor';
export function SimpleManager({ kind }: { kind: ManagerKind }) { return kind === 'category' ? <CategoryManager /> : <InstructorManager />; }

/* ------------------------------- categories ------------------------------- */

const emptyCategory = { name: '', slug: '' };

function CategoryManager() {
  const load = useCallback(() => categoryStore.list(), []);
  const { items, setItems, loading, error, setError } = useCollection<AdminCategory>(load);
  const [draft, setDraft] = useState<{ id?: string; name: string; slug: string } | null>(null);
  const [removing, setRemoving] = useState<AdminCategory | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(operation: () => Promise<AdminCategory[]>) {
    setBusy(true); setError('');
    try { setItems(await operation()); setDraft(null); setRemoving(null); }
    catch (reason) { setError(readApiError(reason, 'Amalni bajarib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  return <AdminShell>
    <PageHeader eyebrow="Kontent" title="Kategoriyalar" description="Kurslarni aniq yo‘nalishlar bo‘yicha guruhlang." actions={<Button onClick={() => setDraft({ ...emptyCategory })}>+ Kategoriya qo‘shish</Button>} />
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : items.length === 0 ? <div className="ns-editor-empty"><h2>Kategoriya yo‘q</h2><p>Birinchi kategoriyani qo‘shing — masalan «Dasturlash».</p></div>
      : <AdminTable columns={['Nomi', 'Slug', 'Amallar']} caption="Kategoriyalar">
          {items.map(item => <tr key={item.id}>
            <td><strong>{item.name}</strong></td>
            <td>/{item.slug}</td>
            <td><RowActions>
              <button type="button" onClick={() => setDraft({ id: item.id, name: item.name, slug: item.slug })}>Tahrirlash</button>
              <button type="button" onClick={() => setRemoving(item)}>O‘chirish</button>
            </RowActions></td>
          </tr>)}
        </AdminTable>}

    {draft ? <Drawer title={draft.id ? 'Kategoriyani tahrirlash' : 'Yangi kategoriya'} onClose={() => setDraft(null)}>
      <form onSubmit={event => { event.preventDefault(); const payload = { name: draft.name.trim(), slug: (draft.slug || slugify(draft.name)).trim() }; void run(() => draft.id ? categoryStore.update(draft.id, payload) : categoryStore.create(payload)); }}>
        <Input id="category-name" label="Nomi" required requiredMark value={draft.name} onChange={event => setDraft({ ...draft, name: event.target.value, slug: draft.id ? draft.slug : slugify(event.target.value) })} />
        <Input id="category-slug" label="Slug" required requiredMark value={draft.slug} hint="Manzilda ko‘rinadigan qism: /courses?category=…" onChange={event => setDraft({ ...draft, slug: event.target.value })} />
        <div className="ns-dialog-actions">
          <Button type="button" variant="secondary" onClick={() => setDraft(null)}>Bekor qilish</Button>
          <Button type="submit" loading={busy} disabled={!draft.name.trim()}>Saqlash</Button>
        </div>
      </form>
    </Drawer> : null}

    <ConfirmDialog open={removing !== null} title="Kategoriyani o‘chirasizmi?" description={removing ? `«${removing.name}» o‘chiriladi. Unga bog‘langan kurs bo‘lsa, server ruxsat bermaydi.` : ''} confirmLabel="O‘chirish" danger busy={busy} onClose={() => setRemoving(null)} onConfirm={() => { const target = removing; if (target) void run(() => categoryStore.remove(target.id)); }} />
  </AdminShell>;
}

/* ------------------------------- instructors ------------------------------ */

type InstructorDraft = { id?: string; name: string; slug: string; title: string; photo_url: string; experience: string; bio: string };
const emptyInstructor: InstructorDraft = { name: '', slug: '', title: '', photo_url: '', experience: '', bio: '' };

function InstructorManager() {
  const load = useCallback(() => instructorStore.list(), []);
  const { items, setItems, loading, error, setError } = useCollection<AdminInstructor>(load);
  const [draft, setDraft] = useState<InstructorDraft | null>(null);
  const [removing, setRemoving] = useState<AdminInstructor | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(operation: () => Promise<AdminInstructor[]>) {
    setBusy(true); setError('');
    try { setItems(await operation()); setDraft(null); setRemoving(null); }
    catch (reason) { setError(readApiError(reason, 'Amalni bajarib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  return <AdminShell>
    <PageHeader eyebrow="Kontent" title="Ustozlar" description="Public sahifada «Amaliy tajribaga ega mutaxassislar» bo‘limida ko‘rinadigan ustozlar." actions={<Button onClick={() => setDraft({ ...emptyInstructor })}>+ Ustoz qo‘shish</Button>} />
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : items.length === 0 ? <div className="ns-editor-empty"><h2>Ustoz qo‘shilmagan</h2><p>Kursga ustoz biriktirish uchun avval shu yerda ustoz profilini yarating.</p></div>
      : <div className="ns-manager-grid">
          {items.map(item => <Card key={item.id} className="ns-manager-card">
            <span className="ns-person-visual" aria-hidden="true">{item.name.split(' ').map(part => part.charAt(0)).join('').slice(0, 2)}</span>
            <div>
              <h2>{item.name}</h2>
              <strong>{item.title}</strong>
              <p>{item.experience}</p>
              <p>{item.bio}</p>
              <RowActions>
                <button type="button" onClick={() => setDraft({ id: item.id, name: item.name, slug: item.slug, title: item.title, photo_url: item.photo_url, experience: item.experience, bio: item.bio })}>Tahrirlash</button>
                <button type="button" onClick={() => setRemoving(item)}>O‘chirish</button>
              </RowActions>
            </div>
          </Card>)}
        </div>}

    {draft ? <Drawer title={draft.id ? 'Ustozni tahrirlash' : 'Yangi ustoz'} onClose={() => setDraft(null)}>
      <form onSubmit={event => {
        event.preventDefault();
        const payload = { name: draft.name.trim(), slug: (draft.slug || slugify(draft.name)).trim(), title: draft.title.trim(), photo_url: draft.photo_url.trim(), experience: draft.experience.trim(), bio: draft.bio.trim() };
        void run(() => draft.id ? instructorStore.update(draft.id, payload) : instructorStore.create(payload));
      }}>
        <div className="ns-form-grid">
          <Input id="instructor-name" label="To‘liq ism" required requiredMark value={draft.name} onChange={event => setDraft({ ...draft, name: event.target.value, slug: draft.id ? draft.slug : slugify(event.target.value) })} />
          <Input id="instructor-title" label="Lavozim" required requiredMark value={draft.title} onChange={event => setDraft({ ...draft, title: event.target.value })} />
        </div>
        <Input id="instructor-slug" label="Slug" required requiredMark value={draft.slug} hint="Public profil manzili uchun." onChange={event => setDraft({ ...draft, slug: event.target.value })} />
        <ImagePicker label="Ustoz rasmi" recommended="400×400" aspect="1 / 1" value={draft.photo_url} onChange={url => setDraft({ ...draft, photo_url: url })} />
        <Input id="instructor-experience" label="Tajriba" placeholder="8 yillik amaliy tajriba" value={draft.experience} onChange={event => setDraft({ ...draft, experience: event.target.value })} />
        <Textarea id="instructor-bio" label="Bio" rows={5} value={draft.bio} onChange={event => setDraft({ ...draft, bio: event.target.value })} />
        <div className="ns-dialog-actions">
          <Button type="button" variant="secondary" onClick={() => setDraft(null)}>Bekor qilish</Button>
          <Button type="submit" loading={busy} disabled={!draft.name.trim() || !draft.title.trim()}>Saqlash</Button>
        </div>
      </form>
    </Drawer> : null}

    <ConfirmDialog open={removing !== null} title="Ustozni o‘chirasizmi?" description={removing ? `«${removing.name}» profili o‘chiriladi. Unga bog‘langan kurs bo‘lsa, server ruxsat bermaydi.` : ''} confirmLabel="O‘chirish" danger busy={busy} onClose={() => setRemoving(null)} onConfirm={() => { const target = removing; if (target) void run(() => instructorStore.remove(target.id)); }} />
  </AdminShell>;
}

/* ------------------------------- testimonials ----------------------------- */

type TestimonialDraft = { id?: string; author_name: string; author_title: string; quote: string; photo_url: string; is_published: boolean; position: number };
const emptyTestimonial: TestimonialDraft = { author_name: '', author_title: '', quote: '', photo_url: '', is_published: true, position: 1 };

export function TestimonialsManager() {
  const load = useCallback(() => testimonialStore.list(), []);
  const { items, setItems, loading, error, setError } = useCollection<AdminTestimonial>(load);
  const [draft, setDraft] = useState<TestimonialDraft | null>(null);
  const [removing, setRemoving] = useState<AdminTestimonial | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(operation: () => Promise<AdminTestimonial[]>) {
    setBusy(true); setError('');
    try { setItems(await operation()); setDraft(null); setRemoving(null); }
    catch (reason) { setError(readApiError(reason, 'Amalni bajarib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  return <AdminShell>
    <PageHeader eyebrow="Ijtimoiy isbot" title="Talabalar fikrlari" description="Faqat admin boshqaradigan kontent. Foydalanuvchi reyting tizimi mavjud emas." actions={<Button onClick={() => setDraft({ ...emptyTestimonial, position: items.length + 1 })}>+ Fikr qo‘shish</Button>} />
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : items.length === 0 ? <div className="ns-editor-empty"><h2>Fikr qo‘shilmagan</h2><p>Bosh sahifadagi «Talabalar fikri» bo‘limi shu ro‘yxatdan to‘ldiriladi.</p></div>
      : <div className="ns-manager-grid">
          {items.map(item => <Card key={item.id} className="ns-testimonial-admin">
            <Badge tone={item.is_published ? 'success' : 'neutral'}>{item.is_published ? 'Public' : 'Yashirin'}</Badge>
            <blockquote>“{item.quote}”</blockquote>
            <strong>{item.author_name}</strong>
            <small>{item.author_title}</small>
            <RowActions>
              <button type="button" onClick={() => setDraft({ id: item.id, author_name: item.author_name, author_title: item.author_title, quote: item.quote, photo_url: item.photo_url, is_published: item.is_published, position: item.position })}>Tahrirlash</button>
              <button type="button" onClick={() => setRemoving(item)}>O‘chirish</button>
            </RowActions>
          </Card>)}
        </div>}

    {draft ? <Drawer title={draft.id ? 'Fikrni tahrirlash' : 'Yangi fikr'} onClose={() => setDraft(null)}>
      <form onSubmit={event => {
        event.preventDefault();
        const payload = { author_name: draft.author_name.trim(), author_title: draft.author_title.trim(), quote: draft.quote.trim(), photo_url: draft.photo_url.trim(), is_published: draft.is_published, position: draft.position };
        void run(() => draft.id ? testimonialStore.update(draft.id, payload) : testimonialStore.create(payload));
      }}>
        <div className="ns-form-grid">
          <Input id="testimonial-name" label="Ism" required requiredMark value={draft.author_name} onChange={event => setDraft({ ...draft, author_name: event.target.value })} />
          <Input id="testimonial-title" label="Kasb yoki lavozim" required requiredMark value={draft.author_title} onChange={event => setDraft({ ...draft, author_title: event.target.value })} />
        </div>
        <Textarea id="testimonial-quote" label="Fikr matni" rows={5} required value={draft.quote} onChange={event => setDraft({ ...draft, quote: event.target.value })} />
        <ImagePicker label="Talaba rasmi" recommended="400×400" aspect="1 / 1" value={draft.photo_url} onChange={url => setDraft({ ...draft, photo_url: url })} />
        <Input id="testimonial-order" label="Tartib raqami" type="number" min="1" value={draft.position} onChange={event => setDraft({ ...draft, position: Number(event.target.value) || 1 })} />
        <Checkbox id="testimonial-published" label="Bosh sahifada ko‘rsatish" checked={draft.is_published} onChange={event => setDraft({ ...draft, is_published: event.target.checked })} />
        <div className="ns-dialog-actions">
          <Button type="button" variant="secondary" onClick={() => setDraft(null)}>Bekor qilish</Button>
          <Button type="submit" loading={busy} disabled={!draft.author_name.trim() || !draft.quote.trim()}>Saqlash</Button>
        </div>
      </form>
    </Drawer> : null}

    <ConfirmDialog open={removing !== null} title="Fikrni o‘chirasizmi?" description={removing ? `«${removing.author_name}» fikri butunlay o‘chiriladi.` : ''} confirmLabel="O‘chirish" danger busy={busy} onClose={() => setRemoving(null)} onConfirm={() => { const target = removing; if (target) void run(() => testimonialStore.remove(target.id)); }} />
  </AdminShell>;
}
