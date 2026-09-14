import type { Metadata } from 'next';
import { CourseDetailScreen } from '@/components/screens/public/CourseDetailScreen';

type PageProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ state?: string }>;
};

type CourseMetadata = { title: string; short_description: string; image_url: string };

async function loadMetadata(slug: string): Promise<CourseMetadata | null> {
  const origin = (process.env.BACKEND_INTERNAL_URL || 'http://localhost:8000').replace(/\/$/, '');
  try {
    const response = await fetch(`${origin}/api/v1/courses/${encodeURIComponent(slug)}`, {
      next: { revalidate: 300 },
    });
    return response.ok ? await response.json() as CourseMetadata : null;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const course = await loadMetadata(slug);
  if (!course) return { title: 'Kurs haqida', alternates: { canonical: `/courses/${slug}` } };
  return {
    title: course.title,
    description: course.short_description,
    alternates: { canonical: `/courses/${slug}` },
    openGraph: {
      type: 'website', title: course.title, description: course.short_description,
      ...(course.image_url ? { images: [{ url: course.image_url, alt: course.title }] } : {}),
    },
  };
}

export default async function Page({ params, searchParams }: PageProps) {
  const [{ slug }, { state }] = await Promise.all([params, searchParams]);
  return <CourseDetailScreen slug={slug} state={state} />;
}
