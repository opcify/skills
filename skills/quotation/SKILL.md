---
name: quotation
description: Draft, send, and convert quotes end-to-end. Use whenever the task is to send a quote or estimate, share a drafted quote, check quote status, or turn an accepted quote into an invoice. Handles client lookup/create, quote creation, delivery by email and/or shareable link and/or PDF (per the requested channels), and one-command conversion to a Ledger invoice once the client accepts.
---

# Quotation — Agent Skill

## When to use

Use this skill whenever the incoming task is to:

- Send a quote or estimate to a new or existing client.
- Share a previously-drafted quote via another channel.
- Check whether a client has accepted or declined a quote.
- Turn an accepted quote into an invoice on the Ledger.

You **own the whole flow**. If the request is "send Alex a quote for 2 hours of gutter work at $120/hr, valid 14 days", everything below is your job: look up or create the client, draft the quote, deliver it, track status, and convert it to an invoice when ready — don't hand the user back partial results and ask them to finish.

## One-command philosophy

The goal is to replace separate quoting apps. When the incoming request is unambiguous, **do not** re-ask for data you already have (name, email, rate, scope). If something is genuinely missing, ask once, concisely.

Default delivery: **both email and shareable link**. If the request specifies channels, follow them. If only the PDF is requested, render the PDF and report the file path — another skill or a follow-up task can route the file.

## Setup

This skill depends on the `reportlab` Python package for PDF generation. It is **not** preinstalled in the gateway image — install it once per workspace:

```bash
uv pip install --python /home/node/.openclaw-env/bin/python3 reportlab
```

`himalaya` (for email) is already available on agents that have Gmail configured. If email send fails because himalaya is not configured, fall back to the shareable link.

No other dependencies — all HTTP calls to Opcify use the Python stdlib.

## Environment

Same as the `opcify` skill — the runtime exports `$OPCIFY_API_URL`, `$OPCIFY_API_KEY`, `$OPCIFY_WORKSPACE_ID` for you.

## Commands

All commands are exposed through `scripts/quote.py`. Run from the skill directory:

```bash
python scripts/quote.py <subcommand> [flags]
```

### `create` — draft a new quote

```bash
python scripts/quote.py create \
  --client-email alex@example.com \
  --client-name "Alex Morgan" \
  --description "Gutter repair & cleaning" \
  --items '[{"description":"Labour, 2 hrs","qty":2,"unit_price":120},{"description":"Materials","qty":1,"unit_price":80}]' \
  --valid-days 14 \
  --terms "50% deposit on acceptance. Balance due on completion." \
  --currency USD
```

Behavior:

1. Searches clients (`GET /clients?q=<email>`). If found, reuses. Otherwise creates a new client with the provided name, email, and any extra fields passed via `--client-phone`, `--client-company`, `--client-address`.
2. Creates a `LedgerEntry` row with `type="quote"`, `amount = sum(qty × unit_price)`, `metadata = {status:"draft", lineItems, shareToken, validUntil, terms, quoteNumber}`.
3. Prints JSON: `{quoteId, quoteNumber, shareToken, shareUrl, clientId, total, currency}` — capture this for follow-up commands.

### `send` — deliver a draft quote

```bash
python scripts/quote.py send --id <quoteId> --channels email,link,pdf
```

Channels:

- `email` — sends via `himalaya message send` with an HTML body summarising the quote and a PDF attachment. Uses the client's email from the quote's client record.
- `link` — prints the public shareable URL so it can be copied into SMS/WhatsApp/Slack/etc.
- `pdf` — renders a PDF to `/tmp/quote-<id>.pdf` and prints the absolute path. A follow-up task or another skill (e.g. `opcify-pdf` or a Drive uploader) decides where the file ultimately lives.

Any combination is valid. After a successful send the quote's `metadata.status` flips from `draft` → `sent`.

### `status` — inspect a quote

```bash
python scripts/quote.py status --id <quoteId>
```

Prints current status (`draft`/`sent`/`viewed`/`accepted`/`declined`/`converted`/`expired`), total, client, acceptance/decline timestamps, and the share URL.

### `list` — show recent quotes

```bash
python scripts/quote.py list [--status accepted] [--client-id <id>] [--limit 20]
```

### `convert` — turn an accepted quote into an invoice

```bash
python scripts/quote.py convert --id <quoteId>
```

Creates a new `LedgerEntry` with `type="income"`, `attachmentType="invoice"`, copying amount, currency, description, client, and line items from the quote. Flips the original quote's `metadata.status` to `"converted"` and writes the new invoice id into `metadata.convertedInvoiceId`. Returns the new invoice id.

Refuses with a clear message if the quote is not in a convertible state (`declined`, `expired`, or already `converted`).

## Typical flows

### Task: "Send Alex a quote for 2 hrs plumbing at $120/hr"

1. `create --client-email ... --items '[{"description":"Plumbing, 2 hrs","qty":2,"unit_price":120}]' --valid-days 14`
2. `send --id <id> --channels email,link`
3. Report back: "Sent. Share link: <url>. I'll surface any response from Alex."

### Task: "Did Alex accept the gutter quote?"

1. `list --status accepted` (or `status --id <id>` if the id is already known).
2. Report the state and any acceptance timestamp.

### Task: "Turn that into an invoice"

1. Find the most recent `accepted` quote for the referenced client (`list --client-id ... --status accepted`).
2. `convert --id <id>`.
3. Report: "Invoice #... created on the Ledger. Net income +$X."

## Status transitions

```
draft → sent → viewed → accepted → converted
                     └→ declined
                     └→ expired (via validUntil)
```

`viewed` is set automatically by the public share page the first time the client opens it. `accepted`/`declined` are set by the buttons on the share page — the workspace inbox gets a notification when it happens, so usually the next inbound task will already reference the acceptance.

## Inbox notifications

When a client accepts or declines via the shareable link, the Opcify backend creates an inbox item in the workspace (kind: `follow_up`, linked to the client). You don't need to poll — but you can read the inbox (`GET /workspaces/:workspaceId/inbox`) if a task asks for current status across quotes.

## Reference

- Client CRUD: see `templates/skills/opcify/reference/clients.md`.
- Ledger API shape: see `templates/skills/opcify/reference/ledger.md`.
- Email sending with himalaya: see the pattern in `templates/skills/opcify/scripts/email-watcher.py`.
