import type { ReactNode } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui';

export function AdminTable({ columns, children, caption, className }: { columns: string[]; children: ReactNode; caption: string; className?: string }) { return <div className="ns-table-wrap"><table className={['ns-admin-table', className].filter(Boolean).join(' ')}><caption className="sr-only">{caption}</caption><thead><tr>{columns.map(column=><th key={column} scope="col">{column}</th>)}</tr></thead><tbody>{children}</tbody></table></div> }
export function KpiCard({ label, value, note, mark, href }: { label: string; value: string | number; note: string; mark: string; href?: string }) {
  const card = <Card className="ns-kpi-card"><span aria-hidden="true">{mark}</span><div><small>{label}</small><strong>{value}</strong><p>{note}</p></div></Card>;
  return href ? <Link className="ns-kpi-link" href={href} aria-label={`${label}: ${value}. Batafsil ko‘rish`}>{card}</Link> : card;
}
export function RowActions({ children }: { children: ReactNode }) { return <div className="ns-row-actions">{children}</div> }
