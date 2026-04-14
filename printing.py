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


def _find_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        font_path,
        os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf"),
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def composite_label(user_name: str, interest: str) -> Image.Image:
    label_info = next(l for l in ALL_LABELS if l.identifier == LABEL)
    target_w, _ = label_info.dots_printable
    content_h = round(PRINT_HEIGHT_MM * 300 / 25.4)

    canvas = Image.new("RGB", (target_w, content_h), "white")
    draw = ImageDraw.Draw(canvas)
    PAD = 14

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # Top row: name top-right, smaller — 20% of height
    top_h = int(content_h * 0.20)

    # Name (top right, smaller)
    name_area_w = target_w - PAD * 2
    name_font_size = min(top_h - PAD * 2, 40)
    name_font = _find_font(font_path, name_font_size)
    while name_font_size > 12:
        name_font = _find_font(font_path, name_font_size)
        bbox = name_font.getbbox(user_name)
        if (bbox[2] - bbox[0]) <= name_area_w:
            break
        name_font_size -= 4

    name_bbox = name_font.getbbox(user_name)
    name_text_h = name_bbox[3] - name_bbox[1]
    name_y = (top_h - name_text_h) // 2 - name_bbox[1]
    name_x = target_w - PAD - (name_bbox[2] - name_bbox[0])
    draw.text((name_x, name_y), user_name, fill="#3c1c71", font=name_font)

    # Interests — stacked vertically, centered
    interest_area_top = top_h
    interest_area_h = content_h - interest_area_top - PAD
    items = [s.strip() for s in (interest or "").split(",") if s.strip()]

    if items:
        line_count = len(items)
        line_spacing = 8
        available_h = interest_area_h - (line_count - 1) * line_spacing
        interest_font_size = min(int(available_h / line_count * 0.85), 120)

        while interest_font_size > 12:
            interest_font = _find_font(font_path, interest_font_size)
            max_w = max(interest_font.getbbox(item)[2] - interest_font.getbbox(item)[0] for item in items)
            if max_w <= target_w - PAD * 2:
                break
            interest_font_size -= 4
        interest_font = _find_font(font_path, interest_font_size)

        line_heights = []
        for item in items:
            bbox = interest_font.getbbox(item)
            line_heights.append(bbox[3] - bbox[1])
        total_text_h = sum(line_heights) + (line_count - 1) * line_spacing

        y_cursor = interest_area_top + (interest_area_h - total_text_h) // 2
        for idx, item in enumerate(items):
            bbox = interest_font.getbbox(item)
            text_w = bbox[2] - bbox[0]
            x = (target_w - text_w) // 2 - bbox[0]
            draw.text((x, y_cursor - bbox[1]), item, fill="#3c1c71", font=interest_font)
            y_cursor += line_heights[idx] + line_spacing

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
