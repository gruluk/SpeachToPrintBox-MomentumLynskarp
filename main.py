import base64
import os
import threading
from io import BytesIO

import requests
import tkinter as tk
import glob
from PIL import Image, ImageDraw, ImageFont, ImageTk

from camera import Camera
from config import (
    BG, MUTED, WARNING,
    START, INFO, PREVIEW, VALIDATING, REVIEW, NAME_INPUT,
    WAITING, PROCESSING, RESULT,
    ASSETS_DIR, SERVER_URL,
    PRINTER_VENDOR, PRINTER_PRODUCT, ENABLE_LOCAL_PRINT,
)
from printing import composite_label, print_image
from screens import (
    StartScreen, PreviewControls, ValidatingControls, ReviewControls,
    NameInputScreen, WaitingScreen, ResultControls,
    PrinterDot, InfoScreen,
)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.camera = Camera()
        self.captured_photo: Image.Image | None = None
        self.state = START

        self.user_name = ""

        self._gen_result: Image.Image | None = None
        self._gen_ready = False
        self._gen_error = ""
        self._gen_char_id = ""

        self._countdown_n = 0

        self._setup_window()
        self._build_ui()
        self._show_state(START)
        self._poll_printer()
        self._update_preview()

    def _setup_window(self):
        self.root.title("Sopra Steria Pixel Booth")
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)
        self.root.after(50, self._post_geometry)
        self.root.bind("<Escape>", lambda e: self._on_close())

    def _post_geometry(self):
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+0+0")
        self.camera.set_display_size(w, h)

    def _build_ui(self):
        self.display_label = tk.Label(self.root, bg="black")
        self.display_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.start_scr    = StartScreen(self.root, on_start=self._on_start)
        self.preview_ctrl = PreviewControls(self.root, on_take=self._take_photo, on_debug=self._debug_print)
        self.valid_ctrl   = ValidatingControls(self.root, on_retake=self._retake)
        self.review_ctrl  = ReviewControls(self.root, on_retake=self._retake, on_next=self._proceed_to_name)
        self.name_scr     = NameInputScreen(self.root, on_next=self._on_name_next, on_retake=self._retake)
        self.waiting_scr  = WaitingScreen(self.root, on_retake=self._retake)
        self.result_ctrl  = ResultControls(self.root, on_done=self._on_done)
        self.printer_dot  = PrinterDot(self.root)
        self.info_scr     = InfoScreen(self.root, on_continue=self._on_info_continue)

        self._all_screens = [
            self.start_scr, self.info_scr, self.preview_ctrl, self.valid_ctrl,
            self.review_ctrl, self.name_scr, self.waiting_scr,
            self.result_ctrl, self.printer_dot,
        ]

    # --- Preview loop ---

    def _update_preview(self):
        if self.state == PREVIEW:
            try:
                frame = self.camera.get_frame()
                if frame is not None:
                    if self._countdown_n > 0:
                        frame = frame.copy()
                        draw = ImageDraw.Draw(frame)
                        txt = str(self._countdown_n)
                        font_size = min(frame.width, frame.height) // 2
                        try:
                            fnt = ImageFont.truetype(
                                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                font_size,
                            )
                        except Exception:
                            fnt = ImageFont.load_default()
                        bbox = fnt.getbbox(txt)
                        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                        x = (frame.width - tw) // 2 - bbox[0]
                        y = (frame.height - th) // 2 - bbox[1]
                        draw.text((x + 4, y + 4), txt, fill=(0, 0, 0), font=fnt)
                        draw.text((x, y), txt, fill=(255, 255, 255), font=fnt)
                    photo = ImageTk.PhotoImage(frame)
                    self.display_label.config(image=photo)
                    self.display_label.image = photo
            except Exception:
                pass
        self.root.after(33, self._update_preview)

    # --- State machine ---

    def _show_state(self, state: str):
        self.state = state
        for s in self._all_screens:
            s.hide()

        if state == START:
            self.start_scr.show()
            return

        if state == INFO:
            self.info_scr.show()
            return

        self.printer_dot.show()

        if state == PREVIEW:
            self.preview_ctrl.show()
        elif state == VALIDATING:
            self.valid_ctrl.show()
        elif state == REVIEW:
            self.review_ctrl.show()
        elif state == NAME_INPUT:
            self.name_scr.show()
            self.root.after(100, self.name_scr.focus)
        elif state == WAITING:
            self.waiting_scr.show()
        elif state in (PROCESSING, RESULT):
            self.result_ctrl.show()

    # --- State transitions ---

    def _photo_to_jpeg_bytes(self) -> bytes:
        buf = BytesIO()
        self.captured_photo.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return buf.getvalue()

    def _on_start(self):
        self._show_state(INFO)

    def _on_info_continue(self):
        self._show_state(PREVIEW)
        self.preview_ctrl.set_status("Se i kameraet og trykk Ta bilde!")

    def _take_photo(self):
        self._countdown_n = 3
        self.preview_ctrl.disable_take()
        self.preview_ctrl.set_status("Gjør deg klar...")
        self.root.after(1000, self._countdown_tick)

    def _countdown_tick(self):
        self._countdown_n -= 1
        if self._countdown_n > 0:
            self.root.after(1000, self._countdown_tick)
        else:
            self._countdown_n = 0
            self._actually_take_photo()

    def _actually_take_photo(self):
        self.preview_ctrl.enable_take()
        frame = self.camera.get_snapshot()
        if frame is None:
            return
        self.captured_photo = frame
        # Display snapshot fill-cropped to screen
        w = self.root.winfo_width() or 640
        h = self.root.winfo_height() or 480
        scale = max(w / frame.width, h / frame.height)
        new_w, new_h = int(frame.width * scale), int(frame.height * scale)
        display = frame.resize((new_w, new_h), Image.BILINEAR)
        left, top = (new_w - w) // 2, (new_h - h) // 2
        display = display.crop((left, top, left + w, top + h))
        photo = ImageTk.PhotoImage(display)
        self.display_label.config(image=photo)
        self.display_label.image = photo
        self._show_state(VALIDATING)
        self.valid_ctrl.set_status("Sjekker bildet...")
        threading.Thread(target=self._run_validation, daemon=True).start()

    def _run_validation(self):
        try:
            resp = requests.post(
                f"{SERVER_URL}/validate",
                files={"image": ("photo.jpg", self._photo_to_jpeg_bytes(), "image/jpeg")},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            ok, message = data["ok"], data.get("message", "")
        except Exception:
            ok, message = True, ""

        if ok:
            self.root.after(0, self._on_validation_ok)
        else:
            self.root.after(0, self._on_validation_fail, message)

    def _on_validation_ok(self):
        if self.captured_photo is None:
            return
        self._gen_result = None
        self._gen_ready = False
        self._gen_error = ""
        self._gen_char_id = ""
        photo_bytes = self._photo_to_jpeg_bytes()
        threading.Thread(target=self._process, args=(photo_bytes,), daemon=True).start()
        self._show_state(REVIEW)
        self.review_ctrl.set_status("Fornøyd med bildet?")

    def _on_validation_fail(self, message: str):
        self.valid_ctrl.set_status(f"{message} — prøv igjen", WARNING)

    def _reset_session(self):
        self.captured_photo = None
        self.user_name = ""
        self._gen_result = None
        self._gen_ready = False
        self._gen_error = ""
        self._countdown_n = 0
        self.preview_ctrl.enable_take()

    def _retake(self):
        self._reset_session()
        self._show_state(PREVIEW)
        self.preview_ctrl.set_status("Se i kameraet og trykk Ta bilde!")

    def _on_done(self):
        self._reset_session()
        self._show_state(START)

    def _proceed_to_name(self):
        self.name_scr.clear()
        self._show_state(NAME_INPUT)

    def _on_name_next(self):
        name = self.name_scr.get_name().strip()
        if not name:
            return
        self.user_name = name
        threading.Thread(target=self._publish, daemon=True).start()
        if self._gen_ready:
            if self._gen_result is not None:
                self._show_result(self._gen_result)
            else:
                self._show_state(REVIEW)
                self.review_ctrl.set_status(f"Feil: {self._gen_error}", WARNING)
        else:
            self._show_state(WAITING)
            self._check_gen_ready()

    def _check_gen_ready(self):
        if not self._gen_ready:
            self.root.after(500, self._check_gen_ready)
            return
        if self._gen_result is not None:
            self._show_result(self._gen_result)
        else:
            self._show_state(REVIEW)
            self.review_ctrl.set_status(f"Feil: {self._gen_error}", WARNING)

    def _process(self, photo_bytes: bytes):
        try:
            resp = requests.post(
                f"{SERVER_URL}/generate",
                files={"image": ("photo.jpg", photo_bytes, "image/jpeg")},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            img_bytes = base64.b64decode(data["image_b64"])
            self._gen_char_id = data.get("id", "")
            self._gen_result = Image.open(BytesIO(img_bytes))
        except Exception as e:
            self._gen_error = str(e)
            import traceback; traceback.print_exc()
        finally:
            self._gen_ready = True
            if self.state == WAITING:
                self.root.after(0, self._check_gen_ready)

    def _publish(self):
        if not self._gen_char_id:
            return
        try:
            requests.post(
                f"{SERVER_URL}/publish/{self._gen_char_id}",
                data={"name": self.user_name},
                timeout=10,
            )
        except Exception:
            pass

    # --- Result / print ---

    def _show_result(self, image: Image.Image):
        composited = composite_label(image, self.user_name)
        self._display_composited(composited)

    def _debug_print(self):
        name = self.user_name or "Debug User"
        image = Image.open(os.path.join(ASSETS_DIR, "style_reference.PNG"))
        composited = composite_label(image, name)
        self._display_composited(composited)

    def _display_composited(self, composited: Image.Image):
        self._show_state(RESULT)
        w = self.root.winfo_width() or 640
        h = self.root.winfo_height() or 480
        scale = min(w / composited.width, h / composited.height)
        display = composited.resize(
            (int(composited.width * scale), int(composited.height * scale)), Image.NEAREST
        )
        photo = ImageTk.PhotoImage(display)
        self.display_label.config(image=photo)
        self.display_label.image = photo
        self.result_ctrl.set_status("Skriver ut...")
        threading.Thread(target=self._do_print, args=(composited,), daemon=True).start()

    def _do_print(self, composited: Image.Image):
        if not ENABLE_LOCAL_PRINT:
            self.root.after(0, self.result_ctrl.set_status, "Ferdig! Trykk Prøv igjen for å starte på nytt.")
            self.root.after(0, self.result_ctrl.set_print_status, "Skriver ut via Mac.")
            return
        try:
            print_image(composited)
            self.root.after(0, self.result_ctrl.set_status, "Utskrevet! Trykk Prøv igjen for å starte på nytt.")
            self.root.after(0, self.result_ctrl.set_print_status, "Etikett sendt til skriveren.")
        except Exception as e:
            import traceback; traceback.print_exc()
            self.root.after(0, self.result_ctrl.set_status, "Ferdig! Trykk Prøv igjen for å starte på nytt.")
            self.root.after(0, self.result_ctrl.set_print_status, f"Utskrift feilet: {e}")

    # --- Printer polling ---

    def _poll_printer(self):
        threading.Thread(target=self._check_printer, daemon=True).start()
        self.root.after(10000, self._poll_printer)

    def _check_printer(self):
        """Check printer connection via sysfs — never opens the USB device."""
        connected = False
        try:
            vendor_hex = f"{PRINTER_VENDOR:04x}"
            product_hex = f"{PRINTER_PRODUCT:04x}"
            for path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
                if open(path).read().strip() == vendor_hex:
                    prod_path = path.replace("idVendor", "idProduct")
                    if open(prod_path).read().strip() == product_hex:
                        connected = True
                        break
        except Exception:
            pass
        self.root.after(0, self.printer_dot.set_connected, connected)

    def _on_close(self):
        self.camera.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
