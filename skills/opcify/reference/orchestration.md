# Orchestration reference

For orchestrator agents (COO, directors) and any agent that reports multi-step progress back to Opcify via the gateway callback.

## `report()` helper

Define this at the start of the task and call `report '<JSON payload>'` for each callback. Single-step agents call it once; orchestrators call it many times.

```bash
CALLBACK_URL="<from callbackUrl in the execute command>"
CALLBACK_TOKEN="<from callbackToken in the execute command; may be empty>"

report() {
  if [ -n "$CALLBACK_TOKEN" ]; then
    curl -s -X POST "$CALLBACK_URL" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $CALLBACK_TOKEN" \
      -d "$1"
  else
    curl -s -X POST "$CALLBACK_URL" \
      -H "Content-Type: application/json" \
      -d "$1"
  fi
}
```

## Sync execution steps endpoint

This is the OpenClaw gateway callback. It is intentionally NOT workspace-scoped — the gateway already authenticates via the per-workspace API key in the `Authorization` header. Always use the `callbackUrl` / `callbackToken` passed with the execute command; never construct this URL yourself.

```
POST /tasks/${TASK_ID}/execution-steps/sync
```

### Concrete examples

Copy these shapes exactly. Field names are case-sensitive — inventing names like `stepId`, `name`, `description`, `executionSteps`, or `resultContent` is the #1 cause of "kanban shows no progress" bugs and blank review panels.

#### Plan callback (right after planning; all steps pending)

```bash
report '{
  "executionMode": "orchestrated",
  "steps": [
    { "stepOrder": 1, "agentName": "Researcher", "title": "Research competitors",      "status": "pending" },
    { "stepOrder": 2, "agentName": "Executor",   "title": "Write comparison report",   "status": "pending" },
    { "stepOrder": 3, "agentName": "Reviewer",   "title": "Review report",             "status": "pending" }
  ]
}'
```

#### Final callback (after the last step completes; includes `outputContent` and `finalTaskStatus`)

`outputContent` lives **on the last step** — NOT at the top level, and the field is `outputContent` (NOT `resultContent`). It holds the full deliverable. `outputSummary` stays a one-liner.

```bash
report '{
  "executionMode": "orchestrated",
  "finalTaskStatus": "done",
  "steps": [
    { "stepOrder": 1, "agentName": "Researcher", "title": "Research competitors",    "status": "completed", "outputSummary": "Found 6 competitors; Lenovo leads at 27%" },
    { "stepOrder": 2, "agentName": "Executor",   "title": "Write comparison report", "status": "completed", "outputSummary": "Produced 180-word report" },
    { "stepOrder": 3, "agentName": "Reviewer",   "title": "Review report",           "status": "completed", "outputSummary": "APPROVED — all criteria met",
      "outputContent": "## Laptop market comparison\n\n(Full multi-paragraph report body here — include Archives Director markdown links for deliverable files.)"
    }
  ]
}'
```

The server promotes the last completed step's `outputSummary` → `Task.resultSummary` and its `outputContent` → `Task.resultContent` — which are what the review panel renders. Omitting `outputContent` leaves the review panel's "Result Output" empty (falls back to `resultSummary`), so always include it on the final callback.

### Field reference

**Top level:**
- `steps` (array) — **required**. Always the FULL list of planned steps, in every callback.
- `executionMode` — optional but set it to `"orchestrated"` for multi-step tasks, `"single"` for single-step.
- `finalTaskStatus` (`"done"` | `"failed"` | `"stopped"`) — ONLY on the very last callback of the task. Omit it in intermediate callbacks.

**Per step:**
- `stepOrder` (integer ≥ 1) — **required**. 1-indexed.
- `status` (`"pending"` | `"running"` | `"completed"` | `"failed"`) — **required**. Pick one exact value; do NOT emit the pipe-separated string.
- `agentName` (string) — **strongly recommended.** The delegated sub-agent's display name (e.g. `"Researcher"`, `"Market Researcher"`). The kanban shows this while the step is running. If you omit it, the kanban can't display a running-agent label.
- `title` (string) — **strongly recommended.** One-line description of the step. The kanban shows this on the step timeline. If you omit it, the step appears nameless.
- `outputSummary` (string) — add to each completed step.
- `outputContent` (string) — add ONLY to the LAST step in the FINAL callback. Never to intermediate steps.
- `startedAt` / `finishedAt` (ISO-8601 strings) — add real timestamps. Opcify uses these for execution-duration metrics (see "Timestamp accuracy" below).
- `roleLabel`, `instruction`, `agentId` — optional extras.

### Invalid field names (do NOT use)

The schema rejects unknown fields. Common mistakes:

- `stepId` — no such field. Use `stepOrder`.
- `name` — no such field. Use `title` for the step title, `agentName` for the agent.
- `description` — no such field. Use `instruction` or fold into `title`.
- `executionSteps` — no such TOP-LEVEL field. The field is `steps`.
- `resultContent` — no such per-step field. Use `outputContent` on the last step. (`resultContent` exists on the Task itself — the server derives it from your step's `outputContent` automatically.)
- `outputContent` at the top level — belongs on the last STEP in the final callback, not at the root.

### Timestamp accuracy

Always send real `startedAt` / `finishedAt` values on each step — do not omit them. Opcify uses the earliest `steps[].startedAt` in the first report to stamp the task-level `Task.startedAt` (which drives execution duration and the aggregate metrics at `/kanban/stats`). Omitting them makes the task look like it started at the server-receive time, overestimating execution duration. Each POST to this endpoint also updates the step's `updatedAt` on the server, which is how Opcify records "when did this agent last report in".

## Orchestrator callback pattern

For a plan with N steps, send `1 + 2N` callbacks. Every callback carries the FULL step list with each step's current status.

| # | When | What's in the payload |
|---|------|----------------------|
| 1 | After planning, before any spawn | All N steps `"pending"` |
| 2k | Right before spawning step `k`'s agent | Prior steps `"completed"`, step `k` `"running"`, later steps `"pending"` |
| 2k + 1 | Right after step `k`'s agent returns | Step `k` `"completed"` with `outputSummary` |

The final callback (step `N` completing) also carries `"finalTaskStatus": "done"` and `outputContent` on the last step.

**Never skip the `"running"` callback** — it's what makes the kanban show step `k` is in progress. A step that jumps straight from `"pending"` to `"completed"` looks frozen to the user.

## Handling Task Cancellation

The user can stop a task at any time via the Opcify UI. When this happens, the task status changes to `"stopped"`. **Orchestrator agents must check for this before each delegation step to avoid wasting work.**

### Pre-spawn status check

Before every `sessions_spawn()` call and before every callback, check if the task is still running:

```bash
TASK_JSON=$(curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"})
```

Parse `status` from the response. If it's `"stopped"`:

1. Do NOT spawn any more agents.
2. Send one final callback with `"finalTaskStatus": "stopped"` and the remaining steps marked `"failed"`:

```bash
report '{
  "executionMode": "orchestrated",
  "finalTaskStatus": "stopped",
  "steps": [
    { "stepOrder": 1, "agentName": "Researcher", "status": "completed", "outputSummary": "Research completed before stop" },
    { "stepOrder": 2, "agentName": "Executor", "status": "failed", "outputSummary": "Stopped by user" },
    { "stepOrder": 3, "agentName": "Reviewer", "status": "failed", "outputSummary": "Stopped by user" }
  ]
}'
```

3. Exit immediately.

### HTTP 409 response

If any callback to Opcify returns HTTP 409, the task has already been stopped. Treat this the same way — stop all work and exit. Do NOT try to set the status again — Opcify has already done it.
