"""
Seed script — inserts N fake characters via the server's admin seed endpoint.
Characters appear on screens immediately (broadcast via WebSocket) and are persisted to InstantDB.

Usage:
  python seed.py                          # insert 400 characters
  python seed.py 50                       # insert 50 characters
  python seed.py --clear                  # delete all existing characters via InstantDB
  python seed.py --url https://your.app   # target a specific server (default: localhost:8000)

The server must be running. Set ADMIN_PASSWORD env var if it differs from the default.
"""

import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BATCH = 20  # characters per request
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "bytefest26")


def seed(n: int, base_url: str):
    print(f"Seeding {n} characters via {base_url}/admin/api/seed ...")
    inserted = 0
    while inserted < n:
        batch = min(BATCH, n - inserted)
        r = httpx.post(
            f"{base_url}/admin/api/seed",
            params={"count": batch},
            auth=("admin", ADMIN_PASSWORD),
            timeout=60,
        )
        r.raise_for_status()
        inserted += batch
        print(f"  inserted {inserted}/{n}")
        time.sleep(0.2)
    print(f"Done. Inserted {n} characters.")


def clear_all(base_url: str):
    print(f"Clearing all characters via {base_url}/admin/api/characters ...")
    r = httpx.delete(
        f"{base_url}/admin/api/characters",
        auth=("admin", ADMIN_PASSWORD),
        timeout=60,
    )
    r.raise_for_status()
    print(f"Done. Deleted {r.json()['deleted']} characters.")


if __name__ == "__main__":
    args = sys.argv[1:]
    url = "http://localhost:8000"
    if "--url" in args:
        idx = args.index("--url")
        url = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if "--clear" in args:
        clear_all(url)
    else:
        n = int(args[0]) if args else 400
        seed(n, url)
