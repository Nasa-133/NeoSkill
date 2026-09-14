import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { ESLint } from 'eslint';

test('frontend rejects imports of backend internals', async () => {
  const eslint = new ESLint();
  for (const specifier of ['../../backend/src/app', '@neoskill/backend', '@neoskill/backend/catalog']) {
    const [result] = await eslint.lintText(`import '${specifier}';`, { filePath: 'src/boundary-probe.ts' });
    assert.ok(result.messages.some((message) => message.ruleId === 'no-restricted-imports'), specifier);
  }
});

test('the install manifest has no workspace or filesystem dependencies', async () => {
  const manifest = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));
  assert.equal(manifest.workspaces, undefined);
  for (const [name, version] of Object.entries({ ...manifest.dependencies, ...manifest.devDependencies })) {
    assert.doesNotMatch(version, /^(file:|link:|workspace:|\.\.?\/|\/)/, name);
    assert.notEqual(name, '@neoskill/backend');
  }
});
