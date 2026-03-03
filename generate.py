import base64
from io import BytesIO

import openai
import pixellab
from PIL import Image

# Pixflux max is 400x400 — use full width at label ratio (88:36)
IMAGE_SIZE = {"width": 400, "height": 164}


def _describe_person(photo: Image.Image) -> str:
    client = openai.OpenAI()

    buffer = BytesIO()
    photo.save(buffer, format="JPEG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this person's appearance in as much detail as possible for generating a pixel art character portrait. "
                            "Include: hair color, length and style; eye color and shape; skin tone; face shape; "
                            "any distinctive facial features (glasses, beard, freckles, etc.); "
                            "clothing colors, style and any visible accessories. "
                            "Be specific and detailed — the more detail, the better the pixel art result."
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
        max_tokens=300,
    )

    return response.choices[0].message.content


def generate_image(photo: Image.Image) -> Image.Image:
    description = _describe_person(photo)

    client = pixellab.Client.from_env()

    response = client.generate_image_pixflux(
        description=f"pixel art character portrait, {description}",
        image_size=IMAGE_SIZE,
    )

    return response.image.pil_image().convert("L")
