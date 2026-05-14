#!/home/node/.openclaw-env/bin/python3
"""
_r2.py — shared helpers for the Cloudflare R2 storage skill.

R2 is S3-compatible, so we reuse _s3.py's helpers with a custom endpoint URL
built from the R2_ACCOUNT_ID env var. The only difference from plain S3:
  - endpoint_url = https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com
  - Env vars are R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / R2_BUCKET_NAME / R2_PREFIX
  - Optional R2_PUBLIC_DOMAIN for public URLs (e.g. files.example.com)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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


def _get_endpoint_url() -> str:
    account_id = os.environ.get("R2_ACCOUNT_ID")
    if not account_id:
        print(
            "ERROR: R2_ACCOUNT_ID is not set.\n"
            "       Export it: export R2_ACCOUNT_ID=your-cloudflare-account-id",
            file=sys.stderr,
        )
        sys.exit(1)
    return f"https://{account_id}.r2.cloudflarestorage.com"


def get_r2_client():
    """Return a boto3 S3 client configured for Cloudflare R2."""
    try:
        import boto3  # type: ignore
    except ImportError:
        print(
            "ERROR: boto3 is not installed.\n"
            "       Run: uv pip install boto3",
            file=sys.stderr,
        )
        sys.exit(1)

    endpoint_url = _get_endpoint_url()

    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        print(
            "ERROR: R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY must be set.\n"
            "       Get them from Cloudflare dashboard → R2 → Manage R2 API Tokens.",
            file=sys.stderr,
        )
        sys.exit(1)

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


def get_bucket():
    """Return (s3_client, bucket_name, prefix)."""
    bucket_name = os.environ.get("R2_BUCKET_NAME")
    if not bucket_name:
        print(
            "ERROR: R2_BUCKET_NAME is not set.\n"
            "       Export it: export R2_BUCKET_NAME=your-bucket-name",
            file=sys.stderr,
        )
        sys.exit(1)

    client = get_r2_client()
    prefix = (os.environ.get("R2_PREFIX") or "").strip("/")
    return client, bucket_name, prefix


def public_url(remote_path: str) -> str | None:
    """Return a public URL if R2_PUBLIC_DOMAIN is configured."""
    domain = os.environ.get("R2_PUBLIC_DOMAIN")
    if not domain:
        return None
    return f"https://{domain}/{remote_path}"


def full_remote_path(prefix: str, remote_path: str) -> str:
    remote_path = remote_path.lstrip("/")
    if prefix:
        return f"{prefix}/{remote_path}"
    return remote_path


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def emit_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def emit_error_json(message: str, **extra: Any) -> None:
    payload: dict[str, Any] = {"error": message, "provider": "cloudflare-r2"}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit machine-readable JSON to stdout",
    )
