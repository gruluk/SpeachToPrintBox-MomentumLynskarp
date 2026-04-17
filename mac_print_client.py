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

import qrcode
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
QR_BASE_URL     = os.getenv("QR_BASE_URL", "https://lynskarp.soprasteria.no")


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

_BUNDLED_FONT = os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf")


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_BUNDLED_FONT, size)


def composite_label(user_name: str, interest: str, user_id: str = "") -> Image.Image:
    """Create a label with square QR code on the left and name + interests on the right."""
    DPI = 300
    target_w  = round(LABEL_W_MM  * DPI / 25.4)
    content_h = round(CONTENT_H_MM * DPI / 25.4)
    PAD = 14

    canvas = Image.new("RGB", (target_w, content_h), "white")
    draw = ImageDraw.Draw(canvas)

    # --- Square QR code on the left ---
    qr_url = f"{QR_BASE_URL}/u/{user_id}" if user_id else "https://lynskarp.soprasteria.no"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_size = content_h - PAD * 2
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    canvas.paste(qr_img, (PAD, PAD))

    # --- Text area on the right ---
    text_left = PAD + qr_size + PAD * 2
    text_area_w = target_w - text_left - PAD
    text_area_top = PAD

    # Separator line
    sep_x = PAD + qr_size + PAD
    draw.line([(sep_x, PAD + 10), (sep_x, content_h - PAD - 10)], fill="#cccccc", width=2)

    # Name (top-right aligned)
    name_font_size = 36
    try:
        name_font = _find_font(name_font_size)
        while name_font_size > 12:
            name_font = _find_font(name_font_size)
            bbox = name_font.getbbox(user_name)
            if (bbox[2] - bbox[0]) <= text_area_w:
                break
            name_font_size -= 4
    except Exception:
        name_font = ImageFont.load_default()

    name_bbox = name_font.getbbox(user_name)
    name_text_w = name_bbox[2] - name_bbox[0]
    name_text_h = name_bbox[3] - name_bbox[1]
    name_x = target_w - PAD - name_text_w - name_bbox[0]
    name_y = text_area_top - name_bbox[1]
    draw.text((name_x, name_y), user_name, fill="black", font=name_font)

    # Interests (below name, left-aligned with word wrap)
    items = [s.strip() for s in (interest or "").split(",") if s.strip()]
    interest_top = text_area_top + name_text_h + 16
    interest_area_h = content_h - interest_top - PAD
    item_spacing = 35

    if items:
        interest_font_size = 60
        wrapped_lines = []
        while interest_font_size > 10:
            interest_font = _find_font(interest_font_size)
            line_h = interest_font.getbbox("Ag")[3] - interest_font.getbbox("Ag")[1]
            wrapped_lines = []
            for item in items:
                words = item.split()
                lines = []
                current = words[0]
                for word in words[1:]:
                    test = current + " " + word
                    tw = interest_font.getbbox(test)[2] - interest_font.getbbox(test)[0]
                    if tw <= text_area_w:
                        current = test
                    else:
                        lines.append(current)
                        current = word
                lines.append(current)
                wrapped_lines.append(lines)
            total_lines = sum(len(lines) for lines in wrapped_lines)
            total_h = total_lines * line_h + (len(items) - 1) * item_spacing
            if total_h <= interest_area_h:
                break
            interest_font_size -= 4
        interest_font = _find_font(interest_font_size)
        line_h = interest_font.getbbox("Ag")[3] - interest_font.getbbox("Ag")[1]

        total_lines = sum(len(lines) for lines in wrapped_lines)
        total_h = total_lines * line_h + (len(items) - 1) * item_spacing
        y_cursor = interest_top + (interest_area_h - total_h) // 2

        for idx, lines in enumerate(wrapped_lines):
            for line in lines:
                bbox = interest_font.getbbox(line)
                draw.text((text_left, y_cursor - bbox[1]), line, fill="#444444", font=interest_font)
                y_cursor += line_h
            if idx < len(wrapped_lines) - 1:
                y_cursor += item_spacing

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
        label = composite_label(name, interest, user_id)
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
