'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { courses as fixtureCourses } from '@/lib/fixtures';
import { api, useMockData } from '@/lib/api';
import { useResource } from '@/lib/use-resource';
import { CourseCard } from '@/components/domain/Public';
import { PublicShell } from '@/components/layout/Shells';
import { EmptyState, ErrorState, Input, Select, Skeleton } from '@/components/ui';

export function CoursesScreen() {
  const params=useSearchParams(); const router=useRouter(); const pathname=usePathname(); const ui=useMockData ? params.get('ui') : null;
  const [search,setSearch]=useState(()=>params.get('q')??''); const [category,setCategory]=useState(()=>params.get('category')??''); const [level,setLevel]=useState(()=>params.get('level')??''); const [price,setPrice]=useState(()=>params.get('price')??'');
  const resource=useResource(useCallback(()=>api.courses(),[]),useCallback(()=>fixtureCourses,[]));

  // Keeps the filter state shareable and survivable across a reload without spamming history.
  useEffect(()=>{
    const next=new URLSearchParams(); if(ui)next.set('ui',ui);
    for(const [key,value] of [['q',search],['category',category],['level',level],['price',price]] as const) if(value)next.set(key,value);
    const query=next.toString(); const target=query?`${pathname}?${query}`:pathname;
    const timer=window.setTimeout(()=>router.replace(target,{scroll:false}),300);
    return ()=>window.clearTimeout(timer);
  },[search,category,level,price,ui,pathname,router]);

  const categories=useMemo(()=>Array.from(new Map((resource.data??[]).flatMap(item=>item.category?[[item.category.slug,item.category.name] as const]:[])).entries()),[resource.data]);
  const filtered=useMemo(()=>(resource.data??[]).filter(course => ui!=='empty' && (!search || `${course.title} ${course.short_description}`.toLowerCase().includes(search.toLowerCase())) && (!category || course.category?.slug === category) && (!level || course.level === level) && (!price || (price === 'free' ? course.is_free : !course.is_free))),[resource.data,search,category,level,price,ui]);
  const dirty=Boolean(search||category||level||price);
  const clear=useCallback(()=>{setSearch('');setCategory('');setLevel('');setPrice('')},[]);

  return <PublicShell><section className="ns-page-hero"><div className="ns-container"><p className="ns-eyebrow">Kurslar katalogi</p><h1>Kelajagingiz uchun kerakli ko‘nikmani tanlang</h1><p>Amaliy darslar, topshiriqlar va testlar bilan yangi yo‘nalishni izchil o‘rganing.</p></div></section><section className="ns-section"><div className="ns-container"><div className="ns-filters"><div className="ns-filter-search"><Input id="course-search" label="Kurs qidirish" placeholder="Masalan, Python" type="search" value={search} onChange={event => setSearch(event.target.value)} /></div><Select id="category" label="Kategoriya" value={category} onChange={event=>setCategory(event.target.value)}><option value="">Barchasi</option>{categories.map(([slug,name])=><option key={slug} value={slug}>{name}</option>)}</Select><Select id="level" label="Daraja" value={level} onChange={event=>setLevel(event.target.value)}><option value="">Barchasi</option><option value="BEGINNER">Boshlang‘ich</option><option value="INTERMEDIATE">O‘rta</option><option value="ADVANCED">Yuqori</option></Select><Select id="price" label="Narx" value={price} onChange={event=>setPrice(event.target.value)}><option value="">Barchasi</option><option value="free">Bepul</option><option value="paid">Pullik</option></Select></div>{(ui==='loading'||resource.loading)?<div className="ns-course-grid" aria-label="Kurslar yuklanmoqda">{[1,2,3].map(item=><Skeleton className="ns-course-skeleton" key={item}/>)}</div>:(ui==='error'||resource.error)?<ErrorState description={resource.error||undefined} onRetry={resource.retry}/>:<><div className="ns-results-head" aria-live="polite"><strong>{filtered.length} ta kurs topildi</strong>{dirty ? <button type="button" onClick={clear}>Filtrlarni tozalash</button> : null}</div>{filtered.length ? <div className="ns-course-grid">{filtered.map(course=><CourseCard key={course.id} course={course}/>)}</div> : <EmptyState title="Mos kurs topilmadi" description="Qidiruv so‘zini yoki filtrlarni o‘zgartirib ko‘ring." actionLabel={dirty?'Filtrlarni tozalash':undefined} onAction={dirty?clear:undefined} />}</>}</div></section></PublicShell>;
}
