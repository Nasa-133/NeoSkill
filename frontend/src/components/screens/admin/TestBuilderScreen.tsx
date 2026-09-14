'use client';

import { readApiError } from '@/lib/api';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { curriculum, listCourses, questions as questionApi, type AdminModuleNode, type AdminQuestion } from '@/lib/admin-data';
import { AdminShell } from '@/components/layout/Shells';
import { Badge, Button, Card, Input, PageHeader, Select, Textarea } from '@/components/ui';

function blankQuestion(testId: string): AdminQuestion {
  const id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `q-${Date.now()}`;
  return { id, test: testId, text: '', position: 0, options: [0, 1, 2, 3].map(index => ({ id: `${id}-o${index}`, text: '', position: index + 1, is_correct: index === 0 })) };
}


export function TestBuilderScreen() {
  const params = useSearchParams(); const router = useRouter(); const pathname = usePathname();
  const [courses, setCourses] = useState<{ id: string; title: string }[]>([]);
  const [courseId, setCourseId] = useState(params.get('course') ?? '');
  const [topicId, setTopicId] = useState(params.get('topic') ?? '');
  const [tree, setTree] = useState<AdminModuleNode[]>([]);
  const [items, setItems] = useState<AdminQuestion[]>([]);
  const [score, setScore] = useState('70');
  const [loading, setLoading] = useState(true);
  const [treeLoading, setTreeLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    listCourses()
      .then(list => { if (!live) return; setCourses(list); if (!courseId && list[0]) setCourseId(list[0].id); })
      .catch(reason => { if (live) setError(readApiError(reason, 'Kurslar ro‘yxatini yuklab bo‘lmadi.')); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  const loadTree = useCallback(async (id: string) => {
    setTreeLoading(true);
    try {
      const value = await curriculum.load(id);
      setTree(value);
      const topics = value.flatMap(module => module.topics);
      setTopicId(current => topics.some(item => item.id === current) ? current : (topics.find(item => item.test) ?? topics[0])?.id ?? '');
    } catch (reason) { setError(readApiError(reason, 'O‘quv dasturini yuklab bo‘lmadi.')); setTree([]); }
    finally { setTreeLoading(false); }
  }, []);

  useEffect(() => { if (courseId) void loadTree(courseId); }, [courseId, loadTree]);

  const topic = useMemo(() => tree.flatMap(module => module.topics).find(item => item.id === topicId), [tree, topicId]);
  const parentModule = useMemo(() => tree.find(module => module.topics.some(item => item.id === topicId)), [tree, topicId]);
  const course = courses.find(item => item.id === courseId);
  const test = topic?.test ?? null;

  useEffect(() => {
    if (!test) { setItems([]); return; }
    setScore(String(test.passing_score));
    let live = true;
    questionApi.load(test.id).then(value => { if (live) setItems(value); }).catch(reason => { if (live) setError(readApiError(reason, 'Savollarni yuklab bo‘lmadi.')); });
    return () => { live = false; };
  }, [test]);

  // Keeps the selection in the URL so the curriculum editor can deep-link here.
  useEffect(() => {
    if (!courseId) return;
    const next = new URLSearchParams(); next.set('course', courseId); if (topicId) next.set('topic', topicId);
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }, [courseId, topicId, pathname, router]);

  function setOption(id: string, index: number, text: string) {
    setItems(value => value.map(item => item.id === id ? { ...item, options: item.options.map((option, order) => order === index ? { ...option, text } : option) } : item));
    setMessage('');
  }
  function setCorrect(id: string, index: number) {
    setItems(value => value.map(item => item.id === id ? { ...item, options: item.options.map((option, order) => ({ ...option, is_correct: order === index })) } : item));
    setMessage('');
  }
  function reorder(index: number, delta: number) {
    setItems(value => { const next = [...value]; const [item] = next.splice(index, 1); next.splice(index + delta, 0, item!); return next; });
    setMessage('');
  }

  const valid = items.length > 0
    && items.every(item => item.text.trim() && item.options.length === 4 && item.options.every(option => option.text.trim()) && item.options.filter(option => option.is_correct).length === 1)
    && Number(score) >= 1 && Number(score) <= 100;

  async function createTest() {
    if (!topic || !courseId) return;
    setBusy(true); setError('');
    try { setTree(await curriculum.saveTest(courseId, topic.id, { passing_score: 70, question_count: null, is_required: true })); }
    catch (reason) { setError(readApiError(reason, 'Testni yaratib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  async function save() {
    if (!test || !courseId || !topic) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await curriculum.saveTest(courseId, topic.id, { passing_score: Number(score), question_count: null, is_required: test.is_required }, test.id);
      setItems(await questionApi.save(test.id, items.map((item, index) => ({ ...item, position: index + 1 }))));
      setTree(await curriculum.load(courseId));
      setMessage('Test saqlandi.');
    } catch (reason) { setError(readApiError(reason, 'Testni saqlab bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  const topicCount = tree.reduce((sum, module) => sum + module.topics.length, 0);
  const withTest = tree.reduce((sum, module) => sum + module.topics.filter(item => item.test).length, 0);

  return <AdminShell>
    <PageHeader
      eyebrow="Baholash"
      title="Mavzu testlari"
      description="Test bitta mavzuga biriktiriladi. Chapdan modul va mavzuni tanlang, o‘ng tomonda savollarni yozing."
      actions={test ? <Button onClick={save} loading={busy} disabled={!valid}>Testni saqlash</Button> : undefined}
    />

    <div className="ns-test-course-picker">
      <Select id="test-course" label="Kurs" value={courseId} onChange={event => { setCourseId(event.target.value); setTopicId(''); setError(''); setMessage(''); }}>
        {courses.length === 0 ? <option value="">Kurs yo‘q</option> : null}
        {courses.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
      </Select>
      <div className="ns-test-course-meta">
        <span><small>Mavzular</small><strong>{topicCount}</strong></span>
        <span><small>Testi bor</small><strong>{withTest}</strong></span>
      </div>
      {courseId ? <Link className="ns-table-link" href={`/admin/courses/${courseId}/edit`}>O‘quv dasturini tahrirlash →</Link> : null}
    </div>

    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}

    {loading ? <p className="ns-muted">Yuklanmoqda…</p>
      : courses.length === 0 ? <div className="ns-editor-empty"><h2>Hali kurs yo‘q</h2><p>Test qo‘shish uchun avval kurs yarating.</p><Link className="ns-link-button" href="/admin/courses/new">+ Yangi kurs</Link></div>
      : <div className="ns-test-layout">
          <aside className="ns-test-tree" aria-label="Kurs mavzulari">
            {treeLoading ? <p className="ns-muted">Yuklanmoqda…</p>
              : tree.length === 0 ? <p className="ns-muted">Bu kursda modul yo‘q. Avval o‘quv dasturida modul va mavzu qo‘shing.</p>
              : tree.map(module => <section key={module.id}>
                  <h3>{module.position}-MODUL · {module.title}</h3>
                  {module.topics.length === 0 ? <p className="ns-muted">Mavzu yo‘q</p>
                    : module.topics.map(item => <button
                        key={item.id}
                        type="button"
                        data-active={item.id === topicId || undefined}
                        onClick={() => { setTopicId(item.id); setMessage(''); setError(''); }}
                      >
                        <span>{item.position}. {item.title}</span>
                        <Badge tone={item.test ? 'success' : 'neutral'}>{item.test ? `${item.test.passing_score}%` : 'yo‘q'}</Badge>
                      </button>)}
                </section>)}
          </aside>

          <section className="ns-test-editor">
            {!topic ? <div className="ns-editor-empty"><h2>Mavzu tanlanmagan</h2><p>Chapdagi ro‘yxatdan mavzuni tanlang.</p></div>
              : <>
                <nav className="ns-breadcrumb" aria-label="Test joylashuvi">
                  <span>{course?.title}</span><span>›</span>
                  <span>{parentModule?.position}-modul: {parentModule?.title}</span><span>›</span>
                  <strong>{topic.position}-mavzu: {topic.title}</strong>
                </nav>

                {!test ? <div className="ns-editor-empty">
                    <h2>Bu mavzuda test yo‘q</h2>
                    <p>Test yaratsangiz, talaba mavzu darslarini tugatgach uni topshiradi va keyingi mavzu shundan keyin ochiladi.</p>
                    <Button onClick={createTest} loading={busy}>«{topic.title}» uchun test yaratish</Button>
                  </div>
                  : <>
                    <div className="ns-test-settings">
                      <div><small>Mavzudagi darslar</small><strong>{topic.lessons.length}</strong></div>
                      <Input id="passing-score" label="O‘tish bali (%)" type="number" min="1" max="100" value={score} onChange={event => { setScore(event.target.value); setMessage(''); }} />
                      <div><small>Savollar</small><strong>{items.length} ta</strong></div>
                    </div>

                    {items.length === 0 ? <div className="ns-editor-empty"><h2>Savol qo‘shilmagan</h2><p>Talaba test topshirishi uchun kamida bitta savol kerak.</p></div> : null}

                    <div className="ns-question-builder">
                      {items.map((question, index) => <Card key={question.id} className="ns-builder-card">
                        <header>
                          <strong>{index + 1}-savol</strong>
                          <button type="button" disabled={index === 0} aria-label="Yuqoriga" onClick={() => reorder(index, -1)}>↑</button>
                          <button type="button" disabled={index === items.length - 1} aria-label="Pastga" onClick={() => reorder(index, 1)}>↓</button>
                          <button type="button" aria-label="Savolni o‘chirish" onClick={() => { setItems(value => value.filter(item => item.id !== question.id)); setMessage(''); }}>×</button>
                        </header>
                        <Textarea id={`question-${question.id}`} label="Savol matni" rows={2} value={question.text} onChange={event => { setItems(value => value.map(item => item.id === question.id ? { ...item, text: event.target.value } : item)); setMessage(''); }} />
                        <fieldset>
                          <legend>Javob variantlari — to‘g‘risini belgilang</legend>
                          {question.options.map((option, optionIndex) => <div key={option.id}>
                            <input type="radio" name={`correct-${question.id}`} aria-label={`${optionIndex + 1}-variant to‘g‘ri`} checked={option.is_correct} onChange={() => setCorrect(question.id, optionIndex)} />
                            <Input id={`option-${question.id}-${optionIndex}`} label={`${String.fromCharCode(65 + optionIndex)} varianti`} value={option.text} onChange={event => setOption(question.id, optionIndex, event.target.value)} />
                          </div>)}
                        </fieldset>
                      </Card>)}
                    </div>

                    <div className="ns-dialog-actions">
                      <Button variant="secondary" onClick={() => { setItems(value => [...value, blankQuestion(test.id)]); setMessage(''); }}>+ Savol qo‘shish</Button>
                      <Button onClick={save} loading={busy} disabled={!valid}>Testni saqlash</Button>
                    </div>

                    {!valid && items.length > 0 ? <p className="ns-field__error" role="alert">Har bir savolda matn, 4 ta to‘ldirilgan variant va aynan bitta to‘g‘ri javob bo‘lishi kerak. O‘tish bali 1–100 oralig‘ida.</p> : null}
                    {message ? <p className="ns-save-message" role="status">✓ {message}</p> : null}
                  </>}
              </>}
          </section>
        </div>}
  </AdminShell>;
}
