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
import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from PIL import Image

from generate import generate_image
from validate import validate_photo

app = FastAPI()

# In-memory store — sufficient for a single event day
characters: List[dict] = []
connections: List[WebSocket] = []


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
    character = {"id": char_id, "image_b64": img_b64}
    characters.append(character)

    await broadcast({"type": "new_character", **character})

    return {"id": char_id, "image_b64": img_b64}


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
