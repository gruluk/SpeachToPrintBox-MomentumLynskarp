import os
from dotenv import load_dotenv

load_dotenv()

# --- Bytefest '26 brand palette ---
BLUE_PALE    = "#C1E6F2"
BLUE_LIGHT   = "#ADDDEC"
BLUE_BRAND   = "#32ABD0"
BLUE_DARK    = "#1D7B91"
ORANGE_BRAND = "#FB9214"
ORANGE_MID   = "#F5B166"
ORANGE_PALE  = "#F9CB99"
GREEN_BRAND  = "#539227"
GREEN_MID    = "#80963A"
GREEN_DARK   = "#5A6731"
GREEN_LIGHT  = "#73C78C"
BROWN        = "#8F5741"
BEIGE        = "#D1B7AD"

# --- Semantic colors (mapped from palette) ---
BG             = BLUE_PALE
DISPLAY_BG     = BLUE_LIGHT
TEXT           = BLUE_DARK
MUTED          = BLUE_BRAND
ACCENT         = BLUE_DARK
ACCENT_ACTIVE  = "#155e6e"   # BLUE_DARK darkened for pressed state
SUCCESS        = GREEN_BRAND
SUCCESS_ACTIVE = GREEN_MID
WARNING        = ORANGE_BRAND

# --- Printer ---
PRINTER_MODEL   = "QL-1110NWB"
PRINTER_VENDOR  = 0x04f9
PRINTER_PRODUCT = 0x20a8
PRODUCTION_MODE     = os.getenv("PRODUCTION_MODE",     "false").lower() == "true"
ENABLE_LOCAL_PRINT  = os.getenv("ENABLE_LOCAL_PRINT",  "false").lower() == "true"
LABEL           = "103" if PRODUCTION_MODE else "103x164"
PRINT_HEIGHT_MM = 45  # content height for both continuous and die-cut

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

# --- Assets / server ---
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
SERVER_URL  = os.getenv("SERVER_URL", "http://localhost:8000")

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
