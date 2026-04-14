// Managed by Myco. Regenerated on `myco update`. Edit src/symbionts/templates/opencode/plugin.ts in the Myco repo instead.
// myco:plugin-marker:opencode
//
// Myco Codebase Intelligence Plugin for OpenCode.
//
// This plugin runs inside opencode's Bun runtime and communicates with the local
// Myco daemon over HTTP — no subprocess spawns, no hook CLI, no stdin piping.
//
//   Capture: POST /sessions/register, /sessions/unregister, /events, /events/stop
//   Context: GET  /api/digest
//   Inject:  client.session.prompt({ noReply: true, parts: [{ synthetic: true }] })
//
// See https://opencode.ai/docs/plugins/
//
// Degraded-mode safety: this plugin ships committed inside any project that has
// run `myco init` — the file lives at .opencode/plugins/myco.ts in that project's
// repo. When a teammate clones such a project WITHOUT having Myco installed
// locally, opencode will still load this plugin (the file is right there in the
// cloned repo). To stay invisible in that case, the plugin has NO external
// runtime imports — only node:fs and node:path, which are always available in
// Bun's runtime. Every path that would contact the Myco daemon gracefully no-ops
// when `.myco/daemon.json` is absent or the daemon is unreachable, so the plugin
// becomes invisible rather than throwing. Do NOT add runtime imports from
// @opencode-ai/plugin or any other package — that would break this guarantee.

import { readFileSync, appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Keep in sync with `TOOL_OUTPUT_PREVIEW_CHARS` in src/constants.ts (currently 200).
 * The plugin file is standalone and cannot import from Myco — this value is copied
 * so every symbiont records tool_output previews at the same length.
 */
const TOOL_OUTPUT_PREVIEW_CHARS = 200;

/** Timeout for daemon HTTP calls — must be short so we never block opencode. */
const MYCO_FETCH_TIMEOUT_MS = 3000;

/** Tail window read from opencode when building the end-of-turn assistant summary. */
const SESSION_IDLE_TAIL_LIMIT = 12;

/** Max size of resume context injection to keep resumed sessions lean. */
const RESUME_CONTEXT_MAX_CHARS = 4000;

/** Heading prefix for compaction context — makes Myco's contribution recognizable in the compacted summary. */
const COMPACTION_HEADING = "## Myco — Project Context (preserved across compaction)\n\n";

/**
 * Marker set on the `metadata` field of every synthetic TextPartInput this
 * plugin injects via `client.session.prompt({ noReply: true, ... })`. The
 * `chat.message` handler checks for this marker and skips matching messages
 * so the injection doesn't re-enter as if it were a new user prompt.
 *
 * Why not the `synthetic` flag? opencode's own prompt.ts uses `synthetic: true`
 * for ~20 distinct internal purposes (plan-mode prompts, build-switch
 * transitions, subagent task summaries, shell-impl wrappers). Filtering on
 * the synthetic flag rejects legitimate user messages whenever opencode has
 * appended one of its own synthetic parts — which caused real user prompts
 * to silently drop in live testing.
 */
const MYCO_METADATA_MARKER = "myco";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type MessagePart = { type?: string; text?: string };
type SessionMessage = { info?: { role?: string }; parts?: MessagePart[] };

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function pickString(
  record: Record<string, unknown>,
  keys: readonly string[],
): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return undefined;
}

export function normalizeToolInput(toolInput: unknown): unknown {
  if (!isRecord(toolInput)) return toolInput;

  const filePath = pickString(toolInput, ["file_path", "filePath", "path"]);
  const workdir = pickString(toolInput, ["workdir", "cwd"]);
  const command = pickString(toolInput, ["command", "cmd"]);

  return {
    ...toolInput,
    ...(filePath ? { file_path: filePath } : {}),
    ...(workdir ? { workdir } : {}),
    ...(command ? { command } : {}),
  };
}

export function collectAssistantSummaryFromMessages(messages: SessionMessage[]): string {
  const summaryParts: string[] = [];
  let foundAssistantBlock = false;

  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (message?.info?.role !== "assistant") {
      if (foundAssistantBlock) break;
      continue;
    }

    foundAssistantBlock = true;
    const text = (message.parts ?? [])
      .filter((part) => part.type === "text" && part.text)
      .map((part) => part.text as string)
      .join("\n")
      .trim();
    if (text) summaryParts.unshift(text);
  }

  return summaryParts.join("\n").trim();
}

