# -*- coding: utf-8 -*-
import pygame
import cv2
import json
import threading
from config import *

# Variables Globales de Recursos (Patrón Singleton simplificado)
GAMES = []
MUSIC_TRACKS = []
cap = None  # Video Capture
video_surface = None
vinyl_original = None
nav_sound = None
custom_font = None
resources_loaded = False
loading_progress = 0

def load_and_scale_image(path, max_width, max_height):
    try:
        img = pygame.image.load(path)
        if img.get_alpha() or img.get_colorkey():
            img = img.convert_alpha()
        else:
            img = img.convert()
        w, h = img.get_size()
        scale = min(max_width / w, max_height / h)
        if scale > 1.0: scale = 1.0
        new_w, new_h = int(w * scale), int(h * scale)
        return pygame.transform.smoothscale(img, (new_w, new_h))
    except Exception as e:
        print(f"❌ Error IMG {path}: {e}")
        fallback = pygame.Surface((100, 100), pygame.SRCALPHA)
        fallback.fill((255, 0, 255))
        return fallback

def create_fallback_vinyl():
    surf = pygame.Surface((VINYL_SIZE, VINYL_SIZE), pygame.SRCALPHA)
    pygame.draw.circle(surf, (40, 40, 40), (VINYL_SIZE//2, VINYL_SIZE//2), VINYL_SIZE//2)
    pygame.draw.circle(surf, (20, 20, 20), (VINYL_SIZE//2, VINYL_SIZE//2), VINYL_SIZE//4)
    return surf

def load_resources_thread(width, height):
    global GAMES, MUSIC_TRACKS, cap, video_surface, vinyl_original
    global nav_sound, custom_font, resources_loaded, loading_progress

    print("🧵 Iniciando hilo de carga...")
    
    # 1. Cargar Fuente
    try:
        if CUSTOM_FONT_PATH.exists():
            custom_font = pygame.font.Font(str(CUSTOM_FONT_PATH), 42)
        else:
            custom_font = pygame.font.Font(None, 36)
    except:
        custom_font = pygame.font.Font(None, 36)
    loading_progress = 10

    # 2. Cargar Audio Navegación
    if NAVIGATION_SOUND_PATH.exists():
        try:
            nav_sound = pygame.mixer.Sound(str(NAVIGATION_SOUND_PATH))
            nav_sound.set_volume(0.3)
        except: pass
    loading_progress = 20

    # 3. Cargar Video (OpenCV)
    if VIDEO_PATH.exists():
        try:
            cap = cv2.VideoCapture(str(VIDEO_PATH))
            if cap.isOpened():
                video_surface = pygame.Surface((width, height))
            else:
                cap = None
        except Exception as e:
            print(f"⚠️ Error Video: {e}")
    loading_progress = 30

    # 4. Cargar Vinilo
    if VINYL_DISC_IMAGE.exists():
        try:
            vinyl_raw = pygame.image.load(str(VINYL_DISC_IMAGE)).convert_alpha()
            vinyl_original = pygame.transform.smoothscale(vinyl_raw, (VINYL_SIZE, VINYL_SIZE))
        except:
            vinyl_original = create_fallback_vinyl()
    else:
        vinyl_original = create_fallback_vinyl()
    loading_progress = 40

    # 5. Cargar Música
    tracks = []
    if MUSIC_FOLDER.exists():
        for ext in ["*.ogg", "*.OGG"]:
            for file in MUSIC_FOLDER.glob(ext):
                if not any(t["path"] == str(file.resolve()) for t in tracks):
                    tracks.append({"path": str(file.resolve()), "name": file.stem})
    MUSIC_TRACKS = tracks
    loading_progress = 50

    # 6. Cargar Juegos (JSON + Imágenes)
    if GAMES_JSON.exists():
        try:
            with open(GAMES_JSON, 'r', encoding='utf-8') as f:
                raw_games = json.load(f)
            
            total_games = len(raw_games)
            processed_games = []
            
            for i, game in enumerate(raw_games):
                current_percent = 50 + int((i / total_games) * 40)
                loading_progress = current_percent
                
                icon_path = validate_path(game.get("icon", ""))
                logo_path = validate_path(game.get("logo", ""))
                exe_path = validate_path(game.get("ruta_ejecutable", ""))
                sound_path = validate_path(game.get("sound", ""))
                
                if icon_path and logo_path and exe_path:
                    game_obj = {
                        "nombre": game.get("nombre", "Sin Nombre"),
                        "icon": str(icon_path),
                        "logo": str(logo_path),
                        "ruta_ejecutable": str(exe_path),
                        "tipo": game.get("tipo", "appimage"),
                        "sound_obj": None
                    }
                    
                    game_obj["icon_img"] = load_and_scale_image(str(icon_path), MAX_ICON_WIDTH, MAX_ICON_HEIGHT)
                    game_obj["logo_img"] = load_and_scale_image(str(logo_path), MAX_LOGO_WIDTH, MAX_LOGO_HEIGHT)
                    
                    if sound_path:
                        try:
                            game_obj["sound_obj"] = pygame.mixer.Sound(str(sound_path))
                        except: pass
                    
                    processed_games.append(game_obj)
            
            GAMES = processed_games
        except Exception as e:
            print(f"❌ Error JSON: {e}")
    
    loading_progress = 100
    resources_loaded = True
    print("✅ Carga de recursos finalizada.")
