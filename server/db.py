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


def publish_character(char_id: str, name: str, dino_type: str, image_b64: str,
                      interest: str = "") -> None:
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
                    "interest": interest,
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


# ── Face users ────────────────────────────────────────────────────────────────

def create_face_user(user_id: str, name: str, interest: str, embedding: list[float]) -> None:
    """Insert a new face user record."""
    payload = {
        "steps": [
            [
                "update",
                "face_users",
                user_id,
                {
                    "name": name,
                    "interest": interest,
                    "embedding": embedding,
                    "created_at": int(time.time() * 1000),
                },
            ]
        ]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=15)
    r.raise_for_status()


def get_all_face_users() -> list[dict]:
    """Return all face user records from InstantDB, sorted by created_at."""
    payload = {"query": {"face_users": {}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=15)
    r.raise_for_status()
    users = r.json().get("face_users", [])
    users.sort(key=lambda u: u.get("created_at", 0))
    return users


def delete_face_user(user_id: str) -> None:
    """Delete a face user record from InstantDB."""
    payload = {"steps": [["delete", "face_users", user_id]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def get_face_user(user_id: str) -> dict | None:
    """Return a single face user by id, or None."""
    payload = {"query": {"face_users": {"$": {"where": {"id": user_id}}}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    users = r.json().get("face_users", [])
    return users[0] if users else None


def update_face_user_demos(user_id: str, demo_ids: list[str]) -> None:
    """Store demo choices (list of presentation IDs) on a face user record."""
    payload = {
        "steps": [[
            "update", "face_users", user_id,
            {"demo_ids": demo_ids, "demo_chosen_at": int(time.time() * 1000)},
        ]]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


# ── Registered users (pre-event sign-ups) ─────────────────────────────────────

def create_registered_user(user_id: str, name: str, email: str) -> None:
    """Insert a pre-registered user."""
    payload = {
        "steps": [[
            "update", "registered_users", user_id,
            {"name": name, "email": email, "created_at": int(time.time() * 1000)},
        ]]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=15)
    r.raise_for_status()


def get_all_registered_users() -> list[dict]:
    """Return all registered users, sorted by name."""
    payload = {"query": {"registered_users": {}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=15)
    r.raise_for_status()
    users = r.json().get("registered_users", [])
    users.sort(key=lambda u: u.get("name", "").lower())
    return users


def get_registered_user_by_email(email: str) -> dict | None:
    """Return a registered user by email, or None."""
    payload = {"query": {"registered_users": {}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    for u in r.json().get("registered_users", []):
        if u.get("email", "").lower() == email.lower():
            return u
    return None


def delete_registered_user(user_id: str) -> None:
    """Delete a registered user from InstantDB."""
    payload = {"steps": [["delete", "registered_users", user_id]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


# ── Booths ─────────────────────────────────────────────────────────────────────

def create_booth(booth_id: str, name: str, number: int, mode: str) -> None:
    """Insert a booth config record."""
    payload = {
        "steps": [[
            "update", "booths", booth_id,
            {"name": name, "number": number, "mode": mode,
             "created_at": int(time.time() * 1000)},
        ]]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def get_all_booths() -> list[dict]:
    """Return all booth configs, sorted by number."""
    payload = {"query": {"booths": {}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    booths = r.json().get("booths", [])
    booths.sort(key=lambda b: b.get("number", 0))
    return booths


def update_booth(booth_id: str, mode: str) -> None:
    """Update booth mode."""
    payload = {"steps": [["update", "booths", booth_id, {"mode": mode}]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def delete_booth(booth_id: str) -> None:
    """Delete a booth config."""
    payload = {"steps": [["delete", "booths", booth_id]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


# ── Presentations ──────────────────────────────────────────────────────────────

def create_presentation(pres_id: str, name: str) -> None:
    """Insert a presentation."""
    payload = {
        "steps": [[
            "update", "presentations", pres_id,
            {"name": name, "created_at": int(time.time() * 1000)},
        ]]
    }
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def get_all_presentations() -> list[dict]:
    """Return all presentations, sorted by created_at."""
    payload = {"query": {"presentations": {}}}
    r = httpx.post(f"{_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    presos = r.json().get("presentations", [])
    presos.sort(key=lambda p: p.get("created_at", 0))
    return presos


def update_presentation(pres_id: str, name: str) -> None:
    """Update presentation name."""
    payload = {"steps": [["update", "presentations", pres_id, {"name": name}]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


def delete_presentation(pres_id: str) -> None:
    """Delete a presentation."""
    payload = {"steps": [["delete", "presentations", pres_id]]}
    r = httpx.post(f"{_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
