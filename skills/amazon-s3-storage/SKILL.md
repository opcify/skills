---
name: amazon-s3-storage
description: Upload, download, list, delete, move, and generate pre-signed URLs for files in Amazon S3 buckets. Used by the Archives Director agent to sync workspace deliverables to cloud storage.
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["S3_BUCKET_NAME","AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY"]},"install":[{"id":"boto3","kind":"pip","package":"boto3","bins":[],"label":"Install boto3"}]}}
---

# Amazon S3 Storage

Manage files in an S3 bucket via CLI scripts under `scripts/`. Every script supports `--json` for machine-readable output.

## Setup (run once per workspace)

```bash
# 1. Install the AWS SDK
uv pip install boto3

# 2. Set environment variables
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_REGION=us-east-1
export S3_BUCKET_NAME=your-bucket-name

# 3. Optional: set a path prefix
export S3_PREFIX=workspaces/my-workspace
```

## Scripts

| Script | Purpose | Key flags |
|---|---|---|
| `upload.py LOCAL --remote-path PATH` | Upload a local file to S3 | `--json` |
| `download.py --remote-path PATH --local-path LOCAL` | Download an S3 object to local disk | `--json` |
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
