#!/usr/bin/env python3
"""One-shot migration: push your local ~/.foodhub/data.json up to the remote server.

Usage:
    set FOODHUB_API_URL=https://your-app.up.railway.app
    set FOODHUB_TOKEN=your-secret-token
    python scripts/upload_local.py

This reads the local file directly and PUTs it to /data, seeding the server with
your existing food definitions and history. Run once when first moving to remote mode.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

LOCAL_FILE = Path.home() / ".foodhub" / "data.json"


def main() -> int:
    api_url = os.environ.get("FOODHUB_API_URL")
    token = os.environ.get("FOODHUB_TOKEN")
    if not api_url or not token:
        print("Set FOODHUB_API_URL and FOODHUB_TOKEN first.", file=sys.stderr)
        return 1
    if not LOCAL_FILE.exists():
        print(f"No local data found at {LOCAL_FILE}", file=sys.stderr)
        return 1

    doc = json.loads(LOCAL_FILE.read_text())
    foods = len(doc.get("foods", {}))
    days = len(set(doc.get("log", {})) | set(doc.get("exercise", {})))
    print(f"Uploading {foods} foods and {days} days of history to {api_url} ...")

    req = urllib.request.Request(
        api_url.rstrip("/") + "/data",
        data=json.dumps(doc).encode(),
        method="PUT",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Server rejected upload: {e.code} {e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Could not reach server: {e.reason}", file=sys.stderr)
        return 1

    print(f"Done. Server updated_at = {result.get('updated_at')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
