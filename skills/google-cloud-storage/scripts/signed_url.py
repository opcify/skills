#!/home/node/.openclaw-env/bin/python3
"""Generate a time-limited signed URL for a GCS object."""

import argparse
import sys
from datetime import timedelta

from _gcs import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a signed URL for a GCS object.")
    parser.add_argument("--remote-path", required=True, help="Remote object path")
    parser.add_argument(
        "--expiry",
        type=int,
        default=604800,
        help="Link expiry in seconds (default 604800 = 7 days, max 604800)",
    )
    add_json_flag(parser)
    args = parser.parse_args()

    # GCS V4 signed URLs max out at 7 days
    expiry = min(args.expiry, 604800)

    try:
        client, bucket, prefix = get_bucket()
        blob_name = full_remote_path(prefix, args.remote_path)
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiry),
            method="GET",
        )

        result = {
            "url": url,
            "remote_path": blob_name,
            "bucket": bucket.name,
            "expiry_seconds": expiry,
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Signed URL (expires in {expiry}s):")
        print(url)

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
