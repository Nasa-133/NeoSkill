export const statusLabels = {
  PENDING: 'Kutilmoqda', APPROVED: 'Tasdiqlangan', REJECTED: 'Rad etilgan', ACTIVE: 'Faol',
  LOCKED: 'Yopiq', AVAILABLE: 'Ochiq', CURRENT: 'Hozirgi', COMPLETED: 'Tugallangan',
  READY: 'Tayyor', PASSED: 'O‘tdi', FAILED: 'O‘tmadi', DRAFT: 'Qoralama',
  PUBLISHED: 'Nashr qilingan', ARCHIVED: 'Arxivlangan',
} as const;

export type KnownStatus = keyof typeof statusLabels;
export function statusTone(status: KnownStatus): 'neutral' | 'brand' | 'success' | 'warning' | 'danger' {
  if (['ACTIVE', 'COMPLETED', 'PASSED', 'APPROVED', 'PUBLISHED'].includes(status)) return 'success';
  if (['PENDING', 'READY'].includes(status)) return 'warning';
  if (['FAILED', 'REJECTED'].includes(status)) return 'danger';
  if (['AVAILABLE', 'CURRENT'].includes(status)) return 'brand';
  return 'neutral';
}
