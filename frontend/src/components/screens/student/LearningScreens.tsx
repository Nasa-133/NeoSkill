'use client';
import Link from 'next/link'; import { useSearchParams } from 'next/navigation'; import { useCallback, useEffect, useState } from 'react';
import { learningNavigation, lesson as lessonFixture, practice as practiceFixture, topicTest as topicTestFixture } from '@/lib/fixtures'; import { api, readApiError, useMockData } from '@/lib/api'; import { useCurrentUser, roleLabel } from '@/lib/session'; import { simulateMutation, useResource } from '@/lib/use-resource'; import type { DeviceChoice, LearningNavigation, LessonDetail, LessonPreview, Practice, ReferralSummary, TopicTest } from '@/lib/types'; import { LearningSidebar } from '@/components/domain/Student'; import { VideoPlayer } from '@/components/domain/Video'; import { PublicShell, StudentShell } from '@/components/layout/Shells'; import { Badge, Button, Card, EmptyState, ErrorState, Input, ProgressBar, Radio, RouteLoading } from '@/components/ui';

/** Flattens the course tree so lesson navigation follows the real order. */
function lessonSequence(navigation: LearningNavigation) { return navigation.modules.flatMap(module => module.topics.flatMap(topic => topic.lessons.map(item => ({ ...item, topic_id: topic.id })))); }
function firstOpenLessonId(navigation: LearningNavigation) { const sequence = lessonSequence(navigation); return (sequence.find(item => !item.is_locked && !item.is_completed) ?? sequence.find(item => !item.is_locked) ?? sequence[0])?.id; }

export function LearningOverview({ slug }: { slug: string }) {
  const resource = useResource(useCallback(() => api.learning(slug), [slug]), useCallback(() => learningNavigation, []));
  if (resource.loading) return <StudentShell><RouteLoading /></StudentShell>;
  if (resource.error || !resource.data) return <StudentShell><ErrorState title="Kursni ochib bo‘lmadi" description={resource.error || undefined} onRetry={resource.retry} /></StudentShell>;
  const navigation = resource.data;
  const continueId = navigation.progress.current_lesson_id ?? firstOpenLessonId(navigation);
  return <StudentShell><div className="ns-learning-layout"><LearningSidebar navigation={navigation} courseSlug={slug} /><main className="ns-learning-main"><div className="ns-learning-welcome"><Badge tone="brand">O‘qish davom etmoqda</Badge><h1>{navigation.title}</h1><p>Modul va mavzularni ketma-ket yakunlang. Keyingi mavzu testdan muvaffaqiyatli o‘tgach ochiladi.</p><ProgressBar value={navigation.progress.percent} />{continueId ? <Link className="ns-link-button" href={`/learn/${slug}/lesson/${continueId}`}>Darsni davom ettirish</Link> : null}</div><section><h2>Kurs rejasi</h2><div className="ns-module-grid">{navigation.modules.map(module => <Card key={module.id}><small>{module.position}-MODUL</small><h3>{module.title}</h3><p>{module.topics.length} mavzu · {module.topics.reduce((sum, item) => sum + item.lessons.length, 0)} dars</p><Badge tone={module.topics.every(item => item.is_locked) ? 'neutral' : 'brand'}>{module.topics.every(item => item.is_locked) ? 'Yopiq' : 'Davom etmoqda'}</Badge></Card>)}</div></section></main></div></StudentShell>;
}

/* ------------------------------- free preview ------------------------------ */

