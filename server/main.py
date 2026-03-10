"""
Bytefest '26 — Central server

Endpoints:
  GET  /          — TV wall display (open in browser on each TV)
  GET  /health    — health check
  POST /validate  — photo quality gate (gpt-4o-mini)
  POST /generate  — pixel art generation (gpt-image-1), stores + broadcasts result
  GET  /characters — all generated characters so far (for wall reconnects)
  WS   /ws        — WebSocket feed for the TV wall
"""

import asyncio
import base64
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
from generate import generate_image
from validate import validate_photo

_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "bytefest26")
_security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_security)):
    ok = secrets.compare_digest(credentials.password.encode(), _ADMIN_PASSWORD.encode())
    if not ok:
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})


# In-memory store — populated from InstantDB on startup
characters: List[dict] = []
connections: List[WebSocket] = []

# ── TV wall world coordinates ─────────────────────────────────────────────────
# The wall is 4 screens side-by-side. Each Pi opens /wall?screen=N and offsets
# its rendering by N × _LOGICAL_SCREEN_W pixels.
_LOGICAL_SCREEN_W = 1920   # configure each Pi to output 1920×1080
_WORLD_W          = _LOGICAL_SCREEN_W * 4   # 7680 — full 4-screen width
_WORLD_H          = 1080
_WALL_HEADER_H    = 120    # keep characters below the header
_WALL_GROUND_H    = 220    # keep characters above the ground-dino scene
_WALL_CHAR_SIZE   = 144
_WALL_MARGIN      = 24
_CHAR_SPEED_MIN   = 30    # px/s  — slow DVD-screensaver drift
_CHAR_SPEED_MAX   = 60    # px/s
_PHYSICS_TICK     = 0.1   # seconds between physics updates (10 fps)


def _assign_world_pos(char: dict) -> None:
    """Assign a random starting position and velocity for DVD-style bouncing."""
    char['x'] = float(random.randint(_WALL_MARGIN,
                                     _WORLD_W - _WALL_CHAR_SIZE - _WALL_MARGIN))
    char['y'] = float(random.randint(_WALL_HEADER_H,
                                     _WORLD_H - _WALL_CHAR_SIZE - _WALL_GROUND_H))
    speed = random.uniform(_CHAR_SPEED_MIN, _CHAR_SPEED_MAX)
    angle = random.uniform(0, 2 * math.pi)
    char['vx'] = speed * math.cos(angle)
    char['vy'] = speed * math.sin(angle)


async def _character_movement_loop() -> None:
    """Physics loop: advance every character each tick, bounce off walls, broadcast positions."""
    x_min = float(_WALL_MARGIN)
    x_max = float(_WORLD_W - _WALL_CHAR_SIZE - _WALL_MARGIN)
    y_min = float(_WALL_HEADER_H)
    y_max = float(_WORLD_H - _WALL_CHAR_SIZE - _WALL_GROUND_H)

    while True:
        try:
            await asyncio.sleep(_PHYSICS_TICK)
            if not characters:
                continue

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
):
    char = next((c for c in characters if c["id"] == char_id), None)
    if not char:
        return {"error": "not found"}
    char["name"] = name
    char["dino_type"] = dino_type
    await broadcast({"type": "new_character", **char})

    # Persist to InstantDB (non-blocking — fire and forget)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            instant_db.publish_character,
            char_id, name, dino_type, char["image_b64"],
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
    connections.append(ws)
    # Send all existing characters so the wall is up to date on reconnect
    for char in characters:
        await ws.send_text(json.dumps({"type": "new_character", **char}))
    try:
        while True:
            await ws.receive_text()  # keep-alive
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
