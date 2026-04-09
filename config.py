import os
from dotenv import load_dotenv

load_dotenv()

# --- Sopra Steria brand palette ---
PURPLE       = "#3c1c71"
PURPLE_BG    = "#ede9f2"
PURPLE_DARK  = "#2a1338"
PURPLE_WARM  = "#7a1c71"
BEIGE        = "#ece1d4"
RED          = "#bf022b"
ORANGE       = "#e06c00"
GREY         = "#a7a7a6"
LIGHT_GREY   = "#ededed"
BLACK        = "#1c1c1a"

# --- Semantic colors (mapped from palette) ---
BG             = PURPLE_BG
DISPLAY_BG     = LIGHT_GREY
TEXT           = PURPLE_DARK
MUTED          = PURPLE
ACCENT         = PURPLE
ACCENT_ACTIVE  = "#2a1338"
SUCCESS        = RED
SUCCESS_ACTIVE = "#8a0120"
WARNING        = ORANGE

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
INFO          = "info"
PREVIEW       = "preview"
VALIDATING    = "validating"
REVIEW        = "review"
NAME_INPUT    = "name_input"
WAITING       = "waiting"
PROCESSING    = "processing"
RESULT        = "result"

# --- Assets / server ---
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
SERVER_URL  = os.getenv("SERVER_URL", "http://localhost:8000")
