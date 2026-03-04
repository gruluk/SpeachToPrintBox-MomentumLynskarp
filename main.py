import base64
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageTk
import threading
import os
import subprocess
import tempfile
import requests
from dotenv import load_dotenv

load_dotenv()

from camera import Camera

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

# --- Colors ---
BG = "#1a1a2e"
PANEL = "#16213e"
ACCENT = "#e94560"
ACCENT_ACTIVE = "#c73652"
TEXT = "#eaeaea"
MUTED = "#666680"
SUCCESS = "#2ed573"
WARNING = "#ffa502"

# --- States ---
PREVIEW = "preview"
VALIDATING = "validating"
REVIEW = "review"
PROCESSING = "processing"
RESULT = "result"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.camera = Camera()
        self.captured_photo: Image.Image | None = None
        self.state = PREVIEW

        self._setup_window()
        self._build_ui()
        self._poll_printer()
        self._update_preview()

    def _setup_window(self):
        self.root.title("Speech To Print Box")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # --- Top bar (fixed) ---
        top_bar = tk.Frame(self.root, bg=BG)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=16, pady=(12, 4))

        tk.Label(top_bar, text="Speech To Print Box",
                 font=("Helvetica", 16, "bold"), fg=TEXT, bg=BG).pack(side=tk.LEFT)

        printer_frame = tk.Frame(top_bar, bg=BG)
        printer_frame.pack(side=tk.RIGHT)
        self.printer_dot = tk.Label(printer_frame, text="●", font=("Helvetica", 10), fg=MUTED, bg=BG)
        self.printer_dot.pack(side=tk.LEFT, padx=(0, 4))
        self.printer_status_var = tk.StringVar(value="Checking printer...")
        tk.Label(printer_frame, textvariable=self.printer_status_var,
                 font=("Helvetica", 10), fg=MUTED, bg=BG).pack(side=tk.LEFT)

        # --- Bottom bar (fixed) ---
        bottom_bar = tk.Frame(self.root, bg=BG)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=12)

        self.print_var = tk.StringVar(value="")
        tk.Label(bottom_bar, textvariable=self.print_var,
                 font=("Helvetica", 10), fg=MUTED, bg=BG).pack()

        self.status_var = tk.StringVar(value="Look at the camera and press Take Photo!")
        self.status_label = tk.Label(bottom_bar, textvariable=self.status_var,
                 font=("Helvetica", 11), fg=MUTED, bg=BG)
        self.status_label.pack(pady=(0, 8))

        self.btn_frame = tk.Frame(bottom_bar, bg=BG)
        self.btn_frame.pack()

        self.take_btn = tk.Button(
            self.btn_frame, text="Take Photo",
            font=("Helvetica", 14, "bold"), fg="white", bg=ACCENT,
            activebackground=ACCENT_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=32, pady=12, cursor="hand2", borderwidth=0,
            command=self._take_photo,
        )
        self.take_btn.pack(side=tk.LEFT, padx=6)

        self.retake_btn = tk.Button(
            self.btn_frame, text="Retake",
            font=("Helvetica", 14, "bold"), fg="white", bg=MUTED,
            activebackground="#555570", activeforeground="white",
            relief=tk.FLAT, padx=32, pady=12, cursor="hand2", borderwidth=0,
            command=self._retake,
        )

        self.generate_btn = tk.Button(
            self.btn_frame, text="Generate & Print",
            font=("Helvetica", 14, "bold"), fg="white", bg=SUCCESS,
            activebackground="#25b560", activeforeground="white",
            relief=tk.FLAT, padx=32, pady=12, cursor="hand2", borderwidth=0,
            command=self._generate,
        )

        # --- Preview area (fills remaining space) ---
        self.display_frame = tk.Frame(self.root, bg="black")
        self.display_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.display_label = tk.Label(self.display_frame, bg="black")
        self.display_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    # --- Preview loop ---

    def _display_size(self):
        w = self.display_frame.winfo_width() or 640
        h = self.display_frame.winfo_height() or 480
        return w, h

    def _fit_size(self, image: Image.Image):
        frame_w, frame_h = self._display_size()
        scale = min(frame_w / image.width, frame_h / image.height)
        return int(image.width * scale), int(image.height * scale)

    def _update_preview(self):
        if self.state == PREVIEW:
            try:
                frame = self.camera.get_frame().transpose(Image.FLIP_LEFT_RIGHT)
                display = frame.resize(self._fit_size(frame), Image.BILINEAR)
                photo = ImageTk.PhotoImage(display)
                self.display_label.config(image=photo)
                self.display_label.image = photo
            except Exception:
                pass
        self.root.after(50, self._update_preview)

    # --- State transitions ---

    def _photo_to_jpeg_bytes(self) -> bytes:
        buf = BytesIO()
        self.captured_photo.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return buf.getvalue()

    def _take_photo(self):
        self.captured_photo = self.camera.get_frame().transpose(Image.FLIP_LEFT_RIGHT)

        display = self.captured_photo.resize(self._fit_size(self.captured_photo), Image.BILINEAR)
        photo = ImageTk.PhotoImage(display)
        self.display_label.config(image=photo)
        self.display_label.image = photo

        self._show_state(VALIDATING)
        self.status_var.set("Checking photo...")
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
            # Server unreachable — let the user proceed
            ok, message = True, ""

        if ok:
            self.root.after(0, self._on_validation_ok)
        else:
            self.root.after(0, self._on_validation_fail, message)

    def _on_validation_ok(self):
        self._show_state(REVIEW)
        self.status_var.set("Happy with the photo?")
        self.status_label.config(fg=MUTED)

    def _on_validation_fail(self, message: str):
        self.status_var.set(f"{message} — try again")
        self.status_label.config(fg=WARNING)

    def _retake(self):
        self.captured_photo = None
        self._show_state(PREVIEW)
        self.status_var.set("Look at the camera and press Take Photo!")
        self.status_label.config(fg=MUTED)

    def _generate(self):
        self._show_state(PROCESSING)
        self.status_var.set("Generating pixel art...")
        self.print_var.set("")
        threading.Thread(target=self._process, daemon=True).start()

    def _process(self):
        try:
            resp = requests.post(
                f"{SERVER_URL}/generate",
                files={"image": ("photo.jpg", self._photo_to_jpeg_bytes(), "image/jpeg")},
                timeout=120,
            )
            resp.raise_for_status()
            img_bytes = base64.b64decode(resp.json()["image_b64"])
            image = Image.open(BytesIO(img_bytes))
            self.root.after(0, self._show_result, image)
        except Exception as e:
            self.root.after(0, self.status_var.set, f"Error: {e}")
            self.root.after(0, self._show_state, REVIEW)

    def _show_result(self, image: Image.Image):
        self._show_state(RESULT)
        display = image.resize(self._fit_size(image), Image.NEAREST)
        photo = ImageTk.PhotoImage(display)
        self.display_label.config(image=photo)
        self.display_label.image = photo
        self.status_var.set("Printing...")
        threading.Thread(target=self._print_image, args=(image,), daemon=True).start()

    def _print_image(self, image: Image.Image):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp_path = f.name
            image.convert("RGB").save(tmp_path, dpi=(300, 300))
            subprocess.run(
                ["lp", "-d", "Leitz_Icon_Wi-Fi",
                 "-o", "media=Multipurpose70030001",
                 "-o", "fit-to-page",
                 tmp_path],
                check=True,
            )
            self.root.after(0, self.status_var.set, "Printed! Press Retake to go again.")
            self.root.after(0, self.print_var.set, "Label sent to printer.")
        except Exception as e:
            self.root.after(0, self.status_var.set, "Done! Press Retake to go again.")
            self.root.after(0, self.print_var.set, f"Print failed: {e}")
        finally:
            os.unlink(tmp_path)
            self.root.after(0, self._show_state, RESULT)

    def _show_state(self, state: str):
        self.state = state
        self.take_btn.pack_forget()
        self.retake_btn.pack_forget()
        self.generate_btn.pack_forget()

        if state == PREVIEW:
            self.take_btn.pack(side=tk.LEFT, padx=4)
        elif state == VALIDATING:
            self.retake_btn.config(text="Retake")
            self.retake_btn.pack(side=tk.LEFT, padx=4)
        elif state == REVIEW:
            self.retake_btn.config(text="Retake")
            self.retake_btn.pack(side=tk.LEFT, padx=4)
            self.generate_btn.pack(side=tk.LEFT, padx=4)
        elif state == PROCESSING:
            pass
        elif state == RESULT:
            self.retake_btn.config(text="Try Again")
            self.retake_btn.pack(side=tk.LEFT, padx=4)

    # --- Printer status ---

    def _poll_printer(self):
        threading.Thread(target=self._check_printer, daemon=True).start()
        self.root.after(10000, self._poll_printer)

    def _check_printer(self):
        try:
            result = subprocess.run(
                ["lpstat", "-p", "Leitz_Icon_Wi-Fi"],
                capture_output=True, text=True, timeout=5,
            )
            connected = result.returncode == 0 and any(
                s in result.stdout for s in ("idle", "printing")
            )
        except Exception:
            connected = False
        self.root.after(0, self._update_printer_indicator, connected)

    def _update_printer_indicator(self, connected: bool):
        if connected:
            self.printer_dot.config(fg=SUCCESS)
            self.printer_status_var.set("Printer connected")
        else:
            self.printer_dot.config(fg=ACCENT)
            self.printer_status_var.set("Printer offline")

    def _on_close(self):
        self.camera.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
