import type { HTMLAttributes } from 'react';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function Card({ className, padding = 'md', ...props }: CardProps) {
  return (
    <div
      className={['ns-card', className].filter(Boolean).join(' ')}
      data-padding={padding}
      {...props}
    />
  );
}

