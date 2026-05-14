#!/home/node/.openclaw-env/bin/python3
"""List objects in a Google Cloud Storage bucket."""

import argparse
import sys

from _gcs import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="List objects in a GCS bucket.")
    parser.add_argument("--prefix", default="", help="Object prefix filter (e.g. reports/)")
    parser.add_argument("--limit", type=int, default=100, help="Max items to return")
    parser.add_argument("--recursive", action="store_true", help="List all objects recursively (default: shallow, one level only)")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, root_prefix = get_bucket()
        search_prefix = full_remote_path(root_prefix, args.prefix) if args.prefix else root_prefix
        if search_prefix and not search_prefix.endswith("/"):
            search_prefix += "/"

        delimiter = None if args.recursive else "/"
        blobs = bucket.list_blobs(prefix=search_prefix or None, delimiter=delimiter, max_results=args.limit)

        items = []
        for blob in blobs:
            display_name = blob.name
            if root_prefix and display_name.startswith(root_prefix + "/"):
                display_name = display_name[len(root_prefix) + 1 :]
            items.append({
                "name": display_name,
                "size": blob.size,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "content_type": blob.content_type,
                "type": "file",
            })

        # Collect common prefixes (virtual folders) from the delimiter response
        folders = []
        if not args.recursive:
            for prefix_obj in blobs.prefixes:
                display_name = prefix_obj
                if root_prefix and display_name.startswith(root_prefix + "/"):
                    display_name = display_name[len(root_prefix) + 1 :]
                folders.append({
                    "name": display_name,
                    "type": "folder",
                })

        result = {
            "bucket": bucket.name,
            "prefix": args.prefix,
            "folders": folders,
            "items": items,
            "count": len(items) + len(folders),
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Bucket: {bucket.name}  Prefix: {args.prefix or '(root)'}  Items: {len(items)}  Folders: {len(folders)}")
        for folder in folders:
            print(f"  {'[folder]':>10}  {folder['name']}")
        for item in items:
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
