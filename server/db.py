"""
InstantDB Admin HTTP API integration.

Requires env vars:
  INSTANT_APP_ID        — from https://www.instantdb.com/dash
  INSTANT_ADMIN_TOKEN   — from app settings → Admin Token
"""

import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://api.instantdb.com"
_APP_ID = os.getenv("INSTANT_APP_ID", "")
_ADMIN_TOKEN = os.getenv("INSTANT_ADMIN_TOKEN", "")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_ADMIN_TOKEN}",
        "App-Id": _APP_ID,
        "Content-Type": "application/json",
    }


def publish_character(char_id: str, name: str, dino_type: str, image_b64: str) -> None:
    """Insert a new character record with printed=false."""
    payload = {
        "steps": [
            [
                "update",
                "characters",
                char_id,
                {
                    "name": name,
                    "dino_type": dino_type,
                    "image_b64": image_b64,
                    "printed": False,
                    "created_at": int(time.time() * 1000),
                },
            ]
        ]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=15)
    r.raise_for_status()


def delete_character(char_id: str) -> None:
    """Delete a character record from InstantDB."""
    payload = {
        "steps": [["delete", "characters", char_id]]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def mark_printed(char_id: str) -> None:
    """Mark an existing character as printed."""
    payload = {
        "steps": [["update", "characters", char_id, {"printed": True}]]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def update_character_meta(char_id: str, name: str | None, dino_type: str | None) -> None:
    """Update name and/or dino_type for an existing character."""
    fields = {}
    if name is not None:
        fields["name"] = name
    if dino_type is not None:
        fields["dino_type"] = dino_type
    if not fields:
        return
    payload = {"steps": [["update", "characters", char_id, fields]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def set_printed(char_id: str, printed: bool) -> None:
    payload = {"steps": [["update", "characters", char_id, {"printed": printed}]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def get_printed_ids() -> set:
    """Return IDs of all characters marked as printed in InstantDB."""
    payload = {"query": {"characters": {"$": {"where": {"printed": True}}}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return {c["id"] for c in r.json().get("characters", [])}


def get_all_characters() -> list[dict]:
    """Return all character records from InstantDB, sorted by created_at."""
    payload = {"query": {"characters": {}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=15)
    r.raise_for_status()
    chars = r.json().get("characters", [])
    chars.sort(key=lambda c: c.get("created_at", 0))
    return chars


def get_unprinted() -> list[dict]:
    """Return all character records where printed == false."""
    payload = {"query": {"characters": {"$": {"where": {"printed": False}}}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("characters", [])
