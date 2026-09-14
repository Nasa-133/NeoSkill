import type { ButtonHTMLAttributes, ReactNode } from 'react';

export function IconButton({ label, children, className, ...props }: { label: string; children: ReactNode } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} aria-label={label} className={['ns-icon-button', className].filter(Boolean).join(' ')}>{children}</button>;
}
