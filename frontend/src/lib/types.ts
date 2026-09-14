export type UUID = string;

export interface PublicSettings {
  platform_name: string; footer_text: string; company_name: string; about_title: string;
  about_text: string; company_address: string; support_email: string; support_telegram: string;
  support_phone: string; working_hours: string;
}
export interface PlatformSettings extends PublicSettings {
  smtp_source: 'ENV' | 'ADMIN'; smtp_host: string; smtp_port: number; smtp_username: string;
  smtp_security: 'TLS' | 'SSL' | 'NONE'; smtp_from_email: string; smtp_password_set: boolean;
  updated_at: string | null;
}
export type EnrollmentState = 'FREE_START' | 'PAID_REQUEST' | 'PENDING' | 'ACTIVE' | 'REJECTED';

export interface Category { id: UUID; name: string; slug: string }
export interface Instructor { name: string; slug: string; title: string; photo_url: string; experience: string; bio: string; website_url?: string; social_links?: Record<string, string> }
export interface LessonSummary { id: UUID; title: string; position: number; kind: 'VIDEO' | 'TEXT'; duration_minutes: number; free_preview: boolean; access: 'PREVIEW' | 'LOCKED' }
export interface TopicSummary { id: UUID; title: string; position: number; lessons: LessonSummary[] }
export interface ModuleSummary { id: UUID; title: string; position: number; topics: TopicSummary[] }
export interface FAQ { id: UUID; question: string; answer: string; position: number }
export interface Course { id: UUID; title: string; slug: string; short_description: string; image_url: string; level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'; language: string; duration_minutes: number; is_free: boolean; price: string; category: Category | null; instructor: Instructor | null }
export interface CourseDetail extends Course { description: string; what_you_will_learn: string[]; audience: string[]; requirements: string[]; modules: ModuleSummary[]; faqs: FAQ[]; enrollment_state: EnrollmentState; referral_discount_percent: number; discounted_price: string | null }
export interface Testimonial { id: UUID; name: string; profession: string; text: string; active: boolean; position: number }
export interface HomeContent { courses: Course[]; categories: Category[]; instructors: Instructor[]; testimonials: Testimonial[] }
export interface User { id: UUID; email: string | null; first_name: string; last_name: string; role: 'STUDENT' | 'ADMIN' }
export interface ApiErrorBody { detail?: string; code?: string; [key: string]: unknown }

export interface CourseProgress { required_units: number; completed_units: number; percent: number; is_complete: boolean; current_lesson_id?: UUID | null }
export interface MyCourse { id: UUID; status: 'ACTIVE'; activated_at: string; course: Course; progress: CourseProgress }
export interface LearningLesson { id: UUID; title: string; position: number; is_required: boolean; is_completed: boolean; is_locked: boolean; free_preview: boolean }
export interface LearningTopic { id: UUID; title: string; position: number; is_locked: boolean; practice: { id: UUID; is_required: boolean; is_completed: boolean } | null; test: { id: UUID; status: 'LOCKED' | 'READY' | 'PASSED' | 'FAILED' } | null; lessons: LearningLesson[] }
export interface LearningModule { id: UUID; title: string; position: number; topics: LearningTopic[] }
export interface LearningNavigation { id: UUID; title: string; slug: string; progress: CourseProgress; modules: LearningModule[] }
export interface LessonDetail { id: UUID; topic: UUID; topic_title: string; course_slug: string; title: string; position: number; kind: 'VIDEO' | 'TEXT'; content: string; video_url: string; material_url: string; duration_minutes: number; is_required: boolean; free_preview: boolean; is_completed?: boolean }
export interface LessonPreview { id: UUID; course_slug: string; title: string; kind: 'VIDEO' | 'TEXT'; content: string; video_url: string; material_url: string; duration_minutes: number; free_preview: boolean }
export interface Practice { id: UUID; topic: UUID; topic_title: string; course_slug: string; instructions: string; example: string; resource_url: string; is_required: boolean; is_completed?: boolean }
export interface TestOption { id: UUID; text: string; position: number }
export interface TestQuestionData { id: UUID; text: string; position: number; options: TestOption[] }
export interface TopicTest { test_id: UUID; available: boolean; required_lessons: number; completed_required_lessons: number; passing_score: number; questions: TestQuestionData[] }

// Admin curriculum tree — mirrors the backend admin serializers exactly.
export interface AdminModule { id: UUID; course: UUID; title: string; position: number }
export interface AdminTopic { id: UUID; module: UUID; title: string; position: number }
export interface AdminLesson { id: UUID; topic: UUID; title: string; position: number; kind: 'VIDEO' | 'TEXT'; content: string; video_url: string; material_url: string; duration_minutes: number; is_required: boolean; free_preview: boolean }
export interface AdminPractice { id: UUID; topic: UUID; instructions: string; example: string; resource_url: string; is_required: boolean }
export interface AdminTopicTest { id: UUID; topic: UUID; passing_score: number; question_count: number | null; is_required: boolean }
export interface AdminQuestionOption { id: UUID; text: string; position: number; is_correct: boolean }
export interface AdminQuestion { id: UUID; test: UUID; text: string; position: number; options: AdminQuestionOption[] }
export interface AdminTopicNode extends AdminTopic { lessons: AdminLesson[]; practice: AdminPractice | null; test: AdminTopicTest | null }
export interface AdminModuleNode extends AdminModule { topics: AdminTopicNode[] }
export interface AdminInstructor { id: UUID; name: string; slug: string; title: string; photo_url: string; experience: string; bio: string }
export interface AdminCategory { id: UUID; name: string; slug: string }

export interface AdminCourse {
  id: UUID; category: UUID | null; instructor: UUID | null; title: string; slug: string;
  short_description: string; description: string; image_url: string;
  level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'; language: string; duration_minutes: number;
  is_free: boolean; price: string | null; status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  sequential_learning: boolean; what_you_will_learn: string[]; audience: string[]; requirements: string[];
  telegram_group_url: string; support_url: string;
}

export interface AdminAccount { id: UUID; email: string; first_name: string; last_name: string; full_name: string; role: 'STUDENT' | 'ADMIN'; is_active: boolean; date_joined: string; referral_code: string; referred_by: UUID | null; referral_discount_percent: number; referral_discount_applied: number }
export interface AdminCourseAccess { id: UUID; course_id: UUID; course_title: string; status: string; activated_at: string }

export interface AdminStats { total_users: number; active_enrollments: number; total_courses: number; free_courses: number; paid_courses: number; pending_requests: number; passed_attempts: number; failed_attempts: number }
export interface AdminEnrollmentStat { id: UUID; user_id: UUID; user_email: string | null; user_name: string; course_id: UUID; course_slug: string; course_title: string; access_type: 'FREE' | 'PAID'; status: 'ACTIVE'; activated_at: string }
export interface AdminAttemptStat { id: UUID; user_id: UUID; user_email: string | null; user_name: string; course_slug: string; course_title: string; topic_title: string; score: number; result: 'PASSED' | 'FAILED'; completed_at: string }
export type EnrollmentRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED';
export interface AdminEnrollmentRequest { id: UUID; course: UUID; course_slug: string; course_title: string; user: UUID; user_email: string | null; user_name: string; status: EnrollmentRequestStatus; note: string; list_price: string | null; referral_discount_percent: number; requested_price: string | null; requested_at: string; reviewed_at: string | null }

export interface ReferralOffer { code: string; inviter_name: string; discount_percent: number }
export interface ReferralSummary { user_id: UUID; email: string | null; full_name: string; referral_code: string; referral_path: string; discount_percent: number; applied_discount_percent: number; invited_by_name: string; referred_count: number; referred_with_access: number; free_access_count: number; paid_access_count: number }
export interface ReferredCourseAccess { id: UUID; course_title: string; access_type: 'FREE' | 'PAID'; activated_at: string }
export interface ReferredUser { id: UUID; email: string | null; full_name: string; discount_percent: number; joined_at: string; course_access: ReferredCourseAccess[] }
export interface AdminReferralDetail extends ReferralSummary { referred_users: ReferredUser[] }

export interface DeviceChoice { id: UUID; name: string; created_at: string; last_seen_at: string; current?: boolean }
