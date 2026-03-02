import pixellab
from PIL import Image

# 400x400 is the maximum for PixelLab Pixflux — matches our square 8cm label
IMAGE_SIZE = {"width": 400, "height": 400}


def generate_image(description: str) -> Image.Image:
    client = pixellab.Client.from_env()

    response = client.generate_image_pixflux(
        description=description,
        image_size=IMAGE_SIZE,
    )

    return response.image.pil_image().convert("L")
