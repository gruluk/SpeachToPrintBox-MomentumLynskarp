import os
import tkinter as tk
from PIL import Image, ImageTk

from config import (
    BG, TEXT, MUTED, ACCENT, ACCENT_ACTIVE, SUCCESS, SUCCESS_ACTIVE, WARNING,
    ASSETS_DIR,
)


class StartScreen:
    def __init__(self, root: tk.Tk, on_start):
        self.frame = tk.Frame(root, bg=BG)
        self._logo_photo = None
        try:
            logo_img = Image.open(
                os.path.join(ASSETS_DIR, "Figma assets", "logo_figma.png")
            ).convert("RGBA")
            logo_img.thumbnail((420, 420), Image.LANCZOS)
            self._logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(self.frame, image=self._logo_photo, bg=BG).pack(
                expand=True, pady=(0, 16)
            )
        except Exception:
            tk.Label(
                self.frame, text="BYTEFEST '26",
                font=("Helvetica", 48, "bold"), fg=TEXT, bg=BG,
            ).pack(expand=True)
        tk.Button(
            self.frame, text="START",
            font=("Helvetica", 32, "bold"), fg="white", bg=ACCENT,
            activebackground=ACCENT_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=70, pady=24, cursor="hand2", borderwidth=0,
            command=on_start,
        ).pack(pady=(0, 80))

    def show(self):
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self):
        self.frame.place_forget()


class PreviewControls:
    def __init__(self, root: tk.Tk, on_take, on_debug):
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            root, textvariable=self._status_var,
            font=("Helvetica", 16, "bold"), fg="white", bg="black",
            padx=12, pady=6,
        )
        self._btn_row = tk.Frame(root, bg="black", bd=0, highlightthickness=0)
        self._take_btn = tk.Button(
            self._btn_row, text="Ta bilde",
            font=("Helvetica", 18, "bold"), fg="white", bg=ACCENT,
            activebackground=ACCENT_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=40, pady=16, cursor="hand2", borderwidth=0,
            command=on_take,
        )
        self._take_btn.pack(side=tk.LEFT, padx=6)
        tk.Button(
            self._btn_row, text="Debug-utskrift",
            font=("Helvetica", 18, "bold"), fg="white", bg=WARNING,
            activebackground="#7a4508", activeforeground="white",
            relief=tk.FLAT, padx=40, pady=16, cursor="hand2", borderwidth=0,
            command=on_debug,
        ).pack(side=tk.LEFT, padx=6)

    def show(self):
        self._btn_row.place(relx=0.5, rely=1.0, anchor="s", y=-16)
        self._status_lbl.place(relx=0.5, rely=1.0, anchor="s", y=-90)

    def hide(self):
        self._btn_row.place_forget()
        self._status_lbl.place_forget()

    def set_status(self, msg: str):
        self._status_var.set(msg)

    def disable_take(self):
        self._take_btn.config(state=tk.DISABLED)

    def enable_take(self):
        self._take_btn.config(state=tk.NORMAL)


class ValidatingControls:
    def __init__(self, root: tk.Tk, on_retake):
        self._status_var = tk.StringVar(value="Sjekker bildet...")
        self._status_lbl = tk.Label(
            root, textvariable=self._status_var,
            font=("Helvetica", 16, "bold"), fg="white", bg="black",
            padx=12, pady=6,
        )
        self._btn_row = tk.Frame(root, bg="black", bd=0, highlightthickness=0)
        tk.Button(
            self._btn_row, text="Ta om igjen",
            font=("Helvetica", 18, "bold"), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=40, pady=16, cursor="hand2", borderwidth=0,
            command=on_retake,
        ).pack(side=tk.LEFT, padx=6)

    def show(self):
        self._btn_row.place(relx=0.5, rely=1.0, anchor="s", y=-16)
        self._status_lbl.place(relx=0.5, rely=1.0, anchor="s", y=-90)

    def hide(self):
        self._btn_row.place_forget()
        self._status_lbl.place_forget()

    def set_status(self, msg: str, color: str = "white"):
        self._status_var.set(msg)
        self._status_lbl.config(fg=color)


