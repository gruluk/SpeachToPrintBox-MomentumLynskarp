import gc
import os

import qrcode
import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.labels import ALL_LABELS

from config import (
    PRINTER_MODEL, PRINTER_VENDOR, PRINTER_PRODUCT,
    LABEL, PRINT_HEIGHT_MM, ASSETS_DIR, QR_BASE_URL,
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


def composite_label(user_name: str, interest: str, user_id: str = "") -> Image.Image:
    """Create a label with square QR code on the left and name + interests on the right."""
    label_info = next(l for l in ALL_LABELS if l.identifier == LABEL)
    target_w, _ = label_info.dots_printable
    content_h = round(PRINT_HEIGHT_MM * 300 / 25.4)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    PAD = 14

    canvas = Image.new("RGB", (target_w, content_h), "white")
    draw = ImageDraw.Draw(canvas)

    # --- Square QR code on the left ---
    qr_url = f"{QR_BASE_URL}/u/{user_id}" if user_id else "https://lynskarp.soprasteria.no"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_size = content_h - PAD * 2
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    canvas.paste(qr_img, (PAD, PAD))

    # --- Text area on the right ---
    text_left = PAD + qr_size + PAD * 2
    text_area_w = target_w - text_left - PAD
    text_area_top = PAD

    # Separator line
    sep_x = PAD + qr_size + PAD
    draw.line([(sep_x, PAD + 10), (sep_x, content_h - PAD - 10)], fill="#cccccc", width=2)

    # Name (top-right aligned)
    name_font_size = 40
    name_font = _find_font(font_path, name_font_size)
    while name_font_size > 12:
        name_font = _find_font(font_path, name_font_size)
        bbox = name_font.getbbox(user_name)
        if (bbox[2] - bbox[0]) <= text_area_w:
            break
        name_font_size -= 4

    name_bbox = name_font.getbbox(user_name)
    name_text_w = name_bbox[2] - name_bbox[0]
    name_text_h = name_bbox[3] - name_bbox[1]
    name_x = target_w - PAD - name_text_w - name_bbox[0]
    name_y = text_area_top - name_bbox[1]
    draw.text((name_x, name_y), user_name, fill="black", font=name_font)

    # Interests (below name, stacked, left-aligned)
    items = [s.strip() for s in (interest or "").split(",") if s.strip()]
    interest_top = text_area_top + name_text_h + 16
    interest_area_h = content_h - interest_top - PAD

    if items:
        line_count = len(items)
        line_spacing = 8
        available_h = interest_area_h - (line_count - 1) * line_spacing
        interest_font_size = min(int(available_h / line_count * 0.85), 60)

        while interest_font_size > 10:
            interest_font = _find_font(font_path, interest_font_size)
            max_w = max(interest_font.getbbox(item)[2] - interest_font.getbbox(item)[0] for item in items)
            if max_w <= text_area_w:
                break
            interest_font_size -= 4
        interest_font = _find_font(font_path, interest_font_size)

        line_heights = []
        for item in items:
            bbox = interest_font.getbbox(item)
            line_heights.append(bbox[3] - bbox[1])
        total_text_h = sum(line_heights) + (line_count - 1) * line_spacing

        y_cursor = interest_top + (interest_area_h - total_text_h) // 2
        for idx, item in enumerate(items):
            bbox = interest_font.getbbox(item)
            draw.text((text_left, y_cursor - bbox[1]), item, fill="#444444", font=interest_font)
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