// ---------------------------------------------------------------------------
// Daemon HTTP transport — all communication with the local Myco daemon.
// Every function is best-effort: failures are swallowed so the plugin cannot
// interfere with opencode when Myco is absent or the daemon is unreachable.
// ---------------------------------------------------------------------------

/**
 * Port cache for `.myco/daemon.json`. Read once on first access; refreshed on
 * the next call that follows a failed HTTP request (handles daemon restarts
 * mid-session). `undefined` = never loaded, `null` = loaded but absent.
 */
let cachedDaemonPort: number | null | undefined = undefined;

/**
 * Active opencode sessions tracked by this plugin instance. Populated on
 * `session.created` and drained on `session.deleted` / `server.instance.disposed`.
 *
 * Opencode has no `session.end` event — when the TUI exits normally (Ctrl+C,
 * close terminal), the session stays "active" from the daemon's perspective
 * until the session-maintenance job sweeps it (1-hour threshold). To close
 * sessions cleanly on TUI exit, we track them locally and call unregister
 * for each one when `server.instance.disposed` fires.
 */
const activeOpencodeSessions = new Set<string>();

/** Resume injections are process-local and should run at most once per session. */
const resumeInjectedSessions = new Set<string>();

/** Read the Myco daemon port from .myco/daemon.json in the project directory. */
function readDaemonPortFromDisk(directory: string): number | null {
  try {
    const raw = readFileSync(join(directory, ".myco", "daemon.json"), "utf-8");
    const info = JSON.parse(raw) as { port?: number };
    return typeof info.port === "number" ? info.port : null;
  } catch {
    return null;
  }
}

/** Get the cached daemon port, loading from disk on first access. */
function getDaemonPort(directory: string): number | null {
  if (cachedDaemonPort === undefined) cachedDaemonPort = readDaemonPortFromDisk(directory);
  return cachedDaemonPort;
}

/** Force-refresh the daemon port from disk — used after a fetch failure in case the daemon restarted. */
function refreshDaemonPort(directory: string): number | null {
  cachedDaemonPort = readDaemonPortFromDisk(directory);
  return cachedDaemonPort;
}

/** Fetch with a short timeout. Returns the Response on success, null on failure. */
async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), MYCO_FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    return res.ok ? res : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch from a daemon endpoint with a single retry after refreshing the port.
 * The retry handles the case where the daemon restarted on a different port
 * mid-session; the cache hot-path avoids a sync disk read on every HTTP call.
 */
async function fetchFromDaemon(
  directory: string,
  path: string,
  init?: RequestInit,
): Promise<Response | null> {
  const port = getDaemonPort(directory);
  if (!port) return null;

  const first = await fetchWithTimeout(`http://localhost:${port}${path}`, init);
  if (first) return first;

  // Retry once with a refreshed port — the daemon may have restarted.
  const freshPort = refreshDaemonPort(directory);
  if (!freshPort || freshPort === port) return null;
  return fetchWithTimeout(`http://localhost:${freshPort}${path}`, init);
}

/**
 * POST JSON to a daemon endpoint.
 * Returns `{ ok, data }` — `ok` is true when the HTTP call succeeded, `data`
 * is the parsed response body (may be absent if the body was empty or not JSON).
 */
async function postJson(
  directory: string,
  path: string,
  body: Record<string, unknown>,
): Promise<{ ok: boolean; data?: unknown }> {
  const res = await fetchFromDaemon(directory, path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res) return { ok: false };
  try {
    return { ok: true, data: await res.json() };
  } catch {
    return { ok: true };
  }
}

