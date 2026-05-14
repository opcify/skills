#!/home/node/.openclaw-env/bin/python3
"""Download a file from Google Cloud Storage to a local path."""

import argparse
import os
import sys

from _gcs import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a file from GCS.")
    parser.add_argument("--remote-path", required=True, help="Remote object path")
    parser.add_argument("--local-path", required=True, help="Local destination path")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, prefix = get_bucket()
        blob_name = full_remote_path(prefix, args.remote_path)
        blob = bucket.blob(blob_name)

        os.makedirs(os.path.dirname(args.local_path) or ".", exist_ok=True)
        blob.download_to_filename(args.local_path)

        result = {
            "downloaded": blob_name,
            "local_path": args.local_path,
            "size": os.path.getsize(args.local_path),
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Downloaded: gs://{bucket.name}/{blob_name} → {args.local_path}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
