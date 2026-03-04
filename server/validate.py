"""
Photo quality gate — runs before pixel art generation.

Uses gpt-4o-mini vision to check that the captured photo is actually usable:
a person is present, face is visible and forward-facing, image is bright
and sharp enough.  Returns a ValidationResult so the UI can show specific
feedback instead of silently generating a bad result.
"""

import base64
import json
from dataclasses import dataclass
from io import BytesIO

import openai
from PIL import Image


@dataclass
class ValidationResult:
    ok: bool
    message: str  # short user-facing reason shown when ok=False


def validate_photo(photo: Image.Image) -> ValidationResult:
    client = openai.OpenAI()

    # Downscale before sending — a tiny JPEG is plenty for a quality check
    thumb = photo.resize((320, 240), Image.BILINEAR)
    buffer = BytesIO()
    thumb.save(buffer, format="JPEG", quality=70)
    img_b64 = base64.b64encode(buffer.getvalue()).decode()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are evaluating a photo booth camera capture. "
                            "Decide whether it is usable for generating a pixel art portrait.\n\n"
                            'Respond ONLY with a JSON object: {"ok": true/false, "message": "..."}\n\n'
                            "Set ok=false if ANY of these are true:\n"
                            "- No person is visible in the frame\n"
                            "- The face is not visible, obscured, or in profile / facing away\n"
                            "- The photo is too dark to make out facial features\n"
                            "- The photo is severely blurry or out of focus\n"
                            "- The person is too far away (face smaller than ~10% of frame height)\n\n"
                            "Set ok=true if a person's face is reasonably visible and roughly forward-facing.\n\n"
                            "Keep message under 6 words, friendly and direct. "
                            'Examples: "No face detected", "Move closer to the camera", '
                            '"Too dark — find better lighting", "Please face the camera".\n'
                            "Leave message empty string when ok=true."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
        max_tokens=60,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    return ValidationResult(ok=bool(data["ok"]), message=data.get("message", ""))
