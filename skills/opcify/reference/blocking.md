# Blocking for CEO input reference

Some tasks genuinely can't proceed without the CEO's input — e.g. a critical decision that would waste effort if guessed wrong, or a missing piece of information that no sub-agent can fill. In those cases, pause the task, post a clear question to the kanban, and wait for the CEO's response.

When the CEO responds, Opcify re-dispatches the task with the same session key, so the agent (freshly spawned) sees the full prior transcript plus the CEO's new message in chat history. Session continuity is preserved — the agent picks up where it left off.

## When to block

Block ONLY when:

1. The task **genuinely cannot continue** without new information (e.g. required credential, missing file).
2. A **critical decision** that would waste significant work if guessed wrong (e.g. "publish to production now, or wait until Monday?").
3. An **ambiguous scope** where the CEO's intent is unknowable from context (e.g. "the brief says 'the client' but doesn't name them — which client?").

## When NOT to block

Do NOT block for:

- Minor gaps you can fill with a reasonable default (state the default in the result instead).
- Routine clarifications you can resolve by re-reading the task description.
- Anything a sub-agent could research or decide.
- Partial information that's good enough to make progress.

Blocking halts the kanban until the CEO responds — use it sparingly.

## How to block

Set the task to `waiting` with a concrete question in `blockingQuestion`:

```bash
curl -s -X PATCH "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{
    "status": "waiting",
    "waitingReason": "waiting_for_input",
    "blockingQuestion": "The brief mentions a budget but no amount. Use $10k as default, or hold for confirmation?"
  }'
```

**The question must be specific and self-contained** — the CEO won't see the full task context on the kanban card. State what you need, why you need it, and what the default would be if they said "just continue".

## What happens next

The kanban shows the task as `needs input` with your question. The CEO picks one of three actions:

1. **Continue** — Opcify delivers a `[CEO]: Please continue…` marker into your task session. No re-dispatch, no queued step — you read the message in your session and keep going. Be ready to make a reasonable default decision.
2. **Send response** — the CEO's message lands in your session's chat history as a regular user message. Read the latest chat message and act on it.
3. **Cancel** — the task transitions to `stopped`. You won't receive any further messages.

## On resume

When you're woken by the CEO's message, your session transcript already contains:

- Your original plan and whatever steps you completed
- The question you posted
- The CEO's response (or the `[CEO]: Please continue…` marker for a plain Continue)

Read the latest chat message, then resume your step loop. Do not re-plan from scratch unless the response materially changes the scope.

**The task stays in `waiting` status until you post your next step-sync callback.** Opcify's sync handler auto-transitions the task back to `running` the moment it sees an intermediate callback from you (i.e. one without `finalTaskStatus`). So just continue your normal callback rhythm — don't PATCH the status yourself to "running". The running state is inferred from your first callback after being woken.

## Good vs. bad questions

**Good (specific, resumable):**
- "The listing needs a price. Use the top of the appraisal range ($820k), the middle ($795k), or confirm with the vendor?"
- "Deploy target not specified — push to staging first for review, or straight to prod?"

**Bad (vague, would stall the task):**
- "What do you want me to do?" — re-read the task description.
- "Is this OK?" — show the work and ask for a specific decision.
- "There are lots of options. Which one?" — narrow to 2–3 concrete choices.
