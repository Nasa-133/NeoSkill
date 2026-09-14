'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';

import { roleLabel, signOut, useCurrentUser, userInitials, userName } from '@/lib/session';
import { readApiError } from '@/lib/api';
import { usePlatformSettings } from '@/lib/platform-settings';
import type { User } from '@/lib/types';
import { RouteLoading } from '@/components/ui';

const publicLinks = [{ href: '/courses', label: 'Kurslar' }, { href: '/about', label: 'Biz haqimizda' }, { href: '/contact', label: 'Aloqa' }];
const studentLinks = [{ href: '/dashboard', label: 'Bosh sahifa', mark: '⌂' }, { href: '/my-courses', label: 'Kurslarim', mark: '▤' }, { href: '/profile', label: 'Profil', mark: '○' }];
const adminLinks = [{ href: '/admin', label: 'Boshqaruv paneli', mark: '⌂' }, { href: '/admin/statistics', label: 'Statistika', mark: '↗' }, { href: '/admin/referrals', label: 'Referallar', mark: '%' }, { href: '/admin/courses', label: 'Kurslar', mark: '▤' }, { href: '/admin/categories', label: 'Kategoriyalar', mark: '◇' }, { href: '/admin/instructors', label: 'Ustozlar', mark: '◎' }, { href: '/admin/enrollment-requests', label: 'Arizalar', mark: '✓' }, { href: '/admin/users', label: 'Foydalanuvchilar', mark: '♙' }, { href: '/admin/tests', label: 'Testlar', mark: '?' }, { href: '/admin/testimonials', label: 'Fikrlar', mark: '“' }, { href: '/admin/settings', label: 'Sozlamalar', mark: '⚙' }];

export function Brand({ inverse = false }: { inverse?: boolean }) {
  const { settings } = usePlatformSettings();
  return <Link className="ns-brand" data-inverse={inverse || undefined} href="/" aria-label={`${settings.platform_name} bosh sahifasi`}>{settings.platform_name === 'NeoSkill' ? <><span>Neo</span>Skill</> : settings.platform_name}</Link>;
}

function ActiveLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  const path = usePathname();
  const active = href === '/' || href === '/admin' ? path === href : path === href || path.startsWith(`${href}/`);
  return <Link className={className} data-active={active || undefined} aria-current={active ? 'page' : undefined} href={href}>{children}</Link>;
}

/** A mobile drawer that closes itself on navigation and on Escape. */
function useDrawer() {
  const [open, setOpen] = useState(false);
  const path = usePathname();
  useEffect(() => { setOpen(false); }, [path]);
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);
  return { open, setOpen };
}

function useSignOut() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const run = () => {
    setBusy(true); setError('');
    void signOut()
      .then(() => { window.location.assign('/'); })
      .catch(reason => { setError(readApiError(reason, 'Tizimdan chiqib bo‘lmadi. Qayta urinib ko‘ring.')); })
      .finally(() => setBusy(false));
  };
  return { run, busy, error };
}

/** Keeps guests out of the cabinet and students out of the admin panel. */
function useSessionGuard(need: 'ANY' | 'ADMIN') {
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const path = usePathname();
  const allowed = Boolean(user) && (need !== 'ADMIN' || user?.role === 'ADMIN');
  useEffect(() => {
    if (loading || allowed) return;
    if (!user) router.replace(`/login?next=${encodeURIComponent(path)}`);
    else router.replace('/forbidden');
  }, [loading, allowed, user, router, path]);
  return { user, ready: !loading && allowed };
}

/** Guests get Kirish/Boshlash; a signed-in visitor gets a way back into their cabinet instead. */
function HeaderSession() {
  const { user, loading } = useCurrentUser();
  if (loading) return null;
  if (!user) return <><ActiveLink href="/login">Kirish</ActiveLink><Link className="ns-link-button ns-link-button--compact" href="/register">Boshlash</Link></>;
  if (user.role === 'ADMIN') return <Link className="ns-link-button ns-link-button--compact" href="/admin">Boshqaruv paneli</Link>;
  return <><ActiveLink href="/my-courses">Kurslarim</ActiveLink><Link className="ns-link-button ns-link-button--compact" href="/dashboard">Kabinetim</Link></>;
}

export function PublicHeader() {
  const { open, setOpen } = useDrawer();
  return <header className="ns-public-header"><div className="ns-container ns-public-header__inner"><Brand /><button className="ns-menu-button" type="button" onClick={() => setOpen(value => !value)} aria-expanded={open} aria-controls="public-nav" aria-label="Menyuni ochish">{open ? '×' : '☰'}</button><nav id="public-nav" className="ns-public-nav" data-open={open || undefined} aria-label="Asosiy navigatsiya">{publicLinks.map(link => <ActiveLink key={link.href} href={link.href}>{link.label}</ActiveLink>)}<span className="ns-nav-divider" /><HeaderSession /></nav></div></header>;
}

