"""
Sopra Steria @ UiO — Central server

Endpoints:
  GET  /          — TV wall display (open in browser on the screen)
  GET  /health    — health check
  POST /validate  — photo quality gate (gpt-4o-mini)
  POST /generate  — pixel art generation (gpt-image-1), stores + broadcasts result
  GET  /characters — all generated characters so far (for wall reconnects)
  WS   /ws        — WebSocket feed for the TV wall
"""

import asyncio
import base64
import csv as csv_mod
import io
import json
import math
import os
import random
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from PIL import Image
from pydantic import BaseModel

import db as instant_db
from face import compute_embedding, find_match, FACE_AVAILABLE
from generate import generate_image
from validate import validate_photo

_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "soprasteria")
_security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_security)):
    ok = secrets.compare_digest(credentials.password.encode(), _ADMIN_PASSWORD.encode())
    if not ok:
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})


# In-memory store — populated from InstantDB on startup
characters: List[dict] = []
connections: List[WebSocket] = []
face_users: List[dict] = []
registered_users: List[dict] = []
booths: List[dict] = []

# ── TV wall world coordinates ─────────────────────────────────────────────────
# The wall is 4 screens side-by-side. Each Pi opens /wall?screen=N and offsets
# its rendering by N × _LOGICAL_SCREEN_W pixels.
_LOGICAL_SCREEN_W = 1920   # configure each Pi to output 1920×1080
_WORLD_W          = _LOGICAL_SCREEN_W * 1   # 1920 — single screen
_WORLD_H          = 1080
_WALL_HEADER_H    = 120    # keep characters below the header
_WALL_GROUND_H    = 220    # keep characters above the ground-dino scene
_WALL_CHAR_SIZE   = 144   # default; mutable via admin API
_WALL_MARGIN      = 24
_CHAR_SPEED_MIN   = 30    # px/s  — slow DVD-screensaver drift
_CHAR_SPEED_MAX   = 60    # px/s
_PHYSICS_TICK     = 0.1   # seconds between physics updates (10 fps)


def _assign_world_pos(char: dict, right_side: bool = False) -> None:
    """Assign a random starting position and velocity for DVD-style bouncing."""
    x_min = (_WORLD_W - _LOGICAL_SCREEN_W + _WALL_MARGIN) if right_side else _WALL_MARGIN
    x_max = _WORLD_W - _WALL_CHAR_SIZE - _WALL_MARGIN
    char['x'] = float(random.randint(x_min, x_max))
    char['y'] = float(random.randint(_WALL_HEADER_H,
                                     _WORLD_H - _WALL_CHAR_SIZE - _WALL_GROUND_H))
    speed = random.uniform(_CHAR_SPEED_MIN, _CHAR_SPEED_MAX)
    angle = random.uniform(0, 2 * math.pi)
    char['vx'] = speed * math.cos(angle)
    char['vy'] = speed * math.sin(angle)


