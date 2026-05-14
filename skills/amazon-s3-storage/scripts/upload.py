#!/home/node/.openclaw-env/bin/python3
"""Upload a local file to Amazon S3."""

import argparse
import os
import sys

from _s3 import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file to S3.")
    parser.add_argument("local_path", help="Path to the local file to upload")
    parser.add_argument("--remote-path", required=True, help="Remote object key (e.g. reports/q1.pdf)")
    add_json_flag(parser)
    args = parser.parse_args()

    if not os.path.isfile(args.local_path):
        if args.as_json:
            emit_error_json(f"Local file not found: {args.local_path}")
            sys.exit(0)
        print(f"ERROR: file not found: {args.local_path}", file=sys.stderr)
        sys.exit(1)

    try:
        client, bucket, prefix = get_bucket()
        key = full_remote_path(prefix, args.remote_path)
        client.upload_file(args.local_path, bucket, key)

        result = {
            "uploaded": key,
            "bucket": bucket,
            "size": os.path.getsize(args.local_path),
            "url": f"s3://{bucket}/{key}",
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Uploaded: {args.local_path} → s3://{bucket}/{key}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
