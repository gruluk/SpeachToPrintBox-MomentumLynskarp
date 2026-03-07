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
import os
import secrets
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Restore all characters from InstantDB so a reboot/redeploy loses nothing
    try:
        loop = asyncio.get_event_loop()
        existing = await loop.run_in_executor(None, instant_db.get_all_characters)
        characters.extend(existing)
        print(f"[startup] Restored {len(existing)} characters from InstantDB")
    except Exception as e:
        print(f"[startup] Could not restore characters from InstantDB: {e}")
    yield


app = FastAPI(lifespan=lifespan)


async def broadcast(message: dict):
    data = json.dumps(message)
    dead = []
    for ws in connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)


# --- Health ---

@app.get("/health")
def health():
    return {"ok": True, "characters": len(characters)}


# --- TV wall ---

@app.get("/", response_class=HTMLResponse)
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
