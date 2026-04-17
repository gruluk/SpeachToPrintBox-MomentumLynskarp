"""
Sopra Steria @ Momentum Lynskarp — Central server

Endpoints:
  GET  /health        — health check
  POST /print-label   — print a name+interest label
  GET  /users/{id}    — look up user by ID (for QR scan)
"""

import asyncio
import csv as csv_mod
import io
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import qrcode
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from PIL import Image, ImageDraw, ImageFont

import db as instant_db

_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "soprasteria")
_security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_security)):
    ok = secrets.compare_digest(credentials.password.encode(), _ADMIN_PASSWORD.encode())
    if not ok:
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})


# In-memory store — populated from InstantDB on startup
users: List[dict] = []
booths: List[dict] = []
presentations: List[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    # Restore users
    try:
        us = await loop.run_in_executor(None, instant_db.get_all_users)
        users.extend(us)
        print(f"[startup] Restored {len(us)} users from InstantDB")
    except Exception as e:
        print(f"[startup] Could not restore users from InstantDB: {e}")
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
    # Restore presentations
    try:
        ps = await loop.run_in_executor(None, instant_db.get_all_presentations)
        presentations.extend(ps)
        print(f"[startup] Restored {len(ps)} presentations from InstantDB")
    except Exception as e:
        print(f"[startup] Could not restore presentations from InstantDB: {e}")
    yield


app = FastAPI(lifespan=lifespan)


# --- Health ---

@app.get("/health")
def health():
    return {"ok": True, "users": len(users)}


# --- Print label ---

@app.post("/print-label")
async def print_label(
    name: str = Form(""),
    interest: str = Form(""),
    user_id: str = Form(""),
):
    """Store interest and flag user for label printing via mac_print_client."""
    if not user_id:
        return {"ok": False, "error": "user_id required"}

    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return {"ok": False, "error": "user not found"}

    user["interest"] = interest
    user["label_printed"] = False

    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: instant_db.update_user(user_id, interest=interest, label_printed=False),
        )
    except Exception as e:
        print(f"[print-label] DB write failed: {e}")
        return {"ok": False, "error": str(e)}

    print(f"[print-label] queued label for {name!r} interest={interest!r}")
    return {"ok": True}


# --- Label preview ---

_QR_BASE_URL = os.getenv("QR_BASE_URL", "https://lynskarp.soprasteria.no")
_LABEL_W = round(103 * 300 / 25.4)   # 103mm at 300 DPI
_LABEL_H = round(45 * 300 / 25.4)    # 45mm at 300 DPI
_ASSETS_DIR = Path(__file__).parent.parent / "assets"


_BUNDLED_FONT = str(_ASSETS_DIR / "ArialBold.ttf")


def _find_font(size):
    return ImageFont.truetype(_BUNDLED_FONT, size)