/**
 * Append an event to the local buffer at .myco/buffer/<session-id>.jsonl.
 *
 * Used as a fallback when the daemon HTTP POST fails (daemon down, network
 * error, timeout). The daemon replays buffered events via reconcileBufferBatches
 * at startup, so events captured here are NOT lost — they land in the vault
 * the next time the daemon comes back up. Mirrors the fallback pattern in
 * src/hooks/send-event.ts + src/capture/buffer.ts that every other symbiont
 * uses (claude-code, cursor, codex, etc.) via the hook CLI path.
 *
 * Without this fallback, opencode would have a significant parity gap — all
 * other symbionts preserve events across daemon downtime, but opencode events
 * would be silently dropped the moment the daemon was unreachable.
 *
 * The entry shape matches EventBuffer.append(): event payload with session_id
 * stripped (it's in the filename) and an auto-injected ISO timestamp.
 */
function bufferEvent(
  directory: string,
  sessionId: string,
  event: Record<string, unknown>,
): void {
  try {
    const bufferDir = join(directory, ".myco", "buffer");
    mkdirSync(bufferDir, { recursive: true });
    const filePath = join(bufferDir, `${sessionId}.jsonl`);
    // Strip session_id from the entry — it's encoded in the filename
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { session_id: _sid, ...payload } = event;
    const line = JSON.stringify({
      ...payload,
      timestamp: payload.timestamp ?? new Date().toISOString(),
    });
    appendFileSync(filePath, line + "\n");
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[myco] Failed to buffer event:", err);
  }
}

/**
 * POST a capture event to the daemon with buffer fallback on failure.
 * Used for user_prompt and tool_use events — both are replayed from the
 * buffer by reconcileBufferBatches when the daemon restarts.
 */
async function postEventWithBuffer(
  directory: string,
  sessionId: string,
  event: Record<string, unknown>,
): Promise<void> {
  const result = await postJson(directory, "/events", event);
  if (!result.ok) {
    bufferEvent(directory, sessionId, event);
  }
}

/** Register an opencode session with the daemon. */
async function mycoRegisterSession(
  directory: string,
  sessionId: string,
  parentSessionId: string | undefined,
): Promise<void> {
  await postJson(directory, "/sessions/register", {
    session_id: sessionId,
    agent: "opencode",
    parent_session_id: parentSessionId,
    started_at: new Date().toISOString(),
  });
}

/** Unregister an opencode session. */
async function mycoUnregisterSession(directory: string, sessionId: string): Promise<void> {
  await postJson(directory, "/sessions/unregister", { session_id: sessionId });
}

/** Post a user prompt event. Images, if any, are shipped as an array of
 * `{ data: base64, mediaType }` objects — the daemon's event dispatcher persists
 * them as attachments keyed to the newly-opened prompt batch.
 *
 * Opencode has no on-disk transcript for Myco to mine, so images attached by
 * the user in the TUI must travel with the prompt event itself. Other symbionts
 * (claude-code, cursor) extract images from their JSONL transcripts at stop time.
 *
 * Falls back to the local buffer if the daemon is unreachable so events are
 * replayed on daemon restart (same resilience the other symbionts get via
 * src/hooks/send-event.ts).
 */
async function mycoPostUserPrompt(
  directory: string,
  sessionId: string,
  prompt: string,
  images: Array<{ data: string; mediaType: string }>,
): Promise<void> {
  await postEventWithBuffer(directory, sessionId, {
    type: "user_prompt",
    session_id: sessionId,
    agent: "opencode",
    prompt,
    ...(images.length > 0 ? { images } : {}),
  });
}

/** Post a tool use event. Falls back to the local buffer on failure. */
async function mycoPostToolUse(
  directory: string,
  sessionId: string,
  toolName: string,
  toolInput: unknown,
  toolOutput: string,
): Promise<void> {
  await postEventWithBuffer(directory, sessionId, {
    type: "tool_use",
    session_id: sessionId,
    agent: "opencode",
    tool_name: toolName,
    tool_input: toolInput,
    output_preview: toolOutput,
  });
}

/** Post a stop event with the last assistant message as the response summary. */
async function mycoPostStop(
  directory: string,
  sessionId: string,
  lastAssistantMessage: string | undefined,
): Promise<void> {
  await postJson(directory, "/events/stop", {
    session_id: sessionId,
    agent: "opencode",
    last_assistant_message: lastAssistantMessage,
  });
}