export function LessonPreviewScreen({ slug, id }: { slug: string; id: string }) {
  const resource = useResource(useCallback(() => api.lessonPreview(id), [id]), useCallback((): LessonPreview => ({ id: lessonFixture.id, course_slug: lessonFixture.course_slug, title: lessonFixture.title, kind: lessonFixture.kind, content: lessonFixture.content, video_url: lessonFixture.video_url, material_url: lessonFixture.material_url, duration_minutes: lessonFixture.duration_minutes, free_preview: true }), []));
  if (resource.loading) return <PublicShell><RouteLoading /></PublicShell>;
  if (resource.error || !resource.data) return <PublicShell><div className="ns-container ns-section"><EmptyState title="Bepul dars topilmadi" description="Bu dars bepul tanishuv uchun ochilmagan yoki kurs hali nashr qilinmagan." actionHref={`/courses/${slug}`} actionLabel="Kurs sahifasi" /></div></PublicShell>;
  const item = resource.data;
  const courseSlug = item.course_slug || slug;
  return <PublicShell><div className="ns-container ns-section"><article className="ns-lesson">
    <nav className="ns-breadcrumb"><Link href={`/courses/${courseSlug}`}>Kurs sahifasi</Link><span>›</span><span>Bepul dars</span></nav>
    <Badge tone="brand">Bepul tanishuv darsi</Badge>
    <h1>{item.title}</h1>
    <p className="ns-lesson-meta">{item.duration_minutes} daqiqa · {item.kind === 'VIDEO' ? 'Video dars' : 'Matnli dars'}</p>
    {item.kind === 'VIDEO' ? <VideoPlayer url={item.video_url} title={item.title} /> : null}
    {item.content ? <section className="ns-lesson-content"><h2>Dars haqida</h2><p>{item.content}</p>{item.material_url ? <a href={item.material_url} target="_blank" rel="noreferrer">Qo‘shimcha materialni ochish ↗</a> : null}</section> : null}
    <footer className="ns-lesson-actions">
      <Link className="ns-link-button ns-link-button--secondary" href={`/courses/${courseSlug}`}>← Kurs sahifasiga qaytish</Link>
      <Link className="ns-link-button" href={`/courses/${courseSlug}#enroll`}>Kursga yozilish</Link>
    </footer>
  </article></div></PublicShell>;
}

/* --------------------------------- lesson --------------------------------- */

type LessonBundle = { navigation: LearningNavigation; detail: LessonDetail; practice: Practice | null };