def _generate_label(user_name: str, interest: str, user_id: str) -> bytes:
    PAD = 14
    canvas = Image.new("RGB", (_LABEL_W, _LABEL_H), "white")
    draw = ImageDraw.Draw(canvas)

    # Square QR code on the left
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(f"{_QR_BASE_URL}/u/{user_id}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_size = _LABEL_H - PAD * 2
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    canvas.paste(qr_img, (PAD, PAD))

    # Text area on the right
    text_left = PAD + qr_size + PAD * 2
    text_area_w = _LABEL_W - text_left - PAD
    sep_x = PAD + qr_size + PAD
    draw.line([(sep_x, PAD + 10), (sep_x, _LABEL_H - PAD - 10)], fill="#cccccc", width=2)

    # Name (top-right)
    name_font_size = 56
    name_font = _find_font(name_font_size)
    while name_font_size > 12:
        name_font = _find_font(name_font_size)
        bbox = name_font.getbbox(user_name)
        if (bbox[2] - bbox[0]) <= text_area_w:
            break
        name_font_size -= 4
    name_bbox = name_font.getbbox(user_name)
    name_text_w = name_bbox[2] - name_bbox[0]
    name_text_h = name_bbox[3] - name_bbox[1]
    name_x = _LABEL_W - PAD - name_text_w - name_bbox[0]
    draw.text((name_x, PAD - name_bbox[1]), user_name, fill="black", font=name_font)

    # Interests (below name, left-aligned)
    items = [s.strip() for s in (interest or "").split(",") if s.strip()]
    interest_top = PAD + name_text_h + 16
    interest_area_h = _LABEL_H - interest_top - PAD

    if items:
        line_count = len(items)
        line_spacing = 8
        available_h = interest_area_h - (line_count - 1) * line_spacing
        interest_font_size = min(int(available_h / line_count * 0.85), 100)
        while interest_font_size > 10:
            interest_font = _find_font(interest_font_size)
            max_w = max(interest_font.getbbox(item)[2] - interest_font.getbbox(item)[0] for item in items)
            if max_w <= text_area_w:
                break
            interest_font_size -= 4
        interest_font = _find_font(interest_font_size)

        line_heights = []
        for item in items:
            bbox = interest_font.getbbox(item)
            line_heights.append(bbox[3] - bbox[1])
        total_text_h = sum(line_heights) + (line_count - 1) * line_spacing

        y_cursor = interest_top + (interest_area_h - total_text_h) // 2
        for idx, item in enumerate(items):
            bbox = interest_font.getbbox(item)
            draw.text((text_left, y_cursor - bbox[1]), item, fill="#444444", font=interest_font)
            y_cursor += line_heights[idx] + line_spacing

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


@app.get("/label-preview/{user_id}")
def label_preview(user_id: str, name: str = "", interest: str = ""):
    """Generate and return the label image as PNG.
    Accepts name/interest as query params to avoid race conditions."""
    if not name:
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        name = user.get("name", "")
        interest = interest or user.get("interest", "")
    png = _generate_label(name, interest, user_id)
    return Response(content=png, media_type="image/png")


# --- Admin panel ---

@app.get("/admin", response_class=HTMLResponse)
def admin_page(_=Depends(require_admin)):
    return (Path(__file__).parent / "static" / "admin.html").read_text()


# --- Users ---

@app.get("/users")
def search_users(q: str = ""):
    """Search users by name. No auth — booth needs this."""
    q_lower = q.strip().lower()

    def _user_dict(u):
        return {
            "id": u["id"],
            "name": u["name"],
            "email": u.get("email", ""),
            "has_char": False,
        }

    if not q_lower:
        return [_user_dict(u) for u in users]
    return [
        _user_dict(u)
        for u in users
        if u.get("name", "").lower().startswith(q_lower)
    ]


def _parse_spreadsheet(raw: bytes, filename: str) -> list[dict]:
    """Parse CSV or XLSX into a list of dicts with lowercased keys."""
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
    """Import users from CSV or XLSX. Skips duplicates by email."""
    raw = await file.read()
    rows = _parse_spreadsheet(raw, file.filename or "")

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found")

    col_keys = list(rows[0].keys())
    name_col = next((k for k in col_keys if "name" in k), None)
    email_col = next((k for k in col_keys if "email" in k), None)
    if not name_col or not email_col:
        raise HTTPException(status_code=400, detail=f"File must have 'Name' and 'Email' columns. Found: {col_keys}")

    existing_emails = {u.get("email", "").lower() for u in users}
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
        users.append(user)
        existing_emails.add(email.lower())

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, instant_db.create_user, user_id, name, email
            )
        except Exception as e:
            print(f"[import] DB write failed for {email}: {e}")
        imported += 1

    print(f"[import] Imported {imported}, skipped {skipped}")
    return {"ok": True, "imported": imported, "skipped": skipped, "total": len(users)}


@app.get("/admin/api/users")
def admin_list_users(_=Depends(require_admin)):
    """Full user list for admin panel."""
    result = []
    for u in users:
        result.append({
            "id": u["id"],
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "interest": u.get("interest", ""),
            "label_printed": u.get("label_printed"),
            "wants_demo": bool(u.get("wants_demo")),
            "created_at": u.get("created_at", 0),
        })
    result.sort(key=lambda u: u.get("name", "").lower())
    return result


