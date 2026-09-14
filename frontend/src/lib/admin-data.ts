'use client';

import { api, useMockData } from './api';
import { courseDetails } from './fixtures';
import type { AdminCategory, AdminCourse, AdminInstructor, AdminLesson, AdminModuleNode, AdminPractice, AdminQuestion, AdminTopicNode, AdminTopicTest, UUID } from './types';

export type { AdminLesson, AdminModuleNode, AdminPractice, AdminQuestion, AdminTopicNode, AdminTopicTest };

function newId() { return typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `id-${Math.round(performance.now() * 1000)}`; }
function pause(ms = 220) { return new Promise<void>(resolve => { window.setTimeout(resolve, ms); }); }
function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)) as T; }
function renumber<T extends { position: number }>(items: T[]) { items.forEach((item, index) => { item.position = index + 1; }); }

/* ------------------------------------------------------------------ *
 * Mock store — edits survive navigation for the whole browser session *
 * ------------------------------------------------------------------ */

const mockTrees = new Map<UUID, AdminModuleNode[]>();
const mockQuestions = new Map<UUID, AdminQuestion[]>();

function seedTree(courseId: UUID): AdminModuleNode[] {
  const detail = courseDetails.find(item => item.id === courseId);
  if (!detail) return [];
  return detail.modules.map((module, moduleIndex) => {
    const moduleId = `${courseId}-m${moduleIndex + 1}`;
    return {
      id: moduleId, course: courseId, title: module.title, position: moduleIndex + 1,
      topics: module.topics.map((topic, topicIndex) => {
        const topicId = `${moduleId}-t${topicIndex + 1}`;
        const first = moduleIndex === 0 && topicIndex === 0;
        return {
          id: topicId, module: moduleId, title: topic.title, position: topicIndex + 1,
          lessons: topic.lessons.map((lesson, lessonIndex) => ({
            id: `${topicId}-l${lessonIndex + 1}`, topic: topicId, title: lesson.title, position: lessonIndex + 1,
            kind: lesson.kind, content: '', video_url: 'https://example.com/video', material_url: '',
            duration_minutes: lesson.duration_minutes, is_required: true, free_preview: lesson.free_preview,
          })),
          practice: first ? { id: `${topicId}-p`, topic: topicId, instructions: 'Ismingizni ekranga chiqaruvchi kichik dastur yozing.', example: 'print("Salom, NeoSkill!")', resource_url: '', is_required: true } : null,
          test: first ? { id: `${topicId}-test`, topic: topicId, passing_score: 70, question_count: null, is_required: true } : null,
        };
      }),
    };
  });
}

function mockTree(courseId: UUID) {
  let value = mockTrees.get(courseId);
  if (!value) { value = seedTree(courseId); mockTrees.set(courseId, value); }
  return value;
}

function findTopic(tree: AdminModuleNode[], topicId: UUID): AdminTopicNode | undefined {
  return tree.flatMap(module => module.topics).find(topic => topic.id === topicId);
}

function seedQuestions(testId: UUID): AdminQuestion[] {
  return [
    { id: `${testId}-q1`, test: testId, text: 'Python fayli qaysi kengaytma bilan saqlanadi?', position: 1, options: ['.py', '.html', '.css', '.sql'].map((text, index) => ({ id: `${testId}-q1-o${index + 1}`, text, position: index + 1, is_correct: index === 0 })) },
    { id: `${testId}-q2`, test: testId, text: 'Qiymatni ekranga chiqaruvchi funksiya qaysi?', position: 2, options: ['input()', 'print()', 'len()', 'type()'].map((text, index) => ({ id: `${testId}-q2-o${index + 1}`, text, position: index + 1, is_correct: index === 1 })) },
  ];
}

function mockQuestionList(testId: UUID) {
  let value = mockQuestions.get(testId);
  if (!value) { value = testId.endsWith('-test') ? seedQuestions(testId) : []; mockQuestions.set(testId, value); }
  return value;
}

/* ------------------------------------------------------------------ *
 * Curriculum                                                          *
 * ------------------------------------------------------------------ */

async function loadTree(courseId: UUID): Promise<AdminModuleNode[]> {
  if (useMockData) { await pause(); return clone(mockTree(courseId)); }
  return api.adminCurriculum(courseId);
}

/** Applies a change and returns the refreshed tree, so callers only ever hold one state value. */
async function apply(courseId: UUID, mockOp: (tree: AdminModuleNode[]) => void, remoteOp: () => Promise<unknown>): Promise<AdminModuleNode[]> {
  if (useMockData) { await pause(); mockOp(mockTree(courseId)); }
  else await remoteOp();
  return loadTree(courseId);
}

