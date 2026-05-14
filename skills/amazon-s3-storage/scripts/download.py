#!/home/node/.openclaw-env/bin/python3
"""Download a file from Amazon S3 to a local path."""

import argparse
import os
import sys

from _s3 import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a file from S3.")
    parser.add_argument("--remote-path", required=True, help="Remote object key")
    parser.add_argument("--local-path", required=True, help="Local destination path")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, prefix = get_bucket()
        key = full_remote_path(prefix, args.remote_path)
        os.makedirs(os.path.dirname(args.local_path) or ".", exist_ok=True)
        client.download_file(bucket, key, args.local_path)

        result = {
            "downloaded": key,
            "local_path": args.local_path,
            "size": os.path.getsize(args.local_path),
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Downloaded: s3://{bucket}/{key} → {args.local_path}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
