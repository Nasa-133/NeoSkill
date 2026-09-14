'use client';

import Link from 'next/link';
import { useCallback } from 'react';

import { CourseCard, InstructorCard, TestimonialCard } from '@/components/domain/Public';
import { PublicShell } from '@/components/layout/Shells';
import { ErrorState, RouteLoading } from '@/components/ui';
import { api } from '@/lib/api';
import {
  courses as fixtureCourses,
  instructors as fixtureInstructors,
  testimonials as fixtureTestimonials,
} from '@/lib/fixtures';
import type { HomeContent } from '@/lib/types';
import { useResource } from '@/lib/use-resource';

const fixtureHome: HomeContent = {
  courses: fixtureCourses,
  categories: Array.from(
    new Map(fixtureCourses.flatMap(course => course.category ? [[course.category.slug, course.category] as const] : [])).values(),
  ),
  instructors: fixtureInstructors,
  testimonials: fixtureTestimonials,
};

const platformFaqs = [
  ['Kurslarni qanday boshlayman?', 'Kursni tanlang va email orqali hisob oching. Bepul kurs darhol ochiladi.'],
  ['Pullik kursga qanday yozilaman?', 'Ariza yuborasiz. Admin tasdiqlagach kurs Kurslarim bo‘limida paydo bo‘ladi.'],
  ['Progress saqlanadimi?', 'Ha, tugallangan dars, amaliyot va test natijalari serverda saqlanadi.'],
];