function move<T>(items: T[], index: number, delta: number) {
  const target = index + delta;
  if (index < 0 || target < 0 || target >= items.length) return false;
  const [item] = items.splice(index, 1);
  items.splice(target, 0, item!);
  return true;
}

export const curriculum = {
  load: loadTree,

  addModule: (courseId: UUID, title: string) => apply(courseId,
    tree => { tree.push({ id: newId(), course: courseId, title, position: tree.length + 1, topics: [] }); renumber(tree); },
    () => api.adminCreate('modules', { course: courseId, title })),

  renameModule: (courseId: UUID, moduleId: UUID, title: string) => apply(courseId,
    tree => { const target = tree.find(item => item.id === moduleId); if (target) target.title = title; },
    () => api.adminUpdate('modules', moduleId, { title })),

  removeModule: (courseId: UUID, moduleId: UUID) => apply(courseId,
    tree => { const index = tree.findIndex(item => item.id === moduleId); if (index >= 0) { tree.splice(index, 1); renumber(tree); } },
    () => api.adminDelete('modules', moduleId)),

  moveModule: (courseId: UUID, moduleId: UUID, delta: number) => apply(courseId,
    tree => { if (move(tree, tree.findIndex(item => item.id === moduleId), delta)) renumber(tree); },
    async () => {
      const tree = await loadTree(courseId);
      const order = tree.map(item => item.id);
      if (move(order, order.indexOf(moduleId), delta)) await api.adminReorder(`courses/${courseId}/modules/reorder`, order);
    }),

  addTopic: (courseId: UUID, moduleId: UUID, title: string) => apply(courseId,
    tree => { const target = tree.find(item => item.id === moduleId); if (target) { target.topics.push({ id: newId(), module: moduleId, title, position: target.topics.length + 1, lessons: [], practice: null, test: null }); renumber(target.topics); } },
    () => api.adminCreate('topics', { module: moduleId, title })),

  renameTopic: (courseId: UUID, topicId: UUID, title: string) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic) topic.title = title; },
    () => api.adminUpdate('topics', topicId, { title })),

  removeTopic: (courseId: UUID, topicId: UUID) => apply(courseId,
    tree => { for (const node of tree) { const index = node.topics.findIndex(item => item.id === topicId); if (index >= 0) { node.topics.splice(index, 1); renumber(node.topics); return; } } },
    () => api.adminDelete('topics', topicId)),

  moveTopic: (courseId: UUID, moduleId: UUID, topicId: UUID, delta: number) => apply(courseId,
    tree => { const target = tree.find(item => item.id === moduleId); if (target && move(target.topics, target.topics.findIndex(item => item.id === topicId), delta)) renumber(target.topics); },
    async () => {
      const tree = await loadTree(courseId);
      const order = (tree.find(item => item.id === moduleId)?.topics ?? []).map(item => item.id);
      if (move(order, order.indexOf(topicId), delta)) await api.adminReorder(`modules/${moduleId}/topics/reorder`, order);
    }),

  addLesson: (courseId: UUID, topicId: UUID, lesson: Omit<AdminLesson, 'id' | 'topic' | 'position'>) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic) { topic.lessons.push({ ...lesson, id: newId(), topic: topicId, position: topic.lessons.length + 1 }); renumber(topic.lessons); } },
    () => api.adminCreate('lessons', { ...lesson, topic: topicId })),

  updateLesson: (courseId: UUID, lessonId: UUID, patch: Partial<AdminLesson>) => apply(courseId,
    tree => { const lesson = tree.flatMap(module => module.topics).flatMap(topic => topic.lessons).find(item => item.id === lessonId); if (lesson) Object.assign(lesson, patch); },
    () => api.adminUpdate('lessons', lessonId, patch)),

  removeLesson: (courseId: UUID, topicId: UUID, lessonId: UUID) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic) { const index = topic.lessons.findIndex(item => item.id === lessonId); if (index >= 0) { topic.lessons.splice(index, 1); renumber(topic.lessons); } } },
    () => api.adminDelete('lessons', lessonId)),

  moveLesson: (courseId: UUID, topicId: UUID, lessonId: UUID, delta: number) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic && move(topic.lessons, topic.lessons.findIndex(item => item.id === lessonId), delta)) renumber(topic.lessons); },
    async () => {
      const tree = await loadTree(courseId);
      const order = (findTopic(tree, topicId)?.lessons ?? []).map(item => item.id);
      if (move(order, order.indexOf(lessonId), delta)) await api.adminReorder(`topics/${topicId}/lessons/reorder`, order);
    }),

  savePractice: (courseId: UUID, topicId: UUID, practice: Omit<AdminPractice, 'id' | 'topic'>, existingId?: UUID) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic) topic.practice = { ...practice, id: existingId ?? newId(), topic: topicId }; },
    () => existingId ? api.adminUpdate('practices', existingId, practice) : api.adminCreate('practices', { ...practice, topic: topicId })),

  removePractice: (courseId: UUID, topicId: UUID, practiceId: UUID) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic) topic.practice = null; },
    () => api.adminDelete('practices', practiceId)),

  saveTest: (courseId: UUID, topicId: UUID, test: Omit<AdminTopicTest, 'id' | 'topic'>, existingId?: UUID) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic) topic.test = { ...test, id: existingId ?? `${topicId}-test`, topic: topicId }; },
    () => existingId ? api.adminUpdate('topic-tests', existingId, test) : api.adminCreate('topic-tests', { ...test, topic: topicId })),

  removeTest: (courseId: UUID, topicId: UUID, testId: UUID) => apply(courseId,
    tree => { const topic = findTopic(tree, topicId); if (topic) topic.test = null; mockQuestions.delete(testId); },
    () => api.adminDelete('topic-tests', testId)),
};

