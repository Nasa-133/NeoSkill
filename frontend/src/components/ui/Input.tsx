import type { InputHTMLAttributes } from 'react';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  error?: string | undefined;
  hint?: string | undefined;
  id: string;
  label: string;
  requiredMark?: boolean;
}

export function Input({ error, hint, id, label, requiredMark, ...props }: InputProps) {
  const messageId = error || hint ? `${id}-message` : undefined;

  return (
    <div className="ns-field">
      <label className="ns-field__label" htmlFor={id}>
        {label}{requiredMark ? <span aria-hidden="true"> *</span> : null}
      </label>
      <input
        {...props}
        aria-describedby={messageId}
        aria-invalid={error ? true : undefined}
        className={['ns-input', props.className].filter(Boolean).join(' ')}
        id={id}
      />
      {error ? (
        <p className="ns-field__error" id={messageId} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="ns-field__hint" id={messageId}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
