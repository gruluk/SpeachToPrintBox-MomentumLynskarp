import gc
import os

import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.labels import ALL_LABELS

from config import (
    PRINTER_MODEL, PRINTER_VENDOR, PRINTER_PRODUCT,
    LABEL, PRINT_HEIGHT_MM, ASSETS_DIR,
)


def composite_label(character: Image.Image, user_name: str) -> Image.Image:
    label_info = next(l for l in ALL_LABELS if l.identifier == LABEL)
    target_w, _ = label_info.dots_printable
    content_h = round(PRINT_HEIGHT_MM * 300 / 25.4)

    canvas = Image.new("RGB", (target_w, content_h), "white")
    draw = ImageDraw.Draw(canvas)
    PAD = 14

    # Left column: character image (square, full height)
    split_x = int(target_w * 0.40)
    char_size = min(split_x - PAD * 2, content_h - PAD * 2)
    char = character.convert("RGBA")
    char = char.resize((char_size, char_size), Image.NEAREST)
    char_x = (split_x - char_size) // 2
    char_y = (content_h - char_size) // 2
    canvas.paste(char, (char_x, char_y), char)

    # Right column bounds
    right_x = split_x + PAD
    right_w = target_w - right_x - PAD

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # Logo (top right, small)
    logo_bottom = PAD
    try:
        logo = Image.open(
            os.path.join(ASSETS_DIR, "SopraSteria", "sopra_steria_logo.png")
        ).convert("RGBA")
        logo_h = content_h // 3
        logo_w = int(logo.width * logo_h / logo.height)
        if logo_w > right_w:
            logo_w = right_w
            logo_h = int(logo.height * logo_w / logo.width)
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        canvas.paste(logo, (right_x, PAD), logo)
        logo_bottom = PAD + logo_h
    except Exception:
        pass

    # Name (right, fills space below logo)
    name_area_top = logo_bottom + PAD
    name_area_h = content_h - name_area_top - PAD
    font_size = min(int(name_area_h * 0.80), 200)
    try:
        font = ImageFont.truetype(font_path, font_size)
        while font_size > 12:
            font = ImageFont.truetype(font_path, font_size)
            bbox = font.getbbox(user_name)
            if (bbox[2] - bbox[0]) <= right_w:
                break
            font_size -= 4
    except Exception:
        font = ImageFont.load_default()

    name_y = name_area_top + (name_area_h - font_size) // 2
    draw.text((right_x, name_y), user_name, fill="#3c1c71", font=font)

    return canvas


def _usb_write(data: bytes) -> None:
    """Send raw raster bytes directly to the printer via PyUSB."""
    gc.collect()

    dev = usb.core.find(idVendor=PRINTER_VENDOR, idProduct=PRINTER_PRODUCT)
    if dev is None:
        raise RuntimeError("Printer not found")

    try:
        # Detach any kernel driver (usblp, ipp-usb, etc.) from all interfaces.
        cfg = dev.get_active_configuration()
        for intf in cfg:
            n = intf.bInterfaceNumber
            try:
                dev.detach_kernel_driver(n)
                print(f"[usb] detached kernel driver from interface {n}")
            except usb.core.USBError as e:
                if e.errno != 2:  # ENOENT = no driver attached, that's fine
                    print(f"[usb] detach iface {n}: errno={e.errno} {e}")

        usb.util.claim_interface(dev, 0)

        cfg = dev.get_active_configuration()
        intf = cfg[(0, 0)]
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(
                e.bEndpointAddress
            ) == usb.util.ENDPOINT_OUT,
        )
        if ep_out is None:
            raise RuntimeError("Bulk OUT endpoint not found")

        for offset in range(0, len(data), 512):
            ep_out.write(data[offset : offset + 512], timeout=15000)

    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:
            pass
        usb.util.dispose_resources(dev)


def print_image(image: Image.Image) -> None:
    """Render and send image to label printer. Raises on failure."""
    if not hasattr(Image, "ANTIALIAS"):
        Image.ANTIALIAS = Image.LANCZOS

    label_info = next(l for l in ALL_LABELS if l.identifier == LABEL)
    target_w, target_h_label = label_info.dots_printable
    content_h = round(PRINT_HEIGHT_MM * 300 / 25.4)
    target_h = content_h if target_h_label == 0 else target_h_label

    img = image.convert("RGB")
    if img.width != target_w or img.height != content_h:
        img.thumbnail((target_w, content_h), Image.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), "white")
    paste_y = (target_h - img.height) // 2
    canvas.paste(img, ((target_w - img.width) // 2, paste_y))
    img = canvas

    qlr = BrotherQLRaster(PRINTER_MODEL)
    convert(qlr, [img], LABEL, cut=True, rotate="0", dpi_600=False)
    _usb_write(qlr.data)
