---
name: opcify
description: Report task status and results back to Opcify via API callbacks. Use when you receive a task from Opcify and need to acknowledge, execute, and report back.
---

# Opcify — Agent Skill

## Overview

Opcify is the task and business management system that dispatches work to you. When you receive a task from Opcify, follow this skill to acknowledge, execute, and report back. Deeper topics (orchestration, review workflow, clients, ledger, email inbox, full API reference) live in the `reference/` sub-files — `Read` only the ones relevant to your task.

## Environment

All three variables are exported into your shell at container start, so `$OPCIFY_API_URL`, `$OPCIFY_API_KEY`, and `$OPCIFY_WORKSPACE_ID` are always available to bash commands — you do **not** need to read `openclaw.json`.

- `OPCIFY_API_URL` — Base URL of the Opcify API (e.g. `http://127.0.0.1:4210` or `https://api.opcify.ai`).
- `OPCIFY_API_KEY` — per-workspace API key. Send as `Authorization: Bearer ${OPCIFY_API_KEY}`. Every endpoint under `/workspaces/${OPCIFY_WORKSPACE_ID}/…` requires it.
- `OPCIFY_WORKSPACE_ID` — This agent's workspace ID. It is embedded in every path you call, e.g. `${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/clients`.

**URL shape.** Every Opcify resource (tasks, clients, ledger, inbox, agents, chat, kanban, archives, openclaw-config) lives under `/workspaces/${OPCIFY_WORKSPACE_ID}/…`. The only exception is `/dashboard/summary?workspaceId=${OPCIFY_WORKSPACE_ID}`, which stays at the root path for historical reasons but still requires the same `Authorization: Bearer ${OPCIFY_API_KEY}` header.

**Never emit literal `${...}` placeholders** in callback payloads or chat messages — expand shell variables first.

## Execute Command Fields

When Opcify dispatches a task to OpenClaw, the execute command JSON includes:

| Field | Description |
|-------|-------------|
| `taskId` | The Opcify task ID — use this in all API callbacks |
| `goal` | Task title / primary instruction |
| `description` | Full task description (may be null) |
| `callbackUrl` | Full URL to POST your status report to |
| `callbackToken` | Bearer token — include as `Authorization: Bearer {token}` |
| `agent.skills` | Array of skill keys installed on this agent |

Always use `callbackUrl` and `callbackToken` from the execute command — never construct them yourself.

## Task Status Values

Opcify uses these exact status strings — do NOT use any other values:

| Status    | Meaning                                      |
|-----------|----------------------------------------------|
| `queued`  | Task is waiting to be picked up              |
| `running` | Task is actively being worked on             |
| `waiting` | Task is blocked or awaiting review           |
| `done`    | Task completed successfully                  |
| `failed`  | Task failed                                  |
| `stopped` | Task was stopped by the user                 |

### Waiting reasons (optional, set via `waitingReason` field)

When setting status to `waiting`, include a reason:

- `waiting_for_review` — Work is done, needs human review
- `waiting_for_input` — Blocked on user clarification
- `waiting_for_dependency` — Blocked on another task
- `waiting_for_retry` — Needs retry after transient failure
- `waiting_for_external` — Waiting on external system

## Message Format

When Opcify dispatches a task to you via the Gateway, the message contains:

```
[OPCIFY-TASK]
Task ID: <id>
Title: <title>
Description: <description>
Priority: <high|medium|low>
[/OPCIFY-TASK]
```

Parse the Task ID from this block and use it in all API callbacks.

If the description contains an `---ATTACHED FILES---` block, see `reference/attachments.md`.

## When You Receive a Task

Follow this sequence exactly.

### Step 1: Check if the task is still active

Before doing anything, check whether the CEO has already stopped this task:

```bash
TASK_JSON=$(curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"})
```

If the `status` field in the response is `"stopped"`, **exit immediately** — do not acknowledge, do not do any work.

### Step 2: Acknowledge — set status to `running`

Update the task status so Opcify knows you've picked it up:

```bash
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/status" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{"status": "running"}')
```

If the HTTP status code is **409**, the task has been stopped — exit immediately.

### Step 3: Execute the task

Read the task title and description carefully. Do the work. If you're an orchestrator, see `reference/orchestration.md` for the multi-step callback pattern.

### Step 4: Report the result

Use the `callbackUrl` and `callbackToken` from the execute command.

> **Orchestrators (COO, directors) — STOP.** The single-step example below does NOT apply to you. You send many callbacks with `executionMode: "orchestrated"` and a specific field shape. Read `reference/orchestration.md` BEFORE your first callback. Inventing field names (`stepId`, `name`, `description`, `executionSteps`) silently succeeds at the API but leaves the kanban blank.

For a single-step agent, one call with `finalTaskStatus` set is all you need:

**On success:**
```bash
curl -s -X POST "${CALLBACK_URL}" \
  -H "Content-Type: application/json" \
  ${CALLBACK_TOKEN:+-H "Authorization: Bearer ${CALLBACK_TOKEN}"} \
  -d '{
    "executionMode": "single",
    "finalTaskStatus": "done",
    "steps": [
      {
        "stepOrder": 1,
        "agentName": "My Agent",
        "status": "completed",
        "outputSummary": "Task completed successfully"
      }
    ]
  }'
```

**On failure:**
```bash
curl -s -X POST "${CALLBACK_URL}" \
  -H "Content-Type: application/json" \
  ${CALLBACK_TOKEN:+-H "Authorization: Bearer ${CALLBACK_TOKEN}"} \
  -d '{
    "executionMode": "single",
    "finalTaskStatus": "failed",
    "steps": [
      {
        "stepOrder": 1,
        "status": "failed",
        "outputSummary": "Task failed: <reason>"
      }
    ]
  }'
```

## Reference index

Read only the sub-files relevant to your task — they are NOT loaded automatically.

| If you need to…                                                       | Read                          |
|-----------------------------------------------------------------------|-------------------------------|
| Handle a multi-step orchestrated task (COO, directors) — callback sequence, `report()` helper, cancellation handling, HTTP 409 | `reference/orchestration.md`  |
| Read file attachments (`---ATTACHED FILES---` block)                  | `reference/attachments.md`    |
| Handle task review chat (accept / retry / follow-up)                  | `reference/review.md`         |
| Pause a task and ask the CEO a critical question (kanban "needs input") | `reference/blocking.md`       |
| Look up a specific task API endpoint or `/kanban/stats`               | `reference/api.md`            |
| Look up, create, update, or link clients                              | `reference/clients.md`        |
| Record income / expenses, financial summaries                         | `reference/ledger.md`         |
| Triage emails and push to Opcify Inbox                                | `reference/inbox.md`          |
