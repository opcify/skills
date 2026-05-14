#!/home/node/.openclaw-env/bin/python3
"""
setenv.py — persist cloud storage env vars to .cloud-env.json.

Run once after configuring the skill's environment variables. This writes
them to a JSON file so that scripts invoked outside of OpenClaw (e.g. via
docker exec from the Opcify Files page) can load them at import time.

Usage:
    python3 scripts/setenv.py [--json]
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(SCRIPT_DIR, ".cloud-env.json")
PROVIDER = "google-cloud-storage"
ENV_KEYS = ["GCS_BUCKET_NAME", "GCS_CREDENTIALS_JSON", "GCS_PREFIX"]


def main():
    as_json = "--json" in sys.argv

    env = {}
    for key in ENV_KEYS:
        val = os.environ.get(key)
        if val:
            env[key] = val

    if not env.get("GCS_BUCKET_NAME"):
        if as_json:
            print(json.dumps({"error": "GCS_BUCKET_NAME not set", "provider": PROVIDER}))
        else:
            print("ERROR: GCS_BUCKET_NAME is not set.", file=sys.stderr)
            sys.exit(1)
        return

    data = {"provider": PROVIDER, "env": env}
    with open(ENV_FILE, "w") as f:
        json.dump(data, f, indent=2)

    result = {"written": ENV_FILE, "provider": PROVIDER, "keys": list(env.keys())}
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Environment written to {ENV_FILE}")
        for k in env:
            display = "[set]" if "KEY" in k or "SECRET" in k or "JSON" in k else env[k]
            print(f"  {k}={display}")


if __name__ == "__main__":
    main()
