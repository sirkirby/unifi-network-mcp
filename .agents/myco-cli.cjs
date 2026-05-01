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
// globally-installed users) or an absolute path to a dev binary (what
// `make dev-link` writes). Absolute paths bypass
// PATH entirely, which matters because GUI-launched agents (Cursor,
// Claude Code desktop, etc.) run under macOS launchd and inherit a
// minimal PATH that typically doesn't include `~/.local/bin`.
//
// Runtime scope is an entrypoint concern, not a CLI subcommand concern:
//
// - capture scope (`.agents/myco-run.cjs`) uses the main repo pin in git
//   worktrees so hook capture keeps writing to the shared vault.
// - project scope (`.agents/myco-cli.cjs`) prefers a worktree-local pin for
//   interactive CLI/tool testing, then falls back to the main repo pin.
const args = process.argv.slice(2);
const runtimeScope = resolveRuntimeScope();
let bin = 'myco';
const alias = findRuntimeCommand(process.cwd(), runtimeScope);
if (alias) bin = alias;

function resolveRuntimeScope() {
  const envScope = process.env.MYCO_RUNTIME_SCOPE;
  if (envScope === 'capture' || envScope === 'project') return envScope;
  return path.basename(process.argv[1] || '') === 'myco-cli.cjs' ? 'project' : 'capture';
}

function findRuntimeCommand(cwd, scope) {
  try {
    if (scope === 'capture') {
      return findRuntimeCommandFrom(resolveSearchStart(cwd));
    }

    const local = findRuntimeCommandFrom(path.resolve(cwd));
    if (local) return local;

    const fallbackStart = resolveSearchStart(cwd);
    if (path.resolve(fallbackStart) === path.resolve(cwd)) return null;
    return findRuntimeCommandFrom(fallbackStart);
  } catch {
    return null;
  }
}

function findRuntimeCommandFrom(startDir) {
  let dir = path.resolve(startDir);
  while (true) {
    const aliasPath = path.join(dir, '.myco', 'runtime.command');
    try {
      const alias = fs.readFileSync(aliasPath, 'utf-8').trim();
      if (alias) return alias;
    } catch { /* not here */ }
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function resolveSearchStart(cwd) {
  let dir = path.resolve(cwd);
  while (true) {
    const gitEntry = path.join(dir, '.git');
    try {
      const stat = fs.lstatSync(gitEntry);
      if (stat.isDirectory()) return dir;
      if (stat.isFile()) {
        const content = fs.readFileSync(gitEntry, 'utf-8').trim();
        const match = content.match(/^gitdir:\s*(.+)$/m);
        if (match && match[1]) {
          const gitdir = path.isAbsolute(match[1]) ? match[1] : path.resolve(dir, match[1]);
          return path.resolve(gitdir, '..', '..', '..');
        }
        return dir;
      }
    } catch {
      // no .git here; keep walking
    }
    const parent = path.dirname(dir);
    if (parent === dir) return cwd;
    dir = parent;
  }
}

function toolNameFromArgs(args) {
  if (args[0] !== 'tool' || args[1] !== 'call') return undefined;
  for (let idx = 2; idx < args.length; idx++) {
    const arg = args[idx];
    if (arg === '--json') continue;
    if (arg === '--input') {
      idx++;
      continue;
    }
    if (arg && !arg.startsWith('-')) return arg;
  }
  return undefined;
}

function writeToolRuntimeUnavailable(command, args) {
  const tool = toolNameFromArgs(args);
  const envelope = {
    ok: false,
    ...(tool ? { tool } : {}),
    error: {
      code: 'runtime_unavailable',
      message: `Myco runtime command '${command}' could not be found. Check .myco/runtime.command or run Myco update from a shell where Myco is installed.`,
    },
  };
  process.stdout.write(`${JSON.stringify(envelope, null, 2)}\n`);
}

try {
  execFileSync(bin, args, { stdio: 'inherit' });
} catch (e) {
  if (e.code === 'ENOENT') {
    if (args[0] === 'tool') {
      writeToolRuntimeUnavailable(bin, args);
      process.exit(1);
    }
    process.exit(0);
  }
  process.exit(e.status ?? 1);
}
