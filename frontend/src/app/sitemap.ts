import type { MetadataRoute } from 'next';

export const dynamic = 'force-dynamic';

type CoursePage = { count: number; results: Array<{ slug: string }> };

async function publishedCourseSlugs(): Promise<string[]> {
  const backend = (process.env.BACKEND_INTERNAL_URL || 'http://localhost:8000').replace(/\/$/, '');
  const slugs: string[] = [];
  try {
    for (let page = 1; page <= 100; page += 1) {
      const response = await fetch(`${backend}/api/v1/courses?page_size=48&page=${page}`, { cache: 'no-store' });
      if (!response.ok) return [];
      const payload = await response.json() as CoursePage;
      slugs.push(...payload.results.map(course => course.slug));
      if (slugs.length >= payload.count || payload.results.length === 0) break;
    }
  } catch {
    return [];
  }
  return slugs;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = (process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000').replace(/\/$/, '');
  const courses = await publishedCourseSlugs();
  const now = new Date();
  return ['', '/courses', '/about', '/contact', '/privacy', '/terms', ...courses.map(slug => `/courses/${slug}`)]
    .map(path => ({ url: `${base}${path}`, lastModified: now }));
}
