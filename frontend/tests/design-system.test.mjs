import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

async function filesUnder(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? filesUnder(target) : [target];
  }));
  return nested.flat();
}

test('Figma colors are centralized instead of scattered through components', async () => {
  const files = await filesUnder('src/components');
  for (const file of files) {
    const source = await readFile(file, 'utf8');
    assert.doesNotMatch(source, /#[0-9a-f]{3,8}\b|(?:rgb|hsl)a?\(/i, file);
  }
});

test('the central theme contains the audited Figma palette', async () => {
  const css = (await readFile('src/app/globals.css', 'utf8')).toLowerCase();
  for (const color of [
    '#1d4e79', '#1b1e25', '#6b7078', '#f6f9fc', '#d9dee5', '#e5e8ed',
    '#141a24', '#171c26', '#218c54', '#e3f5e8', '#f59e0a', '#cc3333',
  ]) {
    assert.ok(css.includes(color), `Missing audited token ${color}`);
  }
  assert.match(css, /--shadow-surface:\s*none/);
});

