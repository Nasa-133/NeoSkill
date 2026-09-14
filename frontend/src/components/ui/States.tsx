import Link from 'next/link';
import type { HTMLAttributes, ReactNode } from 'react';

import { Button } from './Button';

export function ProgressBar({ value, label = 'Jarayon' }: { value: number; label?: string }) {
  const safe = Math.min(100, Math.max(0, value));
  return <div className="ns-progress-wrap"><div className="ns-progress-label"><span>{label}</span><strong>{safe}%</strong></div><div className="ns-progress" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={safe}><span style={{ width: `${safe}%` }} /></div></div>;
}

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden="true" className={['ns-skeleton', className].filter(Boolean).join(' ')} {...props} />;
}

export function EmptyState({ title, description, actionHref, actionLabel, onAction }: { title: string; description: string; actionHref?: string | undefined; actionLabel?: string | undefined; onAction?: (() => void) | undefined }) {
  const action = actionLabel && onAction ? <Button onClick={onAction}>{actionLabel}</Button> : actionHref && actionLabel ? <Link className="ns-link-button" href={actionHref}>{actionLabel}</Link> : null;
  return <section className="ns-state"><span className="ns-state__icon" aria-hidden="true">○</span><h2>{title}</h2><p>{description}</p>{action}</section>;
}

export function ErrorState({ title = 'Ma’lumotni yuklab bo‘lmadi', description = 'Internet aloqasini tekshirib, qayta urinib ko‘ring.', onRetry }: { title?: string | undefined; description?: string | undefined; onRetry?: (() => void) | undefined }) {
  return <section className="ns-state ns-state--error" role="alert"><span className="ns-state__icon" aria-hidden="true">!</span><h2>{title}</h2><p>{description}</p>{onRetry ? <Button onClick={onRetry} variant="secondary">Qayta urinish</Button> : null}</section>;
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return <header className="ns-page-header"><div>{eyebrow ? <p className="ns-eyebrow">{eyebrow}</p> : null}<h1>{title}</h1>{description ? <p>{description}</p> : null}</div>{actions ? <div className="ns-page-actions">{actions}</div> : null}</header>;
}

export function Tabs({ items, active }: { items: { href: string; label: string; count?: number }[]; active: string }) {
  return <nav className="ns-tabs" aria-label="Bo‘limlar">{items.map(item => <Link key={item.href} href={item.href} aria-current={active === item.href ? 'page' : undefined}>{item.label}{item.count === undefined ? null : <span>{item.count}</span>}</Link>)}</nav>;
}