async def _character_movement_loop() -> None:
    """Physics loop: advance every character each tick, bounce off walls, broadcast positions."""
    while True:
        try:
            await asyncio.sleep(_PHYSICS_TICK)
            if not characters:
                continue

            x_min = float(_WALL_MARGIN)
            x_max = float(_WORLD_W - _WALL_CHAR_SIZE - _WALL_MARGIN)
            y_min = float(_WALL_HEADER_H)
            y_max = float(_WORLD_H - _WALL_CHAR_SIZE - _WALL_GROUND_H)

            for char in list(characters):
                char['x'] = char.get('x', 0.0) + char.get('vx', 0) * _PHYSICS_TICK
                char['y'] = char.get('y', 0.0) + char.get('vy', 0) * _PHYSICS_TICK

                if char['x'] < x_min:
                    char['x'] = x_min
                    char['vx'] = abs(char.get('vx', 1))
                elif char['x'] > x_max:
                    char['x'] = x_max
                    char['vx'] = -abs(char.get('vx', 1))

                if char['y'] < y_min:
                    char['y'] = y_min
                    char['vy'] = abs(char.get('vy', 1))
                elif char['y'] > y_max:
                    char['y'] = y_max
                    char['vy'] = -abs(char.get('vy', 1))

            await broadcast({
                'type': 'positions',
                'chars': [{'id': c['id'], 'x': round(c['x']), 'y': round(c['y'])}
                          for c in characters],
            })
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[physics] tick error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Restore all characters from InstantDB so a reboot/redeploy loses nothing
    try:
        loop = asyncio.get_event_loop()
        existing = await loop.run_in_executor(None, instant_db.get_all_characters)
        for char in existing:
            _assign_world_pos(char)
        characters.extend(existing)
        print(f"[startup] Restored {len(existing)} characters from InstantDB")
    except Exception as e:
        print(f"[startup] Could not restore characters from InstantDB: {e}")
    # Restore face users
    try:
        fu = await loop.run_in_executor(None, instant_db.get_all_face_users)
        face_users.extend(fu)
        print(f"[startup] Restored {len(fu)} face users from InstantDB (face_recognition={'available' if FACE_AVAILABLE else 'NOT available'})")
    except Exception as e:
        print(f"[startup] Could not restore face users from InstantDB: {e}")
    # Restore registered users
    try:
        ru = await loop.run_in_executor(None, instant_db.get_all_registered_users)
        registered_users.extend(ru)
        print(f"[startup] Restored {len(ru)} registered users from InstantDB")
    except Exception as e:
        print(f"[startup] Could not restore registered users from InstantDB: {e}")
    # Restore booths (create default if none exist)
    try:
        bs = await loop.run_in_executor(None, instant_db.get_all_booths)
        booths.extend(bs)
        if not booths:
            default_id = str(uuid.uuid4())
            default_booth = {"id": default_id, "name": "Booth 1", "number": 1, "mode": "both"}
            booths.append(default_booth)
            await loop.run_in_executor(None, instant_db.create_booth, default_id, "Booth 1", 1, "both")
            print("[startup] Created default booth 1")
        print(f"[startup] Restored {len(booths)} booths from InstantDB")
    except Exception as e:
        print(f"[startup] Could not restore booths from InstantDB: {e}")
    # Start the wall movement loop
    move_task = asyncio.create_task(_character_movement_loop())
    yield
    move_task.cancel()
    try:
        await move_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


async def broadcast(message: dict):
    if not connections:
        return
    data = json.dumps(message)
    conns = list(connections)

    async def send_one(ws):
        try:
            await asyncio.wait_for(ws.send_text(data), timeout=3.0)
            return None
        except Exception:
            return ws

    dead = [ws for ws in await asyncio.gather(*[send_one(ws) for ws in conns]) if ws is not None]
    for ws in dead:
        if ws in connections:
            connections.remove(ws)
        try:
            await ws.close()
        except Exception:
            pass


# --- Health ---

@app.get("/health")
def health():
    return {"ok": True, "characters": len(characters)}


# --- TV wall ---

@app.get("/", response_class=HTMLResponse)
@app.get("/wall", response_class=HTMLResponse)
def wall():
    return (Path(__file__).parent / "static" / "wall.html").read_text()


# --- Pi endpoints ---

@app.post("/validate")
async def validate(image: UploadFile = File(...)):
    data = await image.read()
    photo = Image.open(io.BytesIO(data)).convert("RGB")
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, validate_photo, photo
        )
        return {"ok": result.ok, "message": result.message}
    except Exception:
        # If validation fails, let the Pi proceed rather than blocking
        return {"ok": True, "message": ""}


@app.post("/generate")
async def generate(image: UploadFile = File(...)):
    data = await image.read()
    photo = Image.open(io.BytesIO(data)).convert("RGB")

    # Run blocking OpenAI call in thread pool
    result = await asyncio.get_event_loop().run_in_executor(
        None, generate_image, photo
    )

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    char_id = str(uuid.uuid4())
    # Store without name/dino_type — Pi will call /publish once user fills them in
    character = {"id": char_id, "image_b64": img_b64, "name": "", "dino_type": ""}
    _assign_world_pos(character)
    characters.append(character)

    return {"id": char_id, "image_b64": img_b64}


