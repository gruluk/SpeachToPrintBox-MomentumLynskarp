#!/usr/bin/env python3
"""
Bytefest '26 — Mac print client

Connects to the event server WebSocket and prints a label whenever
a new character is published.

Setup (one-time):
  pip install websocket-client Pillow
  Install the official Brother QL-1110NWB driver from Brother's website
  Add the printer in System Settings → Printers
  Run `lpstat -p` to find the exact printer name, set PRINTER_NAME below

Run:
  python3 mac_print_client.py
"""

import base64
import json
import os
import subprocess
import tempfile
import time
from io import BytesIO

import websocket
from PIL import Image, ImageDraw, ImageFont

# ── Configuration ────────────────────────────────────────────────────────────
SERVER_WS_URL = "wss://speachtoprintbox-production.up.railway.app/ws"

# Run `lpstat -p` to find the exact name — usually something like:
#   Brother_QL-1110NWB  or  Brother_QL_1110NWB
PRINTER_NAME = "Brother_QL-1110NWB"

ASSETS_DIR    = os.path.join(os.path.dirname(__file__), "assets")
LABEL_W_MM    = 103
CONTENT_H_MM  = 45

DINO_NAMES = {
    "1": "Brachiosaurus",
    "2": "Triceratops",
    "3": "Stegosaurus",
    "4": "Pterodactyl",
}
# ─────────────────────────────────────────────────────────────────────────────


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf"),
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def composite_label(character: Image.Image, user_name: str, dino_type: str) -> Image.Image:
    DPI = 300
    target_w  = round(LABEL_W_MM   * DPI / 25.4)
    content_h = round(CONTENT_H_MM * DPI / 25.4)

    canvas = Image.new("RGB", (target_w, content_h), "white")
    draw   = ImageDraw.Draw(canvas)
    PAD    = 14

    # Left column: character image (square, full height)
    split_x   = int(target_w * 0.40)
    char_size = min(split_x - PAD * 2, content_h - PAD * 2)
    char = character.convert("RGBA").resize((char_size, char_size), Image.NEAREST)
    canvas.paste(char, ((split_x - char_size) // 2, (content_h - char_size) // 2), char)

    right_x = split_x + PAD
    right_w = target_w - right_x - PAD

    # Logo (top right)
    logo_bottom = PAD
    try:
        logo = Image.open(
            os.path.join(ASSETS_DIR, "Figma assets", "logo_figma.png")
        ).convert("RGBA")
        logo_h = content_h // 5
        logo_w = int(logo.width * logo_h / logo.height)
        if logo_w > right_w:
            logo_w = right_w
            logo_h = int(logo.height * logo_w / logo.width)
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        canvas.paste(logo, (right_x, PAD), logo)
        logo_bottom = PAD + logo_h
    except Exception:
        pass

    # Dino name (bottom right)
    dino_label_size = max(16, content_h // 16)
    draw.text(
        (right_x, content_h - PAD - dino_label_size),
        DINO_NAMES.get(dino_type, ""),
        fill="#4a8a9e",
        font=_find_font(dino_label_size),
    )
    dino_label_top = content_h - PAD - dino_label_size

    # Name (right middle)
    name_area_top = logo_bottom + PAD
    name_area_h   = dino_label_top - name_area_top - PAD
    font_size = min(int(name_area_h * 0.80), 200)
    font = _find_font(font_size)
    while font_size > 12:
        font = _find_font(font_size)
        bbox = font.getbbox(user_name)
        if (bbox[2] - bbox[0]) <= right_w:
            break
        font_size -= 4
    name_y = name_area_top + (name_area_h - font_size) // 2
    draw.text((right_x, name_y), user_name, fill="#2d5c6a", font=font)

    return canvas


def print_label(image: Image.Image) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        image.save(f, format="PNG")
        tmp_path = f.name
    try:
        subprocess.run(
            ["lp", "-d", PRINTER_NAME, "-o", "fit-to-page", tmp_path],
            check=True,
        )
        print(f"[print] sent to {PRINTER_NAME}")
    except subprocess.CalledProcessError as e:
        print(f"[print] lp failed: {e}")
    finally:
        os.unlink(tmp_path)


# ── WebSocket handlers ────────────────────────────────────────────────────────

def on_message(ws, message):
    try:
        msg = json.loads(message)
        if msg.get("type") != "new_character":
            return
        name = msg.get("name", "").strip()
        if not name:
            return  # character not yet published (no name yet)
        dino_type = msg.get("dino_type", "1")
        image_b64 = msg.get("image_b64", "")
        if not image_b64:
            return

        print(f"[ws] printing: {name} ({DINO_NAMES.get(dino_type, dino_type)})")
        img   = Image.open(BytesIO(base64.b64decode(image_b64)))
        label = composite_label(img, name, dino_type)
        print_label(label)
    except Exception as e:
        print(f"[error] {e}")


def on_error(ws, error):
    print(f"[ws] error: {error}")


def on_close(ws, code, msg):
    print(f"[ws] closed ({code}), reconnecting in 5s...")
    time.sleep(5)
    connect()


def on_open(ws):
    print(f"[ws] connected to {SERVER_WS_URL}")


def connect():
    ws = websocket.WebSocketApp(
        SERVER_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()


if __name__ == "__main__":
    print(f"Bytefest '26 print client — printer: {PRINTER_NAME}")
    connect()