class ReviewControls:
    def __init__(self, root: tk.Tk, on_retake, on_next):
        self._status_var = tk.StringVar(value="Fornøyd med bildet?")
        self._status_lbl = tk.Label(
            root, textvariable=self._status_var,
            font=("Helvetica", 16, "bold"), fg="white", bg="black",
            padx=12, pady=6,
        )
        self._btn_row = tk.Frame(root, bg="black", bd=0, highlightthickness=0)
        tk.Button(
            self._btn_row, text="Ta om igjen",
            font=("Helvetica", 18, "bold"), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=40, pady=16, cursor="hand2", borderwidth=0,
            command=on_retake,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            self._btn_row, text="Neste →",
            font=("Helvetica", 18, "bold"), fg="white", bg=SUCCESS,
            activebackground=SUCCESS_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=40, pady=16, cursor="hand2", borderwidth=0,
            command=on_next,
        ).pack(side=tk.LEFT, padx=6)

    def show(self):
        self._btn_row.place(relx=0.5, rely=1.0, anchor="s", y=-16)
        self._status_lbl.place(relx=0.5, rely=1.0, anchor="s", y=-90)

    def hide(self):
        self._btn_row.place_forget()
        self._status_lbl.place_forget()

    def set_status(self, msg: str, color: str = "white"):
        self._status_var.set(msg)
        self._status_lbl.config(fg=color)


class NameInputScreen:
    def __init__(self, root: tk.Tk, on_next, on_retake):
        self.frame = tk.Frame(root, bg=BG)
        tk.Label(
            self.frame, text="Hva heter du?",
            font=("Helvetica", 28, "bold"), fg=TEXT, bg=BG,
        ).pack(pady=(28, 12))
        self._entry = tk.Entry(
            self.frame, font=("Helvetica", 30), fg=TEXT,
            justify=tk.CENTER, relief=tk.FLAT,
            bg="white", insertbackground=TEXT, width=20,
        )
        self._entry.pack(pady=4, ipady=12)
        self._entry.bind("<Return>", lambda _e: on_next())

        btn_row = tk.Frame(self.frame, bg=BG)
        btn_row.pack(pady=10)
        tk.Button(
            btn_row, text="Ta om igjen",
            font=("Helvetica", 18, "bold"), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=40, pady=14, cursor="hand2", borderwidth=0,
            command=on_retake,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            btn_row, text="Neste →",
            font=("Helvetica", 18, "bold"), fg="white", bg=SUCCESS,
            activebackground=SUCCESS_ACTIVE, activeforeground="white",
            relief=tk.FLAT, padx=40, pady=14, cursor="hand2", borderwidth=0,
            command=on_next,
        ).pack(side=tk.LEFT, padx=6)

        kb_frame = tk.Frame(self.frame, bg=BG)
        kb_frame.pack(pady=(6, 12))
        KEY_ROWS = [list("QWERTYUIOPÅ"), list("ASDFGHJKLØÆ"), list("ZXCVBNM")]
        for row in KEY_ROWS:
            rf = tk.Frame(kb_frame, bg=BG)
            rf.pack(pady=2)
            for ch in row:
                tk.Button(
                    rf, text=ch,
                    font=("Helvetica", 16, "bold"), fg=TEXT, bg="white",
                    activebackground="#c8dde8", activeforeground=TEXT,
                    relief=tk.FLAT, width=3, pady=10, borderwidth=0,
                    command=lambda c=ch: self._key_press(c),
                ).pack(side=tk.LEFT, padx=2)
        bot_row = tk.Frame(kb_frame, bg=BG)
        bot_row.pack(pady=2)
        tk.Button(
            bot_row, text="SLETT",
            font=("Helvetica", 16, "bold"), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=22, pady=10, borderwidth=0,
            command=self._key_backspace,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            bot_row, text="MELLOMROM",
            font=("Helvetica", 16, "bold"), fg=TEXT, bg="white",
            activebackground="#c8dde8", activeforeground=TEXT,
            relief=tk.FLAT, padx=70, pady=10, borderwidth=0,
            command=lambda: self._key_press(" "),
        ).pack(side=tk.LEFT, padx=4)

    def _key_press(self, char: str):
        self._entry.insert(tk.END, char)

    def _key_backspace(self):
        current = self._entry.get()
        if current:
            self._entry.delete(len(current) - 1, tk.END)

    def get_name(self) -> str:
        return self._entry.get()

    def clear(self):
        self._entry.delete(0, tk.END)

    def focus(self):
        self._entry.focus_set()

    def show(self):
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self):
        self.frame.place_forget()