/* ------------------------------------------------------------------ *
 * Test questions                                                      *
 * ------------------------------------------------------------------ */

export const questions = {
  async load(testId: UUID): Promise<AdminQuestion[]> {
    if (useMockData) { await pause(); return clone(mockQuestionList(testId)); }
    return api.adminList<AdminQuestion>('questions', `?test=${testId}`);
  },
  async save(testId: UUID, list: AdminQuestion[]): Promise<AdminQuestion[]> {
    if (useMockData) { await pause(400); mockQuestions.set(testId, clone(list)); return clone(list); }

    const existing = await api.adminList<AdminQuestion>('questions', `?test=${testId}`);
    const keep = new Set(list.map(item => item.id));
    await Promise.all(existing.filter(item => !keep.has(item.id)).map(item => api.adminDelete('questions', item.id)));

    // Position is never sent here: (test, position) is unique, so renumbering one row at a
    // time collides with whichever row still holds that slot. The order is applied at the
    // end through the reorder endpoint, which offsets every position atomically.
    const ids: UUID[] = [];
    for (const question of list) {
      const payload = {
        test: testId,
        text: question.text,
        options: question.options.map((option, order) => ({ text: option.text, position: order + 1, is_correct: option.is_correct })),
      };
      if (existing.some(item => item.id === question.id)) { await api.adminUpdate('questions', question.id, payload); ids.push(question.id); }
      else { const created = await api.adminCreate<AdminQuestion>('questions', payload); ids.push(created.id); }
    }
    if (ids.length > 1) await api.adminReorder(`topic-tests/${testId}/questions/reorder`, ids);
    return api.adminList<AdminQuestion>('questions', `?test=${testId}`);
  },
};

/* ------------------------------------------------------------------ *
 * Flat collections (instructors, categories, testimonials)            *
 * ------------------------------------------------------------------ */

/** Field names follow the backend TestimonialSerializer, not the public fixture shape. */
export interface AdminTestimonial { id: UUID; author_name: string; author_title: string; quote: string; photo_url: string; is_published: boolean; position: number }

type Seeded = { instructors: AdminInstructor[]; categories: AdminCategory[]; testimonials: AdminTestimonial[] };
const mockCollections = new Map<keyof Seeded, unknown[]>();

function mockCollection<K extends keyof Seeded>(key: K, seed: () => Seeded[K]): Seeded[K] {
  let value = mockCollections.get(key) as Seeded[K] | undefined;
  if (!value) { value = seed(); mockCollections.set(key, value); }
  return value;
}

/** One CRUD shape for every flat admin list, so each screen stays a thin form. */
function collection<T extends { id: UUID }, K extends keyof Seeded>(key: K, resource: string, seed: () => Seeded[K]) {
  const store = () => mockCollection(key, seed) as unknown as T[];
  return {
    async list(): Promise<T[]> {
      if (useMockData) { await pause(); return clone(store()); }
      return api.adminList<T>(resource);
    },
    async create(payload: Omit<T, 'id'>): Promise<T[]> {
      if (useMockData) { await pause(); store().push({ ...payload, id: newId() } as T); }
      else await api.adminCreate(resource, payload);
      return this.list();
    },
    async update(id: UUID, payload: Partial<T>): Promise<T[]> {
      if (useMockData) { await pause(); const found = store().find(item => item.id === id); if (found) Object.assign(found, payload); }
      else await api.adminUpdate(resource, id, payload);
      return this.list();
    },
    async remove(id: UUID): Promise<T[]> {
      if (useMockData) { await pause(); const list = store(); const index = list.findIndex(item => item.id === id); if (index >= 0) list.splice(index, 1); }
      else await api.adminDelete(resource, id);
      return this.list();
    },
  };
}

