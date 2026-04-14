#!/usr/bin/env python3
"""
Momentum Lynskarp — Mac print client

Polls InstantDB for users with label_printed=false and prints name+interest
labels on the Brother QL-1110NWB label printer.

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


def get_users_to_print() -> list[dict]:
    """Return users where label_printed == false."""
    payload = {"query": {"users": {"$": {"where": {"label_printed": False}}}}}
    r = requests.post(f"{_INSTANT_BASE}/admin/query", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("users", [])


def mark_label_printed(user_id: str) -> None:
    """Set label_printed=true on a user."""
    payload = {"steps": [["update", "users", user_id, {"label_printed": True}]]}
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


def composite_label(user_name: str, interest: str) -> Image.Image:
    """Create a label with logo (top-left), name (top-right), interests stacked vertically below."""
    DPI = 300
    target_w  = round(LABEL_W_MM  * DPI / 25.4)
    content_h = round(CONTENT_H_MM * DPI / 25.4)

    canvas = Image.new("RGB", (target_w, content_h), "white")
    draw   = ImageDraw.Draw(canvas)
    PAD    = 14

    # Top row: name centered — 25% of height
    top_h = int(content_h * 0.25)

    # Name (centered)
    name_area_w = target_w - PAD * 2
    name_font_size = min(top_h - PAD * 2, 80)
    try:
        name_font = _find_font(name_font_size)
        while name_font_size > 12:
            name_font = _find_font(name_font_size)
            bbox = name_font.getbbox(user_name)
            if (bbox[2] - bbox[0]) <= name_area_w:
                break
            name_font_size -= 4
    except Exception:
        name_font = ImageFont.load_default()

    name_bbox = name_font.getbbox(user_name)
    name_text_h = name_bbox[3] - name_bbox[1]
    name_text_w = name_bbox[2] - name_bbox[0]
    name_y = (top_h - name_text_h) // 2 - name_bbox[1]
    name_x = (target_w - name_text_w) // 2 - name_bbox[0]
    draw.text((name_x, name_y), user_name, fill="#3c1c71", font=name_font)

    # Interests — stacked vertically, centered
    interest_area_top = top_h
    interest_area_h = content_h - interest_area_top - PAD
    items = [s.strip() for s in (interest or "").split(",") if s.strip()]

    if items:
        # Calculate font size that fits all items
        line_count = len(items)
        line_spacing = 8
        available_h = interest_area_h - (line_count - 1) * line_spacing
        interest_font_size = min(int(available_h / line_count * 0.85), 120)

        # Shrink until widest item fits
        while interest_font_size > 12:
            interest_font = _find_font(interest_font_size)
            max_w = max(interest_font.getbbox(item)[2] - interest_font.getbbox(item)[0] for item in items)
            if max_w <= target_w - PAD * 2:
                break
            interest_font_size -= 4
        interest_font = _find_font(interest_font_size)

        # Measure total height of all lines
        line_heights = []
        for item in items:
            bbox = interest_font.getbbox(item)
            line_heights.append(bbox[3] - bbox[1])
        total_text_h = sum(line_heights) + (line_count - 1) * line_spacing

        # Draw each item centered
        y_cursor = interest_area_top + (interest_area_h - total_text_h) // 2
        for idx, item in enumerate(items):
            bbox = interest_font.getbbox(item)
            text_w = bbox[2] - bbox[0]
            x = (target_w - text_w) // 2 - bbox[0]
            draw.text((x, y_cursor - bbox[1]), item, fill="#3c1c71", font=interest_font)
            y_cursor += line_heights[idx] + line_spacing

    return canvas


# ── Printing ──────────────────────────────────────────────────────────────────

def send_to_printer(image: Image.Image) -> bool:
    """Send image to the printer via CUPS. Returns True on success."""
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


# ── Process a user ────────────────────────────────────────────────────────────

def process_user(user: dict) -> None:
    user_id  = user["id"]
    name     = user.get("name", "").strip()
    interest = user.get("interest", "")

    if not name:
        print(f"[skip]  {user_id} — no name, skipping")
        return

    print(f"[label] compositing for {name!r} interest={interest!r}")
    try:
        label = composite_label(name, interest)
    except Exception as e:
        print(f"[error] compositing failed: {e}")
        return

    success = send_to_printer(label)
    if success:
        mark_label_printed(user_id)
        print(f"[db]    marked {user_id} as label_printed")
    else:
        print(f"[warn]  print failed — will retry next poll")


# ── Startup checks ────────────────────────────────────────────────────────────

def check_printer() -> None:
    """Log CUPS printer status on startup."""
    try:
        result = subprocess.run(["lpstat", "-p", PRINTER_NAME],
                                capture_output=True, text=True)
        status = (result.stdout + result.stderr).strip()
        print(f"[cups]  {status if status else f'{PRINTER_NAME} not found in lpstat'}")
    except FileNotFoundError:
        print("[cups]  lpstat not available — CUPS may not be installed")

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


# ── Poll loop ─────────────────────────────────────────────────────────────────

def poll_loop() -> None:
    if not _APP_ID or not _ADMIN_TOKEN:
        print("[error] INSTANT_APP_ID and INSTANT_ADMIN_TOKEN must be set in .env")
        return

    print(f"Momentum Lynskarp print client — printer: {PRINTER_NAME}")
    check_printer()
    print(f"Polling InstantDB every {POLL_INTERVAL}s for users needing labels...")

    while True:
        try:
            to_print = get_users_to_print()
            if to_print:
                print(f"[poll] {len(to_print)} user(s) need labels")
                for user in to_print:
                    process_user(user)
        except Exception as e:
            print(f"[poll] error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll_loop()
