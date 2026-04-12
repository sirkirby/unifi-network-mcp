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

// Resolve the myco command name.
//
// Source of truth is `.myco/runtime.command` — a one-line plain-text file
// containing the command to invoke (e.g. `myco`, `myco-dev`, or a user's
// own alias). When absent or empty, the default is `myco`.
//
// We resolve the file path via __dirname so the guard doesn't depend on
// the agent's current working directory. Lifecycle hook wrappers `cd` to
// project root before invoking us, but not every agent keeps that contract
// reliably under every shell — __dirname removes the dependency entirely.
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