export const instructorStore = collection<AdminInstructor, 'instructors'>('instructors', 'instructors', () => [
  { id: 'instructor-1', name: 'Sardor Karimov', slug: 'sardor-karimov', title: 'Senior Python Developer', photo_url: '', experience: '8 yillik amaliy tajriba', bio: 'Murakkab mavzularni sodda va amaliy misollar orqali tushuntiradigan dasturchi va mentor.' },
  { id: 'instructor-2', name: 'Madina Aliyeva', slug: 'madina-aliyeva', title: 'Product Designer', photo_url: '', experience: '6 yillik mahsulot dizayni tajribasi', bio: 'Mahsulot dizayni va foydalanuvchi tajribasi bo‘yicha mutaxassis.' },
]);

export const categoryStore = collection<AdminCategory, 'categories'>('categories', 'categories', () => [
  { id: 'cat-python', name: 'Dasturlash', slug: 'dasturlash' },
  { id: 'cat-design', name: 'Dizayn', slug: 'dizayn' },
  { id: 'cat-business', name: 'Biznes', slug: 'biznes' },
]);

export const testimonialStore = collection<AdminTestimonial, 'testimonials'>('testimonials', 'testimonials', () => [
  { id: 'testimonial-1', author_name: 'Aziza Sobirova', author_title: 'Junior dasturchi', quote: 'Darslarning ketma-ketligi va amaliy topshiriqlar o‘rganishni ancha osonlashtirdi.', photo_url: '', is_published: true, position: 1 },
  { id: 'testimonial-2', author_name: 'Jasur Rahmonov', author_title: 'Talaba', quote: 'Har mavzudan keyingi test qayerda xato qilayotganimni tushunishga yordam berdi.', photo_url: '', is_published: true, position: 2 },
]);

export function slugify(value: string) {
  return value.toLowerCase().trim()
    .replace(/[‘’']/g, '')
    .replace(/[^a-z0-9Ѐ-ӿ]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export async function listCourses(): Promise<{ id: UUID; title: string }[]> {
  return (await courseStore.list()).map(item => ({ id: item.id, title: item.title }));
}

/* ------------------------------------------------------------------ *
 * Courses                                                             *
 * ------------------------------------------------------------------ */

const mockCourses = new Map<UUID, AdminCourse>();

function seedCourses(): AdminCourse[] {
  if (mockCourses.size === 0) {
    for (const item of courseDetails) {
      mockCourses.set(item.id, {
        id: item.id, category: item.category?.id ?? null, instructor: null,
        title: item.title, slug: item.slug, short_description: item.short_description,
        description: item.description, image_url: item.image_url, level: item.level,
        language: item.language, duration_minutes: item.duration_minutes,
        is_free: item.is_free, price: item.is_free ? null : item.price,
        status: 'PUBLISHED', sequential_learning: true,
        what_you_will_learn: item.what_you_will_learn, audience: item.audience,
        requirements: item.requirements, telegram_group_url: '', support_url: '',
      });
    }
  }
  return [...mockCourses.values()];
}

export const courseStore = {
  async list(): Promise<AdminCourse[]> {
    if (useMockData) { await pause(); return clone(seedCourses()); }
    return api.adminList<AdminCourse>('courses');
  },
  async get(id: UUID): Promise<AdminCourse> {
    if (useMockData) { await pause(); seedCourses(); const found = mockCourses.get(id); if (!found) throw new Error('Kurs topilmadi.'); return clone(found); }
    return api.adminGet<AdminCourse>('courses', id);
  },
  async create(payload: Omit<AdminCourse, 'id'>): Promise<AdminCourse> {
    if (useMockData) { await pause(); const created = { ...payload, id: newId() }; mockCourses.set(created.id, created); return clone(created); }
    return api.adminCreate<AdminCourse>('courses', payload);
  },
  async update(id: UUID, payload: Partial<AdminCourse>): Promise<AdminCourse> {
    if (useMockData) { await pause(); seedCourses(); const found = mockCourses.get(id); if (!found) throw new Error('Kurs topilmadi.'); Object.assign(found, payload); return clone(found); }
    return api.adminUpdate<AdminCourse>('courses', id, payload);
  },
  async remove(id: UUID): Promise<void> {
    if (useMockData) { await pause(); mockCourses.delete(id); return; }
    await api.adminDelete('courses', id);
  },
};
