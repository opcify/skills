#!/home/node/.openclaw-env/bin/python3
"""
_s3.py — shared helpers for the Amazon S3 storage skill scripts.

Handles:
  - boto3 client creation from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION
  - Bucket + prefix resolution from S3_BUCKET_NAME / S3_PREFIX
  - JSON output helpers
  - Common argparse boilerplate

Also used as the base for the Cloudflare R2 skill (_r2.py imports from here
and overrides the endpoint URL).
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


# ---------------------------------------------------------------------------
# Auth + config
# ---------------------------------------------------------------------------

def get_s3_client(endpoint_url: str | None = None):
    """Return a boto3 S3 client. Reads credentials from standard AWS env vars.

    Args:
        endpoint_url: Override the S3 endpoint (used by R2 for S3-compat API).
    """
    try:
        import boto3  # type: ignore
    except ImportError:
        print(
            "ERROR: boto3 is not installed.\n"
            "       Run: uv pip install boto3",
            file=sys.stderr,
        )
        sys.exit(1)

    kwargs: dict[str, Any] = {}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    kwargs["region_name"] = region

    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key

    return boto3.client("s3", **kwargs)


def get_bucket(endpoint_url: str | None = None, bucket_env: str = "S3_BUCKET_NAME", prefix_env: str = "S3_PREFIX"):
    """Return (s3_client, bucket_name, prefix)."""
    bucket_name = os.environ.get(bucket_env)
    if not bucket_name:
        print(
            f"ERROR: {bucket_env} is not set.\n"
            f"       Export it: export {bucket_env}=your-bucket-name",
            file=sys.stderr,
        )
        sys.exit(1)

    client = get_s3_client(endpoint_url)
    prefix = (os.environ.get(prefix_env) or "").strip("/")
    return client, bucket_name, prefix


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


def emit_error_json(message: str, provider: str = "amazon-s3", **extra: Any) -> None:
    payload: dict[str, Any] = {"error": message, "provider": provider}
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
