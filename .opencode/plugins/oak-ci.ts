/**
 * OAK Codebase Intelligence Plugin for OpenCode
 *
 * This plugin integrates OpenCode with OAK's Codebase Intelligence system,
 * enabling session tracking, memory injection, and activity capture.
 *
 * Events handled:
 * - session.created: Initialize CI session, inject context
 * - chat.message: Capture user prompts, create prompt batches
 * - tool.execute.after: Capture tool usage, inject relevant memories
 * - session.idle: End prompt batch, fetch response summary, trigger processing
 * - session.deleted: Finalize session, generate summary
 * - file.edited: Capture file modifications
 * - todo.updated: Capture agent planning/task list updates
 *
 * @see https://opencode.ai/docs/plugins/
 */

import type { Plugin } from "@opencode-ai/plugin";

/**
 * Helper to call oak ci hook command with JSON payload
 */
async function callOakHook(
  $: any,
  hookName: string,
  payload: Record<string, unknown>
): Promise<{ success: boolean; result?: unknown; error?: string }> {
  try {
    const jsonPayload = JSON.stringify(payload);
    const result =
      await $`echo ${jsonPayload} | oak ci hook ${hookName} --agent opencode`;
    return { success: true, result };
  } catch (error) {
    // Don't let hook failures break OpenCode - log and continue
    console.error(`[oak-ci] Hook ${hookName} failed:`, error);
    return { success: false, error: String(error) };
  }
}

/**
 * Format todo items for storage
 */
function formatTodos(
  todos: Array<{ id?: string; content?: string; status?: string }>
): string {
  if (!todos || todos.length === 0) return "";
  return todos.map((t) => `[${t.status || "pending"}] ${t.content || ""}`).join("\n");
}

/**
 * OAK Codebase Intelligence Plugin
 */
export const OakCIPlugin: Plugin = async ({ project, client, $, directory, worktree }) => {
  // Log plugin initialization
  await client.app.log({
    service: "oak-ci",
    level: "info",
    message: "OAK Codebase Intelligence plugin initialized",
    extra: { directory, worktree },
  });

  return {
    /**
     * Session created - initialize CI tracking
     */
    event: async ({ event }) => {
      // session.created: properties.info is a Session object with { id, parentID?, ... }
      if (event.type === "session.created") {
        const info = (event.properties as any)?.info || {};
        await callOakHook($, "sessionStart", {
          session_id: info.id,
          parent_session_id: info.parentID || undefined,
          agent: "opencode",
          source: info.parentID ? "resume" : "startup",
        });
      }

      // Session deleted: properties.info is a Session object
      if (event.type === "session.deleted") {
        const info = (event.properties as any)?.info || {};
        await callOakHook($, "sessionEnd", {
          session_id: info.id,
          agent: "opencode",
        });
      }

      // Session idle: agent finished responding
      // Fetch the last assistant message to capture response summary
      if (event.type === "session.idle") {
        const props = event.properties as any;
        const sessionId = props?.sessionID;
        if (!sessionId) return;

        // Fetch recent messages to get the assistant's response
        let responseSummary = "";
        try {
          const result = await client.session.messages({
            path: { id: sessionId },
            query: { directory },
          });
          const messages = (result as any)?.data || [];
          // Find the last assistant message
          for (let i = messages.length - 1; i >= 0; i--) {
            const msg = messages[i];
            if (msg?.info?.role === "assistant") {
              // Extract text parts from the assistant message
              const textParts = (msg.parts || [])
                .filter((p: any) => p.type === "text" && p.text)
                .map((p: any) => p.text);
              responseSummary = textParts.join("\n");
              break;
            }
          }
        } catch (err) {
          // Non-fatal: summary is optional
          console.error("[oak-ci] Failed to fetch messages for summary:", err);
        }

        await callOakHook($, "stop", {
          session_id: sessionId,
          response_summary: responseSummary || undefined,
          agent: "opencode",
        });
      }

      // Todo updated - capture planning information
      if (event.type === "todo.updated") {
        const props = event.properties as any;
        const todos = props?.todos || [];
        const todoSummary = formatTodos(todos);

        await callOakHook($, "postToolUse", {
          session_id: props?.sessionID,
          tool_name: "TodoUpdate",
          tool_input: { todos, count: todos.length },
          tool_output: todoSummary,
          agent: "opencode",
        });
      }

      // File edited - capture file modifications
      // Note: file.edited only has { file: string }, no sessionID.
      // This will be a no-op (daemon drops missing session_id).
      // tool.execute.after captures file ops with correct session ID.
      if (event.type === "file.edited") {
        const props = event.properties as any;
        await callOakHook($, "postToolUse", {
          session_id: props?.sessionID,
          tool_name: "Write",
          tool_input: { file_path: props?.file },
          tool_output: `Modified ${props?.file}`,
          agent: "opencode",
        });
      }
    },

    /**
     * Chat message - capture user prompts and create prompt batches
     * Fires when the user sends a message to the agent.
     * Parts contain TextPart objects with the actual prompt text.
     */
    "chat.message": async (input, output) => {
      const sessionId = input.sessionID;
      if (!sessionId) return;

      // Extract prompt text from parts (TextPart has type: "text" and text: string)
      const textParts = (output.parts || [])
        .filter((p: any) => p.type === "text" && p.text)
        .map((p: any) => p.text);
      const prompt = textParts.join("\n");
      if (!prompt) return;

      await callOakHook($, "UserPromptSubmit", {
        session_id: sessionId,
        prompt,
        agent: "opencode",
      });
    },

    /**
     * Post-tool execution - capture tool usage and inject context
     */
    "tool.execute.after": async (input, output) => {
      const toolName = input.tool || "unknown";
      const sessionId = (input as any).sessionID;

      // Skip if no session context
      if (!sessionId) return;

      // Build output summary from output.output (SDK type)
      let outputSummary = "";
      if (output.output) {
        outputSummary = output.output.length > 500 ? output.output.slice(0, 500) + "..." : output.output;
      }

      // Extract metadata if available (may contain tool args)
      const metadata = output.metadata || {};

      await callOakHook($, "postToolUse", {
        session_id: sessionId,
        tool_name: toolName,
        tool_input: metadata,
        tool_output: outputSummary,
        agent: "opencode",
      });
    },
  };
};

// Default export for OpenCode plugin discovery
export default OakCIPlugin;
