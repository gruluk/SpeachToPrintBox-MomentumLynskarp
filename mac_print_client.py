#!/usr/bin/env python3
"""
Bytefest '26 — Mac print client

Polls InstantDB for unprinted characters and prints them on the Brother
QL-1110NWB label printer.

Setup (one-time):
  pip install requests Pillow python-dotenv
  Install the official Brother QL-1110NWB driver from Brother's website
  Add the printer in System Settings → Printers
  Run `lpstat -p` to find the exact printer name, set PRINTER_NAME below
  Add INSTANT_APP_ID and INSTANT_ADMIN_TOKEN to your .env file

Run:
  python3 mac_print_client.py
"""

import os
import subprocess
import tempfile
import time
from io import BytesIO
import base64

import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

# Run `lpstat -p` to find the exact name — usually something like:
#   Brother_QL-1110NWB  or  Brother_QL_1110NWB
PRINTER_NAME = "Brother_QL_1110NWB"

POLL_INTERVAL = 5  # seconds between InstantDB polls

ASSETS_DIR    = os.path.join(os.path.dirname(__file__), "assets")
LABEL_W_MM    = 103
CONTENT_H_MM  = 45

DINO_NAMES = {
    "1": "Brachiosaurus",
    "2": "Triceratops",
    "3": "Stegosaurus",
    "4": "Pterodactyl",
}

# ── InstantDB ─────────────────────────────────────────────────────────────────

_INSTANT_BASE  = "https://api.instantdb.com"
_APP_ID        = os.getenv("INSTANT_APP_ID", "")
_ADMIN_TOKEN   = os.getenv("INSTANT_ADMIN_TOKEN", "")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_ADMIN_TOKEN}",
        "App-Id": _APP_ID,
        "Content-Type": "application/json",
    }


def get_unprinted() -> list[dict]:
    payload = {"query": {"characters": {"$": {"where": {"printed": False}}}}}
    r = requests.post(f"{_INSTANT_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("characters", [])


def mark_printed(char_id: str) -> None:
    payload = {"steps": [["update", "characters", char_id, {"printed": True}]]}
    r = requests.post(f"{_INSTANT_BASE}/admin/transact", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()


# ── Label compositing ─────────────────────────────────────────────────────────

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


# ── Printing ──────────────────────────────────────────────────────────────────

def print_label(image: Image.Image) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        image.save(f, format="PNG")
        tmp_path = f.name
    try:
        subprocess.run(
            [
                "lp", "-d", PRINTER_NAME,
                "-o", f"PageSize=Custom.{LABEL_W_MM}x{CONTENT_H_MM}mm",
                "-o", "MediaType=roll",
                "-o", "CutMedia=EndOfJob",
                tmp_path,
            ],
            check=True,
        )
        print(f"[print] sent to {PRINTER_NAME}")
    except subprocess.CalledProcessError as e:
        print(f"[print] lp failed: {e}")
    finally:
        os.unlink(tmp_path)


# ── Poll loop ─────────────────────────────────────────────────────────────────

def process_character(char: dict) -> None:
    char_id   = char["id"]
    name      = char.get("name", "").strip()
    dino_type = char.get("dino_type", "1")
    image_b64 = char.get("image_b64", "")

    if not name or not image_b64:
        print(f"[skip] {char_id} — missing name or image")
        return

    print(f"[print] {name} ({DINO_NAMES.get(dino_type, dino_type)})")
    img   = Image.open(BytesIO(base64.b64decode(image_b64)))
    label = composite_label(img, name, dino_type)
    print_label(label)
    mark_printed(char_id)
    print(f"[db]    marked {char_id} as printed")


def poll_loop() -> None:
    if not _APP_ID or not _ADMIN_TOKEN:
        print("[error] INSTANT_APP_ID and INSTANT_ADMIN_TOKEN must be set in .env")
        return

    print(f"Bytefest '26 print client — printer: {PRINTER_NAME}")
    print(f"Polling InstantDB every {POLL_INTERVAL}s for unprinted characters...")

    while True:
        try:
            unprinted = get_unprinted()
            if unprinted:
                print(f"[poll] {len(unprinted)} unprinted character(s)")
                for char in unprinted:
                    process_character(char)
        except Exception as e:
            print(f"[poll] error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll_loop()
