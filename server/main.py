"""
Sopra Steria @ Momentum Lynskarp — Central server

Endpoints:
  GET  /health    — health check
  POST /validate  — photo quality gate (gpt-4o-mini)
  POST /face/enroll   — enroll a face for recognition
  POST /face/recognize — recognize a face
  POST /print-label   — print a name+interest label
"""

import asyncio
import csv as csv_mod
import io
import json
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from PIL import Image

import db as instant_db
from face import compute_embedding, find_match, FACE_AVAILABLE
from validate import validate_photo

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
        enrolled = sum(1 for u in us if u.get("embedding"))
        print(f"[startup] Restored {len(us)} users ({enrolled} with face) from InstantDB (face_recognition={'available' if FACE_AVAILABLE else 'NOT available'})")
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


# --- Photo validation ---

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
        # If validation fails, let the booth proceed rather than blocking
        return {"ok": True, "message": ""}


# --- Print label ---

@app.post("/print-label")
async def print_label(
    name: str = Form(""),
    interest: str = Form(""),
    user_id: str = Form(""),
):
    """Generate and print a label with name and interest."""
    from printing import composite_label, print_image
    from config import ENABLE_LOCAL_PRINT

    # Store interest on user record
    if user_id and interest:
        user = next((u for u in users if u["id"] == user_id), None)
        if user:
            user["interest"] = interest
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: instant_db.update_user(user_id, interest=interest),
                )
            except Exception as e:
                print(f"[print-label] DB write failed: {e}")

    try:
        label = await asyncio.get_event_loop().run_in_executor(
            None, composite_label, name, interest
        )
    except Exception as e:
        print(f"[print] composite failed: {e}")
        return {"ok": False, "error": str(e)}

    if ENABLE_LOCAL_PRINT:
        try:
            await asyncio.get_event_loop().run_in_executor(None, print_image, label)
            return {"ok": True, "printed": True}
        except Exception as e:
            print(f"[print] print failed: {e}")
            return {"ok": False, "error": str(e)}

    return {"ok": True, "printed": False, "message": "Local printing disabled"}


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
    pres_names = {p["id"]: p["name"] for p in presentations}

    result = []
    for u in users:
        demo_ids = u.get("demo_ids", [])
        result.append({
            "id": u["id"],
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "interest": u.get("interest", ""),
            "has_face": bool(u.get("embedding")),
            "demos": [pres_names.get(did, did) for did in demo_ids],
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

    if body.get("clear_embedding"):
        user.pop("embedding", None)
        db_updates["embedding"] = None

    if body.get("clear_interest"):
        user.pop("interest", None)
        db_updates["interest"] = None

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
    """Store demo choices (list of presentation IDs) for a user."""
    user_id = body.get("user_id")
    demo_ids = body.get("demo_ids", [])
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    user["demo_ids"] = demo_ids
    user["demo_chosen_at"] = int(time.time() * 1000)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: instant_db.update_user(user_id, demo_ids=demo_ids, demo_chosen_at=int(time.time() * 1000)),
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


# --- Face recognition ---

@app.post("/face/enroll")
async def face_enroll(
    image: UploadFile = File(...),
    user_id: str = Form(...),
):
    """Enroll a face for an existing user. Stores embedding on user record."""
    if not FACE_AVAILABLE:
        raise HTTPException(status_code=503, detail="face_recognition library not available")

    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    data = await image.read()
    result = await asyncio.get_event_loop().run_in_executor(
        None, compute_embedding, data
    )

    if not result["found"]:
        return {"ok": False, "error": "no_face", "time_ms": result["time_ms"]}

    user["embedding"] = result["embedding"]

    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: instant_db.update_user(user_id, embedding=result["embedding"]),
        )
    except Exception as e:
        print(f"[face] InstantDB write failed: {e}")

    return {
        "ok": True,
        "user_id": user_id,
        "name": user.get("name", ""),
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

    # Filter to users with face embeddings
    enrolled = [u for u in users if u.get("embedding")]
    match = find_match(result["embedding"], enrolled, threshold)

    return {
        "ok": True,
        "time_ms": result["time_ms"],
        **match,
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
