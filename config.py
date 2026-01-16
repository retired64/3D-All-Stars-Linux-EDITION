# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# ==========================================
# ⚙️ CONFIGURACIÓN GENERAL
# ==========================================
WINDOW_TITLE = "3D All Stars Deluxe - Linux EDITION"
FPS = 60

# --- Rutas BASE ---
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()

# --- Rutas de Archivos ---
VIDEO_PATH = BASE_DIR / "assets" / "background.mp4"
MUSIC_FOLDER = BASE_DIR / "assets" / "ogg-sounds"
NAVIGATION_SOUND_PATH = BASE_DIR / "assets" / "sounds" / "navigation_sound.wav"
SPLASH_IMAGE_PATH = BASE_DIR / "assets" / "splash.png"
SPLASH_SOUND_PATH = BASE_DIR / "assets" / "sounds" / "splash_sound.wav"
GAMES_JSON = BASE_DIR / "games.json"
VINYL_DISC_IMAGE = BASE_DIR / "assets" / "vinyl_disc.png"
CUSTOM_FONT_PATH = BASE_DIR / "assets" / "fonts" / "SuperMario256.ttf"

# --- Configuración del Creador ---
CREATOR_NAME = "By Retired64"
CREATOR_USERNAME = "Retired64"
YOUTUBE_URL = "https://www.youtube.com/@Retired64"

MARIO64_COLORS = [
    (255, 50, 50), (255, 220, 50), (50, 255, 100),
    (50, 150, 255), (255, 150, 50), (200, 50, 255),
]

# --- Configuración Visual ---
MAX_ICON_WIDTH = 500
MAX_ICON_HEIGHT = 500
MAX_LOGO_WIDTH = 900
MAX_LOGO_HEIGHT = 450
TRANSITION_SPEED = 0.18
VINYL_SIZE = 120
VINYL_MARGIN = 30
VINYL_ROTATION_SPEED = 1.5
JOYSTICK_DEADZONE = 0.3

# Función auxiliar esencial
def validate_path(path_str):
    if not path_str: return None
    path = Path(path_str)
    if not path.is_absolute(): path = BASE_DIR / path
    return path.resolve() if path.exists() else None
