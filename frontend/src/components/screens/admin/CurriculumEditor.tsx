'use client';

import { readApiError } from '@/lib/api';
import Link from 'next/link';
import { useCallback, useEffect, useState, type ReactNode } from 'react';

import { curriculum, type AdminLesson, type AdminModuleNode, type AdminPractice, type AdminTopicNode } from '@/lib/admin-data';
import { RowActions } from '@/components/domain/Admin';
import { Badge, Button, Checkbox, ConfirmDialog, Input, Select, Textarea } from '@/components/ui';

type LessonDraft = Omit<AdminLesson, 'id' | 'topic' | 'position'>;
const emptyLesson: LessonDraft = { title: '', kind: 'VIDEO', content: '', video_url: '', material_url: '', duration_minutes: 10, is_required: true, free_preview: false };
const emptyPractice = { instructions: '', example: '', resource_url: '', is_required: false };

/** A one-line "add" or "rename" field, used everywhere a title is typed. */
function NameForm({ label, value, onSubmit, onCancel, submitLabel = 'Saqlash' }: { label: string; value?: string; onSubmit: (value: string) => void; onCancel: () => void; submitLabel?: string }) {
  const [text, setText] = useState(value ?? '');
  return <form className="ns-inline-name" onSubmit={event => { event.preventDefault(); if (text.trim()) onSubmit(text.trim()); }}>
    <input className="ns-input" aria-label={label} placeholder={label} value={text} autoFocus onChange={event => setText(event.target.value)} />
    <Button type="submit" size="sm" disabled={!text.trim()}>{submitLabel}</Button>
    <Button type="button" size="sm" variant="ghost" onClick={onCancel}>Bekor qilish</Button>
  </form>;
}

function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return <div className="ns-inline-form" role="dialog" aria-modal="true" aria-label={title}>
    <header><h2>{title}</h2><button type="button" onClick={onClose} aria-label="Yopish">×</button></header>
    {children}
  </div>;
}

