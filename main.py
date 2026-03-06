import base64
import tkinter as tk
from collections import Counter
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageTk
import threading
import time
import os
import requests
import usb.core
import usb.util
from dotenv import load_dotenv
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.labels import ALL_LABELS

load_dotenv()

from camera import Camera

SERVER_URL      = os.getenv("SERVER_URL", "http://localhost:8000")
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"
ASSETS_DIR      = os.path.join(os.path.dirname(__file__), "assets")

# --- Colors (Bytefest '26 palette) ---
BG           = "#c2e8f7"
DISPLAY_BG   = "#96cfe0"
TEXT         = "#2d5c6a"
MUTED        = "#4a8a9e"
ACCENT       = "#2d5c6a"
ACCENT_ACTIVE = "#1e3f4a"
SUCCESS      = "#5b8c3e"
SUCCESS_ACTIVE = "#4a7533"
WARNING      = "#a05c10"

# --- Printer ---
PRINTER_MODEL   = "QL-1110NWB"
PRINTER_URI     = "usb://0x04f9:0x20a8"
LABEL           = "103" if PRODUCTION_MODE else "103x164"
PRINT_HEIGHT_MM = 45    # content height for both continuous and die-cut

# --- States ---
START         = "start"
PREVIEW       = "preview"
VALIDATING    = "validating"
REVIEW        = "review"
NAME_INPUT    = "name_input"
QUESTIONNAIRE = "questionnaire"
WAITING       = "waiting"
PROCESSING    = "processing"
RESULT        = "result"

# --- Questionnaire ---
QUESTIONS = [
    {
        "q": "Production is on fire 🔥. You...",
        "a": [
            ("Blame the intern", "1"),
            ("Open 3 incidents, close 2 immediately", "2"),
            ("Push a hotfix without testing", "3"),
            ("Already left for vacation", "4"),
        ],
    },
    {
        "q": "Your README is...",
        "a": [
            ("A detailed 40-page novel", "1"),
            ("A strongly-worded warning", "2"),
            ("Three emojis and a broken badge", "3"),
            ("What's a README?", "4"),
        ],
    },
    {
        "q": "You at a hackathon:",
        "a": [
            ("Planning the perfect architecture", "1"),
            ("Defending your tech choices loudly", "2"),
            ("Rewriting in a new framework at 2am", "3"),
            ("Pitching 5 ideas to anyone nearby", "4"),
        ],
    },
]