export function PublicFooter() {
  const { settings } = usePlatformSettings();
  return <footer className="ns-footer"><div className="ns-container ns-footer__grid"><div><Brand inverse /><p>{settings.footer_text}</p></div><div><h2>Platforma</h2><Link href="/courses">Kurslar</Link><Link href="/about">Biz haqimizda</Link><Link href="/contact">Aloqa</Link></div><div><h2>Yordam</h2><Link href="/contact">Qo‘llab-quvvatlash</Link><Link href="/privacy">Maxfiylik</Link><Link href="/terms">Foydalanish shartlari</Link></div></div><div className="ns-container ns-footer__bottom">© {new Date().getFullYear()} {settings.company_name}. Barcha huquqlar himoyalangan.</div></footer>;
}

export function PublicShell({ children }: { children: ReactNode }) { return <><PublicHeader /><main id="main-content">{children}</main><PublicFooter /></>; }

export function AuthShell({ children, title, description }: { children: ReactNode; title: string; description: string }) {
  return <main className="ns-auth-shell"><div className="ns-auth-brand"><Brand /></div><section className="ns-auth-card"><div className="ns-auth-copy"><span className="ns-auth-mark">N</span><h1>{title}</h1><p>{description}</p></div>{children}</section><p className="ns-auth-foot">Yordam kerakmi? <Link href="/contact">Biz bilan bog‘laning</Link></p></main>;
}

function UserBlock({ user, dark = false }: { user: User | null; dark?: boolean }) { return <div className="ns-user-block" data-dark={dark || undefined}><span className="ns-avatar">{userInitials(user)}</span><span><strong>{userName(user)}</strong><small>{roleLabel(user)}</small></span></div>; }

export function StudentShell({ children }: { children: ReactNode }) {
  const { open, setOpen } = useDrawer();
  const { user, ready } = useSessionGuard('ANY');
  const signOutState = useSignOut();
  if (!ready) return <RouteLoading />;
  return <div className="ns-app-shell"><aside className="ns-student-sidebar" data-open={open || undefined}><Brand /><nav aria-label="Talaba bo‘limlari">{studentLinks.map(link => <ActiveLink key={link.href} href={link.href}><span aria-hidden="true">{link.mark}</span>{link.label}</ActiveLink>)}</nav><div className="ns-sidebar-bottom"><UserBlock user={user} />{signOutState.error ? <small role="alert">{signOutState.error}</small> : null}<button type="button" disabled={signOutState.busy} onClick={signOutState.run}>{signOutState.busy ? 'Chiqilmoqda…' : 'Chiqish'}</button></div></aside><div className="ns-app-main"><header className="ns-app-header"><button className="ns-menu-button" type="button" onClick={() => setOpen(value => !value)} aria-expanded={open} aria-label="Navigatsiyani ochish">☰</button><span className="ns-app-header__title">NeoSkill</span><UserBlock user={user} /></header><main id="main-content" className="ns-app-content">{children}</main></div>{open ? <button className="ns-sidebar-backdrop" aria-label="Navigatsiyani yopish" onClick={() => setOpen(false)} /> : null}</div>;
}

export function AdminShell({ children }: { children: ReactNode }) {
  const { open, setOpen } = useDrawer();
  const { user, ready } = useSessionGuard('ADMIN');
  const signOutState = useSignOut();
  if (!ready) return <RouteLoading />;
  return <div className="ns-app-shell ns-admin-shell"><aside className="ns-admin-sidebar" data-open={open || undefined}><Brand inverse /><p className="ns-sidebar-label">ADMIN PANEL</p><nav aria-label="Admin bo‘limlari">{adminLinks.map(link => <ActiveLink key={link.href} href={link.href}><span aria-hidden="true">{link.mark}</span>{link.label}</ActiveLink>)}</nav><div className="ns-sidebar-bottom"><UserBlock user={user} dark />{signOutState.error ? <small role="alert">{signOutState.error}</small> : null}<button type="button" disabled={signOutState.busy} onClick={signOutState.run}>{signOutState.busy ? 'Chiqilmoqda…' : 'Chiqish'}</button></div></aside><div className="ns-app-main"><header className="ns-admin-header"><button className="ns-menu-button" type="button" onClick={() => setOpen(value => !value)} aria-expanded={open} aria-label="Admin navigatsiyasini ochish">☰</button><div><strong>NeoSkill boshqaruvi</strong><small>Kontent va talabalarni boshqaring</small></div><UserBlock user={user} /></header><main id="main-content" className="ns-app-content">{children}</main></div>{open ? <button className="ns-sidebar-backdrop" aria-label="Navigatsiyani yopish" onClick={() => setOpen(false)} /> : null}</div>;
}