@app.post("/publish/{char_id}")
async def publish_character(
    char_id: str,
    name: str = Form(""),
    dino_type: str = Form(""),
    interest: str = Form(""),
):
    char = next((c for c in characters if c["id"] == char_id), None)
    if not char:
        return {"error": "not found"}
    char["name"] = name
    char["dino_type"] = dino_type
    char["interest"] = interest
    _assign_world_pos(char, right_side=True)
    await broadcast({"type": "new_character", **char})

    # Persist to InstantDB (non-blocking — fire and forget)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            instant_db.publish_character,
            char_id, name, dino_type, char["image_b64"], interest,
        )
    except Exception as e:
        print(f"[db] InstantDB write failed: {e}")

    return {"ok": True}


@app.get("/characters")
def get_characters():
    return characters


# --- TV wall WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    # Send all existing characters BEFORE joining the broadcast pool.
    # The physics loop yields to the event loop between ticks, so adding
    # to connections first would cause concurrent sends on the same socket
    # (this loop + broadcast), corrupting WebSocket frames.
    await ws.send_text(json.dumps({"type": "char_size", "size": _WALL_CHAR_SIZE}))
    for char in characters:
        await ws.send_text(json.dumps({"type": "new_character", **char}))
    connections.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive / ping
    except WebSocketDisconnect:
        if ws in connections:
            connections.remove(ws)


# --- Admin panel ---

class CharacterPatch(BaseModel):
    name: Optional[str] = None
    dino_type: Optional[str] = None


@app.get("/admin", response_class=HTMLResponse)
def admin_page(_=Depends(require_admin)):
    return (Path(__file__).parent / "static" / "admin.html").read_text()


@app.delete("/admin/api/characters/{char_id}")
async def admin_delete_character(char_id: str, _=Depends(require_admin)):
    char = next((c for c in characters if c["id"] == char_id), None)
    if not char:
        raise HTTPException(status_code=404, detail="not found")
    characters.remove(char)
    await broadcast({"type": "remove_character", "id": char_id})
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.delete_character, char_id
        )
    except Exception as e:
        print(f"[db] delete failed: {e}")
    return {"ok": True}


@app.patch("/admin/api/characters/{char_id}")
async def admin_update_character(char_id: str, body: CharacterPatch, _=Depends(require_admin)):
    char = next((c for c in characters if c["id"] == char_id), None)
    if not char:
        raise HTTPException(status_code=404, detail="not found")
    if body.name is not None:
        char["name"] = body.name
    if body.dino_type is not None:
        char["dino_type"] = body.dino_type
    await broadcast({"type": "update_character", **char})
    # Persist name/dino_type to InstantDB so mac_print_client picks up the new values
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.update_character_meta, char_id, body.name, body.dino_type
        )
    except Exception as e:
        print(f"[db] update_character_meta failed: {e}")
    return {"ok": True, **char}


@app.post("/admin/api/characters/{char_id}/reprint")
async def admin_reprint(char_id: str, _=Depends(require_admin)):
    char = next((c for c in characters if c["id"] == char_id), None)
    if not char:
        raise HTTPException(status_code=404, detail="not found")
    char["printed"] = False
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.set_printed, char_id, False
        )
    except Exception as e:
        print(f"[db] reprint failed: {e}")
    return {"ok": True}


@app.get("/admin/api/char-size")
async def admin_get_char_size(_=Depends(require_admin)):
    return {"char_size": _WALL_CHAR_SIZE}


@app.post("/admin/api/char-size")
async def admin_set_char_size(body: dict, _=Depends(require_admin)):
    global _WALL_CHAR_SIZE
    size = body.get("char_size")
    if not isinstance(size, int) or size < 48 or size > 400:
        raise HTTPException(status_code=400, detail="char_size must be int between 48 and 400")
    _WALL_CHAR_SIZE = size
    await broadcast({"type": "char_size", "size": size})
    return {"ok": True, "char_size": size}


@app.delete("/admin/api/characters")
async def admin_clear_all(_=Depends(require_admin)):
    """Remove all characters from memory, broadcast removals, and delete from InstantDB."""
    ids = [c["id"] for c in characters]
    characters.clear()
    for char_id in ids:
        await broadcast({"type": "remove_character", "id": char_id})
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, instant_db.delete_character, char_id
            )
        except Exception as e:
            print(f"[db] delete failed: {e}")
    return {"ok": True, "deleted": len(ids)}


