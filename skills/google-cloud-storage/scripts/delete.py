#!/home/node/.openclaw-env/bin/python3
"""Delete an object from Google Cloud Storage."""

import argparse
import sys

from _gcs import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete an object from GCS.")
    parser.add_argument("--remote-path", required=True, help="Remote object path to delete")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, prefix = get_bucket()
        blob_name = full_remote_path(prefix, args.remote_path)
        blob = bucket.blob(blob_name)
        blob.delete()

        result = {"deleted": blob_name, "bucket": bucket.name, "fetched_at": now_iso()}

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Deleted: gs://{bucket.name}/{blob_name}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
