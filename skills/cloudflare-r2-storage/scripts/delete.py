#!/home/node/.openclaw-env/bin/python3
"""Delete an object from Cloudflare R2."""

import argparse
import sys

from _r2 import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete an object from R2.")
    parser.add_argument("--remote-path", required=True, help="Remote object key")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, prefix = get_bucket()
        key = full_remote_path(prefix, args.remote_path)
        client.delete_object(Bucket=bucket, Key=key)

        if args.as_json:
            emit_json({"deleted": key, "bucket": bucket, "fetched_at": now_iso()})
            sys.exit(0)
        print(f"Deleted: r2://{bucket}/{key}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
