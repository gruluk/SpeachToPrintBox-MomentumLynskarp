from PIL import Image

from pixelart import pixelate


def generate_image(photo: Image.Image) -> Image.Image:
    return pixelate(photo).convert("L")
