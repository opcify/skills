# Ledger management reference

The ledger tracks all financial entries (income and expenses) for the workspace. Entries can optionally be linked to a client and/or a task.

## Ledger entry types

| Type      | Meaning                          |
|-----------|----------------------------------|
| `income`  | Money received (payment, revenue)|
| `expense` | Money spent (cost, vendor bill)  |

## Attachment types

| Type      | Meaning                          |
|-----------|----------------------------------|
| `invoice` | An invoice document              |
| `receipt` | A receipt or proof of payment    |

## Ledger API reference

All ledger endpoints are workspace-scoped and require `Authorization: Bearer ${OPCIFY_API_KEY}`.

### List ledger entries
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/ledger
Optional query params:
  type       — Filter: "income" | "expense"
  clientId   — Filter by client
  category   — Filter by category string
  q          — Search description, notes, or category
  sort       — "entryDate_asc" | "amount_desc" | "amount_asc" (default: "entryDate_desc")
  dateFrom   — ISO date string, entries on or after this date
  dateTo     — ISO date string, entries on or before this date
Returns: [
  {
    id, type, amount, currency, description, category, entryDate,
    client: { id, name, company } | null,
    task: { id, title } | null,
    ...
  },
  ...
]
```

### Get ledger summary
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/ledger/summary
Optional query params:
  dateFrom   — ISO date string
  dateTo     — ISO date string
Returns: { totalIncome: 5000.00, totalExpense: 2100.00, net: 2900.00 }
```

### Get ledger entry detail
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/ledger/:id
Returns: {
  id, type, amount, currency, clientId, taskId, category,
  description, attachmentType, attachmentUrl, notes, entryDate,
  client: { id, name, company } | null,
  task: { id, title } | null
}
```

### Create ledger entry
```
POST /workspaces/${OPCIFY_WORKSPACE_ID}/ledger
Body: {
  "type": "income",                  // required: "income" | "expense"
  "amount": 1500.00,                 // required: positive number
  "currency": "USD",                 // optional, default "USD"
  "clientId": "client-cuid",         // optional: link to client
  "taskId": "task-cuid",             // optional: link to task
  "category": "development",         // optional: freeform category
  "description": "Landing page build", // required
  "attachmentType": "invoice",       // optional: "invoice" | "receipt"
  "attachmentUrl": "https://...",    // optional: URL to document
  "notes": "Paid via wire transfer", // optional
  "entryDate": "2026-03-15"          // optional, default now
}
Returns: 201 Created
```

### Update ledger entry
```
PATCH /workspaces/${OPCIFY_WORKSPACE_ID}/ledger/:id
Body: {
  "type": "income" | "expense",         // optional
  "amount": 1500.00,                    // optional, must be positive
  "currency": "USD",                    // optional
  "clientId": "..." | null,             // optional
  "taskId": "..." | null,               // optional
  "category": "..." | null,             // optional
  "description": "...",                 // optional
  "attachmentType": "invoice" | "receipt" | null,
  "attachmentUrl": "..." | null,
  "notes": "..." | null,
  "entryDate": "2026-03-15"             // optional
}
```

### Delete ledger entry
```
DELETE /workspaces/${OPCIFY_WORKSPACE_ID}/ledger/:id
Returns: 204 No Content (permanent delete)
```

## Common workflows

### Record income when a task completes

After setting a task to `done`, record the income entry if the task is billable:

```bash
# 1. Complete the task
curl -s -X PATCH "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}/status" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{"status": "done"}'

# 2. Get task details to find clientId and workspace
TASK=$(curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks/${TASK_ID}" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"})

# 3. Record ledger income entry
curl -s -X POST "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/ledger" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{
    "type": "income",
    "amount": 500.00,
    "clientId": "'${CLIENT_ID}'",
    "taskId": "'${TASK_ID}'",
    "category": "development",
    "description": "Task completed: Landing page build"
  }'
```

### Check financial summary for a client

```bash
# Get all ledger entries for a specific client
curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/ledger?clientId=${CLIENT_ID}" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"}

# Get overall workspace financial summary
curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/ledger/summary" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"}
```