export function LessonScreen({ slug, id }: { slug: string; id: string }) {
  const search = useSearchParams(); const denied = useMockData && search.get('access') === 'denied';
  const { user } = useCurrentUser();
  const resource = useResource(
    useCallback(async (): Promise<LessonBundle> => {
      const [navigation, detail] = await Promise.all([api.learning(slug), api.lesson(id)]);
      const practice = await api.practice(detail.topic).catch(() => null);
      return { navigation, detail, practice };
    }, [slug, id]),
    useCallback((): LessonBundle => ({ navigation: learningNavigation, detail: lessonFixture, practice: practiceFixture }), []),
  );

  const [complete, setComplete] = useState(false);
  const [practiceDone, setPracticeDone] = useState(false);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!resource.data) return;
    setComplete(resource.data.detail.is_completed ?? false);
    setPracticeDone(resource.data.practice?.is_completed ?? false);
    setMessage('');
  }, [resource.data]);

  async function finish(type: 'lesson' | 'practice') {
    const topicId = resource.data?.detail.topic;
    setBusy(type); setMessage('');
    try {
      if (useMockData) await simulateMutation(null);
      else if (type === 'lesson') await api.completeLesson(id);
      else if (topicId) await api.completePractice(topicId);
      if (type === 'lesson') setComplete(true); else setPracticeDone(true);
      setMessage(type === 'lesson' ? 'Dars tugallandi. Natija saqlandi.' : 'Topshiriq bajarilgan deb belgilandi.');
    } catch (reason) { setMessage(readApiError(reason, 'Natijani saqlab bo‘lmadi.')); }
    finally { setBusy(''); }
  }

  if (denied) return <StudentShell><EmptyState title="Bu darsga kirish yopiq" description="Kursni o‘rganish uchun faol enrollment kerak." actionHref={`/courses/${slug}`} actionLabel="Kurs haqida" /></StudentShell>;
  if (resource.loading) return <StudentShell><RouteLoading /></StudentShell>;
  if (resource.error || !resource.data) return <StudentShell><ErrorState title="Darsni ochib bo‘lmadi" description={resource.error || undefined} onRetry={resource.retry} /></StudentShell>;

  const { navigation, detail, practice } = resource.data;
  const watermark = user?.email ?? '';
  const sequence = lessonSequence(navigation);
  const position = sequence.findIndex(item => item.id === id);
  const current = position < 0 ? undefined : sequence[position];
  const previous = position > 0 ? sequence[position - 1] : undefined;
  const upcoming = position < 0 ? undefined : sequence[position + 1];
  const lastOfTopic = Boolean(current) && upcoming?.topic_id !== current?.topic_id;
  const topicTest = navigation.modules.flatMap(module => module.topics).find(topic => topic.id === current?.topic_id)?.test ?? null;
  const nextHref = current && lastOfTopic ? (topicTest ? `/learn/${slug}/test/${current.topic_id}` : null) : upcoming ? `/learn/${slug}/lesson/${upcoming.id}` : null;

  return <StudentShell><div className="ns-learning-layout"><LearningSidebar navigation={navigation} courseSlug={slug} currentLesson={id} /><article className="ns-lesson">
    <nav className="ns-breadcrumb"><Link href={`/learn/${slug}`}>{navigation.title}</Link><span>›</span><span>{detail.topic_title}</span></nav>
    <h1>{detail.title}</h1>
    <p className="ns-lesson-meta">{detail.duration_minutes} daqiqa · {detail.kind === 'VIDEO' ? 'Video dars' : 'Matnli dars'}</p>
    {detail.kind === 'VIDEO' ? <>
      <VideoPlayer url={detail.video_url} title={detail.title} {...(watermark ? { watermark } : {})} />
      {watermark ? <p className="ns-video-note">Bu dars sizning hisobingizga bog‘langan. Video ustidagi belgi tarqatilgan nusxani aniqlash uchun qo‘yiladi.</p> : null}
    </> : null}
    {detail.content ? <section className="ns-lesson-content"><h2>Dars haqida</h2><p>{detail.content}</p>{detail.material_url ? <a href={detail.material_url} target="_blank" rel="noreferrer">Qo‘shimcha materialni ochish ↗</a> : null}</section> : null}
    {practice ? <section className="ns-practice" id="practice">
      <Badge tone={practiceDone ? 'success' : 'brand'}>{practiceDone ? 'Bajarildi' : 'Amaliy topshiriq'}</Badge>
      <h2>Bilimingizni amalda sinang</h2>
      <p>{practice.instructions}</p>
      {practice.example ? <pre>{practice.example}</pre> : null}
      {practice.resource_url ? <a href={practice.resource_url} target="_blank" rel="noreferrer">Manbani ochish ↗</a> : null}
      <Button variant={practiceDone ? 'secondary' : 'primary'} loading={busy === 'practice'} disabled={practiceDone} onClick={() => finish('practice')}>{practiceDone ? 'Bajarilgan ✓' : 'Topshiriqni bajardim'}</Button>
    </section> : null}
    {message ? <p className="ns-save-message" role="status">{message}</p> : null}
    <footer className="ns-lesson-actions">
      {previous ? <Link className="ns-link-button ns-link-button--secondary" href={`/learn/${slug}/lesson/${previous.id}`}>← Oldingi dars</Link> : <Link className="ns-link-button ns-link-button--secondary" href={`/learn/${slug}`}>← Kurs rejasi</Link>}
      <Button loading={busy === 'lesson'} disabled={complete} onClick={() => finish('lesson')}>{complete ? 'Dars tugallangan ✓' : 'Darsni tugatdim'}</Button>
      {nextHref ? <Link className="ns-link-button ns-link-button--secondary" href={nextHref}>{lastOfTopic ? 'Mavzu testi →' : 'Keyingi dars →'}</Link> : null}
    </footer>
  </article></div></StudentShell>;
}

