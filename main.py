import tkinter as tk
from PIL import Image, ImageTk
import threading
import os
from dotenv import load_dotenv

load_dotenv()

from audio import AudioRecorder
from transcribe import transcribe_audio
from generate import generate_image

# --- Layout ---
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 680
IMAGE_DISPLAY_SIZE = 400

# --- Colors ---
BG = "#1a1a2e"
PANEL = "#16213e"
ACCENT = "#e94560"
ACCENT_ACTIVE = "#c73652"
TEXT = "#eaeaea"
MUTED = "#666680"
SUCCESS = "#2ed573"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.recorder = AudioRecorder()
        self.current_image: Image.Image | None = None
        self._is_recording = False
        self._is_processing = False

        self._setup_window()
        self._build_ui()

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
            text="Hold the button, speak, release to generate.",
            font=("Helvetica", 10),
            fg=MUTED,
            bg=BG,
        ).pack(pady=(0, 16))

        # Record button
        self.record_btn = tk.Button(
            self.root,
            text="Hold to Record",
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
        )
        self.record_btn.pack(pady=(0, 10))
        self.record_btn.bind("<ButtonPress-1>", self._on_record_press)
        self.record_btn.bind("<ButtonRelease-1>", self._on_record_release)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            fg=MUTED,
            bg=BG,
        ).pack(pady=(0, 12))

        # Transcription panel
        trans_frame = tk.Frame(self.root, bg=PANEL, padx=16, pady=12)
        trans_frame.pack(fill=tk.X, padx=20, pady=(0, 12))

        tk.Label(
            trans_frame,
            text="TRANSCRIPTION",
            font=("Helvetica", 8, "bold"),
            fg=MUTED,
            bg=PANEL,
        ).pack(anchor=tk.W)

        self.transcription_var = tk.StringVar(value="—")
        tk.Label(
            trans_frame,
            textvariable=self.transcription_var,
            font=("Helvetica", 12),
            fg=TEXT,
            bg=PANEL,
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 0))

        # Image display (400x400 — matches label size)
        img_container = tk.Frame(self.root, bg=PANEL, width=IMAGE_DISPLAY_SIZE, height=IMAGE_DISPLAY_SIZE)
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

        # Save button
        self.save_btn = tk.Button(
            self.root,
            text="Save Image",
            font=("Helvetica", 12, "bold"),
            fg="white",
            bg=MUTED,
            activebackground=ACCENT_ACTIVE,
            activeforeground="white",
            relief=tk.FLAT,
            padx=24,
            pady=10,
            state=tk.DISABLED,
            cursor="hand2",
            borderwidth=0,
            command=self._save_image,
        )
        self.save_btn.pack(pady=14)

    # --- Event handlers ---

    def _on_record_press(self, event=None):
        if self._is_processing:
            return
        self._is_recording = True
        self.recorder.start()
        self.record_btn.config(bg=ACCENT_ACTIVE, text="● Recording")
        self.status_var.set("Recording... release to process")

    def _on_record_release(self, event=None):
        if not self._is_recording:
            return
        self._is_recording = False
        audio_path = self.recorder.stop()

        self.record_btn.config(text="Hold to Record", bg=ACCENT)

        if not audio_path:
            self.status_var.set("No audio captured. Try again.")
            return

        self._is_processing = True
        self.record_btn.config(state=tk.DISABLED, text="Processing...")
        self.save_btn.config(state=tk.DISABLED, bg=MUTED)
        threading.Thread(target=self._process, args=(audio_path,), daemon=True).start()

    # --- Background processing ---

    def _process(self, audio_path: str):
        try:
            self.root.after(0, self.status_var.set, "Transcribing...")
            text = transcribe_audio(audio_path)
            self.root.after(0, self.transcription_var.set, text)

            self.root.after(0, self.status_var.set, "Generating image...")
            image = generate_image(text)

            self.root.after(0, self._show_image, image)
        except Exception as e:
            self.root.after(0, self.status_var.set, f"Error: {e}")
        finally:
            self.root.after(0, self._unlock_record_btn)

    def _show_image(self, image: Image.Image):
        self.current_image = image
        photo = ImageTk.PhotoImage(image)
        self.image_label.config(image=photo, text="")
        self.image_label.image = photo  # prevent garbage collection
        self.save_btn.config(state=tk.NORMAL, bg=ACCENT)
        self.status_var.set("Done! Hold to record again.")

    def _unlock_record_btn(self):
        self._is_processing = False
        self.record_btn.config(state=tk.NORMAL, bg=ACCENT, text="Hold to Record")

    def _save_image(self):
        if self.current_image:
            path = os.path.join(os.getcwd(), "output.png")
            self.current_image.save(path)
            self.status_var.set(f"Saved to {path}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
