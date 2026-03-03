import tkinter as tk
from PIL import Image, ImageTk
import threading
import os
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()

from camera import capture_photo
from generate import generate_image

# --- Layout ---
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 420
IMAGE_DISPLAY_W = 400
IMAGE_DISPLAY_H = 164

# --- Colors ---
BG = "#1a1a2e"
PANEL = "#16213e"
ACCENT = "#e94560"
ACCENT_ACTIVE = "#c73652"
TEXT = "#eaeaea"
MUTED = "#666680"
SUCCESS = "#2ed573"

COUNTDOWN_SECONDS = 3


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.current_image: Image.Image | None = None
        self._is_processing = False

        self._setup_window()
        self._build_ui()
        self._poll_printer()

    def _setup_window(self):
        self.root.title("Speech To Print Box")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

    def _build_ui(self):
        # Title
        tk.Label(
            self.root,
            text="Speech To Print Box",
            font=("Helvetica", 17, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(pady=(24, 4))

        tk.Label(
            self.root,
            text="Press the button and look at the camera!",
            font=("Helvetica", 10),
            fg=MUTED,
            bg=BG,
        ).pack(pady=(0, 8))

        # Printer status indicator
        printer_frame = tk.Frame(self.root, bg=BG)
        printer_frame.pack(pady=(0, 12))
        self.printer_dot = tk.Label(printer_frame, text="●", font=("Helvetica", 10), fg=MUTED, bg=BG)
        self.printer_dot.pack(side=tk.LEFT, padx=(0, 4))
        self.printer_status_var = tk.StringVar(value="Checking printer...")
        tk.Label(printer_frame, textvariable=self.printer_status_var, font=("Helvetica", 10), fg=MUTED, bg=BG).pack(side=tk.LEFT)

        # Take photo button
        self.photo_btn = tk.Button(
            self.root,
            text="Take Photo",
            font=("Helvetica", 14, "bold"),
            fg="white",
            bg=ACCENT,
            activebackground=ACCENT_ACTIVE,
            activeforeground="white",
            relief=tk.FLAT,
            padx=32,
            pady=14,
            cursor="hand2",
            borderwidth=0,
            command=self._on_photo_press,
        )
        self.photo_btn.pack(pady=(0, 10))

        # Status
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            fg=MUTED,
            bg=BG,
        ).pack(pady=(0, 12))

        # Image display
        img_container = tk.Frame(self.root, bg=PANEL, width=IMAGE_DISPLAY_W, height=IMAGE_DISPLAY_H)
        img_container.pack(padx=20)
        img_container.pack_propagate(False)

        self.image_label = tk.Label(
            img_container,
            bg=PANEL,
            text="Image will appear here",
            fg=MUTED,
            font=("Helvetica", 11),
        )
        self.image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Print status
        self.print_var = tk.StringVar(value="")
        tk.Label(
            self.root,
            textvariable=self.print_var,
            font=("Helvetica", 10),
            fg=MUTED,
            bg=BG,
        ).pack(pady=8)

    # --- Button handler ---

    def _on_photo_press(self):
        if self._is_processing:
            return
        self._is_processing = True
        self.photo_btn.config(state=tk.DISABLED)
        self.print_var.set("")
        self._countdown(COUNTDOWN_SECONDS)

    def _countdown(self, n: int):
        if n > 0:
            self.status_var.set(f"Get ready... {n}")
            self.root.after(1000, self._countdown, n - 1)
        else:
            self.status_var.set("Capturing photo...")
            threading.Thread(target=self._process, daemon=True).start()

    # --- Background processing ---

    def _process(self):
        try:
            photo = capture_photo()
            self.root.after(0, self.status_var.set, "Generating pixel art...")
            image = generate_image(photo)
            self.root.after(0, self._show_image, image)
        except Exception as e:
            self.root.after(0, self.status_var.set, f"Error: {e}")
        finally:
            self.root.after(0, self._unlock_btn)

    def _show_image(self, image: Image.Image):
        self.current_image = image
        display = image.resize((IMAGE_DISPLAY_W, IMAGE_DISPLAY_H), Image.NEAREST)
        photo = ImageTk.PhotoImage(display)
        self.image_label.config(image=photo, text="")
        self.image_label.image = photo
        self.status_var.set("Printing...")
        threading.Thread(target=self._print_image, args=(image,), daemon=True).start()

    def _print_image(self, image: Image.Image):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp_path = f.name
            image.save(tmp_path, dpi=(300, 300))
            subprocess.run(
                ["lp", "-d", "Leitz_Icon_Wi-Fi",
                 "-o", "media=Multipurpose70030001",
                 "-o", "fit-to-page",
                 tmp_path],
                check=True,
            )
            self.root.after(0, self.status_var.set, "Printed! Press to go again.")
            self.root.after(0, self.print_var.set, "Label sent to printer.")
        except Exception as e:
            self.root.after(0, self.status_var.set, "Done! Press to go again.")
            self.root.after(0, self.print_var.set, f"Print failed: {e}")
        finally:
            os.unlink(tmp_path)

    def _unlock_btn(self):
        self._is_processing = False
        self.photo_btn.config(state=tk.NORMAL)

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
                state in result.stdout for state in ("idle", "printing")
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


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
