'use client';

import { useEffect, useState } from 'react';
import { api, ApiError, useMockData } from './api';
import type { User } from './types';

const MOCK_SESSION_KEY = 'neoskill-mock-user-role';
const SESSION_EVENT = 'neoskill-session-change';

function mockUser(role: User['role']): User {
  return { id: `mock-${role.toLowerCase()}`, email: role === 'ADMIN' ? 'admin@neoskill.local' : 'student@neoskill.local', first_name: role === 'ADMIN' ? 'Admin' : 'Neo', last_name: 'Skill', role };
}

export function readMockUser(): User | null {
  if (typeof window === 'undefined') return null;
  const role = localStorage.getItem(MOCK_SESSION_KEY);
  return role === 'ADMIN' || role === 'STUDENT' ? mockUser(role) : null;
}

export function saveMockUser(role: User['role']) {
  localStorage.setItem(MOCK_SESSION_KEY, role);
  window.dispatchEvent(new Event(SESSION_EVENT));
}

/** Several components ask for the session at once; they should share one request, not race one each. */
let inflight: Promise<User | null> | null = null;
function loadSession(): Promise<User | null> {
  if (!inflight) {
    inflight = api.session().then(result => result.user, () => null);
    void inflight.finally(() => { inflight = null; });
  }
  return inflight;
}

export function useCurrentUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    async function load() {
      if (useMockData) { if (live) { setUser(readMockUser()); setLoading(false); } return; }
      const result = await loadSession();
      if (live) { setUser(result); setLoading(false); }
    }
    void load();
    const refresh = () => void load();
    window.addEventListener(SESSION_EVENT, refresh);
    window.addEventListener('storage', refresh);
    return () => { live = false; window.removeEventListener(SESSION_EVENT, refresh); window.removeEventListener('storage', refresh); };
  }, []);
  return { user, loading };
}

export async function signOut() {
  if (useMockData) localStorage.removeItem(MOCK_SESSION_KEY);
  else {
    try { await api.logout(); }
    catch (reason) {
      // An already-expired server session is equivalent to a completed logout.
      if (!(reason instanceof ApiError) || ![401, 403].includes(reason.status)) throw reason;
    }
  }
  window.dispatchEvent(new Event(SESSION_EVENT));
}

/** Only same-origin absolute paths may come back from a `?next=` query value. */
export function safeNext(value: string | null | undefined, fallback: string) {
  const hasControl = value ? [...value].some(character => character.charCodeAt(0) < 32) : false;
  return value && value.startsWith('/') && !value.startsWith('//') && !value.includes('\\') && !hasControl ? value : fallback;
}

export function userName(user: User | null) {
  if (!user) return 'Foydalanuvchi';
  const full = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
  return full || user.email || 'Foydalanuvchi';
}

export function userInitials(user: User | null) {
  const initials = userName(user).split(' ').filter(Boolean).map(part => part.charAt(0)).join('');
  return (initials || 'N').slice(0, 2).toUpperCase();
}

export function roleLabel(user: User | null) { return user?.role === 'ADMIN' ? 'Administrator' : 'Talaba'; }
export function homePathFor(user: User | null) { return user?.role === 'ADMIN' ? '/admin' : '/dashboard'; }

const DEVICE_KEY = 'neoskill-device-id';

/** A stable id per browser, so the account's device limit can tell them apart. */
export function deviceId(): string {
  const found = window.localStorage.getItem(DEVICE_KEY);
  if (found) return found;
  const value = crypto.randomUUID();
  window.localStorage.setItem(DEVICE_KEY, value);
  return value;
}

export function deviceName(): string {
  const agent = navigator.userAgent;
  const system = /iPhone|iPad/i.test(agent) ? 'iPhone' : /Android/i.test(agent) ? 'Android'
    : /Macintosh/i.test(agent) ? 'Mac' : /Windows/i.test(agent) ? 'Windows'
    : /Linux/i.test(agent) ? 'Linux' : 'Qurilma';
  const browser = /Edg\//.test(agent) ? 'Edge' : /OPR\//.test(agent) ? 'Opera'
    : /Chrome\//.test(agent) ? 'Chrome' : /Firefox\//.test(agent) ? 'Firefox'
    : /Safari\//.test(agent) ? 'Safari' : 'Brauzer';
  return `${system} — ${browser}`;
}
