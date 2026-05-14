#!/home/node/.openclaw-env/bin/python3
"""Search for objects by name pattern in a Google Cloud Storage bucket."""

import argparse
import fnmatch
import sys

from _gcs import add_json_flag, emit_error_json, emit_json, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Search for objects by name in a GCS bucket.")
    parser.add_argument("query", help="Search pattern (supports wildcards: *.pdf, report*)")
    parser.add_argument("--prefix", default="", help="Restrict search to this prefix (e.g. reports/)")
    parser.add_argument("--limit", type=int, default=50, help="Max results to return")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, root_prefix = get_bucket()
        search_prefix = f"{root_prefix}/{args.prefix}".strip("/") if args.prefix else root_prefix
        if search_prefix and not search_prefix.endswith("/"):
            search_prefix += "/"

        blobs = bucket.list_blobs(prefix=search_prefix or None)
        matches = []
        for blob in blobs:
            display_name = blob.name
            if root_prefix and display_name.startswith(root_prefix + "/"):
                display_name = display_name[len(root_prefix) + 1:]
            basename = display_name.rsplit("/", 1)[-1] if "/" in display_name else display_name
            if fnmatch.fnmatch(basename.lower(), args.query.lower()):
                matches.append({
                    "name": display_name,
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "content_type": blob.content_type,
                })
                if len(matches) >= args.limit:
                    break

        result = {
            "bucket": bucket.name,
            "query": args.query,
            "prefix": args.prefix,
            "matches": matches,
            "count": len(matches),
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Bucket: {bucket.name}  Query: {args.query}  Matches: {len(matches)}")
        for item in matches:
            size = f"{item['size']:>10,} B" if item["size"] is not None else "         —"
            print(f"  {size}  {item['name']}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
