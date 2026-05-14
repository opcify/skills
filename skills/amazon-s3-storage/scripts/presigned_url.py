#!/home/node/.openclaw-env/bin/python3
"""Generate a pre-signed download URL for an S3 object."""

import argparse
import sys

from _s3 import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a pre-signed URL for an S3 object.")
    parser.add_argument("--remote-path", required=True, help="Remote object key")
    parser.add_argument(
        "--expiry",
        type=int,
        default=604800,
        help="Link expiry in seconds (default 604800 = 7 days)",
    )
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, prefix = get_bucket()
        key = full_remote_path(prefix, args.remote_path)

        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=args.expiry,
        )

        result = {
            "url": url,
            "remote_path": key,
            "bucket": bucket,
            "expiry_seconds": args.expiry,
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Pre-signed URL (expires in {args.expiry}s):")
        print(url)

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