@app.post("/admin/api/seed")
async def admin_seed(count: int = 10, _=Depends(require_admin)):
    """Insert N fake characters into memory, broadcast to walls, and persist to InstantDB."""
    import base64, io, random
    from PIL import Image, ImageDraw

    names = ["Ada","Bo","Carl","Dina","Emil","Frida","Geir","Hanna","Ida","Jonas",
             "Kari","Lars","Mari","Nils","Ola","Petra","Rolf","Silje","Tor","Una"]
    dino_types = ["dino_1", "dino_2", "dino_3", "dino_4"]

    def make_image(color):
        img = Image.new("RGB", (160, 160), (30, 30, 30))
        draw = ImageDraw.Draw(img)
        r, g, b = color
        draw.ellipse([40, 20, 120, 100], fill=(r, g, b))
        draw.rectangle([55, 100, 105, 150], fill=(r, g, b))
        draw.ellipse([50, 40, 68, 58], fill=(20, 20, 20))
        draw.ellipse([92, 40, 110, 58], fill=(20, 20, 20))
        draw.arc([58, 65, 102, 88], start=10, end=170, fill=(20, 20, 20), width=3)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    added = []
    for i in range(count):
        color = (random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))
        char_id = str(uuid.uuid4())
        name = random.choice(names)
        dino_type = dino_types[i % len(dino_types)]
        image_b64 = await asyncio.get_event_loop().run_in_executor(None, make_image, color)
        char = {"id": char_id, "image_b64": image_b64, "name": name, "dino_type": dino_type}
        _assign_world_pos(char)
        characters.append(char)
        await broadcast({"type": "new_character", **char})
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, instant_db.publish_character, char_id, name, dino_type, image_b64
            )
        except Exception as e:
            print(f"[seed] db write failed: {e}")
        added.append(char_id)

    return {"ok": True, "added": len(added)}


@app.get("/admin/api/sync")
async def admin_sync(_=Depends(require_admin)):
    """Sync printed status from InstantDB into the in-memory list, return updated list."""
    try:
        printed_ids = await asyncio.get_event_loop().run_in_executor(
            None, instant_db.get_printed_ids
        )
        for char in characters:
            char["printed"] = char["id"] in printed_ids
    except Exception as e:
        print(f"[db] sync failed: {e}")
    return characters


# --- Registered users + CSV import ---

@app.get("/registered-users")
def search_registered(q: str = ""):
    """Search pre-registered users by name prefix. No auth — booth needs this."""
    q_lower = q.strip().lower()
    if not q_lower:
        return [{"id": u["id"], "name": u["name"], "email": u.get("email", "")}
                for u in registered_users]
    return [
        {"id": u["id"], "name": u["name"], "email": u.get("email", "")}
        for u in registered_users
        if u.get("name", "").lower().startswith(q_lower)
    ]


def _parse_spreadsheet(raw: bytes, filename: str) -> list[dict]:
    """Parse CSV or XLSX into a list of dicts with 'name' and 'email' keys."""
    if filename.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            raise HTTPException(status_code=400, detail="Empty spreadsheet")
        headers = [str(h or "").strip().lower() for h in rows[0]]
        return [{headers[i]: (str(cell) if cell is not None else "") for i, cell in enumerate(row)}
                for row in rows[1:]]
    else:
        content = raw.decode("utf-8-sig")
        reader = csv_mod.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="Empty CSV or no header row")
        return [{f.strip().lower(): (row.get(f) or "").strip() for f in reader.fieldnames}
                for row in reader]


@app.post("/admin/api/import-users")
async def admin_import_users(file: UploadFile = File(...), _=Depends(require_admin)):
    """Import pre-registered users from CSV or XLSX. Skips duplicates by email."""
    raw = await file.read()
    rows = _parse_spreadsheet(raw, file.filename or "")

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found")

    # Find name and email columns (case-insensitive)
    col_keys = list(rows[0].keys())
    name_col = next((k for k in col_keys if "name" in k), None)
    email_col = next((k for k in col_keys if "email" in k), None)
    if not name_col or not email_col:
        raise HTTPException(status_code=400, detail=f"File must have 'Name' and 'Email' columns. Found: {col_keys}")

    existing_emails = {u.get("email", "").lower() for u in registered_users}
    imported, skipped = 0, 0

    for row in rows:
        name = (row.get(name_col) or "").strip()
        email = (row.get(email_col) or "").strip()
        if not name or not email:
            skipped += 1
            continue
        if email.lower() in existing_emails:
            skipped += 1
            continue

        user_id = str(uuid.uuid4())
        user = {"id": user_id, "name": name, "email": email, "created_at": int(time.time() * 1000)}
        registered_users.append(user)
        existing_emails.add(email.lower())

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, instant_db.create_registered_user, user_id, name, email
            )
        except Exception as e:
            print(f"[import] DB write failed for {email}: {e}")
        imported += 1

    print(f"[import] Imported {imported}, skipped {skipped}")
    return {"ok": True, "imported": imported, "skipped": skipped, "total": len(registered_users)}


