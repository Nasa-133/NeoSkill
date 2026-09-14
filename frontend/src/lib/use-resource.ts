'use client';

import { useCallback, useEffect, useState } from 'react';
import { useMockData } from './api';

export function useResource<T>(loadApi: () => Promise<T>, loadMock: () => T) {
  const [data, setData] = useState<T | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const load = useCallback(async () => { setLoading(true); setError(''); try { setData(useMockData ? loadMock() : await loadApi()); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Ma’lumotni yuklab bo‘lmadi.'); } finally { setLoading(false); } }, [loadApi, loadMock]);
  useEffect(() => { void load(); }, [load]);
  return { data, loading, error, retry: load, setData };
}

export function simulateMutation<T>(value: T, delay = 450) { return new Promise<T>(resolve => window.setTimeout(() => resolve(value), delay)); }
