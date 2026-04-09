"""
Pixel art portrait generation using gpt-image-1.
Server copy — assets resolved relative to repo root (one level up from server/).
"""

import base64
from io import BytesIO
from pathlib import Path

import openai
from PIL import Image

# Assets live at repo root /assets, one level above server/
ASSETS = Path(__file__).parent.parent / "assets"
STYLE_REFERENCE_PATH = ASSETS / "style_reference.png"
LOGO_PATH = ASSETS / "logo.png"

PIXEL_GRID = 128


def _to_png(image: Image.Image) -> BytesIO:
    buf = BytesIO()
    image.convert("RGBA").save(buf, format="PNG")
    buf.seek(0)
    buf.name = "image.png"
    return buf


def _snap_to_grid(image: Image.Image, grid: int) -> Image.Image:
    w, h = image.size
    small = image.resize((grid, grid), Image.LANCZOS)
    return small.resize((w, h), Image.NEAREST)


def generate_image(photo: Image.Image) -> Image.Image:
    client = openai.OpenAI()

    images = [_to_png(photo)]

    style_clause = ""
    if STYLE_REFERENCE_PATH.exists():
        images.append(_to_png(Image.open(STYLE_REFERENCE_PATH)))
        style_clause = (
            "Match the pixel art style of the reference portrait image exactly: "
            "same chunky pixel grid, same outline weight, same limited-palette approach. "
        )

    theme_clause = ""
    if LOGO_PATH.exists():
        images.append(_to_png(Image.open(LOGO_PATH)))
        theme_clause = (
            "Draw colour inspiration from the event logo image: "
            "purple/red tones, a modern corporate-tech aesthetic. "
        )

    prompt = (
        "Generate a pixel art portrait of the person in the first image. "
        f"{style_clause}"
        f"{theme_clause}"
        "Style: chunky square pixels, approximately 64×64 effective pixel grid, "
        "bold 1px dark outlines around all features, limited warm color palette, "
        "retro 16-bit RPG character aesthetic. "
        "Composition: bust portrait — head and upper shoulders only, "
        "perfectly centered, character facing directly forward with eyes looking "
        "straight at the viewer (ignore the person's angle or pose in the photo). "
        "Background: fully transparent."
    )

    response = client.images.edit(
        model="gpt-image-1",
        image=images,
        prompt=prompt,
        size="1024x1024",
        background="transparent",
    )

    img_bytes = base64.b64decode(response.data[0].b64_json)
    image = Image.open(BytesIO(img_bytes)).convert("RGBA")
    return _snap_to_grid(image, PIXEL_GRID)
