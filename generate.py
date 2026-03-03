import pixellab
from PIL import Image

# Bitforge max is 200x200 — maintaining 88:36 label ratio
IMAGE_SIZE = {"width": 200, "height": 82}


def generate_image(photo: Image.Image) -> Image.Image:
    client = pixellab.Client.from_env()

    response = client.generate_image_bitforge(
        description="pixel art portrait of a person",
        image_size=IMAGE_SIZE,
        style_image=photo,
        style_strength=80,
        extra_guidance_scale=8.0,
    )

    return response.image.pil_image().convert("L")
