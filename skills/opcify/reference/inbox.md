# Inbox — email triage reference

The Inbox is the boss's curated action queue. As an agent, your job is to check emails via himalaya, triage them with AI, auto-handle routine ones, and push only the important emails that need the boss's attention to the Opcify Inbox.

## Reading & sending emails

Use the **himalaya** skill for all email operations (reading, replying, sending, forwarding). Himalaya is pre-configured with the boss's Gmail account. See the himalaya SKILL.md for full command reference.

## Email triage logic

When checking emails, classify each one:

1. **Routine / auto-handle** — newsletters, confirmations, receipts, automated notifications. Action: archive, auto-reply with template, or ignore. Do NOT push to Inbox.

2. **Needs boss attention** — client requests, partnership inquiries, contracts, strategic asks, urgent items, or anything you're unsure about. Action: push to Opcify Inbox with AI analysis.

## Pushing emails to the Inbox

For emails that need the boss's attention, POST to the Inbox API:

```bash
curl -s -X POST "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/inbox" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{
    "content": "<full email body text>",
    "kind": "email",
    "source": "email",
    "emailMessageId": "<IMAP Message-ID for dedup>",
    "emailFrom": "sender@example.com",
    "emailTo": "boss@example.com",
    "emailSubject": "Re: Q2 Proposal",
    "emailDate": "2026-04-11T10:30:00Z",
    "emailThreadId": "<thread-id if available>",
    "aiSummary": "Client is requesting timeline update for Q2 deliverables. They seem anxious about the deadline.",
    "aiUrgency": "high",
    "aiSuggestedAction": "reply",
    "aiDraftReply": "Hi John,\n\nThanks for checking in. We are on track for the Q2 deadline..."
  }'
```

### Required fields

| Field | Description |
|-------|-------------|
| `content` | Full email body text (required) |

### Email metadata (strongly recommended)

| Field | Description |
|-------|-------------|
| `emailMessageId` | IMAP Message-ID — used for deduplication |
| `emailFrom` | Sender email address |
| `emailTo` | Recipient(s), comma-separated |
| `emailSubject` | Original subject line |
| `emailDate` | ISO-8601 date when email was sent |
| `emailThreadId` | Thread/conversation grouping ID |

### AI triage fields (add these — they help the boss decide fast)

| Field | Values | Description |
|-------|--------|-------------|
| `aiSummary` | free text | 1-2 sentence summary of why this needs attention |
| `aiUrgency` | `"low"` `"medium"` `"high"` `"critical"` | How urgent is this? |
| `aiSuggestedAction` | `"reply"` `"delegate"` `"approve_draft"` `"create_task"` `"snooze"` `"forward"` | What should the boss do? |
| `aiDraftReply` | free text | Pre-drafted reply the boss can approve and send |

### Other fields

| Field | Values |
|-------|--------|
| `kind` | `"email"` `"idea"` `"request"` `"follow_up"` `"reminder"` |
| `source` | `"email"` `"agent"` `"manual"` `"system"` `"client"` |
| `emailInReplyTo` | Parent Message-ID (for threading) |
| `emailLabels` | JSON string of Gmail labels |

## Capturing sent emails (for thread view)

The Inbox shows conversations as threads. For the boss's own sent replies to appear in the thread, you MUST also push sent emails to the Inbox API.

**When to capture sent emails:**
- When the email watcher notifies you about new sent emails
- After you send an email on the boss's behalf via himalaya

**How to capture:**
```bash
# List recent sent emails
himalaya envelope list --folder "[Gmail]/Sent Mail" --page-size 10

# Read a sent email
himalaya message read --folder "[Gmail]/Sent Mail" <id>
```

Then POST each sent email to the Inbox API with:
- `emailFrom` = the boss's email address (the connected Gmail)
- `emailTo` = the recipient
- `emailMessageId` = the Message-ID (critical for dedup — the API skips duplicates)
- `emailSubject`, `emailDate`, `content` as usual
- `kind` = `"email"`, `source` = `"email"`
- No AI triage fields needed (no aiSummary/aiUrgency/aiSuggestedAction)

The API automatically deduplicates by `emailMessageId`, so it is safe to POST the same sent email multiple times.

## Sending emails

When the boss approves a reply or delegates email sending to you, use the **himalaya** skill to send/reply/forward. See the himalaya SKILL.md for commands.

## Inbox API reference

All inbox endpoints are workspace-scoped and require `Authorization: Bearer ${OPCIFY_API_KEY}`.

### Create inbox item (push email)
```
POST /workspaces/${OPCIFY_WORKSPACE_ID}/inbox
Body: { content, kind?, source?, emailMessageId?, emailFrom?, emailTo?,
        emailSubject?, emailDate?, emailThreadId?, aiSummary?,
        aiUrgency?, aiSuggestedAction?, aiDraftReply? }
Returns: 201 Created (the InboxItem)
Note: If emailMessageId already exists, returns existing item (dedup)
```

### List inbox items
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/inbox
Optional: status, urgency, source, q (search)
Returns: [ { id, content, status, emailFrom, emailSubject, aiSummary, ... } ]
```

### Get inbox stats
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/inbox/stats
Returns: { inbox: 12, critical: 2, high: 5 }
```
