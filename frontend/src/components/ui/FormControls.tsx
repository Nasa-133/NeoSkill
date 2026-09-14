import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';

type SharedField = { id: string; label: string; error?: string | undefined; hint?: string | undefined };

function Message({ id, error, hint }: { id: string; error?: string | undefined; hint?: string | undefined }) {
  if (error) return <p className="ns-field__error" id={id} role="alert">{error}</p>;
  if (hint) return <p className="ns-field__hint" id={id}>{hint}</p>;
  return null;
}

export function Textarea({ id, label, error, hint, className, ...props }: SharedField & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const messageId = error || hint ? `${id}-message` : undefined;
  return <div className="ns-field"><label className="ns-field__label" htmlFor={id}>{label}</label><textarea {...props} id={id} aria-invalid={error ? true : undefined} aria-describedby={messageId} className={['ns-input ns-textarea', className].filter(Boolean).join(' ')} /><Message id={messageId ?? ''} error={error} hint={hint} /></div>;
}

export function Select({ id, label, error, hint, className, children, ...props }: SharedField & SelectHTMLAttributes<HTMLSelectElement>) {
  const messageId = error || hint ? `${id}-message` : undefined;
  return <div className="ns-field"><label className="ns-field__label" htmlFor={id}>{label}</label><select {...props} id={id} aria-invalid={error ? true : undefined} aria-describedby={messageId} className={['ns-input ns-select', className].filter(Boolean).join(' ')}>{children}</select><Message id={messageId ?? ''} error={error} hint={hint} /></div>;
}

export function Checkbox({ id, label, className, ...props }: { id: string; label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return <label className={['ns-check', className].filter(Boolean).join(' ')} htmlFor={id}><input {...props} id={id} type="checkbox" /><span>{label}</span></label>;
}

export function Radio({ id, label, className, ...props }: { id: string; label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return <label className={['ns-check ns-radio', className].filter(Boolean).join(' ')} htmlFor={id}><input {...props} id={id} type="radio" /><span>{label}</span></label>;
}