DINO_NAMES = {
    "1": "Brachiosaurus",
    "2": "Triceratops",
    "3": "Stegosaurus",
    "4": "Pterodactyl",
}


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.camera = Camera()
        self.captured_photo: Image.Image | None = None
        self.state = PREVIEW

        # User session data
        self.user_name = ""
        self.dino_type = "1"
        self._answers: list[str] = []
        self._question_idx = 0

        # Background generation state
        self._gen_result: Image.Image | None = None
        self._gen_ready = False
        self._gen_error = ""
        self._gen_char_id = ""

        self._countdown_n = 0  # >0 while countdown is active

        self._setup_window()
        self._build_ui()
        self._show_state(START)
        self._poll_printer()
        self._update_preview()

    def _setup_window(self):
        self.root.title("Speech To Print Box")
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)          # remove window decorations
        self.root.after(50, self._set_geometry)   # set geometry after first render
        self.root.bind("<Escape>", lambda e: self._on_close())

    def _set_geometry(self):
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+0+0")

    def _build_ui(self):
        # ── Layer 0: full-screen camera / image (behind everything) ──────
        self.display_label = tk.Label(self.root, bg="black")
        self.display_label.place(x=0, y=0, relwidth=1, relheight=1)

        # ── Layer 1a: Start screen ────────────────────────────────────────
        self.start_frame = tk.Frame(self.root, bg=BG)
        self._start_logo_photo = None
        try:
            logo_img = Image.open(
                os.path.join(ASSETS_DIR, "Figma assets", "logo_figma.png")
            ).convert("RGBA")
            logo_img.thumbnail((420, 420), Image.LANCZOS)
            self._start_logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(
                self.start_frame, image=self._start_logo_photo, bg=BG
            ).pack(expand=True, pady=(0, 16))
        except Exception:
            tk.Label(
                self.start_frame, text="BYTEFEST '26",
                font=("Helvetica", 48, "bold"), fg=TEXT, bg=BG,
            ).pack(expand=True)
        tk.Button(
            self.start_frame, text="START",
            font=("Helvetica", 28, "bold"), fg="white", bg=ACCENT,
            activebackground=ACCENT_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=60, pady=20, cursor="hand2", borderwidth=0,
            command=self._on_start,
        ).pack(pady=(0, 80))

        # ── Layer 1b: Name input screen ───────────────────────────────────
        self.name_frame = tk.Frame(self.root, bg=BG)
        tk.Label(self.name_frame, text="What's your name?",
                 font=("Helvetica", 22, "bold"), fg=TEXT, bg=BG).pack(pady=(28, 12))
        self.name_entry = tk.Entry(
            self.name_frame, font=("Helvetica", 26), fg=TEXT,
            justify=tk.CENTER, relief=tk.FLAT,
            bg="white", insertbackground=TEXT, width=20,
        )
        self.name_entry.pack(pady=4, ipady=10)
        self.name_entry.bind("<Return>", lambda _e: self._on_name_next())
        tk.Button(
            self.name_frame, text="Next →",
            font=("Helvetica", 14, "bold"), fg="white", bg=SUCCESS,
            activebackground=SUCCESS_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=32, pady=10, cursor="hand2", borderwidth=0,
            command=self._on_name_next,
        ).pack(pady=10)
        kb_frame = tk.Frame(self.name_frame, bg=BG)
        kb_frame.pack(pady=(6, 12))
        KEY_ROWS = [list("QWERTYUIOPÅ"), list("ASDFGHJKLØÆ"), list("ZXCVBNM")]
        for row in KEY_ROWS:
            rf = tk.Frame(kb_frame, bg=BG)
            rf.pack(pady=2)
            for ch in row:
                tk.Button(
                    rf, text=ch,
                    font=("Helvetica", 13, "bold"), fg=TEXT, bg="white",
                    activebackground="#c8dde8", activeforeground=TEXT,
                    relief=tk.FLAT, width=3, pady=9, borderwidth=0,
                    command=lambda c=ch: self._key_press(c),
                ).pack(side=tk.LEFT, padx=2)
        bot_row = tk.Frame(kb_frame, bg=BG)
        bot_row.pack(pady=2)
        tk.Button(
            bot_row, text="BKSP",
            font=("Helvetica", 13, "bold"), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=18, pady=9, borderwidth=0,
            command=self._key_backspace,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            bot_row, text="SPACE",
            font=("Helvetica", 13, "bold"), fg=TEXT, bg="white",
            activebackground="#c8dde8", activeforeground=TEXT,
            relief=tk.FLAT, padx=60, pady=9, borderwidth=0,
            command=lambda: self._key_press(" "),
        ).pack(side=tk.LEFT, padx=4)

        # ── Layer 1c: Questionnaire screen ────────────────────────────────
        self.quiz_frame = tk.Frame(self.root, bg=BG)
        self.quiz_counter_var = tk.StringVar()
        tk.Label(self.quiz_frame, textvariable=self.quiz_counter_var,
                 font=("Helvetica", 10), fg=MUTED, bg=BG).pack(pady=(24, 4))
        self.quiz_q_var = tk.StringVar()
        tk.Label(self.quiz_frame, textvariable=self.quiz_q_var,
                 font=("Helvetica", 20, "bold"), fg=TEXT, bg=BG,
                 wraplength=720).pack(pady=(0, 20))
        self.quiz_btns_frame = tk.Frame(self.quiz_frame, bg=BG)
        self.quiz_btns_frame.pack(fill=tk.X, padx=80)

        # ── Layer 1d: Waiting screen ──────────────────────────────────────
        self.waiting_frame = tk.Frame(self.root, bg=BG)
        tk.Label(self.waiting_frame, text="Almost ready...",
                 font=("Helvetica", 28, "bold"), fg=TEXT, bg=BG).pack(expand=True)
        tk.Label(self.waiting_frame, text="Generating your character",
                 font=("Helvetica", 14), fg=MUTED, bg=BG).pack(pady=(0, 80))

        # ── Layer 2: Printer dot (floating, top-right corner) ────────────
        self.printer_dot = tk.Label(self.root, text="●",
                                    font=("Helvetica", 10), fg=MUTED, bg="black")

        # ── Layer 3: Bottom overlay (compact, centered) ───────────────────
        self.bottom_bar = tk.Frame(self.root, bg="black")
        self.print_var = tk.StringVar(value="")
        tk.Label(self.bottom_bar, textvariable=self.print_var,
                 font=("Helvetica", 10), fg="#888888", bg="black").pack()
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(self.bottom_bar, textvariable=self.status_var,
                 font=("Helvetica", 11), fg="white", bg="black")
        self.status_label.pack(pady=(4, 4))
        self.btn_frame = tk.Frame(self.bottom_bar, bg="black")
        self.btn_frame.pack(pady=(0, 12))

        self.take_btn = tk.Button(
            self.btn_frame, text="Take Photo",
            font=("Helvetica", 14, "bold"), fg="white", bg=ACCENT,
            activebackground=ACCENT_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=32, pady=12, cursor="hand2", borderwidth=0,
            command=self._take_photo,
        )
        self.debug_btn = tk.Button(
            self.btn_frame, text="Debug Print",
            font=("Helvetica", 14, "bold"), fg="white", bg=WARNING,
            activebackground="#7a4508", activeforeground="white",
            relief=tk.FLAT, padx=32, pady=12, cursor="hand2", borderwidth=0,
            command=self._debug_print,
        )
        self.retake_btn = tk.Button(
            self.btn_frame, text="Retake",
            font=("Helvetica", 14, "bold"), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=32, pady=12, cursor="hand2", borderwidth=0,
            command=self._retake,
        )
        self.next_btn = tk.Button(
            self.btn_frame, text="Next →",
            font=("Helvetica", 14, "bold"), fg="white", bg=SUCCESS,
            activebackground=SUCCESS_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=32, pady=12, cursor="hand2", borderwidth=0,
            command=self._proceed_to_name,
        )

    # --- Preview loop ---

    def _display_size(self):
        w = self.root.winfo_width() or 640
        h = self.root.winfo_height() or 480
        return w, h

    def _fit_size(self, image: Image.Image):
        frame_w, frame_h = self._display_size()
        scale = min(frame_w / image.width, frame_h / image.height)
        return int(image.width * scale), int(image.height * scale)

    def _fill_display(self, image: Image.Image) -> Image.Image:
        """Scale and crop image to fill the full screen (no letterbox)."""
        w, h = self._display_size()
        scale = max(w / image.width, h / image.height)
        new_w, new_h = int(image.width * scale), int(image.height * scale)
        resized = image.resize((new_w, new_h), Image.BILINEAR)
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        return resized.crop((left, top, left + w, top + h))

    def _update_preview(self):
        if self.state == PREVIEW:
            try:
                frame = self.camera.get_frame()
                if frame is None:
                    self.root.after(50, self._update_preview)
                    return
                frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
                display = self._fill_display(frame)
                if self._countdown_n > 0:
                    draw = ImageDraw.Draw(display)
                    txt = str(self._countdown_n)
                    font_size = min(display.width, display.height) // 2
                    try:
                        fnt = ImageFont.truetype(
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                            font_size,
                        )
                    except Exception:
                        fnt = ImageFont.load_default()
                    bbox = fnt.getbbox(txt)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    x = (display.width - tw) // 2 - bbox[0]
                    y = (display.height - th) // 2 - bbox[1]
                    draw.text((x + 4, y + 4), txt, fill=(0, 0, 0), font=fnt)
                    draw.text((x, y), txt, fill=(255, 255, 255), font=fnt)
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

    def _on_start(self):
        self._show_state(PREVIEW)
        self.status_var.set("Look at the camera and press Take Photo!")
        self.status_label.config(fg=MUTED)

    def _take_photo(self):
        self._countdown_n = 3
        self.take_btn.config(state=tk.DISABLED)
        self.status_var.set("Get ready...")
        self.root.after(1000, self._countdown_tick)

    def _countdown_tick(self):
        self._countdown_n -= 1
        if self._countdown_n > 0:
            self.root.after(1000, self._countdown_tick)
        else:
            self._countdown_n = 0
            self._actually_take_photo()

    def _actually_take_photo(self):
        self.take_btn.config(state=tk.NORMAL)
        frame = self.camera.get_frame()
        if frame is None:
            return
        self.captured_photo = frame.transpose(Image.FLIP_LEFT_RIGHT)
        display = self._fill_display(self.captured_photo)
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
            ok, message = True, ""

        if ok:
            self.root.after(0, self._on_validation_ok)
        else:
            self.root.after(0, self._on_validation_fail, message)

    def _on_validation_ok(self):
        if self.captured_photo is None:
            return
        # Start generation immediately while user fills in name + quiz
        self._gen_result = None
        self._gen_ready = False
        self._gen_error = ""
        self._gen_char_id = ""
        photo_bytes = self._photo_to_jpeg_bytes()  # capture before thread starts
        threading.Thread(target=self._process, args=(photo_bytes,), daemon=True).start()

        self._show_state(REVIEW)
        self.status_var.set("Happy with the photo?")
        self.status_label.config(fg=MUTED)

    def _on_validation_fail(self, message: str):
        self.status_var.set(f"{message} — try again")
        self.status_label.config(fg=WARNING)

    def _retake(self):
        self.captured_photo = None
        self.user_name = ""
        self.dino_type = "1"
        self._answers = []
        self._question_idx = 0
        self._gen_result = None
        self._gen_ready = False
        self._gen_error = ""
        self._countdown_n = 0
        self._show_state(PREVIEW)
        self.status_var.set("Look at the camera and press Take Photo!")
        self.status_label.config(fg=MUTED)
        self.take_btn.config(state=tk.NORMAL)

    def _proceed_to_name(self):
        self.name_entry.delete(0, tk.END)
        self._show_state(NAME_INPUT)
        self.status_var.set("Enter your name")

    def _key_press(self, char: str):
        self.name_entry.insert(tk.END, char)

    def _key_backspace(self):
        current = self.name_entry.get()
        if current:
            self.name_entry.delete(len(current) - 1, tk.END)

    def _on_name_next(self):
        name = self.name_entry.get().strip()
        if not name:
            return
        self.user_name = name
        self._question_idx = 0
        self._answers = []
        self._show_question()
        self._show_state(QUESTIONNAIRE)
        self.status_var.set("")

    def _show_question(self):
        q = QUESTIONS[self._question_idx]
        self.quiz_q_var.set(q["q"])
        self.quiz_counter_var.set(f"Question {self._question_idx + 1} of {len(QUESTIONS)}")
        for w in self.quiz_btns_frame.winfo_children():
            w.destroy()
        colors  = [ACCENT, SUCCESS, WARNING, MUTED]
        actives = [ACCENT_ACTIVE, SUCCESS_ACTIVE, "#7a4508", "#3a7080"]
        for i, (text, dino) in enumerate(q["a"]):
            tk.Button(
                self.quiz_btns_frame, text=text,
                font=("Helvetica", 13), fg="white",
                bg=colors[i], activebackground=actives[i], activeforeground="white",
                relief=tk.FLAT, padx=20, pady=14, cursor="hand2", borderwidth=0,
                wraplength=500,
                command=lambda d=dino: self._on_answer(d),
            ).pack(fill=tk.X, pady=5)

    def _on_answer(self, dino: str):
        self._answers.append(dino)
        self._question_idx += 1
        if self._question_idx < len(QUESTIONS):
            self._show_question()
        else:
            self.dino_type = Counter(self._answers).most_common(1)[0][0]
            threading.Thread(target=self._publish, daemon=True).start()
            self._on_questionnaire_done()

    def _on_questionnaire_done(self):
        if self._gen_ready:
            if self._gen_result is not None:
                self.root.after(0, self._show_result, self._gen_result)
            else:
                self.root.after(0, self.status_var.set, f"Error: {self._gen_error}")
                self.root.after(0, self.status_label.config, {"fg": WARNING})
                self.root.after(0, self._show_state, REVIEW)
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
            self.status_var.set(f"Error: {self._gen_error}")
            self.status_label.config(fg=WARNING)
            self._show_state(REVIEW)

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
        """Send name + dino_type to server so character appears on the TV wall."""
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

    # --- Print ---

    def _show_result(self, image: Image.Image):
        self._show_state(RESULT)
        composited = self._composite_label(image)
        display = composited.resize(self._fit_size(composited), Image.NEAREST)
        photo = ImageTk.PhotoImage(display)
        self.display_label.config(image=photo)
        self.display_label.image = photo
        self.status_var.set("Printing...")
        threading.Thread(target=self._print_image, args=(composited,), daemon=True).start()

    def _composite_label(self, character: Image.Image) -> Image.Image:
        label_info = next(l for l in ALL_LABELS if l.identifier == LABEL)
        target_w, _ = label_info.dots_printable
        content_h = round(PRINT_HEIGHT_MM * 300 / 25.4)  # always use exact target height

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
                os.path.join(ASSETS_DIR, "Figma assets", "logo_figma.png")
            ).convert("RGBA")
            logo_h = content_h // 5
            logo_w = int(logo.width * logo_h / logo.height)
            if logo_w > right_w:
                logo_w = right_w
                logo_h = int(logo.height * logo_w / logo.width)
            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
            canvas.paste(logo, (right_x, PAD), logo)
            logo_bottom = PAD + logo_h
        except Exception:
            pass

        # Dino name label (bottom right, small text)
        dino_label_size = max(16, content_h // 16)
        try:
            small_font = ImageFont.truetype(font_path, dino_label_size)
        except Exception:
            small_font = ImageFont.load_default()
        dino_label = DINO_NAMES[self.dino_type]
        draw.text(
            (right_x, content_h - PAD - dino_label_size),
            dino_label,
            fill="#4a8a9e",
            font=small_font,
        )
        dino_label_top = content_h - PAD - dino_label_size

        # Name (right middle, fills space between logo and dino label)
        name_area_top = logo_bottom + PAD
        name_area_h = dino_label_top - name_area_top - PAD
        font_size = min(int(name_area_h * 0.80), 200)
        try:
            font = ImageFont.truetype(font_path, font_size)
            while font_size > 12:
                font = ImageFont.truetype(font_path, font_size)
                bbox = font.getbbox(self.user_name)
                if (bbox[2] - bbox[0]) <= right_w:
                    break
                font_size -= 4
        except Exception:
            font = ImageFont.load_default()

        name_y = name_area_top + (name_area_h - font_size) // 2
        draw.text((right_x, name_y), self.user_name, fill="#2d5c6a", font=font)

        return canvas

    def _debug_print(self):
        self._show_state(PROCESSING)
        self.status_var.set("Debug printing...")
        saved_name = self.user_name
        saved_dino = self.dino_type
        self.user_name = self.user_name or "Debug User"
        self.dino_type = self.dino_type or "1"
        image = Image.open(os.path.join(ASSETS_DIR, "style_reference.PNG"))
        composited = self._composite_label(image)
        self.user_name = saved_name
        self.dino_type = saved_dino
        threading.Thread(target=self._print_image, args=(composited,), daemon=True).start()

    def _print_image(self, image: Image.Image):
        try:
            if not hasattr(Image, "ANTIALIAS"):
                Image.ANTIALIAS = Image.LANCZOS
            dev = usb.core.find(idVendor=0x04f9, idProduct=0x20a8)
            if dev:
                try:
                    dev.reset()
                except Exception:
                    pass
                usb.util.dispose_resources(dev)  # fully drop the handle so brother_ql can claim it
            time.sleep(0.5)

            label_info = next(l for l in ALL_LABELS if l.identifier == LABEL)
            target_w, target_h_label = label_info.dots_printable
            content_h = round(PRINT_HEIGHT_MM * 300 / 25.4)
            # For continuous tape target_h_label==0; for die-cut use content_h centred on label
            target_h = content_h if target_h_label == 0 else target_h_label

            img = image.convert("RGB")
            # Fit composite into the target width × content_h, then centre on full label
            if img.width != target_w or img.height != content_h:
                img.thumbnail((target_w, content_h), Image.LANCZOS)
            canvas = Image.new("RGB", (target_w, target_h), "white")
            paste_y = (target_h - img.height) // 2
            canvas.paste(img, ((target_w - img.width) // 2, paste_y))
            img = canvas

            qlr = BrotherQLRaster(PRINTER_MODEL)
            convert(qlr, [img], LABEL, cut=True, rotate="0", dpi_600=False)
            send(
                instructions=qlr.data,
                printer_identifier=PRINTER_URI,
                backend_identifier="pyusb",
                blocking=True,
            )
            self.root.after(0, self.status_var.set, "Printed! Press Try Again to go again.")
            self.root.after(0, self.print_var.set, "Label sent to printer.")
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[print error] {e}", flush=True)
            self.root.after(0, self.status_var.set, "Done! Press Try Again to go again.")
            self.root.after(0, self.print_var.set, f"Print failed: {e}")
        finally:
            self.root.after(0, self._show_state, RESULT)

    def _show_state(self, state: str):
        self.state = state

        # Hide all content overlays
        for w in (self.start_frame, self.name_frame, self.quiz_frame, self.waiting_frame):
            w.place_forget()
        self.bottom_bar.place_forget()
        self.printer_dot.place_forget()

        if state == START:
            self.start_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            return

        # All non-start states show the bottom overlay and printer dot
        self.bottom_bar.place(relx=0.5, rely=1.0, anchor="s")
        self.printer_dot.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)

        # Content overlays for non-camera screens
        if state == NAME_INPUT:
            self.name_frame.place(relx=0, rely=0, relwidth=1, relheight=0.86)
            self.root.after(100, self.name_entry.focus_set)
        elif state == QUESTIONNAIRE:
            self.quiz_frame.place(relx=0, rely=0, relwidth=1, relheight=0.86)
        elif state == WAITING:
            self.waiting_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Buttons
        self.take_btn.pack_forget()
        self.retake_btn.pack_forget()
        self.debug_btn.pack_forget()
        self.next_btn.pack_forget()

        if state == PREVIEW:
            self.take_btn.pack(side=tk.LEFT, padx=4)
            self.debug_btn.pack(side=tk.LEFT, padx=4)
        elif state == VALIDATING:
            self.retake_btn.config(text="Retake")
            self.retake_btn.pack(side=tk.LEFT, padx=4)
        elif state == REVIEW:
            self.retake_btn.config(text="Retake")
            self.retake_btn.pack(side=tk.LEFT, padx=4)
            self.next_btn.pack(side=tk.LEFT, padx=4)
        elif state in (NAME_INPUT, QUESTIONNAIRE, WAITING):
            self.retake_btn.config(text="Retake")
            self.retake_btn.pack(side=tk.LEFT, padx=4)
        elif state == RESULT:
            self.retake_btn.config(text="Try Again")
            self.retake_btn.pack(side=tk.LEFT, padx=4)

    # --- Printer status ---

    def _poll_printer(self):
        threading.Thread(target=self._check_printer, daemon=True).start()
        self.root.after(10000, self._poll_printer)

    def _check_printer(self):
        try:
            connected = usb.core.find(idVendor=0x04f9, idProduct=0x20a8) is not None
        except Exception:
            connected = False
        self.root.after(0, self._update_printer_indicator, connected)

    def _update_printer_indicator(self, connected: bool):
        self.printer_dot.config(fg=SUCCESS if connected else MUTED)

    def _on_close(self):
        self.camera.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
