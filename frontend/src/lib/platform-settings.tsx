'use client';

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { api } from './api';
import type { PublicSettings } from './types';

const defaults: PublicSettings = {
  platform_name: 'NeoSkill', footer_text: 'O‘rganing. Amalda bajaring. Natijaga erishing.',
  company_name: 'NeoSkill', about_title: 'Ta’limni aniq yo‘l va amaliy natijaga aylantiramiz',
  about_text: '', company_address: '', support_email: '', support_telegram: '', support_phone: '', working_hours: '',
};
const Context = createContext({ settings: defaults, loading: true, error: '', retry: () => {} });
export function PlatformSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState(defaults);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const path = usePathname();
  const retry = useCallback(() => setRevision(value => value + 1), []);
  useEffect(() => {
    const listener = () => retry();
    window.addEventListener('neoskill-settings', listener);
    return () => window.removeEventListener('neoskill-settings', listener);
  }, [retry]);
  useEffect(() => {
    let live = true;
    setLoading(true);
    void api.publicSettings().then(value => { if (live) { setSettings(value); setError(''); } })
      .catch(() => { if (live) setError('Aloqa ma’lumotlarini yuklab bo‘lmadi.'); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [path, revision]);
  return <Context.Provider value={{ settings, loading, error, retry }}>{children}</Context.Provider>;
}
export function usePlatformSettings() { return useContext(Context); }
export function settingsChanged() { window.dispatchEvent(new Event('neoskill-settings')); }
