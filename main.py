import pygame
import numpy as np
import sys
import os
import subprocess
import json
import webbrowser
from pathlib import Path
import threading
import time

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
BACKGROUND_IMAGE = BASE_DIR / "assets" / "fondo.png"
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

# ==========================================
# 🌐 VARIABLES GLOBALES (Estado de Carga)
# ==========================================
GAMES = []
MUSIC_TRACKS = []
background_surface = None
vinyl_original = None
vinyl_disc = None
nav_sound = None
custom_font = None
resources_loaded = False
loading_progress = 0

# ==========================================
# 🛠️ FUNCIONES AUXILIARES
# ==========================================
def validate_path(path_str, base_dir=BASE_DIR):
    if not path_str: return None
    path = Path(path_str)
    if not path.is_absolute(): path = base_dir / path
    return path.resolve() if path.exists() else None

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

def round_image_corners(image, radius):
    rect = image.get_rect()
    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255), rect, border_radius=radius)
    result = image.copy()
    result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return result

def create_fallback_vinyl():
    surf = pygame.Surface((VINYL_SIZE, VINYL_SIZE), pygame.SRCALPHA)
    pygame.draw.circle(surf, (40, 40, 40), (VINYL_SIZE//2, VINYL_SIZE//2), VINYL_SIZE//2)
    pygame.draw.circle(surf, (20, 20, 20), (VINYL_SIZE//2, VINYL_SIZE//2), VINYL_SIZE//4)
    return surf

# ==========================================
# 🧵 HILO DE CARGA DE RECURSOS (BACKGROUND)
# ==========================================
def load_resources_thread(width, height):
    global GAMES, MUSIC_TRACKS, vinyl_original, vinyl_disc
    global nav_sound, custom_font, resources_loaded, loading_progress

    print("🧵 Iniciando carga optimizada...")
    
    # 1. Cargar Fuente
    try:
        if CUSTOM_FONT_PATH.exists():
            custom_font = pygame.font.Font(str(CUSTOM_FONT_PATH), 42)
        else:
            custom_font = pygame.font.Font(None, 36)
    except:
        custom_font = pygame.font.Font(None, 36)
    loading_progress = 15

    # 2. Cargar Audio Navegación
    if NAVIGATION_SOUND_PATH.exists():
        try:
            nav_sound = pygame.mixer.Sound(str(NAVIGATION_SOUND_PATH))
            nav_sound.set_volume(0.3)
        except: pass
    loading_progress = 25

    # 3. Fondo ya cargado en main thread
    loading_progress = 35

    # 4. Cargar Vinilo
    if VINYL_DISC_IMAGE.exists():
        try:
            vinyl_raw = pygame.image.load(str(VINYL_DISC_IMAGE)).convert_alpha()
            vinyl_original = pygame.transform.smoothscale(vinyl_raw, (VINYL_SIZE, VINYL_SIZE))
        except:
            vinyl_original = create_fallback_vinyl()
    else:
        vinyl_original = create_fallback_vinyl()
    vinyl_disc = vinyl_original.copy()
    loading_progress = 45

    # 5. Cargar Música
    tracks = []
    if MUSIC_FOLDER.exists():
        for ext in ["*.ogg", "*.OGG"]:
            for file in MUSIC_FOLDER.glob(ext):
                if not any(t["path"] == str(file.resolve()) for t in tracks):
                    tracks.append({"path": str(file.resolve()), "name": file.stem})
    MUSIC_TRACKS = tracks
    loading_progress = 55

    # 6. Cargar Juegos (JSON + Imágenes)
    if GAMES_JSON.exists():
        try:
            with open(GAMES_JSON, 'r', encoding='utf-8') as f:
                raw_games = json.load(f)
            
            total_games = len(raw_games)
            processed_games = []
            
            for i, game in enumerate(raw_games):
                current_percent = 55 + int((i / total_games) * 40)
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
    print("✅ Carga optimizada completada")

# ==========================================
# 🎮 INICIALIZACIÓN PYGAME
# ==========================================
pygame.init()
pygame.mixer.quit()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)

screen.fill((0, 0, 0))
pygame.display.flip()

pygame.display.set_caption(WINDOW_TITLE)
clock = pygame.time.Clock()

# ==========================================
# 🖼️ CARGA PRIORITARIA DEL FONDO
# ==========================================
print(f"📂 Ruta base: {BASE_DIR}")
print(f"🖼️ Buscando fondo en: {BACKGROUND_IMAGE}")

if BACKGROUND_IMAGE.exists():
    try:
        print("⏳ Cargando fondo...")
        bg_img = pygame.image.load(str(BACKGROUND_IMAGE)).convert()
        background_surface = pygame.transform.smoothscale(bg_img, (WIDTH, HEIGHT))
        print("✅ Fondo cargado y optimizado")
    except Exception as e:
        print(f"⚠️ Error cargando fondo: {e}")
        background_surface = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            progress = y / HEIGHT
            r = int(20 + progress * 20)
            g = int(20 + progress * 40)
            b = int(30 + progress * 60)
            pygame.draw.line(background_surface, (r, g, b), (0, y), (WIDTH, y))
else:
    print(f"⚠️ No se encontró fondo.png, usando degradado")
    background_surface = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        progress = y / HEIGHT
        r = int(20 + progress * 20)
        g = int(20 + progress * 40)
        b = int(30 + progress * 60)
        pygame.draw.line(background_surface, (r, g, b), (0, y), (WIDTH, y))

# ==========================================
# 🕹️ INICIALIZAR JOYSTICKS
# ==========================================
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
for j in joysticks: j.init()

# ==========================================
# 🌊 SPLASH SCREEN & LOADING LOOP
# ==========================================
splash_img = None
if SPLASH_IMAGE_PATH.exists():
    try:
        splash_img = pygame.image.load(str(SPLASH_IMAGE_PATH)).convert_alpha()
        splash_img = pygame.transform.smoothscale(splash_img, (WIDTH, HEIGHT))
    except: pass

splash_sfx = None
if SPLASH_SOUND_PATH.exists():
    try:
        splash_sfx = pygame.mixer.Sound(str(SPLASH_SOUND_PATH))
        splash_sfx.set_volume(0.6)
        splash_sfx.play()
    except: pass

loader = threading.Thread(target=load_resources_thread, args=(WIDTH, HEIGHT))
loader.start()

splash_start_time = pygame.time.get_ticks()
splash_active = True
MIN_SPLASH_TIME = 3000
fade_alpha = 0
fade_direction = 1

while splash_active:
    dt = clock.tick(60)
    current_ms = pygame.time.get_ticks()
    elapsed = current_ms - splash_start_time
    
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    if resources_loaded and elapsed > MIN_SPLASH_TIME:
        fade_direction = -1
    
    if fade_direction == 1:
        fade_alpha = min(255, fade_alpha + 5)
    elif fade_direction == -1:
        fade_alpha = max(0, fade_alpha - 5)
        if fade_alpha == 0:
            splash_active = False
    
    screen.fill((0, 0, 0))
    
    if splash_img:
        splash_img.set_alpha(fade_alpha)
        screen.blit(splash_img, (0, 0))
    
    if loading_progress < 100 and fade_direction == 1:
        bar_width = 200
        bar_height = 4
        bar_x = (WIDTH - bar_width) // 2
        bar_y = HEIGHT - 50
        
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        fill_width = int((loading_progress / 100) * bar_width)
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, fill_width, bar_height))

    pygame.display.flip()

# ==========================================
# 🎵 CONFIGURACIÓN POST-CARGA
# ==========================================
current_track_index = 0
music_loaded = False

if MUSIC_TRACKS:
    try:
        pygame.mixer.music.load(MUSIC_TRACKS[current_track_index]["path"])
        pygame.mixer.music.set_volume(0.22)
        pygame.mixer.music.play(-1)
        music_loaded = True
    except Exception as e:
        print(f"⚠️ Error música: {e}")

def next_track():
    global current_track_index, music_loaded
    if not MUSIC_TRACKS: return
    current_track_index = (current_track_index + 1) % len(MUSIC_TRACKS)
    try:
        pygame.mixer.music.load(MUSIC_TRACKS[current_track_index]["path"])
        pygame.mixer.music.play()
    except: pass

def previous_track():
    global current_track_index, music_loaded
    if not MUSIC_TRACKS: return
    current_track_index = (current_track_index - 1) % len(MUSIC_TRACKS)
    try:
        pygame.mixer.music.load(MUSIC_TRACKS[current_track_index]["path"])
        pygame.mixer.music.play()
    except: pass

# ==========================================
# 🎨 FUNCIONES DE DIBUJO
# ==========================================
def draw_game_card(game, position_offset, center_x, center_y):
    dist = abs(position_offset)
    scale_factor = 1.0 / (1.0 + (dist * 1.0))
    alpha = max(0, 255 - int(dist * 100))
    if alpha <= 5: return

    x_spacing_base = 750
    current_spacing = x_spacing_base * scale_factor
    x_pos = center_x + (position_offset * current_spacing)
    y_offset = (dist ** 2) * 80
    y_pos = center_y - y_offset
    
    icon = game["icon_img"]
    iw, ih = icon.get_size()
    scaled_iw = int(iw * scale_factor)
    scaled_ih = int(ih * scale_factor)
    
    if scaled_iw > 1:
        final_icon = pygame.transform.smoothscale(icon, (scaled_iw, scaled_ih))
        radius = 40 if dist < 0.2 else 20
        final_icon = round_image_corners(final_icon, radius)
        final_icon.set_alpha(alpha)
        
        icon_rect = final_icon.get_rect(center=(x_pos, y_pos))
        
        if dist < 1.5:
            shadow = pygame.Surface((scaled_iw + 20, scaled_ih + 20), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=radius+5)
            screen.blit(shadow, (icon_rect.x - 10, icon_rect.y + 10))
        
        screen.blit(final_icon, icon_rect)

        logo = game["logo_img"]
        lw, lh = logo.get_size()
        logo_scale = scale_factor * 1.54
        slw, slh = int(lw * logo_scale), int(lh * logo_scale)
        
        if slw > 1:
            final_logo = pygame.transform.smoothscale(logo, (slw, slh))
            final_logo.set_alpha(alpha)
            
            logo_y = icon_rect.bottom + (scaled_ih * 0.15)
            logo_rect = final_logo.get_rect(center=(x_pos, logo_y))
            
            if dist < 1.0:
                ls = pygame.Surface((slw + 40, slh // 2), pygame.SRCALPHA)
                pygame.draw.ellipse(ls, (0, 0, 0, 160), ls.get_rect())
                screen.blit(ls, (logo_rect.centerx - (slw//2) - 20, logo_rect.centery - 10))

            screen.blit(final_logo, logo_rect)

def draw_creator_button():
    mouse_pos = pygame.mouse.get_pos()
    full_text = f"By {CREATOR_USERNAME}"
    
    # Calculo seguro del ancho
    total_width = 0
    if custom_font:
        total_width = sum([custom_font.render(c, True, (255,255,255)).get_width() for c in full_text])
    else:
        # Fallback si la fuente no cargó
        total_width = 200 
    
    start_x = WIDTH - total_width - 50
    start_y = HEIGHT - 50
    text_rect = pygame.Rect(start_x, start_y - 35, total_width, 45)
    is_hovered = text_rect.collidepoint(mouse_pos)
    
    if custom_font:
        cx = start_x
        for i, char in enumerate(full_text):
            col = MARIO64_COLORS[i % len(MARIO64_COLORS)]
            ls = custom_font.render(char, True, col)
            ss = custom_font.render(char, True, (0,0,0))
            screen.blit(ss, (cx + 3, start_y + 3))
            screen.blit(ls, (cx, start_y + (-5 if is_hovered else 0)))
            cx += ls.get_width()
        
        if is_hovered:
            pygame.draw.line(screen, (255, 255, 255, 200), (start_x, start_y + 40), (start_x + total_width, start_y + 40), 2)
    return text_rect

vinyl_rotation = 0
vinyl_pulse_phase = 0
def draw_music_player():
    global vinyl_rotation, vinyl_pulse_phase
    if not MUSIC_TRACKS or not vinyl_original or not custom_font: return
    
    vinyl_pulse_phase += 0.15
    pulse_scale = 1.0 + (np.sin(vinyl_pulse_phase) * 0.08)
    vinyl_rotation = (vinyl_rotation + VINYL_ROTATION_SPEED) % 360
    
    cs = int(VINYL_SIZE * pulse_scale)
    sv = pygame.transform.smoothscale(vinyl_original, (cs, cs))
    rv = pygame.transform.rotate(sv, vinyl_rotation)
    
    dx, dy = VINYL_MARGIN + VINYL_SIZE // 2, VINYL_MARGIN + VINYL_SIZE // 2
    d_rect = rv.get_rect(center=(dx, dy))
    
    ss = cs + 10
    ssurf = pygame.Surface((ss, ss), pygame.SRCALPHA)
    pygame.draw.circle(ssurf, (0, 0, 0, 100), (ss//2, ss//2), ss//2)
    screen.blit(ssurf, ssurf.get_rect(center=(dx+5, dy+5)))
    screen.blit(rv, d_rect)
    
    track = MUSIC_TRACKS[current_track_index]
    tx, ty = dx + VINYL_SIZE // 2 + 20, dy - 15
    
    # Efecto de borde en texto
    for ox, oy in [(-2,-2),(-2,0),(-2,2),(0,-2),(0,2),(2,-2),(2,0),(2,2)]:
        screen.blit(custom_font.render(track["name"], True, (0,0,0)), (tx+ox, ty+oy))
        screen.blit(custom_font.render(f"{current_track_index+1}/{len(MUSIC_TRACKS)}", True, (0,0,0)), (tx+ox, ty+50+oy))
        
    screen.blit(custom_font.render(track["name"], True, (255,255,255)), (tx, ty))
    screen.blit(custom_font.render(f"{current_track_index+1}/{len(MUSIC_TRACKS)}", True, (255,255,255)), (tx, ty+50))

# ==========================================
# 🚀 SISTEMA DE LANZAMIENTO
# ==========================================
launching = False
launch_start_time = 0
launch_game_data = None
fade_duration = 1000

def start_launch_sequence(game):
    global launching, launch_start_time, launch_game_data, fade_duration
    launching = True
    launch_start_time = pygame.time.get_ticks()
    launch_game_data = game
    
    if music_loaded: pygame.mixer.music.set_volume(0.02)
    
    if game.get("sound_obj"):
        game["sound_obj"].play()
        fade_duration = int(game["sound_obj"].get_length() * 1000)
    else:
        fade_duration = 1500

def execute_game(game):
    try:
        ruta = Path(game["ruta_ejecutable"])
        os.chmod(ruta, 0o755)
        print(f"🚀 Ejecutando: {ruta}")
        
        env = os.environ.copy()
        # Restaurar LD_LIBRARY_PATH si es necesario para evitar conflictos con AppImages
        if 'LD_LIBRARY_PATH_ORIG' in env:
            env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
        elif 'LD_LIBRARY_PATH' in env:
            del env['LD_LIBRARY_PATH']
        
        proc = subprocess.Popen([str(ruta)], cwd=str(ruta.parent), env=env)
        
        def monitor():
            proc.wait()
            if music_loaded: pygame.mixer.music.set_volume(0.22)
            
        threading.Thread(target=monitor, daemon=True).start()
    except Exception as e:
        print(f"❌ Error lanzando: {e}")

# ==========================================
# 🔄 BUCLE PRINCIPAL
# ==========================================
running = True
target_index = 0
visual_index = 0.0
selected_index = 0
last_axis_time = 0
last_music_change_time = 0
b_button_held = False
b_button_start_time = 0
shutdown_fade = 0
creator_button_rect = None  # Inicializado para evitar errores en el primer frame

while running:
    dt = clock.tick(FPS)
    current_time = pygame.time.get_ticks()
    
    for e in pygame.event.get():
        if e.type == pygame.QUIT: running = False
        
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE: running = False
            
            if not launching and GAMES:
                if e.key in [pygame.K_RIGHT, pygame.K_d]:
                    target_index += 1
                    if nav_sound: nav_sound.play()
                elif e.key in [pygame.K_LEFT, pygame.K_a]:
                    target_index -= 1
                    if nav_sound: nav_sound.play()
                elif e.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    start_launch_sequence(GAMES[selected_index])
            
            if current_time - last_music_change_time > 1000:
                if e.key in [pygame.K_DOWN, pygame.K_s]:
                    next_track()
                    last_music_change_time = current_time
                elif e.key in [pygame.K_UP, pygame.K_w]:
                    previous_track()
                    last_music_change_time = current_time
        
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1 and creator_button_rect and creator_button_rect.collidepoint(e.pos):
                webbrowser.open(YOUTUBE_URL)
        
        elif e.type == pygame.JOYBUTTONDOWN:
            if e.button in [0, 7, 9] and not launching and GAMES:
                start_launch_sequence(GAMES[selected_index])
            elif e.button == 1:
                b_button_held = True
                b_button_start_time = current_time
        
        # --- AQUÍ ESTABA EL ERROR ---
        # Corregido: Se usa e.button en lugar de sys.exit()
        elif e.type == pygame.JOYBUTTONUP:
            if e.button == 1:
                b_button_held = False
                shutdown_fade = 0
        
        elif e.type == pygame.JOYHATMOTION:
            if not launching and GAMES:
                if e.value[0] == 1: 
                    target_index += 1
                    if nav_sound: nav_sound.play()
                elif e.value[0] == -1: 
                    target_index -= 1
                    if nav_sound: nav_sound.play()
            
            if current_time - last_music_change_time > 1000:
                if e.value[1] == -1: 
                    next_track()
                    last_music_change_time = current_time
                elif e.value[1] == 1: 
                    previous_track()
                    last_music_change_time = current_time

    if not launching and GAMES:
        for j in joysticks:
            if j.get_numaxes() >= 2:
                ax = j.get_axis(0)
                if abs(ax) > JOYSTICK_DEADZONE and current_time - last_axis_time > 180:
                    target_index += 1 if ax > 0 else -1
                    if nav_sound: nav_sound.play()
                    last_axis_time = current_time
                ay = j.get_axis(1)
                if abs(ay) > JOYSTICK_DEADZONE and current_time - last_music_change_time > 1000:
                    if ay > 0: next_track()
                    else: previous_track()
                    last_music_change_time = current_time

    if GAMES:
        diff = target_index - visual_index
        visual_index = float(target_index) if abs(diff) < 0.005 else visual_index + diff * TRANSITION_SPEED
        selected_index = int(round(visual_index)) % len(GAMES)

    # Lógica del botón B para apagar
    if b_button_held:
        elapsed_hold = current_time - b_button_start_time
        shutdown_fade = min(int((elapsed_hold / 5000) * 255), 255)
        if elapsed_hold >= 5000: running = False
    elif shutdown_fade > 0:
        shutdown_fade = max(0, shutdown_fade - 10)

    # Dibujado
    if background_surface:
        screen.blit(background_surface, (0, 0))
    else:
        screen.fill((20, 20, 30))

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    if GAMES and not launching:
        cx, cy = WIDTH // 2, HEIGHT // 2 - 60
        base_idx = int(round(visual_index))
        frac = visual_index - base_idx
        for off in sorted([-2, -1, 0, 1, 2], key=lambda x: -abs(x - frac)):
            draw_game_card(GAMES[(base_idx + off) % len(GAMES)], off - frac, cx, cy)
    
    draw_music_player()
    creator_button_rect = draw_creator_button()

    if music_loaded and not pygame.mixer.music.get_busy() and not launching:
        next_track()

    if shutdown_fade > 0:
        s_over = pygame.Surface((WIDTH, HEIGHT))
        s_over.fill((0,0,0))
        s_over.set_alpha(shutdown_fade)
        screen.blit(s_over, (0,0))
        if shutdown_fade > 127:
            txt = pygame.font.Font(None, 70).render(f"Cerrando... {int(shutdown_fade/2.55)}%", True, (255,50,50))
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))

    if launching:
        elapsed = current_time - launch_start_time
        prog = min(elapsed / fade_duration, 1.0)
        
        f_surf = pygame.Surface((WIDTH, HEIGHT))
        f_surf.fill((0,0,0))
        f_surf.set_alpha(int(prog * 255))
        screen.blit(f_surf, (0,0))
        
        if prog > 0.2:
            alpha = int(((prog - 0.2) / 0.8) * 255)
            font_big = pygame.font.Font(None, 90)
            txt = font_big.render(f"Iniciando {launch_game_data['nombre']}...", True, (255,255,255))
            txt.set_alpha(alpha)
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))
            
        if elapsed >= fade_duration:
            execute_game(launch_game_data)
            launching = False

    pygame.display.flip()

pygame.quit()
sys.exit()