class QuestionnaireScreen:
    def __init__(self, root: tk.Tk, on_answer, on_retake):
        self._on_answer = on_answer
        self.frame = tk.Frame(root, bg=BG)
        self._counter_var = tk.StringVar()
        tk.Label(
            self.frame, textvariable=self._counter_var,
            font=("Helvetica", 14), fg=MUTED, bg=BG,
        ).pack(pady=(24, 4))
        self._q_var = tk.StringVar()
        tk.Label(
            self.frame, textvariable=self._q_var,
            font=("Helvetica", 26, "bold"), fg=TEXT, bg=BG, wraplength=800,
        ).pack(pady=(0, 20))
        self._btns_frame = tk.Frame(self.frame, bg=BG)
        self._btns_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=(0, 8))
        self._btns_frame.columnconfigure(0, weight=1)
        self._btns_frame.columnconfigure(1, weight=1)
        self._btns_frame.rowconfigure(0, weight=1)
        self._btns_frame.rowconfigure(1, weight=1)
        tk.Button(
            self.frame, text="Ta om igjen",
            font=("Helvetica", 16), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=24, pady=10, cursor="hand2", borderwidth=0,
            command=on_retake,
        ).pack(pady=(4, 16))

    def set_question(self, q_dict: dict, index: int, total: int):
        self._counter_var.set(f"Spørsmål {index + 1} av {total}")
        self._q_var.set(q_dict["q"])
        for w in self._btns_frame.winfo_children():
            w.destroy()
        colors  = [ACCENT, SUCCESS, WARNING, MUTED]
        actives = [ACCENT_ACTIVE, SUCCESS_ACTIVE, "#7a4508", "#3a7080"]
        for i, (text, dino) in enumerate(q_dict["a"]):
            row, col = divmod(i, 2)
            tk.Button(
                self._btns_frame, text=text,
                font=("Helvetica", 18, "bold"), fg="white",
                bg=colors[i], activebackground=actives[i], activeforeground="white",
                relief=tk.FLAT, cursor="hand2", borderwidth=0,
                wraplength=340,
                command=lambda d=dino: self._on_answer(d),
            ).grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

    def show(self):
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self):
        self.frame.place_forget()


class WaitingScreen:
    def __init__(self, root: tk.Tk, on_retake):
        self.frame = tk.Frame(root, bg=BG)
        tk.Label(
            self.frame, text="Nesten klar...",
            font=("Helvetica", 36, "bold"), fg=TEXT, bg=BG,
        ).pack(expand=True)
        tk.Label(
            self.frame, text="Genererer karakteren din",
            font=("Helvetica", 18), fg=MUTED, bg=BG,
        ).pack()
        tk.Button(
            self.frame, text="Ta om igjen",
            font=("Helvetica", 16), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=24, pady=10, cursor="hand2", borderwidth=0,
            command=on_retake,
        ).pack(pady=(16, 80))

    def show(self):
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self):
        self.frame.place_forget()


class ResultControls:
    def __init__(self, root: tk.Tk, on_done):
        self._labels = tk.Frame(root, bg="black", bd=0, highlightthickness=0)
        self._print_var = tk.StringVar(value="")
        tk.Label(
            self._labels, textvariable=self._print_var,
            font=("Helvetica", 13), fg="#aaaaaa", bg="black",
            padx=8, pady=0,
        ).pack()
        self._status_var = tk.StringVar(value="Skriver ut...")
        tk.Label(
            self._labels, textvariable=self._status_var,
            font=("Helvetica", 16, "bold"), fg="white", bg="black",
            padx=8, pady=4,
        ).pack()
        self._btn_row = tk.Frame(root, bg="black", bd=0, highlightthickness=0)
        tk.Button(
            self._btn_row, text="Prøv igjen",
            font=("Helvetica", 18, "bold"), fg="white", bg=MUTED,
            activebackground="#3a7080", activeforeground="white",
            relief=tk.FLAT, padx=40, pady=16, cursor="hand2", borderwidth=0,
            command=on_done,
        ).pack(side=tk.LEFT, padx=6)

    def show(self):
        self._btn_row.place(relx=0.5, rely=1.0, anchor="s", y=-16)
        self._labels.place(relx=0.5, rely=1.0, anchor="s", y=-100)

    def hide(self):
        self._btn_row.place_forget()
        self._labels.place_forget()

    def set_status(self, msg: str):
        self._status_var.set(msg)

    def set_print_status(self, msg: str):
        self._print_var.set(msg)


class PrinterDot:
    def __init__(self, root: tk.Tk):
        self.label = tk.Label(
            root, text="●", font=("Helvetica", 10), fg=MUTED, bg="black"
        )

    def show(self):
        self.label.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)

    def hide(self):
        self.label.place_forget()

    def set_connected(self, connected: bool):
        self.label.config(fg=SUCCESS if connected else MUTED)