export function CurriculumEditor({ courseId }: { courseId?: string | undefined }) {
  const [tree, setTree] = useState<AdminModuleNode[] | null>(null);
  const [loading, setLoading] = useState(Boolean(courseId));
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [adding, setAdding] = useState('');            // 'module' | `topic:<moduleId>`
  const [renaming, setRenaming] = useState('');        // `module:<id>` | `topic:<id>`
  const [lessonForm, setLessonForm] = useState<{ topicId: string; lesson: AdminLesson | null } | null>(null);
  const [practiceForm, setPracticeForm] = useState<{ topicId: string; practice: AdminPractice | null } | null>(null);
  const [confirm, setConfirm] = useState<{ title: string; description: string; run: () => Promise<AdminModuleNode[]> } | null>(null);

  useEffect(() => {
    if (!courseId) { setLoading(false); return; }
    let live = true;
    setLoading(true);
    curriculum.load(courseId)
      .then(value => { if (live) { setTree(value); setError(''); } })
      .catch(reason => { if (live) setError(readApiError(reason, 'O‘quv dasturini yuklab bo‘lmadi.')); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [courseId]);

  const run = useCallback(async (key: string, operation: () => Promise<AdminModuleNode[]>) => {
    setBusy(key); setError('');
    try { setTree(await operation()); }
    catch (reason) { setError(readApiError(reason, 'Amalni bajarib bo‘lmadi.')); }
    finally { setBusy(''); }
  }, []);

  if (!courseId) return <div className="ns-editor-empty"><h2>O‘quv dasturi</h2><p>Modul va darslarni qo‘shish uchun avval kursni saqlang. Saqlaganingizdan keyin shu bo‘lim ochiladi.</p></div>;
  if (loading) return <div className="ns-editor-empty"><p>O‘quv dasturi yuklanmoqda…</p></div>;

  const modules = tree ?? [];
  const disabled = Boolean(busy);

  return <div className="ns-curriculum-wrap">
    <div className="ns-editor-section-head">
      <div><h2>O‘quv dasturi</h2><p>Modul → mavzu → dars tartibi. Har bir mavzuga amaliyot va test biriktiriladi.</p></div>
      {adding === 'module' ? null : <Button type="button" onClick={() => setAdding('module')} disabled={disabled}>+ Modul qo‘shish</Button>}
    </div>

    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}

    {modules.length === 0 && adding !== 'module' ? <div className="ns-editor-empty"><p>Hali modul yo‘q. Birinchi modulni qo‘shing — masalan «Kirish».</p></div> : null}

    <div className="ns-curriculum-editor">
      {modules.map((module, moduleIndex) => <section key={module.id}>
        <header>
          <span className="ns-order-mark" aria-hidden="true">{module.position}</span>
          {renaming === `module:${module.id}`
            ? <div><NameForm label="Modul nomi" value={module.title} onCancel={() => setRenaming('')} onSubmit={title => { setRenaming(''); void run(module.id, () => curriculum.renameModule(courseId, module.id, title)); }} /></div>
            : <div><small>{module.position}-MODUL</small><strong>{module.title}</strong></div>}
          <RowActions>
            <button type="button" disabled={disabled || moduleIndex === 0} aria-label="Yuqoriga ko‘chirish" onClick={() => void run(module.id, () => curriculum.moveModule(courseId, module.id, -1))}>↑</button>
            <button type="button" disabled={disabled || moduleIndex === modules.length - 1} aria-label="Pastga ko‘chirish" onClick={() => void run(module.id, () => curriculum.moveModule(courseId, module.id, 1))}>↓</button>
            <button type="button" disabled={disabled} onClick={() => setRenaming(`module:${module.id}`)}>Nomini o‘zgartirish</button>
            <button type="button" disabled={disabled} onClick={() => setConfirm({ title: 'Modulni o‘chirasizmi?', description: `«${module.title}» moduli va uning barcha mavzu, dars, amaliyot va testlari o‘chiriladi.`, run: () => curriculum.removeModule(courseId, module.id) })}>O‘chirish</button>
          </RowActions>
        </header>

        <div>
          {module.topics.map((topic, topicIndex) => <TopicBlock
            key={topic.id}
            courseId={courseId}
            moduleId={module.id}
            topic={topic}
            first={topicIndex === 0}
            last={topicIndex === module.topics.length - 1}
            disabled={disabled}
            renaming={renaming}
            setRenaming={setRenaming}
            run={run}
            onEditLesson={lesson => setLessonForm({ topicId: topic.id, lesson })}
            onEditPractice={() => setPracticeForm({ topicId: topic.id, practice: topic.practice })}
            onConfirm={setConfirm}
          />)}

          {adding === `topic:${module.id}`
            ? <NameForm label="Mavzu nomi" onCancel={() => setAdding('')} onSubmit={title => { setAdding(''); void run(module.id, () => curriculum.addTopic(courseId, module.id, title)); }} />
            : <Button type="button" variant="secondary" disabled={disabled} onClick={() => setAdding(`topic:${module.id}`)}>+ Mavzu qo‘shish</Button>}
        </div>
      </section>)}

      {adding === 'module'
        ? <NameForm label="Modul nomi" onCancel={() => setAdding('')} onSubmit={title => { setAdding(''); void run('new-module', () => curriculum.addModule(courseId, title)); }} />
        : null}
    </div>

    {lessonForm ? <LessonDrawer
      courseId={courseId}
      topicId={lessonForm.topicId}
      lesson={lessonForm.lesson}
      onClose={() => setLessonForm(null)}
      onSaved={value => { setTree(value); setLessonForm(null); }}
    /> : null}

    {practiceForm ? <PracticeDrawer
      courseId={courseId}
      topicId={practiceForm.topicId}
      practice={practiceForm.practice}
      onClose={() => setPracticeForm(null)}
      onSaved={value => { setTree(value); setPracticeForm(null); }}
    /> : null}

    <ConfirmDialog
      open={confirm !== null}
      title={confirm?.title ?? ''}
      description={confirm?.description ?? ''}
      confirmLabel="O‘chirish"
      danger
      busy={Boolean(busy)}
      onClose={() => setConfirm(null)}
      onConfirm={() => { const current = confirm; setConfirm(null); if (current) void run('delete', current.run); }}
    />
  </div>;
}

function TopicBlock({ courseId, moduleId, topic, first, last, disabled, renaming, setRenaming, run, onEditLesson, onEditPractice, onConfirm }: {
  courseId: string; moduleId: string; topic: AdminTopicNode; first: boolean; last: boolean; disabled: boolean;
  renaming: string; setRenaming: (value: string) => void;
  run: (key: string, operation: () => Promise<AdminModuleNode[]>) => Promise<void>;
  onEditLesson: (lesson: AdminLesson | null) => void; onEditPractice: () => void;
  onConfirm: (value: { title: string; description: string; run: () => Promise<AdminModuleNode[]> }) => void;
}) {
  const previewCount = topic.lessons.filter(item => item.free_preview).length;
  return <article>
    <header>
      <span className="ns-order-mark" aria-hidden="true">{topic.position}</span>
      {renaming === `topic:${topic.id}`
        ? <div><NameForm label="Mavzu nomi" value={topic.title} onCancel={() => setRenaming('')} onSubmit={title => { setRenaming(''); void run(topic.id, () => curriculum.renameTopic(courseId, topic.id, title)); }} /></div>
        : <div><strong>{topic.title}</strong><small>{topic.lessons.length} dars{previewCount ? ` · ${previewCount} bepul` : ''}{topic.practice ? ' · amaliyot bor' : ''}</small></div>}
      <Badge tone={topic.test ? 'success' : 'neutral'}>{topic.test ? `Test ${topic.test.passing_score}%` : 'Testsiz'}</Badge>
      <RowActions>
        <button type="button" disabled={disabled || first} aria-label="Mavzuni yuqoriga" onClick={() => void run(topic.id, () => curriculum.moveTopic(courseId, moduleId, topic.id, -1))}>↑</button>
        <button type="button" disabled={disabled || last} aria-label="Mavzuni pastga" onClick={() => void run(topic.id, () => curriculum.moveTopic(courseId, moduleId, topic.id, 1))}>↓</button>
        <button type="button" disabled={disabled} onClick={() => setRenaming(`topic:${topic.id}`)}>Nomini o‘zgartirish</button>
        <button type="button" disabled={disabled} onClick={() => onConfirm({ title: 'Mavzuni o‘chirasizmi?', description: `«${topic.title}» mavzusi, darslari, amaliyoti va testi o‘chiriladi.`, run: () => curriculum.removeTopic(courseId, topic.id) })}>O‘chirish</button>
      </RowActions>
    </header>

    <ul>
      {topic.lessons.map((lesson, index) => <li key={lesson.id}>
        <span className="ns-order-mark" aria-hidden="true">{lesson.position}</span>
        <span>
          <span>{lesson.title}</span>
          <small>{lesson.kind === 'VIDEO' ? 'Video' : 'Matn'} · {lesson.duration_minutes} daqiqa · {lesson.is_required ? 'Majburiy' : 'Ixtiyoriy'}</small>
          <Checkbox
            id={`preview-${lesson.id}`}
            label="Bepul preview — mehmonlar ham ko‘ra oladi"
            checked={lesson.free_preview}
            disabled={disabled}
            onChange={event => void run(lesson.id, () => curriculum.updateLesson(courseId, lesson.id, { free_preview: event.target.checked }))}
          />
        </span>
        <RowActions>
          <button type="button" disabled={disabled || index === 0} aria-label="Darsni yuqoriga" onClick={() => void run(lesson.id, () => curriculum.moveLesson(courseId, topic.id, lesson.id, -1))}>↑</button>
          <button type="button" disabled={disabled || index === topic.lessons.length - 1} aria-label="Darsni pastga" onClick={() => void run(lesson.id, () => curriculum.moveLesson(courseId, topic.id, lesson.id, 1))}>↓</button>
          <button type="button" disabled={disabled} onClick={() => onEditLesson(lesson)}>Tahrirlash</button>
          <button type="button" disabled={disabled} onClick={() => onConfirm({ title: 'Darsni o‘chirasizmi?', description: `«${lesson.title}» darsi o‘chiriladi.`, run: () => curriculum.removeLesson(courseId, topic.id, lesson.id) })}>O‘chirish</button>
        </RowActions>
      </li>)}
      {topic.lessons.length === 0 ? <li><span aria-hidden="true">·</span><span><small>Bu mavzuda hali dars yo‘q.</small></span><span /></li> : null}
    </ul>

    <footer>
      <Button type="button" variant="secondary" size="sm" disabled={disabled} onClick={() => onEditLesson(null)}>+ Dars</Button>
      <Button type="button" variant="ghost" size="sm" disabled={disabled} onClick={onEditPractice}>{topic.practice ? 'Amaliyotni tahrirlash' : '+ Amaliyot'}</Button>
      {topic.practice ? <button type="button" disabled={disabled} onClick={() => onConfirm({ title: 'Amaliyotni o‘chirasizmi?', description: 'Mavzu amaliy topshiriqsiz qoladi.', run: () => curriculum.removePractice(courseId, topic.id, topic.practice!.id) })}>Amaliyotni o‘chirish</button> : null}
      {topic.test
        ? <><Link href={`/admin/tests?course=${courseId}&topic=${topic.id}`}>Savollarni tahrirlash →</Link>
            <button type="button" disabled={disabled} onClick={() => onConfirm({ title: 'Testni o‘chirasizmi?', description: 'Mavzu testi va uning savollari o‘chiriladi.', run: () => curriculum.removeTest(courseId, topic.id, topic.test!.id) })}>Testni o‘chirish</button></>
        : <Button type="button" variant="ghost" size="sm" disabled={disabled} onClick={() => void run(topic.id, () => curriculum.saveTest(courseId, topic.id, { passing_score: 70, question_count: null, is_required: true }))}>+ Test qo‘shish</Button>}
    </footer>
  </article>;
}

function LessonDrawer({ courseId, topicId, lesson, onClose, onSaved }: { courseId: string; topicId: string; lesson: AdminLesson | null; onClose: () => void; onSaved: (tree: AdminModuleNode[]) => void }) {
  const [draft, setDraft] = useState<LessonDraft>(lesson ? { title: lesson.title, kind: lesson.kind, content: lesson.content, video_url: lesson.video_url, material_url: lesson.material_url, duration_minutes: lesson.duration_minutes, is_required: lesson.is_required, free_preview: lesson.free_preview } : { ...emptyLesson });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const invalid = !draft.title.trim() || (draft.kind === 'VIDEO' && !draft.video_url.trim()) || (draft.kind === 'TEXT' && !draft.content.trim());

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError('');
    try { onSaved(lesson ? await curriculum.updateLesson(courseId, lesson.id, draft) : await curriculum.addLesson(courseId, topicId, draft)); }
    catch (reason) { setError(readApiError(reason, 'Darsni saqlab bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  return <Drawer title={lesson ? 'Darsni tahrirlash' : 'Yangi dars'} onClose={onClose}>
    <form onSubmit={submit}>
      <Input id="lesson-title" label="Dars nomi" value={draft.title} required requiredMark onChange={event => setDraft({ ...draft, title: event.target.value })} />
      <div className="ns-form-grid">
        <Select id="lesson-kind" label="Turi" value={draft.kind} onChange={event => setDraft({ ...draft, kind: event.target.value === 'TEXT' ? 'TEXT' : 'VIDEO' })}>
          <option value="VIDEO">Video dars</option>
          <option value="TEXT">Matnli dars</option>
        </Select>
        <Input id="lesson-duration" label="Davomiyligi (daqiqa)" type="number" min="1" value={draft.duration_minutes} onChange={event => setDraft({ ...draft, duration_minutes: Number(event.target.value) || 0 })} />
      </div>
      {draft.kind === 'VIDEO'
        ? <Input id="lesson-video" label="Video havolasi" type="url" placeholder="https://customer-....cloudflarestream.com/<id>/iframe" value={draft.video_url} required requiredMark hint="Qo‘llab-quvvatlanadi: Cloudflare Stream, Kinescope, VdoCipher, Bunny, Gumlet, YouTube, Vimeo va to‘g‘ridan-to‘g‘ri .mp4. Platformada videoni ochib «Embed» havolasini nusxalang." onChange={event => setDraft({ ...draft, video_url: event.target.value })} />
        : <Textarea id="lesson-content" label="Dars matni" rows={8} value={draft.content} required hint="Matnli darsda majburiy." onChange={event => setDraft({ ...draft, content: event.target.value })} />}
      {draft.kind === 'VIDEO' ? <Textarea id="lesson-notes" label="Qo‘shimcha izoh" rows={4} value={draft.content} onChange={event => setDraft({ ...draft, content: event.target.value })} /> : null}
      <Input id="lesson-material" label="Material havolasi" type="url" placeholder="https://..." value={draft.material_url} onChange={event => setDraft({ ...draft, material_url: event.target.value })} />
      <Checkbox id="lesson-required" label="Majburiy dars (test ochilishi uchun tugatilishi shart)" checked={draft.is_required} onChange={event => setDraft({ ...draft, is_required: event.target.checked })} />
      <Checkbox id="lesson-preview" label="Bepul preview — ro‘yxatdan o‘tmagan mehmon ham ko‘radi" checked={draft.free_preview} onChange={event => setDraft({ ...draft, free_preview: event.target.checked })} />
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
      <div className="ns-dialog-actions">
        <Button type="button" variant="secondary" onClick={onClose}>Bekor qilish</Button>
        <Button type="submit" loading={busy} disabled={invalid}>Saqlash</Button>
      </div>
    </form>
  </Drawer>;
}

function PracticeDrawer({ courseId, topicId, practice, onClose, onSaved }: { courseId: string; topicId: string; practice: AdminPractice | null; onClose: () => void; onSaved: (tree: AdminModuleNode[]) => void }) {
  const [draft, setDraft] = useState(practice ? { instructions: practice.instructions, example: practice.example, resource_url: practice.resource_url, is_required: practice.is_required } : { ...emptyPractice });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError('');
    try { onSaved(await curriculum.savePractice(courseId, topicId, draft, practice?.id)); }
    catch (reason) { setError(readApiError(reason, 'Amaliyotni saqlab bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  return <Drawer title={practice ? 'Amaliyotni tahrirlash' : 'Amaliy topshiriq'} onClose={onClose}>
    <form onSubmit={submit}>
      <Textarea id="practice-instructions" label="Topshiriq matni" rows={5} required value={draft.instructions} onChange={event => setDraft({ ...draft, instructions: event.target.value })} />
      <Textarea id="practice-example" label="Namuna" rows={4} value={draft.example} onChange={event => setDraft({ ...draft, example: event.target.value })} />
      <Input id="practice-resource" label="Qo‘shimcha havola" type="url" placeholder="https://..." value={draft.resource_url} onChange={event => setDraft({ ...draft, resource_url: event.target.value })} />
      <Checkbox id="practice-required" label="Majburiy topshiriq" checked={draft.is_required} onChange={event => setDraft({ ...draft, is_required: event.target.checked })} />
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
      <div className="ns-dialog-actions">
        <Button type="button" variant="secondary" onClick={onClose}>Bekor qilish</Button>
        <Button type="submit" loading={busy} disabled={!draft.instructions.trim()}>Saqlash</Button>
      </div>
    </form>
  </Drawer>;
}
