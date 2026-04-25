#!/usr/bin/env node
// Myco hook guard — silently no-ops when myco is not installed.
//
// This file is committed to the repo so open-source contributors without
// Myco don't see hook errors in their agent sessions. It stays deliberately
// thin: its only jobs are (1) provide a cross-platform entry point that
// works under every shell our symbionts fire hooks from, and (2) resolve
// which myco binary to exec via .myco/runtime.command.
//
// Managed by: myco init / myco update
// Safe to delete: myco remove
'use strict';

// Skip hooks for Myco's own agent pipeline sessions — they are internal
// and should not be captured as user sessions.
if (process.env.MYCO_AGENT_SESSION) process.exit(0);

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

// Defensively pin cwd to the project root. Cursor's hook spawn drops stdin
// when the command uses shell operators, so our installed hook commands
// invoke this guard directly (no `cd "$(...)" &&` prefix). The chdir keeps
// vault resolution working even when the spawning agent's cwd isn't set.
try { process.chdir(path.resolve(__dirname, '..')); } catch { /* best effort */ }

// Resolve which myco binary to invoke.
//
// `.myco/runtime.command` is the source of truth — a one-line plain-text
// file holding either a PATH-resolvable name (`myco`, the default for
// globally-installed users) or an absolute path (`/Users/chris/.local/
// bin/myco-dev`, what `make dev-link` writes). Absolute paths bypass
// PATH entirely, which matters because GUI-launched agents (Cursor,
// Claude Code desktop, etc.) run under macOS launchd and inherit a
// minimal PATH that typically doesn't include `~/.local/bin`.
//
// We locate the alias file via __dirname so the guard doesn't depend on
// cwd. Hook wrappers `cd` to the project root before invoking us, but
// not every agent keeps that contract across every shell.
let bin = 'myco';
try {
  const aliasPath = path.resolve(__dirname, '..', '.myco', 'runtime.command');
  const alias = fs.readFileSync(aliasPath, 'utf-8').trim();
  if (alias) bin = alias;
} catch { /* missing file → use default */ }

try {
  execFileSync(bin, process.argv.slice(2), { stdio: 'inherit' });
} catch (e) {
  if (e.code === 'ENOENT') process.exit(0);
  process.exit(e.status ?? 1);
}