/* ---------------------------------- test ---------------------------------- */

type TestBundle = { navigation: LearningNavigation; test: TopicTest };

export function TestScreen({ slug, topicId }: { slug: string; topicId: string }) {
  const resource = useResource(
    useCallback(async (): Promise<TestBundle> => {
      const [navigation, test] = await Promise.all([api.learning(slug), api.test(topicId)]);
      return { navigation, test };
    }, [slug, topicId]),
    useCallback((): TestBundle => ({ navigation: learningNavigation, test: topicTestFixture }), []),
  );

  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ score: number; result: 'PASSED' | 'FAILED' } | null>(null);

  async function submit() {
    const test = resource.data?.test;
    if (!test) return;
    setBusy(true); setError('');
    try {
      const payload = test.questions.flatMap(question => answers[question.id] ? [{ question_id: question.id, option_id: answers[question.id]! }] : []);
      const correctFirst = answers[test.questions[0]?.id ?? ''] === test.questions[0]?.options[0]?.id;
      const value = useMockData
        ? await simulateMutation({ score: correctFirst ? 80 : 40, result: (correctFirst ? 'PASSED' : 'FAILED') as 'PASSED' | 'FAILED' })
        : await api.submitTest(topicId, payload);
      setResult(value);
      resource.retry();
    } catch (reason) { setError(readApiError(reason, 'Javoblarni yuborib bo‘lmadi.')); }
    finally { setBusy(false); }
  }

  if (resource.loading) return <StudentShell><RouteLoading /></StudentShell>;
  if (resource.error || !resource.data) return <StudentShell><ErrorState title="Testni ochib bo‘lmadi" description={resource.error || undefined} onRetry={resource.retry} /></StudentShell>;

  const { navigation, test } = resource.data;
  const question = test.questions[index];
  const answered = Object.keys(answers).length;

  if (!test.available && !result) return <StudentShell><div className="ns-learning-layout"><LearningSidebar navigation={navigation} courseSlug={slug} /><main className="ns-test-card">
    <span className="ns-state__icon" aria-hidden="true">◌</span>
    <h1>Test hali yopiq</h1>
    <p>Avval mavzudagi barcha majburiy darslarni tugating. Hozir {test.completed_required_lessons}/{test.required_lessons} dars bajarilgan.</p>
    <ProgressBar value={test.required_lessons ? Math.round(test.completed_required_lessons / test.required_lessons * 100) : 0} label="Darslar holati" />
    <Link className="ns-link-button" href={`/learn/${slug}`}>Kurs rejasiga qaytish</Link>
  </main></div></StudentShell>;

  if (result) {
    const correct = Math.round(test.questions.length * result.score / 100);
    return <StudentShell><div className="ns-learning-layout"><LearningSidebar navigation={navigation} courseSlug={slug} /><main className="ns-test-result" data-result={result.result.toLowerCase()}>
      <span className="ns-result-ring">{result.score}%</span>
      <Badge tone={result.result === 'PASSED' ? 'success' : 'danger'}>{result.result === 'PASSED' ? 'Testdan o‘tdingiz' : 'Yetarli ball to‘planmadi'}</Badge>
      <h1>{result.result === 'PASSED' ? 'Ajoyib natija! Keyingi mavzu ochildi.' : 'Yana bir bor urinib ko‘ring'}</h1>
      <p>O‘tish bali {test.passing_score}%. Natija server tomonidan hisoblanadi va saqlanadi.</p>
      <div className="ns-result-stats"><span><strong>{test.questions.length}</strong><small>Savollar</small></span><span><strong>{correct}</strong><small>To‘g‘ri</small></span><span><strong>{test.questions.length - correct}</strong><small>Xato</small></span></div>
      {result.result === 'PASSED'
        ? <Link className="ns-link-button" href={`/learn/${slug}`}>Keyingi mavzuga o‘tish</Link>
        : <><Button onClick={() => { setResult(null); setAnswers({}); setIndex(0); }}>Qayta topshirish</Button><Link className="ns-link-button ns-link-button--secondary" href={`/learn/${slug}`}>Darslarni qayta ko‘rish</Link></>}
    </main></div></StudentShell>;
  }

  if (test.questions.length === 0) return <StudentShell><div className="ns-learning-layout"><LearningSidebar navigation={navigation} courseSlug={slug} /><main className="ns-test-card">
    <span className="ns-state__icon" aria-hidden="true">◌</span>
    <h1>Testda hali savol yo‘q</h1>
    <p>Bu mavzu testiga savollar qo‘shilmagan. Admin savollarni qo‘shgach test ochiladi.</p>
    <Link className="ns-link-button" href={`/learn/${slug}`}>Kurs rejasiga qaytish</Link>
  </main></div></StudentShell>;

  return <StudentShell><div className="ns-learning-layout"><LearningSidebar navigation={navigation} courseSlug={slug} /><main className="ns-test-taking">
    <header><div><p className="ns-eyebrow">Mavzu testi</p><h1>{navigation.modules.flatMap(module => module.topics).find(topic => topic.id === topicId)?.title ?? 'Test'}</h1></div><strong>{index + 1}/{test.questions.length}</strong></header>
    <ProgressBar value={Math.round((index + 1) / test.questions.length * 100)} label="Test jarayoni" />
    {question ? <section className="ns-question"><h2>{question.text}</h2><div>{question.options.map(option => <Radio key={option.id} id={option.id} name={question.id} checked={answers[question.id] === option.id} onChange={() => setAnswers(value => ({ ...value, [question.id]: option.id }))} label={option.text} />)}</div></section> : null}
    <footer>
      <Button variant="secondary" disabled={index === 0} onClick={() => setIndex(value => value - 1)}>← Oldingi</Button>
      {index < test.questions.length - 1
        ? <Button disabled={!question || !answers[question.id]} onClick={() => setIndex(value => value + 1)}>Keyingi →</Button>
        : <Button loading={busy} disabled={answered < test.questions.length} onClick={submit}>Testni yakunlash</Button>}
    </footer>
    {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    <p className="ns-test-hint">Javoblar serverga yuboriladi. Ballni brauzer belgilamaydi.</p>
  </main></div></StudentShell>;
}

