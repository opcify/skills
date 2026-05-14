#!/home/node/.openclaw-env/bin/python3
"""Move (rename) an object within a Cloudflare R2 bucket."""

import argparse
import sys

from _r2 import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Move/rename an object in R2.")
    parser.add_argument("--from-path", required=True, help="Current remote object key")
    parser.add_argument("--to-path", required=True, help="New remote object key")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, prefix = get_bucket()
        src_key = full_remote_path(prefix, args.from_path)
        dst_key = full_remote_path(prefix, args.to_path)

        client.copy_object(Bucket=bucket, Key=dst_key, CopySource={"Bucket": bucket, "Key": src_key})
        client.delete_object(Bucket=bucket, Key=src_key)

        if args.as_json:
            emit_json({"from": src_key, "to": dst_key, "bucket": bucket, "fetched_at": now_iso()})
            sys.exit(0)
        print(f"Moved: {src_key} → {dst_key}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