export function HomeScreen() {
  const resource = useResource(useCallback(() => api.home(), []), useCallback(() => fixtureHome, []));

  if (resource.loading) return <PublicShell><RouteLoading /></PublicShell>;
  if (resource.error || !resource.data) {
    return <PublicShell><main className="ns-container ns-section"><ErrorState description={resource.error} onRetry={resource.retry} /></main></PublicShell>;
  }

  const { courses, categories, instructors, testimonials } = resource.data;
  return <PublicShell>
    <section className="ns-hero">
      <div className="ns-container ns-hero__grid">
        <div>
          <p className="ns-eyebrow">Kelajagingizni bugun boshlang</p>
          <h1>Bilimdan <span>natijagacha</span> bo‘lgan yo‘l</h1>
          <p className="ns-hero__lead">NeoSkill sizga zamonaviy kasblarni tartibli darslar, amaliy mashqlar va bilimni mustahkamlovchi testlar bilan o‘rgatadi.</p>
          <div className="ns-hero__actions"><Link className="ns-link-button" href="/courses">Kurslarni ko‘rish</Link><Link className="ns-link-button ns-link-button--secondary" href="/register">Bepul boshlash</Link></div>
          <div className="ns-hero__trust"><span><strong>Amaliy</strong><small>o‘quv dasturi</small></span><span><strong>Qulay</strong><small>o‘z tezligingizda</small></span><span><strong>Izchil</strong><small>saqlanuvchi progress</small></span></div>
        </div>
        <div className="ns-hero-art" aria-label="NeoSkill o‘quv jarayoni tasviri"><div className="ns-hero-art__screen"><span>O‘qish jarayoni</span><strong>45%</strong><i><b /></i><ul><li data-done="true">Kursni tanlash</li><li data-done="true">Darsni o‘rganish</li><li>Amaliy topshiriq</li></ul></div><span className="ns-hero-art__badge">✓ Natija saqlandi</span></div>
      </div>
    </section>

    <section className="ns-section">
      <div className="ns-container">
        <header className="ns-section-heading"><div><p className="ns-eyebrow">Ommabop kurslar</p><h2>O‘rganishni bugun boshlang</h2></div><Link href="/courses">Barcha kurslar →</Link></header>
        {courses.length ? <div className="ns-course-grid">{courses.slice(0, 3).map(course => <CourseCard key={course.id} course={course} />)}</div> : <p className="ns-muted">Nashr qilingan kurslar tez orada shu yerda paydo bo‘ladi.</p>}
      </div>
    </section>

    <section className="ns-section ns-section--muted">
      <div className="ns-container"><header className="ns-section-heading"><div><p className="ns-eyebrow">Yo‘nalishlar</p><h2>Kategoriyalar</h2></div></header>
        {categories.length ? <div className="ns-category-grid">{categories.map(category => <Link key={category.id} href={`/courses?category=${encodeURIComponent(category.slug)}`}>{category.name}</Link>)}</div> : <p className="ns-muted">Kategoriyalar kurslar nashr qilingach ko‘rinadi.</p>}
      </div>
    </section>

    <section className="ns-section">
      <div className="ns-container"><header className="ns-centered-heading"><p className="ns-eyebrow">Nega NeoSkill?</p><h2>Natijaga olib boradigan o‘quv muhiti</h2><p>Har bir imkoniyat bitta maqsadga xizmat qiladi: bilimni amaliy ko‘nikmaga aylantirish.</p></header><div className="ns-feature-grid">{[['01','Tartibli yo‘l','Darslar mavzu bo‘yicha ketma-ket ochiladi.'],['02','Amaliy topshiriqlar','Har mavzuni kichik vazifalar bilan mustahkamlaysiz.'],['03','Aniq natija','Test va progress qayerga yetganingizni ko‘rsatadi.'],['04','Doimiy kirish','O‘qishni faol qurilmalaringizda davom ettirasiz.']].map(item => <article key={item[0]}><span>{item[0]}</span><h3>{item[1]}</h3><p>{item[2]}</p></article>)}</div></div>
    </section>

    <section className="ns-section ns-section--muted"><div className="ns-container ns-how"><div><p className="ns-eyebrow">Qanday ishlaydi?</p><h2>To‘rt sodda qadamda yangi ko‘nikma</h2><p>Kursni tanlang, o‘rganing, amalda bajaring va test orqali keyingi bosqichni oching.</p><Link className="ns-link-button ns-link-button--secondary" href="/courses">O‘rganishni boshlash</Link></div><ol>{['Maqsadingizga mos kursni tanlang','Darslarni ketma-ket o‘rganing','Amaliy vazifani bajaring','Testdan o‘tib davom eting'].map((text,index) => <li key={text}><span>{index + 1}</span><strong>{text}</strong></li>)}</ol></div></section>

    <section className="ns-section"><div className="ns-container"><header className="ns-centered-heading"><p className="ns-eyebrow">Ustozlar</p><h2>Amaliy tajribaga ega mutaxassislar</h2></header>{instructors.length ? <div className="ns-instructor-grid">{instructors.map(item => <InstructorCard key={item.slug} instructor={item} />)}</div> : <p className="ns-muted ns-centered-copy">Ustozlar nashr qilingan kurslar bilan birga ko‘rinadi.</p>}</div></section>

    <section className="ns-section ns-section--muted"><div className="ns-container"><header className="ns-centered-heading"><p className="ns-eyebrow">Talabalar fikri</p><h2>NeoSkill bilan o‘rganayotganlar</h2></header>{testimonials.length ? <div className="ns-testimonial-grid">{testimonials.map(item => <TestimonialCard key={item.id} testimonial={item} />)}</div> : <p className="ns-muted ns-centered-copy">Tasdiqlangan talabalar fikri tez orada shu yerda ko‘rinadi.</p>}</div></section>

    <section className="ns-section ns-faq-section"><div className="ns-container ns-faq-summary"><div><p className="ns-eyebrow">Savollar</p><h2>Ko‘p so‘raladigan savollar</h2><p>Javob topilmadimi? Qo‘llab-quvvatlash jamoasi sizga yordam beradi.</p><Link href="/contact">Bog‘lanish →</Link></div><div className="ns-faq-list">{platformFaqs.map((item,index) => <details key={item[0]} open={index === 0}><summary>{item[0]}<span aria-hidden="true">+</span></summary><p>{item[1]}</p></details>)}</div></div></section>
    <section className="ns-final-cta"><div className="ns-container"><h2>Yangi ko‘nikmani bugun boshlang</h2><p>Sizga mos kursni tanlang va birinchi amaliy natijangizga qadam qo‘ying.</p><Link className="ns-link-button ns-link-button--secondary" href="/courses">Kurslarni ko‘rish</Link></div></section>
  </PublicShell>;
}