/* --------------------------------- profile -------------------------------- */

export function ProfileScreen() {
  const { user, loading } = useCurrentUser();
  const [devices, setDevices] = useState<DeviceChoice[] | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [referral, setReferral] = useState<ReferralSummary | null>(null);
  const [referralError, setReferralError] = useState('');
  const [copied, setCopied] = useState(false);
  const [origin, setOrigin] = useState('');

  const loadDevices = useCallback(async () => {
    try { setDevices(await api.devices()); }
    catch (reason) { setError(readApiError(reason, 'Qurilmalarni yuklab bo‘lmadi.')); setDevices([]); }
  }, []);

  useEffect(() => { void loadDevices(); }, [loadDevices]);
  useEffect(() => { setOrigin(window.location.origin); }, []);
  useEffect(() => {
    let live = true;
    void api.myReferral()
      .then(value => { if (live) setReferral(value); })
      .catch(reason => { if (live) setReferralError(readApiError(reason, 'Taklif ma’lumotini yuklab bo‘lmadi.')); });
    return () => { live = false; };
  }, []);

  async function copyReferral() {
    if (!referral) return;
    setReferralError('');
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${referral.referral_path}`);
      setCopied(true);
    } catch (reason) {
      setReferralError(readApiError(reason, 'Havolani nusxalab bo‘lmadi.'));
    }
  }

  async function release(id: string) {
    setBusy(id); setError('');
    try { await api.releaseDevice(id); await loadDevices(); }
    catch (reason) { setError(readApiError(reason, 'Qurilmani chiqarib bo‘lmadi.')); }
    finally { setBusy(''); }
  }

  if (loading) return <StudentShell><RouteLoading /></StudentShell>;

  return <StudentShell><div className="ns-profile-wrap">
    <header><p className="ns-eyebrow">Hisob</p><h1>Profil</h1><p>Hisobingiz ma’lumotlari va faol qurilmalar.</p></header>

    <div className="ns-profile-form">
      <div className="ns-profile-avatar">{(user?.first_name.charAt(0) ?? '') + (user?.last_name.charAt(0) ?? '') || 'N'}</div>
      <div className="ns-form-grid">
        <Input id="first-name" label="Ism" value={user?.first_name || '—'} readOnly disabled />
        <Input id="last-name" label="Familiya" value={user?.last_name || '—'} readOnly disabled />
        <Input id="account-email" label="Email" value={user?.email ?? '—'} readOnly disabled hint="Kirish uchun ishlatiladi." />
        <Input id="account-role" label="Hisob turi" value={roleLabel(user)} readOnly disabled />
      </div>
      <p className="ns-form-note">
        Ism, email yoki rolni o‘zgartirish uchun administratorga murojaat qiling. Parolni
        unutgan bo‘lsangiz, chiqib <Link href="/forgot-password">parolni tiklash</Link> orqali
        yangilaysiz.
      </p>
    </div>

    <section className="ns-referral-card">
      <header><div><p className="ns-eyebrow">Taklif dasturi</p><h2>Do‘stlarni taklif qiling</h2></div>{referral?.applied_discount_percent ? <Badge tone="success">Sizga {referral.applied_discount_percent}% chegirma</Badge> : referral?.discount_percent ? <Badge tone="success">Taklifga {referral.discount_percent}% chegirma</Badge> : null}</header>
      {referralError ? <p className="ns-field__error" role="alert">{referralError}</p> : null}
      {!referral ? <p className="ns-muted">Yuklanmoqda…</p> : <>
        <p>Sizning doimiy kodingiz <strong>{referral.referral_code}</strong>. Havola orqali yangi hisob ochgan odam shu taklifga bir marta bog‘lanadi.</p>
        <div className="ns-referral-link"><code>{`${origin}${referral.referral_path}`}</code><Button size="sm" variant="secondary" onClick={() => void copyReferral()}>{copied ? 'Nusxalandi ✓' : 'Nusxalash'}</Button></div>
        <dl className="ns-referral-metrics"><div><dt>Taklif bilan kirgan</dt><dd>{referral.referred_count}</dd></div><div><dt>Kursga ruxsat olgan</dt><dd>{referral.referred_with_access}</dd></div></dl>
        <p className="ns-form-note">Chegirma miqdorini administrator belgilaydi va u yangi ro‘yxatdan o‘tuvchiga saqlanadi.</p>
      </>}
    </section>

    <section className="ns-device-panel">
      <header><h2>Faol qurilmalar</h2><p>Bitta hisobda ko‘pi bilan 2 ta qurilma bo‘lishi mumkin. Notanish qurilmani darhol chiqarib yuboring.</p></header>
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
      {devices === null ? <p className="ns-muted">Yuklanmoqda…</p>
        : devices.length === 0 ? <p className="ns-muted">Faol qurilma topilmadi.</p>
        : <ul className="ns-access-list">
            {devices.map(item => <li key={item.id}>
              <span>
                {item.name}{item.current ? ' · shu qurilma' : ''}
                <small>Oxirgi faollik: {new Date(item.last_seen_at).toLocaleString('uz-UZ')}</small>
              </span>
              {item.current
                ? <span className="ns-muted">—</span>
                : <button type="button" className="ns-table-link" disabled={busy === item.id} onClick={() => void release(item.id)}>Chiqarib yuborish</button>}
            </li>)}
          </ul>}
    </section>
  </div></StudentShell>;
}
