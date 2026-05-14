#!/home/node/.openclaw-env/bin/python3
"""List objects in a Cloudflare R2 bucket."""

import argparse
import sys

from _r2 import add_json_flag, emit_error_json, emit_json, full_remote_path, get_bucket, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="List objects in an R2 bucket.")
    parser.add_argument("--prefix", default="", help="Object prefix filter")
    parser.add_argument("--limit", type=int, default=100, help="Max items")
    parser.add_argument("--recursive", action="store_true", help="List all objects recursively (default: shallow, one level only)")
    add_json_flag(parser)
    args = parser.parse_args()

    try:
        client, bucket, root_prefix = get_bucket()
        search_prefix = full_remote_path(root_prefix, args.prefix) if args.prefix else root_prefix
        if search_prefix and not search_prefix.endswith("/"):
            search_prefix += "/"

        kwargs = {"Bucket": bucket, "MaxKeys": args.limit}
        if search_prefix:
            kwargs["Prefix"] = search_prefix
        if not args.recursive:
            kwargs["Delimiter"] = "/"

        response = client.list_objects_v2(**kwargs)
        items = []
        for obj in response.get("Contents", []):
            display_name = obj["Key"]
            if root_prefix and display_name.startswith(root_prefix + "/"):
                display_name = display_name[len(root_prefix) + 1 :]
            items.append({
                "name": display_name,
                "size": obj["Size"],
                "updated": obj["LastModified"].isoformat() if obj.get("LastModified") else None,
                "type": "file",
            })

        folders = []
        if not args.recursive:
            for cp in response.get("CommonPrefixes", []):
                display_name = cp["Prefix"]
                if root_prefix and display_name.startswith(root_prefix + "/"):
                    display_name = display_name[len(root_prefix) + 1 :]
                folders.append({
                    "name": display_name,
                    "type": "folder",
                })

        result = {
            "bucket": bucket,
            "prefix": args.prefix,
            "folders": folders,
            "items": items,
            "count": len(items) + len(folders),
            "fetched_at": now_iso(),
        }

        if args.as_json:
            emit_json(result)
            sys.exit(0)
        print(f"Bucket: {bucket}  Prefix: {args.prefix or '(root)'}  Items: {len(items)}  Folders: {len(folders)}")
        for folder in folders:
            print(f"  {'[folder]':>10}  {folder['name']}")
        for item in items:
            print(f"  {item['size']:>10,} B  {item['name']}")

    except Exception as e:
        if args.as_json:
            emit_error_json(f"{type(e).__name__}: {e}")
            sys.exit(0)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
