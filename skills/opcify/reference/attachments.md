# File attachments reference

Tasks may include file attachments. When they do, the task description contains a block like this:

```
---ATTACHED FILES---
File path: /home/node/.openclaw/data/task-uploads/abc123-document.pdf
IMPORTANT: Read each file above using cat before starting this task.
---END ATTACHED FILES---
```

## How to handle attachments

When you see the `---ATTACHED FILES---` block, you MUST read each file using `cat` before doing any work:

```bash
cat /home/node/.openclaw/data/task-uploads/abc123-document.pdf
```

All agents have built-in file operation tools. Always read the file first, then process the task using the file content.

## For orchestrator / COO agents

When a task has file attachments, always include the file path references when delegating to sub-agents. Pass the file paths in the `sessions_spawn` task message so the sub-agent can read and process them.

Example delegation:

```
sessions_spawn({ agentId: "executor", task: "Read and summarize the document at /home/node/.openclaw/data/task-uploads/abc-report.pdf, then produce a summary." })
```

## Requesting human review

If you need human review mid-task:

```bash
curl -s -X PATCH "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{"status": "waiting", "waitingReason": "waiting_for_review"}'
```
