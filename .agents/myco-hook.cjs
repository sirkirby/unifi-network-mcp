#!/usr/bin/env node
// Myco hook guard — silently no-ops when myco-run is not installed.
// This file is committed to the repo so open-source contributors
// without Myco don't see hook errors in their agent sessions.
//
// Managed by: myco init / myco update
// Safe to delete: myco remove
'use strict';
// Skip hooks for Myco's own agent pipeline sessions — they are internal
// and should not be captured as user sessions.
if (process.env.MYCO_AGENT_SESSION) process.exit(0);
const { execFileSync } = require('child_process');
const bin = process.env.MYCO_CMD || 'myco-run';
try {
  execFileSync(bin, process.argv.slice(2), { stdio: 'inherit' });
} catch (e) {
  if (e.code === 'ENOENT') process.exit(0);
  process.exit(e.status ?? 1);
}
