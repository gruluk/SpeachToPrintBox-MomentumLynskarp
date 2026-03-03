import base64
from io import BytesIO
from pathlib import Path

import openai
import pixellab
from PIL import Image

# Pixflux max is 400x400 — use full width at label ratio (88:36)
IMAGE_SIZE = {"width": 400, "height": 164}

# Crush-and-expand: generate full size, downscale to this, then upscale with
# nearest-neighbor to force chunky visible pixels. Lower = bigger/coarser pixels.
# At (50, 20) each "pixel" appears as an 8x8 block in the final image.
PIXEL_ART_SIZE = (50, 20)

# Place your style reference image here (e.g. the event mascot/logo)
STYLE_REFERENCE_PATH = Path(__file__).parent / "style_reference.png"

_style_description_cache: str | None = None


def _image_to_b64(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


def _describe_art_style(style_image: Image.Image) -> str:
    """Use GPT-4o Vision to extract art style descriptors from the reference image."""
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe the pixel art style of this image as a short list of style keywords "
                            "for use in an image generation prompt. Focus on: pixel art characteristics "
                            "(coarse pixels, limited palette), character design (cute/chibi proportions, "
                            "big round eyes, simplified/rounded shapes), outline style, shading approach, "
                            "and overall aesthetic mood. "
                            "Output only a comma-separated list of style descriptors, no full sentences."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{_image_to_b64(style_image)}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()


def _get_style_description() -> str | None:
    """Load and cache the style description from the reference image."""
    global _style_description_cache
    if _style_description_cache is not None:
        return _style_description_cache
    if STYLE_REFERENCE_PATH.exists():
        style_image = Image.open(STYLE_REFERENCE_PATH).convert("RGB")
        _style_description_cache = _describe_art_style(style_image)
        print(f"[Style reference loaded] {_style_description_cache}")
    return _style_description_cache


def _describe_person(photo: Image.Image) -> str:
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this person's appearance concisely for generating a cute pixel art character. "
                            "Include only the most distinctive features: hair color and style, eye color, skin tone, "
                            "any notable facial features (glasses, beard, freckles, etc.), and clothing color. "
                            "Keep it to 2-3 sentences max."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{_image_to_b64(photo)}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content


def generate_image(photo: Image.Image) -> Image.Image:
    style = _get_style_description()
    description = _describe_person(photo)

    if style:
        prompt = (
            f"cute chibi pixel art character portrait, {style}, "
            f"character appearance: {description}"
        )
    else:
        prompt = (
            f"cute chibi pixel art character portrait, coarse pixels, limited color palette, "
            f"big round eyes, simplified rounded shapes, {description}"
        )

    client = pixellab.Client.from_env()
    response = client.generate_image_pixflux(
        description=prompt,
        image_size=IMAGE_SIZE,
    )
    image = response.image.pil_image()
    # Crush to low resolution then scale back up — forces chunky pixel art look
    image = image.resize(PIXEL_ART_SIZE, Image.BILINEAR)
    image = image.resize((IMAGE_SIZE["width"], IMAGE_SIZE["height"]), Image.NEAREST)
    return image.convert("L")
