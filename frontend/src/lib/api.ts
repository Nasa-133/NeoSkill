import type { AdminAccount, AdminAttemptStat, AdminCourseAccess, AdminEnrollmentRequest, AdminEnrollmentStat, AdminModuleNode, AdminReferralDetail, AdminStats, ApiErrorBody, Category, Course, CourseDetail, DeviceChoice, HomeContent, Instructor, LearningNavigation, LessonDetail, LessonPreview, MyCourse, PlatformSettings, Practice, PublicSettings, ReferralOffer, ReferralSummary, Testimonial, TopicTest, User, UUID } from './types';

// Relative by default: requests go to this app's origin and are proxied to the API.
// An unset *or empty* NEXT_PUBLIC_API_URL must fall back, so this uses `||`, not `??`.
const API_URL = (process.env.NEXT_PUBLIC_API_URL?.trim() || '/api/v1').replace(/\/$/, '');
export const useMockData = process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock' || (process.env.NODE_ENV === 'development' && process.env.NEXT_PUBLIC_DATA_SOURCE !== 'api');

export class ApiError extends Error { constructor(public status: number, public body: ApiErrorBody) { super(body.detail ?? 'So‘rov bajarilmadi.'); } }

function cookie(name: string) { if (typeof document === 'undefined') return ''; return document.cookie.split('; ').find(value => value.startsWith(`${name}=`))?.split('=')[1] ?? ''; }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers); headers.set('Accept', 'application/json');
  if (init?.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (init?.method && init.method !== 'GET') headers.set('X-CSRFToken', decodeURIComponent(cookie('csrftoken')));
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include', cache: 'no-store' });
  if (!response.ok) { let body: ApiErrorBody; try { body = await response.json() as ApiErrorBody; } catch { body = { detail: 'Server noto‘g‘ri javob qaytardi.' }; } throw new ApiError(response.status, body); }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
async function csrf() { await request<{ csrf: string }>('/auth/csrf'); }
async function mutate<T>(path: string, method: 'POST' | 'PATCH' | 'PUT' | 'DELETE', payload?: unknown) { await csrf(); return request<T>(path, { method, ...(payload === undefined ? {} : { body: JSON.stringify(payload) }) }); }

type Page<T> = { count: number; next: string | null; results: T[] };
function apiPath(url: string) {
  const parsed = new URL(url, 'http://neoskill.local');
  return `${parsed.pathname.replace(/^\/api\/v1/, '')}${parsed.search}`;
}
async function allPages<T>(path: string): Promise<T[]> {
  const first = await request<T[] | Page<T>>(path);
  if (Array.isArray(first)) return first;
  const items = [...first.results];
  let next = first.next;
  const visited = new Set<string>();
  while (next) {
    if (visited.size >= 100) throw new Error('API pagination limit exceeded.');
    const pathToNext = apiPath(next);
    if (visited.has(pathToNext)) throw new Error('API pagination loop detected.');
    visited.add(pathToNext);
    const page = await request<Page<T>>(pathToNext);
    items.push(...page.results);
    next = page.next;
  }
  return items;
}

export const api = {
  publicSettings: () => request<PublicSettings>('/settings/public'),
  adminSettings: () => request<PlatformSettings>('/admin/settings'),
  saveSettings: (payload: Partial<PlatformSettings> & { smtp_password?: string }) => mutate<PlatformSettings>('/admin/settings', 'PATCH', payload),
  testEmail: (email: string) => mutate<{ detail: string }>('/admin/settings/test-email', 'POST', { email }),
  // The public catalog is paginated; every other list endpoint returns a plain array.
  courses: (params = '') => allPages<Course>(`/courses${params}`),
  home: async (): Promise<HomeContent> => {
    const [courses, categories, instructors, testimonials] = await Promise.all([
      allPages<Course>('/courses'),
      request<Category[]>('/categories'),
      request<Instructor[]>('/instructors'),
      request<Testimonial[]>('/testimonials'),
    ]);
    return { courses, categories, instructors, testimonials };
  },
  course: (slug: string) => request<CourseDetail>(`/courses/${slug}`),
  lessonPreview: (id: UUID) => request<LessonPreview>(`/lessons/${id}/preview`),
  session: () => request<{ user: User }>('/auth/session'),
  register: (payload: { email: string; password: string; first_name: string; last_name: string; device_id: string; device_name: string; referral_code?: string }) => mutate<{ user: User; first_login: boolean }>('/auth/register', 'POST', payload),
  login: (payload: { email: string; password: string; device_id: string; device_name: string; revoke_device_session_id?: string }) => mutate<{ user: User; first_login: boolean }>('/auth/login', 'POST', payload),
  devices: () => request<DeviceChoice[]>('/auth/devices'),
  referralOffer: (code: string) => request<ReferralOffer>(`/referrals/${encodeURIComponent(code)}`),
  myReferral: () => request<ReferralSummary>('/me/referral'),
  releaseDevice: (id: string) => mutate<void>(`/auth/devices?id=${id}`, 'DELETE'),
  requestPasswordReset: (email: string) => mutate<{ detail: string }>('/auth/password-reset', 'POST', { email }),
  confirmPasswordReset: (payload: { uid: string; token: string; password: string }) => mutate<{ detail: string }>('/auth/password-reset/confirm', 'POST', payload),
  adminAccounts: (params = '') => request<AdminAccount[]>(`/admin/users${params}`),
  adminAccountPassword: (id: UUID, password: string) => mutate<void>(`/admin/users/${id}/password`, 'POST', { password }),
  adminAccountCourses: (id: UUID) => request<AdminCourseAccess[]>(`/admin/users/${id}/courses`),
  adminGrantCourse: (id: UUID, courseId: UUID) => mutate<void>(`/admin/users/${id}/courses`, 'POST', { course_id: courseId }),
  adminRevokeCourse: (id: UUID, courseId: UUID) => mutate<void>(`/admin/users/${id}/courses?course_id=${courseId}`, 'DELETE'),
  logout: () => mutate<void>('/auth/logout', 'POST'),
  enrollFree: (slug: string) => mutate<{ next_path: string }>(`/courses/${slug}/enroll/free`, 'POST', {}),
  requestEnrollment: (slug: string, note: string) => mutate<{ next_path: string; status: string }>(`/courses/${slug}/enrollment-requests`, 'POST', { note }),
  myCourses: () => request<MyCourse[]>('/me/courses'), continueCourse: (slug: string) => request<{ next_path: string }>(`/learning/courses/${slug}/continue`),
  learning: (slug: string) => request<LearningNavigation>(`/learning/courses/${slug}`), lesson: (id: UUID) => request<LessonDetail>(`/learning/lessons/${id}`), completeLesson: (id: UUID) => mutate<{ completed_at: string }>(`/learning/lessons/${id}/complete`, 'POST', {}),
  practice: (id: UUID) => request<Practice>(`/learning/topics/${id}/practice`), completePractice: (id: UUID) => mutate<{ completed_at: string }>(`/learning/topics/${id}/practice`, 'POST', {}),
  test: (id: UUID) => request<TopicTest>(`/learning/topics/${id}/test`), submitTest: (id: UUID, answers: { question_id: UUID; option_id: UUID }[]) => mutate<{ attempt_id: UUID; score: number; result: 'PASSED' | 'FAILED'; completed_at: string }>(`/learning/topics/${id}/test`, 'POST', { answers }),
  async uploadImage(file: File) {
    await csrf();
    const body = new FormData(); body.append('file', file);
    return request<{ url: string; content_type: string }>('/admin/uploads/image', { method: 'POST', body });
  },
  adminStats: () => request<AdminStats>('/admin/stats'),
  adminEnrollmentStats: (params = '') => request<AdminEnrollmentStat[]>(`/admin/statistics/enrollments${params}`),
  adminAttemptStats: (params = '') => request<AdminAttemptStat[]>(`/admin/statistics/attempts${params}`),
  adminReferrals: (params = '') => request<ReferralSummary[]>(`/admin/referrals${params}`),
  adminReferral: (id: UUID) => request<AdminReferralDetail>(`/admin/referrals/${id}`),
  adminReferralDiscount: (id: UUID, discount_percent: number) => mutate<ReferralSummary>(`/admin/referrals/${id}`, 'PATCH', { discount_percent }),
  adminEnrollmentRequests: (status: string) => request<AdminEnrollmentRequest[]>(`/admin/enrollment-requests?status=${status}`),
  adminReviewEnrollment: (id: UUID, decision: 'approve' | 'reject') => mutate<AdminEnrollmentRequest>(`/admin/enrollment-requests/${id}/${decision}`, 'POST', {}),
  adminCurriculum: (courseId: UUID) => request<AdminModuleNode[]>(`/admin/courses/${courseId}/curriculum`),
  adminReorder: (path: string, ids: UUID[]) => mutate<void>(`/admin/${path}`, 'POST', { ids }),
  adminList: <T>(resource: string, params = '') => request<T[]>(`/admin/${resource}${params}`), adminGet: <T>(resource: string, id: UUID) => request<T>(`/admin/${resource}/${id}`), adminCreate: <T>(resource: string, payload: unknown) => mutate<T>(`/admin/${resource}`, 'POST', payload), adminUpdate: <T>(resource: string, id: UUID, payload: unknown) => mutate<T>(`/admin/${resource}/${id}`, 'PATCH', payload), adminDelete: (resource: string, id: UUID) => mutate<void>(`/admin/${resource}/${id}`, 'DELETE'), adminAction: <T>(path: string, payload: unknown = {}) => mutate<T>(`/admin/${path}`, 'POST', payload),
};


/**
 * Turns any failure into one readable line.
 * DRF answers validation errors as {field: [message]}, so a bare `error.message`
 * would only ever show the generic fallback and hide the real reason.
 */
export function readApiError(reason: unknown, fallback = 'Amalni bajarib bo‘lmadi.'): string {
  if (reason instanceof ApiError) {
    if (typeof reason.body.detail === 'string') return reason.body.detail;
    for (const [field, value] of Object.entries(reason.body)) {
      if (Array.isArray(value) && value.length) {
        const message = String(value[0]);
        return field === 'non_field_errors' ? message : `${field}: ${message}`;
      }
      if (typeof value === 'string' && field !== 'code') return value;
    }
  }
  if (reason instanceof TypeError) return fallback;
  return reason instanceof Error && reason.message ? reason.message : fallback;
}

export type DeviceLimitError = ApiError & { body: ApiErrorBody & { code: 'device_limit'; devices: DeviceChoice[] } };
export function isDeviceLimit(reason: unknown): reason is DeviceLimitError {
  return reason instanceof ApiError && reason.body.code === 'device_limit' && Array.isArray(reason.body.devices);
}
