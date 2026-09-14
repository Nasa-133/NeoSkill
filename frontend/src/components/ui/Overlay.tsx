'use client';

import { useEffect, type ReactNode } from 'react';
import { Button } from './Button';

export function Modal({ open, title, children, onClose }: { open: boolean; title: string; children: ReactNode; onClose: () => void }) {
  useEffect(() => { if (!open) return; const close = (event: KeyboardEvent) => event.key === 'Escape' && onClose(); document.addEventListener('keydown', close); return () => document.removeEventListener('keydown', close); }, [open, onClose]);
  if (!open) return null;
  return <div className="ns-overlay" role="presentation" onMouseDown={event => event.target === event.currentTarget && onClose()}><section className="ns-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><header><h2 id="modal-title">{title}</h2><button className="ns-icon-button" type="button" onClick={onClose} aria-label="Yopish">×</button></header>{children}</section></div>;
}

export function ConfirmDialog({ open, title, description, confirmLabel = 'Tasdiqlash', danger, busy, onConfirm, onClose }: { open: boolean; title: string; description: string; confirmLabel?: string; danger?: boolean; busy?: boolean; onConfirm: () => void; onClose: () => void }) {
  return <Modal open={open} title={title} onClose={onClose}><p className="ns-muted">{description}</p><div className="ns-dialog-actions"><Button variant="secondary" onClick={onClose}>Bekor qilish</Button><Button variant={danger ? 'danger' : 'primary'} loading={Boolean(busy)} onClick={onConfirm}>{confirmLabel}</Button></div></Modal>;
}