/**
 * Fetch the session-start context for a new opencode session. Hits the daemon's
 * config-aware `POST /context` endpoint, which selects the digest tier the user
 * has configured (`config.context.digest_tier`, default 5000) and returns the
 * full session context (digest + branch + session ID lines).
 *
 * This is the same endpoint Claude Code's session-start hook uses, so opencode
 * sessions receive the same context the user has configured for every other agent.
 */
async function fetchMycoSessionContext(
  directory: string,
  sessionId: string,
): Promise<string | null> {
  const result = await postJson(directory, "/context", { session_id: sessionId });
  if (!result.ok) return null;
  const data = result.data as { text?: string } | undefined;
  const text = data?.text?.trim() ?? "";
  return text.length > 0 ? text : null;
}

/** Fetch a small resume recap for a resumed opencode session. */
async function fetchMycoResumeContext(
  directory: string,
  sessionId: string,
  parentSessionId: string,
): Promise<string | null> {
  const result = await postJson(directory, "/context/resume", {
    session_id: sessionId,
    parent_session_id: parentSessionId,
  });
  if (!result.ok) return null;
  const data = result.data as { text?: string } | undefined;
  const text = data?.text?.trim() ?? "";
  if (!text || text.length > RESUME_CONTEXT_MAX_CHARS) return null;
  return text;
}

/** Post a compaction telemetry event. */
async function mycoPostCompact(
  directory: string,
  sessionId: string,
  trigger: string | undefined,
): Promise<void> {
  await postEventWithBuffer(directory, sessionId, {
    type: "pre_compact",
    session_id: sessionId,
    agent: "opencode",
    ...(trigger ? { trigger } : {}),
  });
}

// ---------------------------------------------------------------------------
// Opencode session injection — push synthetic context into session history.
// ---------------------------------------------------------------------------

/**
 * Inject text into an opencode session as a synthetic (plugin-authored) user turn
 * without triggering an AI response. The text part carries:
 *   - `synthetic: true` so opencode's TUI hides it from the chat log
 *   - `metadata.myco: true` so our own `chat.message` handler can distinguish
 *     this re-entry from a real user message (see MYCO_METADATA_MARKER)
 * Errors are swallowed — injection is best-effort.
 */
async function injectSyntheticContext(
  client: unknown,
  sessionId: string,
  text: string,
): Promise<void> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const c = client as any;
    await c.session.prompt({
      path: { id: sessionId },
      body: {
        parts: [
          {
            type: "text",
            text,
            synthetic: true,
            metadata: { [MYCO_METADATA_MARKER]: true },
          },
        ],
        noReply: true,
      },
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("[myco] Failed to inject synthetic context:", error);
  }
}

/** Flatten todo items into a newline-separated summary. */
function formatTodos(
  todos: Array<{ id?: string; content?: string; status?: string }>,
): string {
  if (!todos || todos.length === 0) return "";
  return todos
    .map((t) => `[${t.status || "pending"}] ${t.content || ""}`)
    .join("\n");
}

/** Truncate tool output for storage. */
function summarizeToolOutput(output: unknown): string {
  if (typeof output !== "string") return "";
  return output.length > TOOL_OUTPUT_PREVIEW_CHARS
    ? output.slice(0, TOOL_OUTPUT_PREVIEW_CHARS) + "..."
    : output;
}

// ---------------------------------------------------------------------------
// Plugin entry
// ---------------------------------------------------------------------------