@app.get("/admin/api/registered-users")
def admin_list_registered(_=Depends(require_admin)):
    return [{"id": u["id"], "name": u["name"], "email": u.get("email", ""),
             "created_at": u.get("created_at", 0)} for u in registered_users]


@app.delete("/admin/api/registered-users/{user_id}")
async def admin_delete_registered_user(user_id: str, _=Depends(require_admin)):
    user = next((u for u in registered_users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    registered_users.remove(user)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.delete_registered_user, user_id
        )
    except Exception as e:
        print(f"[admin] delete registered user failed: {e}")
    return {"ok": True}


@app.post("/admin/api/registered-users")
async def admin_add_registered_user(body: dict, _=Depends(require_admin)):
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    if not name or not email:
        raise HTTPException(status_code=400, detail="name and email required")
    # Check duplicate
    if any(u.get("email", "").lower() == email.lower() for u in registered_users):
        raise HTTPException(status_code=409, detail="email already exists")
    user_id = str(uuid.uuid4())
    user = {"id": user_id, "name": name, "email": email, "created_at": int(time.time() * 1000)}
    registered_users.append(user)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.create_registered_user, user_id, name, email
        )
    except Exception as e:
        print(f"[admin] create registered user failed: {e}")
    return {"ok": True, **user}


# --- Demo choices ---

@app.post("/demo-choice")
async def demo_choice(user_id: str = Form(...), demo: str = Form(...)):
    """Store a demo choice for an enrolled face user."""
    user = next((u for u in face_users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    user["demo_choice"] = demo
    user["demo_chosen_at"] = int(time.time() * 1000)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.update_face_user_demo, user_id, demo
        )
    except Exception as e:
        print(f"[demo] DB write failed: {e}")
    return {"ok": True}


# --- Booths ---

@app.get("/admin/api/booths")
def admin_list_booths(_=Depends(require_admin)):
    return booths


@app.post("/admin/api/booths")
async def admin_create_booth(_=Depends(require_admin)):
    next_number = max((b.get("number", 0) for b in booths), default=0) + 1
    booth_id = str(uuid.uuid4())
    booth = {"id": booth_id, "name": f"Booth {next_number}", "number": next_number, "mode": "both"}
    booths.append(booth)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.create_booth, booth_id, booth["name"], next_number, "both"
        )
    except Exception as e:
        print(f"[booth] create failed: {e}")
    return booth


@app.patch("/admin/api/booths/{booth_id}")
async def admin_update_booth(booth_id: str, body: dict, _=Depends(require_admin)):
    booth = next((b for b in booths if b["id"] == booth_id), None)
    if not booth:
        raise HTTPException(status_code=404, detail="not found")
    mode = body.get("mode")
    if mode and mode in ("both", "register", "demo"):
        booth["mode"] = mode
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, instant_db.update_booth, booth_id, mode
            )
        except Exception as e:
            print(f"[booth] update failed: {e}")
    return {"ok": True, **booth}


@app.delete("/admin/api/booths/{booth_id}")
async def admin_delete_booth(booth_id: str, _=Depends(require_admin)):
    booth = next((b for b in booths if b["id"] == booth_id), None)
    if not booth:
        raise HTTPException(status_code=404, detail="not found")
    booths.remove(booth)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.delete_booth, booth_id
        )
    except Exception as e:
        print(f"[booth] delete failed: {e}")
    return {"ok": True}


@app.get("/booth-config/{number}")
def booth_config(number: int):
    """No auth — booth SPA reads this to know its mode."""
    booth = next((b for b in booths if b.get("number") == number), None)
    if not booth:
        return {"mode": "both"}
    return {"mode": booth.get("mode", "both")}


