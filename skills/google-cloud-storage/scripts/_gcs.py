#!/home/node/.openclaw-env/bin/python3
"""
_gcs.py — shared helpers for the Google Cloud Storage skill scripts.

Handles:
  - Service account auth from GCS_CREDENTIALS_JSON env var
  - Bucket + prefix resolution from GCS_BUCKET_NAME / GCS_PREFIX
  - JSON output helpers matching the yahoo-finance --json contract
  - Common argparse boilerplate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Load env from .cloud-env.json (written by setenv.py) so scripts work
# when invoked directly via docker exec, outside of OpenClaw's skill runner.
# ---------------------------------------------------------------------------

def _load_env():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cloud-env.json")
    try:
        with open(env_file) as f:
            data = json.load(f)
        for key, value in (data.get("env") or {}).items():
            if key not in os.environ:
                os.environ[key] = value
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

_load_env()


# ---------------------------------------------------------------------------
# Auth + config
# ---------------------------------------------------------------------------

def get_client():
    """Return an authenticated google.cloud.storage.Client.

    Auth priority:
      1. GCS_CREDENTIALS_JSON env var (raw JSON string or base64-encoded)
      2. GOOGLE_APPLICATION_CREDENTIALS env var (path to key file — standard GCP)
      3. Application Default Credentials (gcloud auth, metadata server)
    """
    try:
        from google.cloud import storage  # type: ignore
    except ImportError:
        print(
            "ERROR: google-cloud-storage is not installed.\n"
            "       Run: uv pip install google-cloud-storage",
            file=sys.stderr,
        )
        sys.exit(1)

    creds_json = os.environ.get("GCS_CREDENTIALS_JSON")
    if creds_json:
        # Could be raw JSON or base64
        import base64

        try:
            decoded = base64.b64decode(creds_json).decode("utf-8")
            json.loads(decoded)  # validate
            creds_json = decoded
        except Exception:
            pass  # assume it's already raw JSON

        # Write to temp file and point the standard env var at it
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="gcs-creds-"
        )
        tmp.write(creds_json)
        tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

    return storage.Client()


def get_bucket():
    """Return (client, bucket, prefix) from environment."""
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        print(
            "ERROR: GCS_BUCKET_NAME is not set.\n"
            "       Export it: export GCS_BUCKET_NAME=your-bucket-name",
            file=sys.stderr,
        )
        sys.exit(1)

    client = get_client()
    bucket = client.bucket(bucket_name)
    prefix = (os.environ.get("GCS_PREFIX") or "").strip("/")
    return client, bucket, prefix


def full_remote_path(prefix: str, remote_path: str) -> str:
    """Join prefix + remote_path, normalizing slashes."""
    remote_path = remote_path.lstrip("/")
    if prefix:
        return f"{prefix}/{remote_path}"
    return remote_path


# ---------------------------------------------------------------------------
# Output helpers (same contract as yahoo-finance / alpha-vantage skills)
# ---------------------------------------------------------------------------

def emit_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def emit_error_json(message: str, **extra: Any) -> None:
    payload: dict[str, Any] = {"error": message, "provider": "google-cloud-storage"}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Argparse helpers
# ---------------------------------------------------------------------------

def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit machine-readable JSON to stdout",
    )