/**
 * Opencode plugin entry. The function signature matches opencode's Plugin type
 * via duck typing — we deliberately do NOT import the Plugin type from
 * @opencode-ai/plugin so this file has zero external runtime dependencies.
 * That guarantee lets teammates who clone a project that uses Myco still run
 * opencode cleanly even when they don't have Myco installed locally.
 *
 * @param {{ client: any, directory: string, worktree: string }} ctx
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const MycoPlugin = async ({ client, directory, worktree }: { client: any; directory: string; worktree: string }) => {
  // Best-effort init log. Wrapped in try-catch so a future SDK shape change in
  // opencode (e.g. client.app.log moving) cannot prevent the plugin from
  // registering its handlers.
  try {
    await client.app.log({
      service: "myco",
      level: "info",
      message: "Myco plugin initialized",
      extra: { directory, worktree },
    });
  } catch {
    // Swallow — init log is diagnostic only.
  }

  return {
    /**
     * Generic event handler: session lifecycle, todos.
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: async ({ event }: { event: any }) => {
      if (event.type === "session.created") {
        const info = event.properties?.info ?? {};
        const sessionId: string | undefined = info.id;
        if (!sessionId) return;

        activeOpencodeSessions.add(sessionId);

        const parentSessionId = info.parentID || undefined;
        const contextPromise = parentSessionId
          ? (resumeInjectedSessions.has(sessionId)
            ? Promise.resolve(null)
            : fetchMycoResumeContext(directory, sessionId, parentSessionId))
          : fetchMycoSessionContext(directory, sessionId);

        // Run registration and context fetch concurrently — they don't depend
        // on each other, and parallelizing saves one round-trip of latency.
        const [, sessionContext] = await Promise.all([
          mycoRegisterSession(directory, sessionId, parentSessionId),
          contextPromise,
        ]);

        if (sessionContext) {
          await injectSyntheticContext(client, sessionId, sessionContext);
          if (parentSessionId) resumeInjectedSessions.add(sessionId);
        }
        return;
      }

      if (event.type === "session.deleted") {
        const info = event.properties?.info ?? {};
        if (info.id) {
          activeOpencodeSessions.delete(info.id);
          resumeInjectedSessions.delete(info.id);
          await mycoUnregisterSession(directory, info.id);
        }
        return;
      }

      if (event.type === "server.instance.disposed") {
        // Opencode TUI is shutting down. Flush all tracked sessions so the
        // daemon can mark them completed immediately rather than waiting for
        // the stale-session maintenance sweep (1-hour threshold).
        //
        // Fire-and-forget-parallel: the Bun process is about to exit, so we
        // can't rely on awaited fetches completing. Promise.all gives the
        // unregister calls their best shot at landing before teardown; any
        // that don't make it fall back to the session-maintenance job.
        if (activeOpencodeSessions.size === 0) return;
        const toClose = Array.from(activeOpencodeSessions);
        activeOpencodeSessions.clear();
        for (const id of toClose) resumeInjectedSessions.delete(id);
        await Promise.all(toClose.map((id) => mycoUnregisterSession(directory, id)));
        return;
      }

      if (event.type === "session.idle") {
        const sessionId = event.properties?.sessionID;
        if (!sessionId) return;

        // Fetch the last assistant message for a response summary.
        let responseSummary = "";
        try {
          // `limit` is a tail-limit in opencode's server (returns the last N
          // messages in chronological order — verified empirically against
          // opencode v1.4.1 via `opencode serve`). The tail window is large
          // enough to capture a multi-message assistant block at end-of-turn
          // without reading the full session history on every idle event.
          const result = await client.session.messages({
            path: { id: sessionId },
            query: { directory, limit: SESSION_IDLE_TAIL_LIMIT },
          });
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const messages = ((result as any)?.data ?? []) as SessionMessage[];
          responseSummary = collectAssistantSummaryFromMessages(messages);
        } catch (err) {
          // eslint-disable-next-line no-console
          console.error("[myco] Failed to fetch messages for summary:", err);
        }

        await mycoPostStop(directory, sessionId, responseSummary || undefined);
        return;
      }

      if (event.type === "todo.updated") {
        const sessionId = event.properties?.sessionID;
        if (!sessionId) return;
        const todos = event.properties?.todos ?? [];
        await mycoPostToolUse(
          directory,
          sessionId,
          "TodoUpdate",
          { todos, count: todos.length },
          formatTodos(todos),
        );
      }
    },

    /**
     * Chat message: capture the user prompt + any image attachments.
     *
     * Per-turn spore injection is intentionally not done here. A previous iteration
     * injected spores via session.prompt({ noReply: true }) inside this handler, but
     * opencode re-fires chat.message for the synthetic turn and the first real user
     * message landed during the re-entrancy window. Agents can fetch context on
     * demand via the myco_context and myco_search MCP tools.
     *
     * Re-entrancy guard: we check for `metadata.myco === true` on any part to
     * detect our session-start digest injection coming back around. Opencode
     * itself sets `synthetic: true` for many internal purposes (plan-mode
     * prompts, build-switch transitions, subagent task summaries), so the
     * `synthetic` flag alone is NOT reliable as a re-entrancy signal — it
     * would silently drop any user prompt that opencode touched for one of
     * those internal reasons.
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    "chat.message": async (input: any, output: any) => {
      const sessionId = input?.sessionID;
      if (!sessionId) return;

      // Part shapes we care about: text (for the prompt string) and file
      // (for image attachments encoded as data URLs — FilePart.url is
      // `data:<mime>;base64,<data>` per
      // packages/app/src/components/prompt-input/attachments.ts in opencode).
      const allParts = (output?.parts ?? []) as Array<{
        type?: string;
        text?: string;
        mime?: string;
        url?: string;
        synthetic?: boolean;
        metadata?: { [key: string]: unknown };
      }>;
      // Skip if any part carries the Myco metadata marker — that means
      // chat.message is firing for our own injectSyntheticContext call.
      if (allParts.some((p) => p.metadata?.[MYCO_METADATA_MARKER] === true)) return;

      // Prompt text = user's real text only. opencode emits `synthetic: true`
      // text parts for internal scaffolding when the message contains file
      // mentions, plan-mode switches, subagent tasks, and similar — see
      // packages/opencode/src/session/prompt.ts. Those parts include full
      // file contents, tool-call scaffolding, plan instructions, etc. Joining
      // them into prompt_text would bloat every captured user prompt with
      // system-level content that the user never typed.
      const textParts = allParts
        .filter((p) => p.type === "text" && p.text && p.synthetic !== true)
        .map((p) => p.text as string);
      const prompt = textParts.join("\n");
      if (!prompt) return;

      // Extract any image attachments from FilePart data URLs. Non-image file
      // parts (code snippets, documents) are ignored here — only images travel
      // to Myco as binary attachments via the existing attachment pipeline.
      const images: Array<{ data: string; mediaType: string }> = [];
      for (const part of allParts) {
        if (
          part.type !== "file" ||
          !part.mime?.startsWith("image/") ||
          typeof part.url !== "string" ||
          !part.url.startsWith("data:")
        ) {
          continue;
        }
        const commaIdx = part.url.indexOf(",");
        if (commaIdx <= 0) continue;
        const base64 = part.url.slice(commaIdx + 1);
        if (base64) images.push({ data: base64, mediaType: part.mime });
      }

      await mycoPostUserPrompt(directory, sessionId, prompt, images);
    },

    /**
     * Post-tool execution: ship tool usage to Myco.
     *
     * We forward `input.args` as `tool_input` — NOT `output.metadata` — because
     * `args` carries the tool invocation arguments (including `filePath` for
     * write/edit/patch tools), which Myco's plan-capture matcher needs to detect
     * writes to .opencode/plans/*.md.
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    "tool.execute.after": async (input: any, output: any) => {
      const sessionId = input?.sessionID;
      if (!sessionId) return;

      const toolName = input?.tool ?? "unknown";
      const toolInput = normalizeToolInput(input?.args ?? output?.metadata ?? {});
      const toolOutput = summarizeToolOutput(output?.output);

      await mycoPostToolUse(directory, sessionId, toolName, toolInput, toolOutput);
    },

    /**
     * Compaction hook: fires BEFORE opencode generates a continuation summary
     * during session compaction. Pushing the session context into output.context
     * ensures Myco's project knowledge survives compaction rather than being
     * dropped. The fetched context respects the user's configured digest tier.
     *
     * See https://opencode.ai/docs/plugins/#compaction-hooks
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    "experimental.session.compacting": async (input: any, output: any) => {
      const sessionId = input?.sessionID;
      if (!sessionId) return;

      await mycoPostCompact(directory, sessionId, typeof input?.trigger === "string" ? input.trigger : undefined);

      const sessionContext = await fetchMycoSessionContext(directory, sessionId);
      if (!sessionContext) return;

      if (Array.isArray(output?.context)) {
        output.context.push(COMPACTION_HEADING + sessionContext);
      }
    },
  };
};

export default MycoPlugin;
