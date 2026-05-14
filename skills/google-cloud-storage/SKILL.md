---
name: google-cloud-storage
description: Upload, download, list, delete, move, and generate signed URLs for files in Google Cloud Storage buckets. Used by the Archives Director agent to sync workspace deliverables to cloud storage.
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["GCS_BUCKET_NAME","GCS_CREDENTIALS_JSON"]},"install":[{"id":"google-cloud-storage","kind":"pip","package":"google-cloud-storage","bins":[],"label":"Install google-cloud-storage"}]}}
---

# Google Cloud Storage

Manage files in a GCS bucket via CLI scripts under `scripts/`. Every script supports `--json` for machine-readable output.

## Setup (run once per workspace)

```bash
# 1. Install the Python client
uv pip install google-cloud-storage

# 2. Set environment variables
export GCS_BUCKET_NAME=your-bucket-name
export GCS_CREDENTIALS_JSON='{"type":"service_account","project_id":"...","private_key":"..."}'
# Or base64-encode the service account key file:
# export GCS_CREDENTIALS_JSON=$(base64 < service-account-key.json)

# 3. Optional: set a path prefix so all objects land under a workspace-specific folder
export GCS_PREFIX=workspaces/my-workspace
```

## Scripts

| Script | Purpose | Key flags |
|---|---|---|
| `upload.py LOCAL --remote-path PATH` | Upload a local file to GCS | `--json` |
| `download.py --remote-path PATH --local-path LOCAL` | Download a GCS object to local disk | `--json` |
| `list.py` | List objects in the bucket (shallow by default) | `--prefix PREFIX --limit N --recursive --json` |
| `delete.py --remote-path PATH` | Delete an object | `--json` |
| `move.py --from-path SRC --to-path DST` | Rename/move an object within the bucket | `--json` |
| `search.py QUERY` | Search for objects by filename pattern (supports wildcards) | `--prefix PREFIX --limit N --json` |
| `signed_url.py --remote-path PATH` | Generate a time-limited signed download URL | `--expiry SECONDS --json` |
| `setenv.py` | Save env vars to `.cloud-env.json` for direct script access (run once after setup) | `--json` |

## Examples

```bash
# Upload a report
python3 scripts/upload.py /home/node/.openclaw/data/archives/reports/q1.pdf --remote-path reports/q1.pdf --json

# List all objects under reports/
python3 scripts/list.py --prefix reports/ --json

# Search for PDF files
python3 scripts/search.py "*.pdf" --json

# Search within a folder
python3 scripts/search.py "report*" --prefix reports/ --json

# Generate a 7-day signed URL for sharing
python3 scripts/signed_url.py --remote-path reports/q1.pdf --expiry 604800 --json

# Download a file
python3 scripts/download.py --remote-path reports/q1.pdf --local-path /tmp/q1.pdf --json

# Delete
python3 scripts/delete.py --remote-path reports/q1.pdf --json

# Move/rename
python3 scripts/move.py --from-path reports/old-name.pdf --to-path reports/new-name.pdf --json
```

## Limits

- Signed URLs max out at 7 days (604800 seconds) for V4 signatures.
- Upload size is limited by available memory (files are uploaded in one shot). For files >100MB, consider the resumable upload API (not wrapped in these scripts).
- The `GCS_PREFIX` is prepended to all remote paths automatically — you don't need to include it in `--remote-path`.
