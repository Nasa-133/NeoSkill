'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { api, readApiError, useMockData } from '@/lib/api';
import { useCurrentUser } from '@/lib/session';
import { simulateMutation } from '@/lib/use-resource';
import type { Course, CourseDetail, EnrollmentState, FAQ, Instructor, Testimonial } from '@/lib/types';
import { Badge, Button, Card } from '@/components/ui';

const levelNames = { BEGINNER: 'Boshlang‘ich', INTERMEDIATE: 'O‘rta', ADVANCED: 'Yuqori' } as const;
export function levelLabel(level: Course['level']) { return levelNames[level]; }
export function formatDuration(minutes: number) { const hours = Math.floor(minutes / 60); return hours ? `${hours} soat` : `${minutes} daqiqa`; }
export function formatPrice(course: Pick<Course, 'is_free' | 'price'>) { return course.is_free ? 'Bepul' : `${new Intl.NumberFormat('uz-UZ').format(Number(course.price))} so‘m`; }

export function CourseVisual({ title, compact = false, imageUrl }: { title: string; compact?: boolean; imageUrl?: string }) {
  const [broken, setBroken] = useState(false);
  // next/image is deliberately avoided: a cover can be any admin-entered URL, and the
  // optimizer would turn this app into an open image proxy for arbitrary hosts.
  // eslint-disable-next-line @next/next/no-img-element
  if (imageUrl && !broken) return <div className="ns-course-visual ns-course-visual--photo" data-compact={compact || undefined}><img src={imageUrl} alt={`${title} kursi muqovasi`} onError={() => setBroken(true)} /></div>;
  return <div className="ns-course-visual" data-compact={compact || undefined} role="img" aria-label={`${title} kursi muqovasi`}><span>NeoSkill</span><strong>{title.split(' ').slice(0, 3).join(' ')}</strong><i aria-hidden="true">N</i></div>;
}

export function CourseCard({ course }: { course: Course }) {
  return <article className="ns-course-card"><CourseVisual title={course.title} imageUrl={course.image_url} /><div className="ns-course-card__body"><div className="ns-course-card__tags"><Badge tone="brand">{course.category?.name ?? 'Kurs'}</Badge><span>{levelNames[course.level]}</span></div><h3><Link href={`/courses/${course.slug}`}>{course.title}</Link></h3><p>{course.short_description}</p><div className="ns-course-meta"><span>{formatDuration(course.duration_minutes)}</span><span>{course.language}</span></div><div className="ns-course-card__foot"><strong>{formatPrice(course)}</strong><Link href={`/courses/${course.slug}`} aria-label={`${course.title} — batafsil ma’lumot`}>Batafsil <span aria-hidden="true">→</span></Link></div></div></article>;
}

export function InstructorCard({ instructor }: { instructor: Instructor }) {
  const initials = instructor.name.split(' ').map(value => value[0]).join('').slice(0, 2);
  return <Card className="ns-instructor-card">
    {instructor.photo_url
      ? <span className="ns-person-visual ns-person-visual--photo">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={instructor.photo_url} alt={instructor.name} />
        </span>
      : <span className="ns-person-visual" aria-hidden="true">{initials}</span>}
    <div><h3>{instructor.name}</h3><strong>{instructor.title}</strong><p>{instructor.experience}</p></div>
  </Card>;
}
export function TestimonialCard({ testimonial }: { testimonial: Testimonial }) { return <Card className="ns-testimonial"><span aria-hidden="true">“</span><blockquote>{testimonial.text}</blockquote><footer><strong>{testimonial.name}</strong><small>{testimonial.profession}</small></footer></Card>; }
export function FAQList({ items }: { items: FAQ[] }) { return <div className="ns-faq-list">{items.map((item, index) => <details key={item.id} open={index === 0}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div>; }

const ctaLabels: Record<EnrollmentState, string> = { FREE_START: 'Bepul boshlash', PAID_REQUEST: 'Kursga yozilish', PENDING: 'Ariza ko‘rib chiqilmoqda', ACTIVE: 'O‘qishni davom ettirish', REJECTED: 'Qayta ariza yuborish' };
export function EnrollmentCTA({ course, initialState }: { course: CourseDetail; initialState: EnrollmentState }) {
  const router = useRouter(); const { user, loading: sessionLoading } = useCurrentUser(); const [state, setState] = useState(initialState); const [loading, setLoading] = useState(false); const [message, setMessage] = useState('');
  const loginPath = `/login?next=${encodeURIComponent(`/courses/${course.slug}`)}`;
  async function act() { if (state === 'PENDING') return; if (state === 'ACTIVE') { router.push(`/learn/${course.slug}`); return; } if (!user) { router.push(loginPath); return; } setLoading(true); setMessage(''); try { if (useMockData) { await simulateMutation(null); setState(course.is_free ? 'ACTIVE' : 'PENDING'); setMessage(course.is_free ? 'Kurs Kurslarim bo‘limiga qo‘shildi.' : 'Arizangiz yuborildi. Admin javobini shu sahifada ko‘rasiz.'); } else if (course.is_free) { const result = await api.enrollFree(course.slug); router.push(result.next_path); } else { await api.requestEnrollment(course.slug, ''); setState('PENDING'); setMessage('Arizangiz yuborildi.'); } } catch (reason) { const error = reason as { status?: number }; if (error.status === 401 || error.status === 403) router.push(loginPath); else setMessage(readApiError(reason, 'Amalni bajarib bo‘lmadi.')); } finally { setLoading(false); } }
  const guest = !sessionLoading && !user && state !== 'ACTIVE';
  const label = guest ? (course.is_free ? 'Kirish va bepul boshlash' : 'Kirish va ariza yuborish') : ctaLabels[state];
  const discounted = !course.is_free && course.referral_discount_percent > 0 && course.discounted_price;
  return <div className="ns-enrollment-cta" id="enroll"><div><small>Kurs narxi</small>{discounted ? <><s>{formatPrice(course)}</s><strong>{new Intl.NumberFormat('uz-UZ').format(Number(course.discounted_price))} so‘m</strong><Badge tone="success">Referral −{course.referral_discount_percent}%</Badge></> : <strong>{formatPrice(course)}</strong>}</div><Button disabled={state === 'PENDING'} loading={loading || sessionLoading} onClick={act} size="lg">{label}</Button>{message ? <p role="status">{message}</p> : null}<ul><li>Natijalar barcha qurilmalarda saqlanadi</li><li>Amaliy mashqlar va mavzu testlari</li><li>O‘z tezligingizda o‘rganish</li></ul></div>;
}

export function Curriculum({ modules, slug }: { modules: CourseDetail['modules']; slug: string }) { return <div className="ns-curriculum">{modules.map((module, moduleIndex) => <details key={module.id} open={moduleIndex === 0}><summary><span><small>{module.position}-modul</small><strong>{module.title}</strong></span><span>{module.topics.reduce((sum, topic) => sum + topic.lessons.length, 0)} dars</span></summary><div>{module.topics.map(topic => <section key={topic.id}><h3>{topic.title}</h3>{topic.lessons.map(lesson => <div className="ns-curriculum-lesson" key={lesson.id}><span aria-hidden="true">{lesson.free_preview ? '▶' : '◌'}</span><span>{lesson.title}<small>{formatDuration(lesson.duration_minutes)}</small></span>{lesson.free_preview ? <Link href={`/preview/${lesson.id}?course=${slug}`}>Bepul ko‘rish</Link> : <Badge>Yopiq</Badge>}</div>)}</section>)}</div></details>)}</div>; }
