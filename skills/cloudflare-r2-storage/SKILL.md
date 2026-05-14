---
name: cloudflare-r2-storage
description: Upload, download, list, delete, move, and generate pre-signed URLs for files in Cloudflare R2 buckets (S3-compatible API, zero egress fees). Used by the Archives Director agent to sync workspace deliverables to cloud storage.
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["R2_BUCKET_NAME","R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY"]},"install":[{"id":"boto3","kind":"pip","package":"boto3","bins":[],"label":"Install boto3"}]}}
---

# Cloudflare R2 Storage

Manage files in a Cloudflare R2 bucket via CLI scripts under `scripts/`. R2 uses the S3-compatible API via `boto3` with a custom endpoint. **Zero egress fees** — ideal for workspaces that serve files to external stakeholders.

## Setup (run once per workspace)

```bash
# 1. Install the AWS SDK (R2 is S3-compatible)
uv pip install boto3

# 2. Set environment variables
# Get these from Cloudflare dashboard → R2 → Manage R2 API Tokens
export R2_ACCOUNT_ID=your-cloudflare-account-id
export R2_ACCESS_KEY_ID=your-r2-access-key
export R2_SECRET_ACCESS_KEY=your-r2-secret-key
export R2_BUCKET_NAME=your-bucket-name

# 3. Optional: path prefix
export R2_PREFIX=workspaces/my-workspace

# 4. Optional: custom public domain for permanent public URLs
# (requires a custom domain connected to the R2 bucket in Cloudflare dashboard)
export R2_PUBLIC_DOMAIN=files.example.com
```

## Scripts

| Script | Purpose | Key flags |
|---|---|---|
| `upload.py LOCAL --remote-path PATH` | Upload a local file to R2 | `--json` |
| `download.py --remote-path PATH --local-path LOCAL` | Download an R2 object to local disk | `--json` |
| `list.py` | List objects in the bucket (shallow by default) | `--prefix PREFIX --limit N --recursive --json` |
| `delete.py --remote-path PATH` | Delete an object | `--json` |
| `move.py --from-path SRC --to-path DST` | Rename/move an object within the bucket | `--json` |
| `search.py QUERY` | Search for objects by filename pattern (supports wildcards) | `--prefix PREFIX --limit N --json` |
| `presigned_url.py --remote-path PATH` | Generate a time-limited pre-signed download URL | `--expiry SECONDS --json` |
| `setenv.py` | Save env vars to `.cloud-env.json` for direct script access (run once after setup) | `--json` |

## Examples

```bash
python3 scripts/upload.py /home/node/.openclaw/data/archives/reports/q1.pdf --remote-path reports/q1.pdf --json
python3 scripts/list.py --prefix reports/ --json
python3 scripts/search.py "*.pdf" --json
python3 scripts/presigned_url.py --remote-path reports/q1.pdf --expiry 604800 --json
python3 scripts/download.py --remote-path reports/q1.pdf --local-path /tmp/q1.pdf --json
python3 scripts/delete.py --remote-path reports/q1.pdf --json
python3 scripts/move.py --from-path reports/old.pdf --to-path reports/new.pdf --json
```

## Public URLs

If `R2_PUBLIC_DOMAIN` is set (e.g. `files.example.com`), the `upload.py` and `presigned_url.py` scripts return a `public_url` field alongside the pre-signed URL. The public URL is permanent (no expiry) and requires that the custom domain is configured in the Cloudflare dashboard with public access enabled for the bucket.

## Why R2?

- **Zero egress fees** — download as much as you want without bandwidth charges
- **S3-compatible API** — works with `boto3`, AWS CLI, and any S3 SDK
- **Global edge caching** — R2 stores data across Cloudflare's global network
- **Custom domains** — attach your own domain for branded file URLs
