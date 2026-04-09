#!/usr/bin/env python3
"""
Sopra Steria @ UiO — Mac print client

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

ASSETS_DIR      = os.path.join(os.path.dirname(__file__), "assets")
WEB_PUBLIC_DIR  = os.path.join(os.path.dirname(__file__), "web", "public")
LABEL_W_MM      = 103
CONTENT_H_MM    = 45


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


def composite_label(character: Image.Image, user_name: str, dino_type: str = "") -> Image.Image:
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

    # Logo
    logo_bottom = PAD
    try:
        logo = Image.open(
            os.path.join(ASSETS_DIR, "SopraSteria", "sopra_steria_logo.png")
        ).convert("RGBA")
        logo_h = content_h // 3
        logo_w = int(logo.width * logo_h / logo.height)
        if logo_w > right_w:
            logo_w = right_w
            logo_h = int(logo.height * logo_w / logo.width)
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        canvas.paste(logo, (right_x, PAD), logo)
        logo_bottom = PAD + logo_h
    except Exception:
        pass

    # Name — fills all remaining vertical space below the logo
    name_area_top = logo_bottom + PAD
    name_area_h   = content_h - name_area_top - PAD
    font_size = min(int(name_area_h * 0.80), 200)
    while font_size > 12:
        font = _find_font(font_size)
        bbox = font.getbbox(user_name)
        if (bbox[2] - bbox[0]) <= right_w:
            break
        font_size -= 4
    font  = _find_font(font_size)
    name_y = name_area_top + (name_area_h - font_size) // 2
    draw.text((right_x, name_y), user_name, fill="#3c1c71", font=font)

    return canvas


# ── Printing ──────────────────────────────────────────────────────────────────

def print_label(image: Image.Image) -> bool:
    """Send image to the printer. Returns True on success."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        image.save(f, format="PNG")
        tmp_path = f.name

    cmd = [
        "lp", "-d", PRINTER_NAME,
        "-o", f"media=Custom.{LABEL_W_MM}x{CONTENT_H_MM}mm",
        "-o", "MediaType=Continuous",
        "-o", "CutMedia=EndOfJob",
        tmp_path,
    ]
    print(f"[print] running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"[print] lp stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"[print] lp stderr: {result.stderr.strip()}")
        if result.returncode != 0:
            print(f"[print] lp exited with code {result.returncode}")
            return False
        print(f"[print] job queued on {PRINTER_NAME}")
        return True
    except FileNotFoundError:
        print("[print] ERROR: 'lp' command not found — is CUPS installed?")
        return False
    finally:
        os.unlink(tmp_path)


# ── Poll loop ─────────────────────────────────────────────────────────────────

def process_character(char: dict) -> None:
    char_id   = char["id"]
    name      = char.get("name", "").strip()
    dino_type = char.get("dino_type", "")  # already the full name from DB
    image_b64 = char.get("image_b64", "")

    print(f"[char]  id={char_id} name={name!r} dino_type={dino_type!r} "
          f"image_b64={'<present>' if image_b64 else '<MISSING>'}")

    if not name or not image_b64:
        print(f"[skip]  {char_id} — missing name or image, skipping")
        return

    print(f"[print] compositing label for {name} ({dino_type or 'unknown dino'})")
    try:
        img   = Image.open(BytesIO(base64.b64decode(image_b64)))
        label = composite_label(img, name, dino_type)
    except Exception as e:
        print(f"[error] compositing failed: {e}")
        return

    success = print_label(label)
    if success:
        mark_printed(char_id)
        print(f"[db]    marked {char_id} as printed")
    else:
        print(f"[warn]  print failed — NOT marking as printed so it retries next poll")


def check_printer() -> None:
    """Log CUPS printer status on startup."""
    try:
        result = subprocess.run(["lpstat", "-p", PRINTER_NAME],
                                capture_output=True, text=True)
        status = (result.stdout + result.stderr).strip()
        print(f"[cups]  {status if status else f'{PRINTER_NAME} not found in lpstat'}")
    except FileNotFoundError:
        print("[cups]  lpstat not available — CUPS may not be installed")

    # Also list all printers so user can verify the name
    try:
        result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        if lines:
            print("[cups]  all printers:")
            for l in lines:
                print(f"          {l}")
        else:
            print("[cups]  no printers found via lpstat -p")
    except Exception:
        pass


def poll_loop() -> None:
    if not _APP_ID or not _ADMIN_TOKEN:
        print("[error] INSTANT_APP_ID and INSTANT_ADMIN_TOKEN must be set in .env")
        return

    print(f"Sopra Steria print client — printer: {PRINTER_NAME}")
    check_printer()
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
