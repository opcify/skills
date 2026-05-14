# Client management reference

Clients represent the people or organizations that tasks are performed for. Every task can optionally be linked to a client via `clientId`.

## Client status values

| Status     | Meaning                          |
|------------|----------------------------------|
| `active`   | Currently active client (default)|
| `inactive` | Temporarily paused               |
| `archived` | Soft-deleted / no longer active  |

## Client API reference

All client endpoints are workspace-scoped and require `Authorization: Bearer ${OPCIFY_API_KEY}`.

### List clients
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/clients
Optional query params:
  q        — Search by name, company, or email
  status   — Filter: "active" | "inactive" | "archived"
  sort     — "name_asc" | "name_desc" | "createdAt_desc" (default: "updatedAt_desc")
Returns: [ { id, name, company, email, status, _count: { tasks }, ... }, ... ]
```

### Get client details
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/clients/:id
Returns: {
  id, name, company, email, phone, website, address, notes, status,
  _count: { tasks },
  recentTasks: [ { id, title, status, priority, updatedAt }, ... ]  // last 5
}
```

### Create client
```
POST /workspaces/${OPCIFY_WORKSPACE_ID}/clients
Body: {
  "name": "Acme Corp",              // required
  "company": "Acme Corporation",    // optional
  "email": "contact@acme.com",      // optional, must be valid email
  "phone": "+1-555-0100",           // optional
  "website": "https://acme.com",    // optional
  "address": "123 Main St",         // optional
  "notes": "Key account",           // optional
  "status": "active"                // optional, default "active"
}
Returns: 201 Created
```

### Update client
```
PATCH /workspaces/${OPCIFY_WORKSPACE_ID}/clients/:id
Body: {
  "name": "...",         // optional
  "company": "..." | null,
  "email": "..." | null,
  "phone": "..." | null,
  "website": "..." | null,
  "address": "..." | null,
  "notes": "..." | null,
  "status": "active" | "inactive" | "archived"
}
```

### Delete (archive) client
```
DELETE /workspaces/${OPCIFY_WORKSPACE_ID}/clients/:id
Effect: Sets status to "archived" (soft delete, not permanent)
```

### List tasks for a client
```
GET /workspaces/${OPCIFY_WORKSPACE_ID}/clients/:id/tasks
Returns: [ { id, title, status, priority, updatedAt, ... }, ... ]
```

## Linking tasks to clients

When creating or updating a task, set `clientId` to associate it with a client:

```bash
curl -s -X POST "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/tasks" \
  -H "Content-Type: application/json" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"} \
  -d '{
    "title": "Build landing page",
    "agentId": "agent-1",
    "clientId": "client-cuid-here",
    "priority": "high"
  }'
```

To look up which client a task belongs to, fetch the task detail — `clientId` will be present if assigned.

## Common workflow — look up a client before starting work

When a task has a `clientId`, fetch client details for context:

```bash
CLIENT=$(curl -s "${OPCIFY_API_URL}/workspaces/${OPCIFY_WORKSPACE_ID}/clients/${CLIENT_ID}" \
  ${OPCIFY_API_KEY:+-H "Authorization: Bearer ${OPCIFY_API_KEY}"})
# Use client name, notes, and recent tasks for context
```
