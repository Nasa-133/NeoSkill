'use client';

import { useId, useRef, useState } from 'react';

import { api, readApiError } from '@/lib/api';
import { Button } from './Button';
import { Input } from './Input';

const ACCEPT = 'image/jpeg,image/png,image/webp';
const MAX_MB = 2;

/**
 * One field, two ways to fill it: paste a link or upload from this computer.
 * The stored value is always a URL, so the rest of the app needs no upload logic.
 */
export function ImagePicker({ label, value, onChange, recommended, aspect = '16 / 9' }: {
  label: string;
  value: string;
  onChange: (url: string) => void;
  /** e.g. "1200×675" — shown so admins know what size to prepare. */
  recommended: string;
  aspect?: string;
}) {
  const id = useId().replace(/[^a-zA-Z0-9-]/g, '');
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [broken, setBroken] = useState(false);

  async function upload(file: File) {
    setError('');
    if (file.size > MAX_MB * 1024 * 1024) { setError(`Fayl juda katta. Eng kattasi — ${MAX_MB} MB.`); return; }
    setBusy(true);
    try { const result = await api.uploadImage(file); setBroken(false); onChange(result.url); }
    catch (reason) { setError(readApiError(reason, 'Rasmni yuklab bo‘lmadi.')); }
    finally { setBusy(false); if (fileInput.current) fileInput.current.value = ''; }
  }

  return <div className="ns-image-picker">
    <div className="ns-image-picker__field">
      <Input
        id={`${id}-url`}
        label={label}
        type="url"
        placeholder="https://... yoki kompyuterdan yuklang"
        value={value}
        onChange={event => { setBroken(false); setError(''); onChange(event.target.value); }}
        hint={`Tavsiya: ${recommended} px, JPG / PNG / WebP, ${MAX_MB} MB gacha.`}
      />
      <div className="ns-image-picker__actions">
        <input
          ref={fileInput}
          id={`${id}-file`}
          className="sr-only"
          type="file"
          accept={ACCEPT}
          onChange={event => { const file = event.target.files?.[0]; if (file) void upload(file); }}
        />
        <Button type="button" variant="secondary" size="sm" loading={busy} onClick={() => fileInput.current?.click()}>
          Kompyuterdan yuklash
        </Button>
        {value ? <Button type="button" variant="ghost" size="sm" onClick={() => { onChange(''); setBroken(false); setError(''); }}>Olib tashlash</Button> : null}
      </div>
      {error ? <p className="ns-field__error" role="alert">{error}</p> : null}
    </div>

    <div className="ns-image-picker__preview" style={{ aspectRatio: aspect }}>
      {value && !broken
        // eslint-disable-next-line @next/next/no-img-element -- an arbitrary preview URL must not go through the optimizer
        ? <img src={value} alt="" onError={() => setBroken(true)} />
        : <span>{broken ? 'Rasm ochilmadi — havolani tekshiring' : 'Rasm tanlanmagan'}</span>}
    </div>
  </div>;
}
