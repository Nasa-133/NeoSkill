'use client';

import { useEffect } from 'react';

const storageKey = 'neoskill-referral-code';
const codePattern = /^[23456789A-HJ-NP-Z]{12}$/;

export function normalizeReferralCode(value: string) {
  return value.trim().toUpperCase();
}

export function storedReferralCode() {
  if (typeof window === 'undefined') return '';
  const value = normalizeReferralCode(window.localStorage.getItem(storageKey) ?? '');
  return codePattern.test(value) ? value : '';
}

export function forgetReferralCode() {
  if (typeof window !== 'undefined') window.localStorage.removeItem(storageKey);
}

export function ReferralCapture() {
  useEffect(() => {
    const code = normalizeReferralCode(new URLSearchParams(window.location.search).get('ref') ?? '');
    if (codePattern.test(code)) window.localStorage.setItem(storageKey, code);
  }, []);
  return null;
}
