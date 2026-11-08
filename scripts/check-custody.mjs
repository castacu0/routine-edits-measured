#!/usr/bin/env node
/**
 * Repository-wide zero-custody guard.
 *
 * CLAUDE.md hard rule 1: never download, store, cache or log media content or
 * media URLs. Hard rule 3: tests use /fixtures/dummy_hashes.json only.
 *
 * The unit tests in api/tests/zero-custody.test.ts cover the API source. This
 * script covers the WHOLE REPOSITORY, including files nobody thought to test:
 * a stray media file, a fixture edited to hold real data, a script that
 * downloads something.
 *
 * It runs in CI and in the pre-commit hook. It is fast and has no dependencies.
 *
 * Exit codes: 0 ok, 1 violation.
 */
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, extname, relative, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

const SKIP_DIRS = new Set([
  '.git', 'node_modules', '.next', 'dist', 'build', 'coverage', '.terraform',
  // Toolchain directories: third-party package contents are not ours to audit
  // and are recreated from lockfiles, not committed.
  '.venv', 'venv', '__pycache__',
]);
// Note: no entry here for "results" or any other generic name. A broad skip
// blinds the guard to every directory that happens to share the name, which is
// exactly the kind of quiet weakening this file exists to prevent. The research
// harness writes only JSON and Markdown, so it needs no exception.

/** Media that must never enter the repository under any circumstance. */
const FORBIDDEN_EXTENSIONS = new Set([
  '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.heic',
  '.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v',
]);

/** Non-media exceptions that are safe and expected. */
const ALLOWED_MEDIA_PATHS = [
  'api/app/favicon.ico',
];

/**
 * Directories where generated graphics may live.
 *
 * Narrowly scoped on purpose. The only thing written here is chart output
 * rendered from dossier/deck.html by scripts/build-deck.sh: distribution
 * curves and abstract colour panels. No photograph, no person, no case data,
 * and nothing sourced from outside this repository.
 *
 * These files are also gitignored, so the exception governs a working tree
 * only. If you find yourself wanting to widen this list, that is the signal to
 * stop and escalate rather than to edit this array.
 */
const GENERATED_FIGURE_DIRS = [
  'dossier/export/figures',
];

const violations = [];

function walk(dir, visit) {
  for (const entry of readdirSync(dir)) {
    // Any virtualenv, however it is named.
    if (SKIP_DIRS.has(entry) || entry.startsWith('.venv')) continue;
    const full = join(dir, entry);
    const stats = statSync(full);
    if (stats.isDirectory()) walk(full, visit);
    else visit(full);
  }
}

// ── 1. No media files anywhere ───────────────────────────────────────────────
walk(ROOT, (file) => {
  const rel = relative(ROOT, file);
  if (ALLOWED_MEDIA_PATHS.includes(rel)) return;
  if (GENERATED_FIGURE_DIRS.some((dir) => rel.startsWith(`${dir}/`))) return;
  if (FORBIDDEN_EXTENSIONS.has(extname(file).toLowerCase())) {
    violations.push(
      `MEDIA FILE COMMITTED: ${rel}\n` +
        '    No image or video may exist in this repository. If this is a campaign\n' +
        '    asset, it belongs in an approved asset store after trauma-informed\n' +
        '    review, never here. If it is evidence, it must not exist here at all.',
    );
  }
});

// ── 2. The fixture file must stay synthetic ──────────────────────────────────
const fixturePath = join(ROOT, 'fixtures', 'dummy_hashes.json');
if (!existsSync(fixturePath)) {
  violations.push('fixtures/dummy_hashes.json is missing. Tests have no legal dataset.');
} else {
  let fixture;
  try {
    fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
  } catch (err) {
    violations.push(`fixtures/dummy_hashes.json is not valid JSON: ${err.message}`);
  }
  if (fixture) {
    const entries = Array.isArray(fixture) ? fixture : (fixture.hashes ?? []);
    if (entries.length === 0) {
      violations.push('fixtures/dummy_hashes.json contains no hashes.');
    }
    for (const [i, entry] of entries.entries()) {
      if (entry.label !== 'dummy_test_only') {
        violations.push(
          `fixtures/dummy_hashes.json entry ${i} is not labelled "dummy_test_only".\n` +
            '    Only synthetic data may live in /fixtures. CLAUDE.md hard rule 3.',
        );
      }
      if (!/^[a-f0-9]{64}$/.test(entry.hashPDQ ?? '')) {
        violations.push(`fixtures/dummy_hashes.json entry ${i} is not a 64-char hex PDQ hash.`);
      }
    }
    const raw = readFileSync(fixturePath, 'utf8');
    if (/https?:\/\//.test(raw)) {
      violations.push(
        'fixtures/dummy_hashes.json contains a URL. Fixtures hold hashes and labels only.',
      );
    }
  }
}

// ── 3. No committed .env ─────────────────────────────────────────────────────
walk(ROOT, (file) => {
  const rel = relative(ROOT, file);
  const base = rel.split('/').pop() ?? '';
  if (base === '.env' || (base.startsWith('.env.') && base !== '.env.example')) {
    violations.push(
      `SECRET FILE COMMITTED: ${rel}\n` +
        '    CLAUDE.md hard rule 6: nothing in .env is committed. Only .env.example.',
    );
  }
  if (/^service-account.*\.json$/.test(base) || /firebase-adminsdk.*\.json$/.test(base)) {
    violations.push(`CREDENTIAL FILE COMMITTED: ${rel}`);
  }
});

// ── 4. Terraform must not create object storage ──────────────────────────────
// A bucket that exists is a bucket something will eventually write to.
const tfDir = join(ROOT, 'infra', 'terraform');
if (existsSync(tfDir)) {
  walk(tfDir, (file) => {
    if (extname(file) !== '.tf') return;
    const source = readFileSync(file, 'utf8').replace(/(^|\s)#.*$/gm, '$1');
    for (const resource of ['google_storage_bucket', 'google_compute_backend_bucket']) {
      if (new RegExp(`resource\\s+"${resource}"`).test(source)) {
        violations.push(
          `${relative(ROOT, file)} declares ${resource}.\n` +
            '    This project provisions no object storage. Media is never held.\n' +
            '    A change that adds one needs written sign-off from Cesar and Lorena.',
        );
      }
    }
  });
}

// ── Report ───────────────────────────────────────────────────────────────────
if (violations.length > 0) {
  console.error('\n✖ ZERO-CUSTODY VIOLATION\n');
  for (const violation of violations) console.error(`  - ${violation}\n`);
  console.error('These are hard rules from CLAUDE.md. They are not negotiable in review.\n');
  process.exit(1);
}

console.log('✔ Zero-custody checks passed.');
