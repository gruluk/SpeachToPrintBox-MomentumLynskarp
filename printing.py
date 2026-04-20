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


_BUNDLED_FONT = os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf")


def _find_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_BUNDLED_FONT, size)


def composite_label(user_name: str, interest: str, user_id: str = "") -> Image.Image:
    """Create a label with name on top, QR code bottom-left, interests bottom-right."""
    label_info = next(l for l in ALL_LABELS if l.identifier == LABEL)
    target_w, _ = label_info.dots_printable
    content_h = round(PRINT_HEIGHT_MM * 300 / 25.4)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    PAD = 14

    canvas = Image.new("RGB", (target_w, content_h), "white")
    draw = ImageDraw.Draw(canvas)

    # --- Name across the full width at the top ---
    NAME_PAD_TOP = 20
    name_font_size = 72
    name_font = _find_font(font_path, name_font_size)
    while name_font_size > 16:
        name_font = _find_font(font_path, name_font_size)
        bbox = name_font.getbbox(user_name)
        if (bbox[2] - bbox[0]) <= target_w - PAD * 2:
            break
        name_font_size -= 4

    name_bbox = name_font.getbbox(user_name)
    name_text_w = name_bbox[2] - name_bbox[0]
    name_text_h = name_bbox[3] - name_bbox[1]
    # Center the name horizontally
    name_x = (target_w - name_text_w) // 2 - name_bbox[0]
    name_y = NAME_PAD_TOP - name_bbox[1]
    draw.text((name_x, name_y), user_name, fill="black", font=name_font)

    # Separator line below name
    sep_y = NAME_PAD_TOP + name_text_h + 8
    draw.line([(PAD, sep_y), (target_w - PAD, sep_y)], fill="#cccccc", width=2)

    # --- Bottom area: QR left, interests right ---
    bottom_top = sep_y + 10
    bottom_h = content_h - bottom_top - PAD

    # QR code on the left
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(user_id or "NOCODE")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_size = bottom_h
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    canvas.paste(qr_img, (PAD, bottom_top))

    # --- Interests on the right ---
    text_left = PAD + qr_size + PAD * 2
    text_area_w = target_w - text_left - PAD * 2

    items = [s.strip() for s in (interest or "").split(",") if s.strip()]
    item_spacing = 35

    if items:
        interest_font_size = 60
        wrapped_lines = []
        while interest_font_size > 10:
            interest_font = _find_font(font_path, interest_font_size)
            line_h = interest_font.getbbox("Ag")[3] - interest_font.getbbox("Ag")[1]
            wrapped_lines = []
            for item in items:
                words = item.split()
                lines = []
                current = words[0]
                for word in words[1:]:
                    test = current + " " + word
                    tw = interest_font.getbbox(test)[2] - interest_font.getbbox(test)[0]
                    if tw <= text_area_w:
                        current = test
                    else:
                        lines.append(current)
                        current = word
                lines.append(current)
                # Break any lines that are still too wide (long single words)
                final_lines = []
                for line in lines:
                    lw = interest_font.getbbox(line)[2] - interest_font.getbbox(line)[0]
                    if lw <= text_area_w:
                        final_lines.append(line)
                    else:
                        # Character-level break
                        part = ""
                        for ch in line:
                            test_part = part + ch
                            pw = interest_font.getbbox(test_part)[2] - interest_font.getbbox(test_part)[0]
                            if pw > text_area_w and part:
                                final_lines.append(part)
                                part = ch
                            else:
                                part = test_part
                        if part:
                            final_lines.append(part)
                wrapped_lines.append(final_lines)
            total_lines = sum(len(lines) for lines in wrapped_lines)
            total_h = total_lines * line_h + (len(items) - 1) * item_spacing
            if total_h <= bottom_h:
                break
            interest_font_size -= 4
        interest_font = _find_font(font_path, interest_font_size)
        line_h = interest_font.getbbox("Ag")[3] - interest_font.getbbox("Ag")[1]

        total_lines = sum(len(lines) for lines in wrapped_lines)
        total_h = total_lines * line_h + (len(items) - 1) * item_spacing
        y_cursor = bottom_top + (bottom_h - total_h) // 2

        for idx, lines in enumerate(wrapped_lines):
            for line in lines:
                bbox = interest_font.getbbox(line)
                draw.text((text_left, y_cursor - bbox[1]), line, fill="#444444", font=interest_font)
                y_cursor += line_h
            if idx < len(wrapped_lines) - 1:
                y_cursor += item_spacing

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
