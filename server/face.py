"""
Face recognition utilities.

compute_embedding  — extract a 128-dim face embedding from a JPEG image
find_match         — compare an embedding against a list of known users
"""

import math
import time

try:
    import face_recognition
    import numpy as np
    FACE_AVAILABLE = True
except ImportError:
    FACE_AVAILABLE = False


def compute_embedding(image_bytes: bytes) -> dict:
    """Return {"found": bool, "embedding": list[float]|None, "time_ms": float}."""
    if not FACE_AVAILABLE:
        return {"found": False, "embedding": None, "time_ms": 0,
                "error": "face_recognition not installed"}

    start = time.perf_counter()
    # face_recognition expects a numpy array (RGB)
    import io
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(img)

    encodings = face_recognition.face_encodings(img_array)
    elapsed = (time.perf_counter() - start) * 1000

    if not encodings:
        return {"found": False, "embedding": None, "time_ms": round(elapsed, 1)}

    return {
        "found": True,
        "embedding": encodings[0].tolist(),
        "time_ms": round(elapsed, 1),
    }


def find_match(
    embedding: list[float],
    known_users: list[dict],
    threshold: float = 0.6,
) -> dict:
    """Compare embedding against known users.

    Returns {"matched": bool, "user_id", "name", "distance", "all_scores": [...]}.
    """
    if not known_users:
        return {"matched": False, "user_id": None, "name": None,
                "distance": None, "all_scores": []}

    target = np.array(embedding) if FACE_AVAILABLE else None
    if target is None:
        return {"matched": False, "user_id": None, "name": None,
                "distance": None, "all_scores": [],
                "error": "face_recognition not installed"}

    all_scores = []
    best_dist = float("inf")
    best_user = None

    for user in known_users:
        user_emb = user.get("embedding")
        if not user_emb:
            continue
        known = np.array(user_emb)
        dist = float(np.linalg.norm(target - known))
        all_scores.append({
            "user_id": user["id"],
            "name": user.get("name", ""),
            "interest": user.get("interest", ""),
            "distance": round(dist, 4),
        })
        if dist < best_dist:
            best_dist = dist
            best_user = user

    all_scores.sort(key=lambda s: s["distance"])

    matched = best_dist <= threshold and best_user is not None
    return {
        "matched": matched,
        "user_id": best_user["id"] if matched else None,
        "name": best_user.get("name", "") if matched else None,
        "interest": best_user.get("interest", "") if matched else None,
        "distance": round(best_dist, 4) if best_user else None,
        "threshold": threshold,
        "all_scores": all_scores,
    }
