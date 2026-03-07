import base64
import os
import threading
from collections import Counter
from io import BytesIO

import requests
import tkinter as tk
import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont, ImageTk

from camera import Camera
from config import (
    BG, MUTED, WARNING,
    START, PREVIEW, VALIDATING, REVIEW, NAME_INPUT, QUESTIONNAIRE,
    WAITING, PROCESSING, RESULT,
    QUESTIONS, ASSETS_DIR, SERVER_URL,
    PRINTER_VENDOR, PRINTER_PRODUCT,
)
from printing import composite_label, print_image
from screens import (
    StartScreen, PreviewControls, ValidatingControls, ReviewControls,
    NameInputScreen, QuestionnaireScreen, WaitingScreen, ResultControls,
    PrinterDot,
)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.camera = Camera()
        self.captured_photo: Image.Image | None = None
        self.state = START

        self.user_name = ""
        self.dino_type = "1"
        self._answers: list[str] = []
        self._question_idx = 0

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
        self.root.title("Speech To Print Box")
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
        self.quiz_scr     = QuestionnaireScreen(self.root, on_answer=self._on_answer, on_retake=self._retake)
        self.waiting_scr  = WaitingScreen(self.root, on_retake=self._retake)
        self.result_ctrl  = ResultControls(self.root, on_done=self._on_done)
        self.printer_dot  = PrinterDot(self.root)

        self._all_screens = [
            self.start_scr, self.preview_ctrl, self.valid_ctrl, self.review_ctrl,
            self.name_scr, self.quiz_scr, self.waiting_scr, self.result_ctrl,
            self.printer_dot,
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
        elif state == QUESTIONNAIRE:
            self.quiz_scr.show()
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
        self._show_state(PREVIEW)
        self.preview_ctrl.set_status("Look at the camera and press Take Photo!")

    def _take_photo(self):
        self._countdown_n = 3
        self.preview_ctrl.disable_take()
        self.preview_ctrl.set_status("Get ready...")
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
        self.valid_ctrl.set_status("Checking photo...")
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
        self.review_ctrl.set_status("Happy with the photo?")

    def _on_validation_fail(self, message: str):
        self.valid_ctrl.set_status(f"{message} — try again", WARNING)

    def _reset_session(self):
        self.captured_photo = None
        self.user_name = ""
        self.dino_type = "1"
        self._answers = []
        self._question_idx = 0
        self._gen_result = None
        self._gen_ready = False
        self._gen_error = ""
        self._countdown_n = 0
        self.preview_ctrl.enable_take()

    def _retake(self):
        self._reset_session()
        self._show_state(PREVIEW)
        self.preview_ctrl.set_status("Look at the camera and press Take Photo!")

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
        self._question_idx = 0
        self._answers = []
        self.quiz_scr.set_question(QUESTIONS[0], 0, len(QUESTIONS))
        self._show_state(QUESTIONNAIRE)

    def _on_answer(self, dino: str):
        self._answers.append(dino)
        self._question_idx += 1
        if self._question_idx < len(QUESTIONS):
            self.quiz_scr.set_question(
                QUESTIONS[self._question_idx], self._question_idx, len(QUESTIONS)
            )
        else:
            self.dino_type = Counter(self._answers).most_common(1)[0][0]
            threading.Thread(target=self._publish, daemon=True).start()
            self._on_questionnaire_done()

    def _on_questionnaire_done(self):
        if self._gen_ready:
            if self._gen_result is not None:
                self._show_result(self._gen_result)
            else:
                self._show_state(REVIEW)
                self.review_ctrl.set_status(f"Error: {self._gen_error}", WARNING)
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
            self.review_ctrl.set_status(f"Error: {self._gen_error}", WARNING)

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
                data={"name": self.user_name, "dino_type": self.dino_type},
                timeout=10,
            )
        except Exception:
            pass

    # --- Result / print ---

    def _show_result(self, image: Image.Image):
        composited = composite_label(image, self.user_name, self.dino_type)
        self._display_composited(composited)

    def _debug_print(self):
        name = self.user_name or "Debug User"
        dino = self.dino_type or "1"
        image = Image.open(os.path.join(ASSETS_DIR, "style_reference.PNG"))
        composited = composite_label(image, name, dino)
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
        self.result_ctrl.set_status("Printing...")
        threading.Thread(target=self._do_print, args=(composited,), daemon=True).start()

    def _do_print(self, composited: Image.Image):
        try:
            print_image(composited)
            self.root.after(0, self.result_ctrl.set_status, "Printed! Press Try Again to go again.")
            self.root.after(0, self.result_ctrl.set_print_status, "Label sent to printer.")
        except Exception as e:
            import traceback; traceback.print_exc()
            self.root.after(0, self.result_ctrl.set_status, "Done! Press Try Again to go again.")
            self.root.after(0, self.result_ctrl.set_print_status, f"Print failed: {e}")

    # --- Printer polling ---

    def _poll_printer(self):
        threading.Thread(target=self._check_printer, daemon=True).start()
        self.root.after(10000, self._poll_printer)

    def _check_printer(self):
        connected = False
        try:
            dev = usb.core.find(idVendor=PRINTER_VENDOR, idProduct=PRINTER_PRODUCT)
            connected = dev is not None
            if dev is not None:
                usb.util.dispose_resources(dev)
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
