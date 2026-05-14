#!/home/node/.openclaw-env/bin/python3
"""Upload a local file to Cloudflare R2."""

import argparse
import os
import sys

from _r2 import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso, public_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file to R2.")
    parser.add_argument("local_path", help="Path to the local file")
    parser.add_argument("--remote-path", required=True, help="Remote object key")
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
            "url": f"r2://{bucket}/{key}",
            "public_url": public_url(key),
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Uploaded: {args.local_path} → r2://{bucket}/{key}")
        pub = public_url(key)
        if pub:
            print(f"Public URL: {pub}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
