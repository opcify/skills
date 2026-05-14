# Task API reference

All task endpoints are workspace-scoped and require `Authorization: Bearer ${OPCIFY_API_KEY}`. Substitute `${OPCIFY_WORKSPACE_ID}` and `${TASK_ID}` with real values at runtime — do NOT emit the literal placeholder strings.

The gateway callback endpoint `/tasks/:id/execution-steps/sync` is documented separately in `reference/orchestration.md` because it's not workspace-scoped and has orchestrator-specific semantics.

## Update task status only
```
PATCH /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/status
Body: { "status": "queued" | "running" | "waiting" | "done" | "failed" | "stopped" }
```

## Stop a running task
```
POST /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/stop
Effect: Sets status to "stopped", sets finishedAt, cascade-fails dependent tasks
Note: Only works on tasks with status "running" or "queued"
```

## Update task (general — supports status + waitingReason + other fields)
```
PATCH /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}
Body: {
  "status": "...",
  "waitingReason": "waiting_for_review" | "waiting_for_input" | ... | null
}
```

Example — set a task to `waiting` with a reason:

```bash
curl -s -X PATCH "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{"status": "waiting", "waitingReason": "waiting_for_input"}'
```

## Get task details
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}
Returns: {
  id, title, description, status, priority, progress,
  reviewStatus,       // "pending" | "accepted" | "rejected" | "followed_up" | null
  resultSummary,      // final result summary (short)
  resultContent,      // full result content (long)
  createdAt,          // ISO-8601, when the task was created in Opcify
  startedAt,          // ISO-8601 | null, when the task entered "running" for the first time
  finishedAt,         // ISO-8601 | null, when the task reached done/failed/stopped
  sourceTask: {       // if this is a follow-up, the original task
    id, title, resultSummary, reviewStatus
  },
  executionSteps: [   // for orchestrated tasks, each step's output + timing
    {
      stepOrder, agentName, title, status,
      outputSummary,  // brief output of this step
      outputContent,  // full output of this step
      startedAt,      // ISO-8601 | null, agent-reported start time
      finishedAt,     // ISO-8601 | null, agent-reported finish time
      updatedAt       // ISO-8601, server time of this step's last report to Opcify
    }
  ]
}
```

**Timing semantics:**
- `startedAt` = first queued→running transition. Reset to `null` on retry; set to `new Date()` on the next dispatch. Use `finishedAt - startedAt` for **execution duration**, and `startedAt - createdAt` for **queue wait**.
- For each step, `updatedAt` is the canonical "last reported to Opcify" timestamp — Opcify stamps it every time the agent POSTs the step in a sync call. Use this when summarizing "when did each agent last check in".

**Follow-up context:** When working on a follow-up task, use `GET /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${SOURCE_TASK_ID}` to fetch the previous task's full details including its `executionSteps` and `resultContent`. This gives you the complete history of what was researched, produced, and reviewed.

## List queued tasks (for heartbeat polling)
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/tasks?status=queued
Returns: [ { id, title, description, priority, ... }, ... ]
```

## Get task review context
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/review
Returns: full task + executionSteps + review metadata
Use: fetch this before summarizing a reviewable task to the user
```

## Accept a reviewed task
```
POST /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/accept
Body: { "reviewNotes"?: string }
Effect: sets reviewStatus="accepted" and reviewedAt; if this task is itself a
        follow-up, cascades up the sourceTaskId chain and accepts the source(s) too
```

## Retry a reviewed task
```
POST /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/retry
Body: {
  "reviewNotes"?: string,
  "overrideInstruction"?: string   // max 2000 chars; prepended to description as retry guidance
}
Effect: resets status to "queued", clears reviewStatus/reviewedAt/finishedAt,
        and re-enqueues the task for dispatch
```

## Create a follow-up task
```
POST /workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/follow-up
Body: {
  "title"?: string,
  "description"?: string,
  "agentId"?: string,        // defaults to the source task's agent
  "priority"?: "high" | "medium" | "low",
  "plannedDate"?: string     // ISO date
}
Effect: creates a new task linked via sourceTaskId, enqueues it, and sets the
        source task's reviewStatus to "followed_up"
Returns: 201 { followUpTask: { id, title, agentId, status, ... } }
```

## Get Kanban timing stats (for /stats-style queries)

Use this lean endpoint when the boss asks things like *"what did I get done today?"*, *"how long are tasks taking?"*, or *"what's the longest-running task right now?"* — especially from Telegram or any context where loading full Kanban sections would be wasteful.

```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/kanban/stats
Optional query params:
  date     — "YYYY-MM-DD" scope window (defaults to today)
  timezone — IANA zone (e.g. "America/Los_Angeles")
Returns: {
  avgDurationMs,          // number | null, avg (finishedAt - startedAt) over completed tasks
  totalProcessingMs,      // number, sum of the same
  avgQueueWaitMs,         // number | null, avg (startedAt - createdAt) for tasks started in window
  longestRunningMs,       // number | null, max (now - startedAt) across currently-running tasks
  longestRunningTaskId,   // string | null
  longestRunningTaskTitle,// string | null
  completedCount,         // tasks counted into avg/total
  runningCount            // tasks counted into longest-running
}
```

All durations are milliseconds. Format them with whatever unit makes sense for the user (e.g. "47m", "1h 12m"). Guard nulls with "—" or "no running tasks".

**Example — build a short /stats reply for chat or Telegram:**

```bash
STATS=$(curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/kanban/stats?date=$(date +%F)" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"})

echo "$STATS" | jq -r '
  "Today so far:",
  "  • \(.completedCount) tasks completed",
  "  • avg duration \(if .avgDurationMs then (.avgDurationMs/60000|floor|tostring + "m") else "—" end)",
  "  • total processing \(.totalProcessingMs/60000|floor|tostring)m",
  "  • longest running \(if .longestRunningTaskTitle then "\"" + .longestRunningTaskTitle + "\" (\((.longestRunningMs/60000)|floor)m)" else "none" end)"
'
```

Prefer this endpoint over `GET /workspaces/:id/kanban` when you only need metrics — it skips the section payloads and just returns the numbers, which is faster and cheaper for scheduled/recurring summaries.
