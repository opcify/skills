#!/home/node/.openclaw-env/bin/python3
"""Move (rename) an object within a Google Cloud Storage bucket."""

import argparse
import sys

from _gcs import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Move/rename an object in GCS.")
    parser.add_argument("--from-path", required=True, help="Current remote object path")
    parser.add_argument("--to-path", required=True, help="New remote object path")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, prefix = get_bucket()
        src_name = full_remote_path(prefix, args.from_path)
        dst_name = full_remote_path(prefix, args.to_path)

        src_blob = bucket.blob(src_name)
        bucket.copy_blob(src_blob, bucket, dst_name)
        src_blob.delete()

        result = {
            "from": src_name,
            "to": dst_name,
            "bucket": bucket.name,
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Moved: {src_name} → {dst_name}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