# --- Merged users view ---

@app.get("/admin/api/users-merged")
def admin_users_merged(_=Depends(require_admin)):
    """Merged view of registered_users + face_users for the admin panel."""
    # Build lookup of face_users by name (lowercased)
    face_by_name = {}
    for fu in face_users:
        key = fu.get("name", "").strip().lower()
        if key:
            face_by_name[key] = fu

    merged = []
    seen_names = set()
    for ru in registered_users:
        name_key = ru.get("name", "").strip().lower()
        seen_names.add(name_key)
        fu = face_by_name.get(name_key)
        merged.append({
            "id": ru["id"],
            "name": ru.get("name", ""),
            "email": ru.get("email", ""),
            "interest": fu.get("interest", "") if fu else "",
            "registered_at": ru.get("created_at", 0),
            "has_face": fu is not None,
            "face_user_id": fu["id"] if fu else None,
            "demo_choice": fu.get("demo_choice", "") if fu else "",
        })

    # Add face_users not in registered_users
    for fu in face_users:
        key = fu.get("name", "").strip().lower()
        if key and key not in seen_names:
            merged.append({
                "id": fu["id"],
                "name": fu.get("name", ""),
                "email": "",
                "interest": fu.get("interest", ""),
                "registered_at": fu.get("created_at", 0),
                "has_face": True,
                "face_user_id": fu["id"],
                "demo_choice": fu.get("demo_choice", ""),
            })

    merged.sort(key=lambda u: u.get("name", "").lower())
    return merged


# --- Face recognition ---

@app.post("/face/enroll")
async def face_enroll(
    image: UploadFile = File(...),
    name: str = Form(...),
    interest: str = Form(""),
):
    if not FACE_AVAILABLE:
        raise HTTPException(status_code=503, detail="face_recognition library not available")

    data = await image.read()
    result = await asyncio.get_event_loop().run_in_executor(
        None, compute_embedding, data
    )

    if not result["found"]:
        return {"ok": False, "error": "no_face", "time_ms": result["time_ms"]}

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "name": name,
        "interest": interest,
        "embedding": result["embedding"],
        "created_at": int(time.time() * 1000),
    }
    face_users.append(user)

    # Persist to InstantDB
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            instant_db.create_face_user,
            user_id, name, interest, result["embedding"],
        )
    except Exception as e:
        print(f"[face] InstantDB write failed: {e}")

    return {
        "ok": True,
        "user_id": user_id,
        "name": name,
        "interest": interest,
        "embedding_dims": len(result["embedding"]),
        "time_ms": result["time_ms"],
    }


@app.post("/face/recognize")
async def face_recognize(
    image: UploadFile = File(...),
    threshold: float = Form(0.6),
):
    if not FACE_AVAILABLE:
        raise HTTPException(status_code=503, detail="face_recognition library not available")

    data = await image.read()
    result = await asyncio.get_event_loop().run_in_executor(
        None, compute_embedding, data
    )

    if not result["found"]:
        return {"ok": False, "error": "no_face", "time_ms": result["time_ms"]}

    match = find_match(result["embedding"], face_users, threshold)
    return {
        "ok": True,
        "time_ms": result["time_ms"],
        **match,
    }


@app.get("/face/users")
def face_list_users():
    return [
        {"id": u["id"], "name": u["name"], "interest": u.get("interest", ""),
         "created_at": u.get("created_at", 0)}
        for u in face_users
    ]


@app.delete("/face/users/{user_id}")
async def face_delete_user(user_id: str):
    user = next((u for u in face_users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    face_users.remove(user)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.delete_face_user, user_id
        )
    except Exception as e:
        print(f"[face] delete failed: {e}")
    return {"ok": True}


# --- Web booth SPA ---

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_WEB_DIR = Path(__file__).parent / "static" / "web"

if _WEB_DIR.exists():
    app.mount("/booth/assets", StaticFiles(directory=str(_WEB_DIR / "assets")), name="web-assets")

    @app.get("/booth")
    @app.get("/booth/")
    def booth_index():
        return FileResponse(str(_WEB_DIR / "index.html"))

    @app.get("/booth/{path:path}")
    def booth_spa(path: str):
        file_path = _WEB_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_WEB_DIR / "index.html"))
