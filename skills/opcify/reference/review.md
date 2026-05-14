# Task review workflow reference

When a task finishes successfully, Opcify automatically marks it as awaiting review. The user can then chat with you to decide what happens next — accept the result, retry the task with new guidance, or spawn a follow-up. Your job is to map the user's natural-language request to the right API call.

## What "ready for review" means

A task is ready for review when it has:

- `status` = `"done"`
- `reviewStatus` = `"pending"`

Opcify sets `reviewStatus` to `"pending"` automatically the moment a task transitions to `done`. The user's chat is the signal for what to do next.

`reviewStatus` values: `pending` | `accepted` | `rejected` | `followed_up` | `null`.

## Finding tasks ready for review

There is no server-side `reviewStatus` filter yet, so list `done` tasks and filter locally:

```bash
curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks?status=done" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  | jq '[.[] | select(.reviewStatus == "pending")]'
```

## Fetching review context before acting

Before you present a task to the user or take a review action, fetch the review context so you can summarize what was produced:

```bash
curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/review" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"}
```

This returns the full task (including `resultSummary`, `resultContent`, and `executionSteps`) plus the review metadata.

## Mapping user intent to action

| User says…                                           | Action    | Endpoint                      |
|------------------------------------------------------|-----------|-------------------------------|
| "accept", "approve", "looks good", "ship it"         | Accept    | `POST …/tasks/:id/accept`     |
| "retry", "redo", "try again", "run it again with …"  | Retry     | `POST …/tasks/:id/retry`      |
| "follow up with …", "now also …", "do a follow-up"   | Follow-up | `POST …/tasks/:id/follow-up`  |

**Before acting:** if the user is ambiguous about *which* task, ask — do not guess. If multiple tasks are ready for review, list their titles/IDs and ask the user to pick. Never accept, retry, or follow-up a task the user hasn't clearly pointed to.

## Accept

Use when the user confirms the task's result is good. Optionally include their `reviewNotes` if they said something worth recording (e.g. "accept — this is exactly what I wanted for the Acme pitch").

```bash
curl -s -X POST "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/accept" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{"reviewNotes": "Approved — ship as-is"}'
```

**Cascade behavior:** if the task you accept is itself a follow-up (has `sourceTaskId` set), Opcify also marks the source task chain as accepted. Tell the user this happened so they're not surprised ("Accepted — and the original research task it was following up on is now marked accepted too").

## Retry

Use when the user wants the task re-run. This resets the task to `queued`, clears review fields, and re-enqueues it for dispatch. If the user said *why* they want a retry or *what* to change, pass that as `overrideInstruction` (max 2000 chars) — it gets prepended to the task description as guidance for the retry.

```bash
# Simple retry — user just said "run it again"
curl -s -X POST "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/retry" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{}'

# Retry with new guidance — user said "retry but this time focus on Q2 numbers"
curl -s -X POST "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/retry" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{
    "reviewNotes": "First pass missed the Q2 breakdown",
    "overrideInstruction": "Focus on Q2 numbers specifically — include month-by-month revenue and expense trends."
  }'
```

If the user just says "retry" with no explanation, omit `overrideInstruction`.

## Follow-up

Use when the user wants a *new* task that builds on the completed one. The new task is linked via `sourceTaskId`, and the source task's `reviewStatus` flips to `followed_up`. The new task is enqueued immediately.

All body fields are optional — if you omit `agentId`, Opcify uses the source task's agent. If the user gave a short instruction like *"follow up and email the client the summary"*, synthesize a clear `title` and `description` from their intent rather than passing the raw sentence as the title.

```bash
curl -s -X POST "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/follow-up" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{
    "title": "Email Acme the Q2 research summary",
    "description": "Send the Q2 research summary from the previous task to contact@acme.com. Use a short intro paragraph and attach the full report.",
    "priority": "medium"
  }'
```

The response is `201 Created` with `{ followUpTask: {...} }`. Grab the new task's `id` from the response so you can reference it in chat.

## Reporting back in chat

After any successful review action, summarize what happened in the chat reply so the user sees confirmation. Examples:

- Accept: *"Accepted the 'Q2 research summary' task. It's marked complete in the ledger."*
- Retry: *"Retrying the Q2 research task with your new guidance — it's back in the queue and will re-run shortly."*
- Follow-up: *"Created a follow-up task: 'Email Acme the Q2 research summary' (id: `abc123`). It's queued and will start momentarily."*