@app.post("/admin/api/users")
async def admin_add_user(body: dict, _=Depends(require_admin)):
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    if not name or not email:
        raise HTTPException(status_code=400, detail="name and email required")
    if any(u.get("email", "").lower() == email.lower() for u in users):
        raise HTTPException(status_code=409, detail="email already exists")
    user_id = str(uuid.uuid4())
    user = {"id": user_id, "name": name, "email": email, "created_at": int(time.time() * 1000)}
    users.append(user)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.create_user, user_id, name, email
        )
    except Exception as e:
        print(f"[admin] create user failed: {e}")
    return {"ok": True, **user}


@app.patch("/admin/api/users/{user_id}")
async def admin_patch_user(user_id: str, body: dict, _=Depends(require_admin)):
    """Clear specific fields on a user (e.g. embedding, interest)."""
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="not found")

    db_updates = {}

    if body.get("clear_interest"):
        user.pop("interest", None)
        user.pop("label_printed", None)
        db_updates["interest"] = None
        db_updates["label_printed"] = None

    if "wants_demo" in body:
        user["wants_demo"] = bool(body["wants_demo"])
        db_updates["wants_demo"] = bool(body["wants_demo"])

    if db_updates:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: instant_db.update_user(user_id, **db_updates),
            )
        except Exception as e:
            print(f"[admin] patch user failed: {e}")

    return {"ok": True}


@app.delete("/admin/api/users/{user_id}")
async def admin_delete_user(user_id: str, _=Depends(require_admin)):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    users.remove(user)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.delete_user, user_id
        )
    except Exception as e:
        print(f"[admin] delete user failed: {e}")
    return {"ok": True}


# --- Demo choices ---

@app.post("/demo-choice")
async def demo_choice(body: dict):
    """Mark a user as wanting a demo."""
    user_id = body.get("user_id")
    wants_demo = body.get("wants_demo", True)
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    user["wants_demo"] = bool(wants_demo)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: instant_db.update_user(user_id, wants_demo=bool(wants_demo)),
        )
    except Exception as e:
        print(f"[demo] DB write failed: {e}")
    return {"ok": True}


# --- Presentations ---

@app.get("/presentations")
def list_presentations():
    """No auth — booth fetches this to show demo options."""
    return [{"id": p["id"], "name": p["name"]} for p in presentations]


@app.get("/admin/api/presentations")
def admin_list_presentations(_=Depends(require_admin)):
    return presentations


@app.post("/admin/api/presentations")
async def admin_create_presentation(body: dict, _=Depends(require_admin)):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    pres_id = str(uuid.uuid4())
    pres = {"id": pres_id, "name": name, "created_at": int(time.time() * 1000)}
    presentations.append(pres)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.create_presentation, pres_id, name
        )
    except Exception as e:
        print(f"[presentations] create failed: {e}")
    return {"ok": True, **pres}


@app.patch("/admin/api/presentations/{pres_id}")
async def admin_update_presentation(pres_id: str, body: dict, _=Depends(require_admin)):
    pres = next((p for p in presentations if p["id"] == pres_id), None)
    if not pres:
        raise HTTPException(status_code=404, detail="not found")
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    pres["name"] = name
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.update_presentation, pres_id, name
        )
    except Exception as e:
        print(f"[presentations] update failed: {e}")
    return {"ok": True, **pres}


@app.delete("/admin/api/presentations/{pres_id}")
async def admin_delete_presentation(pres_id: str, _=Depends(require_admin)):
    pres = next((p for p in presentations if p["id"] == pres_id), None)
    if not pres:
        raise HTTPException(status_code=404, detail="not found")
    presentations.remove(pres)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, instant_db.delete_presentation, pres_id
        )
    except Exception as e:
        print(f"[presentations] delete failed: {e}")
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


# --- User lookup (for QR scan) ---

@app.get("/users/{user_id}")
def get_user(user_id: str):
    """Look up a user by ID. No auth — booth QR scanner needs this."""
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "id": user["id"],
        "name": user.get("name", ""),
        "interest": user.get("interest", ""),
        "wants_demo": bool(user.get("wants_demo")),
    }


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
