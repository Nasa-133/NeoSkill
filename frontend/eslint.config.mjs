import { defineConfig, globalIgnores } from 'eslint/config';
import js from '@eslint/js';
import next from '@next/eslint-plugin-next';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default defineConfig([
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.mjs'],
    languageOptions: { globals: globals.node },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: { '@next/next': next },
    rules: {
      ...next.configs.recommended.rules,
      ...next.configs['core-web-vitals'].rules,
    },
  },
  {
    rules: {
      'no-restricted-imports': ['error', {
        patterns: [{
          group: ['**/backend', '**/backend/**', '@neoskill/backend', '@neoskill/backend/**'],
          message: 'Use the HTTP API; backend internals do not belong in the frontend.',
        }],
      }],
    },
  },
  globalIgnores(['.next/**', 'coverage/**', 'next-env.d.ts']),
]);
